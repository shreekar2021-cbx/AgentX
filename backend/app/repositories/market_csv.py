"""Bounded local snapshot for price fallback when live and database reads fail."""

import asyncio
import csv
from datetime import date
import os
from pathlib import Path
import tempfile
from uuid import UUID

from pydantic import ValidationError

from app.schemas.market import CommodityIdentity, MarketCommodity, MarketPrice, MarketQuery, market_today

CSV_COLUMNS = (
    "commodity_id", "commodity_code", "mandi_id", "provider_key", "market_name",
    "district", "state", "variety_code", "grade", "min_price", "max_price",
    "modal_price", "currency", "unit", "price_date", "source",
    "source_record_id", "fetched_at", "original_unit",
)
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_ROWS = 10000


class CsvMarketRepository:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._write_lock = asyncio.Lock()

    def _read(self) -> list[MarketPrice]:
        if not self._path.is_file():
            return []
        if self._path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("Local market CSV exceeds size limit")
        rows = []
        with self._path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not set(CSV_COLUMNS).issubset(reader.fieldnames):
                raise ValueError("Local market CSV has an invalid header")
            for record in reader:
                if len(rows) >= MAX_ROWS:
                    break
                try:
                    rows.append(MarketPrice.model_validate({
                        **record,
                        "mandi_id": record["mandi_id"] or None,
                        "district": record["district"] or None,
                        "source_record_id": record["source_record_id"] or None,
                        "original_unit": record["original_unit"] or None,
                    }))
                except (ValidationError, ValueError, TypeError):
                    continue
        return rows

    async def get_commodity(self, commodity_id: UUID) -> CommodityIdentity | None:
        rows = await asyncio.wait_for(asyncio.to_thread(self._read), timeout=2)
        for row in rows:
            if row.commodity_id == commodity_id:
                return CommodityIdentity(
                    id=commodity_id, code=row.commodity_code,
                    name_en=row.commodity_code.replace("_", " ").title(),
                )
        return None

    async def get_commodities(self) -> list[MarketCommodity]:
        rows = await asyncio.wait_for(asyncio.to_thread(self._read), timeout=2)
        commodities = {
            row.commodity_id: MarketCommodity(
                id=row.commodity_id,
                code=row.commodity_code,
                name_en=row.commodity_code.replace("_", " ").title(),
            )
            for row in rows
        }
        return sorted(commodities.values(), key=lambda item: item.name_en.casefold())

    async def get_history(
        self,
        commodity_id: UUID,
        from_date: date,
        *,
        mandi_id: UUID | None = None,
        variety: str | None = None,
        grade: str | None = None,
    ) -> list[MarketPrice]:
        rows = await asyncio.wait_for(asyncio.to_thread(self._read), timeout=2)
        rows = [row for row in rows if (
            row.commodity_id == commodity_id
            and row.price_date >= from_date
            and row.price_date <= market_today()
            and (mandi_id is None or row.mandi_id == mandi_id)
            and (variety is None or row.variety_code.casefold() == variety.casefold())
            and (grade is None or row.grade.casefold() == grade.casefold())
        )]
        return sorted(rows, key=lambda row: (row.price_date, row.fetched_at), reverse=True)[:1000]

    async def get_prices(self, query: MarketQuery) -> tuple[list[MarketPrice], bool]:
        rows = await asyncio.wait_for(asyncio.to_thread(self._read), timeout=2)
        rows = [row for row in rows if (
            row.commodity_id == query.commodity_id
            and row.state.casefold() == query.state.casefold()
            and (not query.district or (row.district or "").casefold() == query.district.casefold())
            and (not query.variety or row.variety_code.casefold() == query.variety.casefold())
        )]
        rows.sort(key=lambda row: (row.price_date, row.fetched_at), reverse=True)
        page = rows[query.offset:query.offset + query.limit + 1]
        return page[:query.limit], len(page) > query.limit

    async def save_prices(self, prices: list[MarketPrice]) -> None:
        async with self._write_lock:
            await asyncio.wait_for(asyncio.to_thread(self._save, prices), timeout=2)

    def _save(self, prices: list[MarketPrice]) -> None:
        existing = self._read()
        keyed = {
            (str(row.commodity_id), row.provider_key, row.variety_code, row.grade,
             row.price_date, row.source): row for row in existing
        }
        for row in prices:
            keyed[(str(row.commodity_id), row.provider_key, row.variety_code, row.grade,
                   row.price_date, row.source)] = row
        retained = sorted(keyed.values(), key=lambda row: (row.price_date, row.fetched_at), reverse=True)[:MAX_ROWS]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", newline="", dir=self._path.parent,
                prefix="market_", suffix=".tmp", delete=False,
            ) as handle:
                temporary = Path(handle.name)
                writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
                writer.writeheader()
                for row in retained:
                    data = row.model_dump(mode="json")
                    writer.writerow({column: data.get(column) or "" for column in CSV_COLUMNS})
            os.replace(temporary, self._path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
