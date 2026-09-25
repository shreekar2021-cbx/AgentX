"""Durable development adapter. Never selected in production."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import aiosqlite

from app.core.errors import AppError
from app.schemas.intelligence import CropHealthResult, OutbreakResult, ReportPublic, RiskResult, WeatherResult


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LocalRepository:
    def __init__(self, path: str) -> None:
        self.path = Path(path)

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
            pragma journal_mode=WAL;
            create table if not exists reports (
              id text primary key, owner_id text not null, crop text not null, field text not null, district text not null,
              symptom_description text not null, notes text, latitude real not null, longitude real not null,
              image_blob blob, image_mime text, status text not null, stage text not null,
              possible_problem text, severity text, confidence real, analysis_json text,
              weather_json text, risk_json text, outbreak_json text, nearby_count integer not null default 0,
              nearby_synthetic_count integer not null default 0,
              input_hash text not null, created_at text not null, analysis_started_at text,
              client_mutation_id text,
              is_synthetic integer not null default 0
            );
            create index if not exists reports_owner_time_idx on reports(owner_id,created_at desc);
            create index if not exists reports_crop_issue_time_idx on reports(crop,possible_problem,created_at desc);
            create index if not exists reports_status_idx on reports(status,created_at desc);
            create table if not exists ai_cache (input_hash text primary key, result_json text not null, expires_at text not null);
            create table if not exists weather_cache_local (cache_key text primary key, result_json text not null, expires_at text not null);
            create table if not exists rate_windows (identity text not null, bucket text not null, window_start integer not null, count integer not null, primary key(identity,bucket,window_start));
            """)
            cursor = await db.execute("pragma table_info(reports)")
            columns = {row[1] for row in await cursor.fetchall()}
            if "district" not in columns:
                await db.execute("alter table reports add column district text not null default 'Unknown'")
            if "nearby_synthetic_count" not in columns:
                await db.execute("alter table reports add column nearby_synthetic_count integer not null default 0")
            if "client_mutation_id" not in columns:
                await db.execute("alter table reports add column client_mutation_id text")
            await db.execute("create unique index if not exists reports_mutation_idx on reports(owner_id,client_mutation_id) where client_mutation_id is not null")
            await db.commit()

    @staticmethod
    def _public(row: aiosqlite.Row) -> ReportPublic:
        return ReportPublic(
            id=UUID(row["id"]), crop=row["crop"], field=row["field"], district=row["district"],
            symptom_description=row["symptom_description"], notes=row["notes"],
            latitude=row["latitude"], longitude=row["longitude"], status=row["status"],
            stage=row["stage"], created_at=datetime.fromisoformat(row["created_at"]),
            is_synthetic=bool(row["is_synthetic"]),
            image_url=f"/api/reports/{row['id']}/image" if row["image_blob"] else None,
            crop_health=CropHealthResult.model_validate_json(row["analysis_json"]) if row["analysis_json"] else None,
            weather=WeatherResult.model_validate_json(row["weather_json"]) if row["weather_json"] else None,
            risk=RiskResult.model_validate_json(row["risk_json"]) if row["risk_json"] else None,
            outbreak=OutbreakResult.model_validate_json(row["outbreak_json"]) if row["outbreak_json"] else None,
            nearby_count=row["nearby_count"], nearby_synthetic_count=row["nearby_synthetic_count"],
        )

    async def create_report(self, owner_id: str, crop: str, field: str, district: str, symptoms: str, notes: str | None, latitude: float, longitude: float, image: bytes, image_mime: str, input_hash: str, client_mutation_id: str | None = None, *, is_synthetic: bool = False) -> ReportPublic:
        report_id = str(uuid4())
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            if client_mutation_id:
                cursor = await db.execute("select * from reports where owner_id=? and client_mutation_id=?", (owner_id, client_mutation_id))
                existing = await cursor.fetchone()
                if existing:
                    if existing["input_hash"] != input_hash:
                        raise AppError(409, "idempotency_conflict", "This offline submission identifier belongs to a different report.")
                    return self._public(existing)
            try:
                await db.execute("insert into reports(id,owner_id,crop,field,district,symptom_description,notes,latitude,longitude,image_blob,image_mime,status,stage,input_hash,created_at,client_mutation_id,is_synthetic) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (report_id, owner_id, crop, field, district, symptoms, notes, latitude, longitude, image, image_mime, "submitted", "validated", input_hash, _utcnow().isoformat(), client_mutation_id, int(is_synthetic)))
            except aiosqlite.IntegrityError:
                if not client_mutation_id:
                    raise
                cursor = await db.execute("select * from reports where owner_id=? and client_mutation_id=?", (owner_id, client_mutation_id))
                existing = await cursor.fetchone()
                if existing:
                    if existing["input_hash"] != input_hash:
                        raise AppError(409, "idempotency_conflict", "This offline submission identifier belongs to a different report.")
                    return self._public(existing)
                raise
            await db.commit()
            cursor = await db.execute("select * from reports where id=?", (report_id,))
            return self._public(await cursor.fetchone())

    async def get_report(self, report_id: str, owner_id: str) -> ReportPublic | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("select * from reports where id=? and owner_id=?", (report_id, owner_id))
            row = await cursor.fetchone()
            return self._public(row) if row else None

    async def list_reports(self, owner_id: str, limit: int = 50) -> list[ReportPublic]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("select * from reports where owner_id=? order by created_at desc limit ?", (owner_id, limit))
            return [self._public(row) for row in await cursor.fetchall()]

    async def get_image(self, report_id: str, owner_id: str) -> tuple[bytes, str] | None:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("select image_blob,image_mime from reports where id=? and owner_id=?", (report_id, owner_id))
            row = await cursor.fetchone()
            return (row[0], row[1]) if row and row[0] else None

    async def get_input_hash(self, report_id: str, owner_id: str) -> str | None:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("select input_hash from reports where id=? and owner_id=?", (report_id, owner_id))
            row = await cursor.fetchone()
            return row[0] if row else None

    async def claim_analysis(self, report_id: str, owner_id: str) -> str:
        """Atomic claim across worker processes; stale claims may be recovered."""
        stale_before = (_utcnow() - timedelta(minutes=3)).isoformat()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("update reports set status='processing',stage='starting',analysis_started_at=? where id=? and owner_id=? and (status in ('submitted','failed') or (status='processing' and analysis_started_at<?))", (_utcnow().isoformat(), report_id, owner_id, stale_before))
            await db.commit()
            if cursor.rowcount:
                return "claimed"
            cursor = await db.execute("select status from reports where id=? and owner_id=?", (report_id, owner_id))
            row = await cursor.fetchone()
            return row[0] if row else "missing"

    async def update_stage(self, report_id: str, owner_id: str, stage: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("update reports set stage=? where id=? and owner_id=? and status='processing'", (stage, report_id, owner_id))
            await db.commit()

    async def save_result(self, report_id: str, owner_id: str, crop_health: CropHealthResult, weather: WeatherResult, risk: RiskResult, outbreak: OutbreakResult, nearby_count: int, nearby_synthetic_count: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("update reports set status='completed',stage='complete',possible_problem=?,severity=?,confidence=?,analysis_json=?,weather_json=?,risk_json=?,outbreak_json=?,nearby_count=?,nearby_synthetic_count=? where id=? and owner_id=?", (
                crop_health.finding.possible_problem, crop_health.finding.severity.value, crop_health.finding.confidence,
                crop_health.model_dump_json(), weather.model_dump_json(), risk.model_dump_json(), outbreak.model_dump_json(), nearby_count, nearby_synthetic_count, report_id, owner_id,
            ))
            await db.commit()

    async def mark_failed(self, report_id: str, owner_id: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("update reports set status='failed',stage='failed' where id=? and owner_id=?", (report_id, owner_id))
            await db.commit()

    async def recent_reports(self, crop: str, since: datetime) -> list[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("select id,owner_id,crop,district,latitude,longitude,possible_problem,severity,confidence,created_at,is_synthetic from reports where lower(crop)=lower(?) and status='completed' and created_at>=? and possible_problem is not null", (crop, since.isoformat()))
            return [dict(row) for row in await cursor.fetchall()]

    async def ai_cache_get(self, input_hash: str) -> CropHealthResult | None:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("select result_json from ai_cache where input_hash=? and expires_at>?", (input_hash, _utcnow().isoformat()))
            row = await cursor.fetchone()
            return CropHealthResult.model_validate_json(row[0]) if row else None

    async def ai_cache_put(self, input_hash: str, result: CropHealthResult, ttl_hours: int = 24) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("insert into ai_cache(input_hash,result_json,expires_at) values(?,?,?) on conflict(input_hash) do update set result_json=excluded.result_json,expires_at=excluded.expires_at", (input_hash, result.model_dump_json(), (_utcnow() + timedelta(hours=ttl_hours)).isoformat()))
            await db.commit()

    async def weather_cache_get(self, cache_key: str, allow_stale: bool = False) -> WeatherResult | None:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("select result_json,expires_at from weather_cache_local where cache_key=?", (cache_key,))
            row = await cursor.fetchone()
            if not row or (not allow_stale and row[1] <= _utcnow().isoformat()):
                return None
            result = WeatherResult.model_validate_json(row[0])
            result.stale = row[1] <= _utcnow().isoformat()
            result.source = "CACHED"
            return result

    async def weather_cache_put(self, cache_key: str, result: WeatherResult, ttl_minutes: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("insert into weather_cache_local(cache_key,result_json,expires_at) values(?,?,?) on conflict(cache_key) do update set result_json=excluded.result_json,expires_at=excluded.expires_at", (cache_key, result.model_dump_json(), (_utcnow() + timedelta(minutes=ttl_minutes)).isoformat()))
            await db.commit()

    async def claim_rate(self, identity: str, bucket: str, limit: int, period_seconds: int) -> bool:
        window = int(_utcnow().timestamp()) // period_seconds
        async with aiosqlite.connect(self.path) as db:
            await db.execute("begin immediate")
            await db.execute("delete from rate_windows where identity=? and bucket=? and window_start<?", (identity, bucket, window - 2))
            cursor = await db.execute("select count from rate_windows where identity=? and bucket=? and window_start=?", (identity, bucket, window))
            row = await cursor.fetchone()
            if row and row[0] >= limit:
                await db.rollback()
                return False
            await db.execute("insert into rate_windows(identity,bucket,window_start,count) values(?,?,?,1) on conflict(identity,bucket,window_start) do update set count=count+1", (identity, bucket, window))
            await db.commit()
            return True

    async def seed_synthetic(self, records: list[dict]) -> int:
        async with aiosqlite.connect(self.path) as db:
            for row in records:
                await db.execute("insert into reports(id,owner_id,crop,field,district,symptom_description,notes,latitude,longitude,status,stage,possible_problem,severity,confidence,input_hash,created_at,is_synthetic) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1) on conflict(id) do update set created_at=excluded.created_at where reports.is_synthetic=1", (
                    row["id"], row["owner_id"], row["crop"], row["field"], row["district"], row["symptom_description"], None,
                    row["latitude"], row["longitude"], "completed", "complete", row["possible_problem"],
                    row["severity"], row["confidence"], row["id"], row["created_at"],
                ))
            await db.commit()
            return len(records)
