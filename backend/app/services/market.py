"""Market price source selection and one normalized API result."""

import base64
import binascii
from datetime import datetime, timedelta
import logging
from uuid import UUID

from app.adapters.market import DataGovMarketAdapter
from app.repositories.market import SupabaseMarketRepository
from app.repositories.market_csv import CsvMarketRepository
from app.schemas.common import ApiWarning
from app.schemas.market import (
    MarketCommodity,
    MarketHistoryResult,
    MarketPrice,
    MarketPriceView,
    MarketPricesResult,
    MarketQuery,
    market_today,
)

logger = logging.getLogger("agrivision.market")


def encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(f"v1:{offset}".encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> int:
    try:
        value = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        version, offset = value.split(":", 1)
        if version != "v1" or not offset.isdecimal() or int(offset) > 10000:
            raise ValueError
        return int(offset)
    except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
        raise ValueError("Invalid market cursor") from exc


class MarketService:
    def __init__(
        self, live: DataGovMarketAdapter | None,
        cached: SupabaseMarketRepository | None,
        fallback: CsvMarketRepository,
    ) -> None:
        self._live, self._cached, self._fallback = live, cached, fallback

    async def get_commodities(self) -> tuple[list[MarketCommodity], str]:
        if self._cached is not None:
            try:
                rows = await self._cached.get_commodities()
                if rows:
                    return rows, "supabase"
            except Exception:
                logger.warning("market_commodity_list_failed")
        try:
            return await self._fallback.get_commodities(), "local_csv"
        except Exception:
            logger.warning("market_csv_commodity_list_failed")
            return [], "unavailable"

    async def get_history(
        self,
        commodity_id: UUID,
        *,
        days: int = 30,
        mandi_id: UUID | None = None,
        variety: str | None = None,
        grade: str | None = None,
    ) -> tuple[MarketHistoryResult, str, list[ApiWarning], datetime | None]:
        from_date = market_today() - timedelta(days=days - 1)
        warnings: list[ApiWarning] = []
        if self._cached is not None:
            try:
                rows = await self._cached.get_history(
                    commodity_id, from_date, mandi_id=mandi_id, variety=variety, grade=grade
                )
                if rows:
                    result = self._history_result("CACHED", days, rows)
                    return result, "supabase", warnings, max(row.fetched_at for row in rows)
            except Exception:
                logger.warning("market_history_cache_failed")
                warnings.append(ApiWarning(code="market_history_cache_unavailable", message="Stored price history is unavailable."))
        try:
            rows = await self._fallback.get_history(
                commodity_id, from_date, mandi_id=mandi_id, variety=variety, grade=grade
            )
            if rows:
                result = self._history_result("FALLBACK", days, rows)
                return result, "local_csv", warnings, max(row.fetched_at for row in rows)
        except Exception:
            logger.warning("market_history_csv_failed")
            warnings.append(ApiWarning(code="market_history_fallback_unavailable", message="Local price history is unavailable."))
        warnings.append(ApiWarning(code="market_history_empty", message="No stored price observations are available for this period."))
        return MarketHistoryResult(source_status="FALLBACK", days=days, prices=[], as_of=None), "local_csv", warnings, None

    @staticmethod
    def _history_result(status: str, days: int, rows: list[MarketPrice]) -> MarketHistoryResult:
        return MarketHistoryResult(
            source_status=status,
            days=days,
            prices=[MarketPriceView.from_price(row) for row in rows],
            as_of=max(row.price_date for row in rows),
        )

    async def get_prices(self, query: MarketQuery) -> tuple[MarketPricesResult | None, str, list[ApiWarning], datetime | None]:
        warnings: list[ApiWarning] = []
        commodity = None
        if self._cached is not None:
            try:
                commodity = await self._cached.get_commodity(query.commodity_id)
            except Exception:
                logger.warning("market_commodity_lookup_failed")
                warnings.append(ApiWarning(code="market_cache_unavailable", message="Stored market data is unavailable."))
        if commodity is None:
            try:
                commodity = await self._fallback.get_commodity(query.commodity_id)
            except Exception:
                logger.warning("market_csv_lookup_failed")

        if self._live is not None and commodity is not None:
            try:
                rows, has_more = await self._live.fetch_prices(query, commodity)
                if self._cached is not None:
                    try:
                        await self._cached.save_prices(rows)
                    except Exception:
                        logger.warning("market_cache_write_failed")
                        warnings.append(ApiWarning(code="market_cache_write_failed", message="Live prices could not be saved to Supabase."))
                    try:
                        details = await self._cached.get_mandi_details(
                            [row.provider_key for row in rows]
                        )
                        rows = [row.model_copy(update={
                            "mandi_id": details[row.provider_key]["id"],
                            "mandi_latitude": details[row.provider_key]["latitude"],
                            "mandi_longitude": details[row.provider_key]["longitude"],
                        }) if row.provider_key in details else row for row in rows]
                    except Exception:
                        logger.warning("market_mandi_location_lookup_failed")
                try:
                    await self._fallback.save_prices(rows)
                except Exception:
                    logger.warning("market_csv_write_failed")
                    warnings.append(ApiWarning(code="market_csv_write_failed", message="Live prices could not be saved locally."))
                return self._result("LIVE", rows, query, has_more), "data.gov.in/AGMARKNET", warnings, max(r.fetched_at for r in rows)
            except Exception:
                logger.warning("market_live_unavailable")
                warnings.append(ApiWarning(code="market_live_unavailable", message="Live AGMARKNET prices are unavailable."))
        else:
            warnings.append(ApiWarning(code="market_live_unconfigured", message="Live market feed is not configured or the commodity is unknown."))

        if self._cached is not None:
            try:
                rows, has_more = await self._cached.get_prices(query)
                if rows:
                    return self._result("CACHED", rows, query, has_more), "supabase", warnings, max(r.fetched_at for r in rows)
            except Exception:
                logger.warning("market_cache_read_failed")
                warnings.append(ApiWarning(code="market_cache_unavailable", message="Stored market data is unavailable."))

        try:
            rows, has_more = await self._fallback.get_prices(query)
            if rows:
                warnings.append(ApiWarning(code="market_local_fallback", message="Showing a local price snapshot; check each observation date before use."))
                return self._result("FALLBACK", rows, query, has_more), "local_csv", warnings, max(r.fetched_at for r in rows)
        except Exception:
            logger.warning("market_csv_read_failed")
            warnings.append(ApiWarning(code="market_csv_unavailable", message="Local market prices are unavailable."))
        return None, "unavailable", warnings, None

    @staticmethod
    def _result(status: str, rows: list[MarketPrice], query: MarketQuery, has_more: bool) -> MarketPricesResult:
        return MarketPricesResult(
            source_status=status,
            prices=[MarketPriceView.from_price(row) for row in rows],
            as_of=max(row.price_date for row in rows),
            is_stale=all(row.stale_by_date for row in rows),
            next_cursor=encode_cursor(query.offset + query.limit) if has_more else None,
        )
