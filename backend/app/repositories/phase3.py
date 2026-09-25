"""Phase 3 owner-scoped local persistence; production still requires an RLS adapter."""

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from uuid import NAMESPACE_DNS, uuid5

import aiosqlite

from app.repositories.local import LocalRepository


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Phase3LocalRepository(LocalRepository):
    async def initialize(self) -> None:
        await super().initialize()
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
            create table if not exists farm_profiles (
              owner_id text primary key, profile_json text not null, updated_at text not null
            );
            create table if not exists crop_portfolio (
              id text primary key, owner_id text not null, crop text not null,
              field text not null, details_json text not null, created_at text not null, updated_at text not null
            );
            create index if not exists portfolio_owner_idx on crop_portfolio(owner_id,updated_at desc);
            create table if not exists app_notifications (
              id text primary key, owner_id text not null, kind text not null,
              title text not null, body text not null, target_url text,
              created_at text not null, read_at text
            );
            create index if not exists notifications_owner_idx on app_notifications(owner_id,created_at desc);
            create table if not exists market_cache (
              cache_key text primary key, result_json text not null, expires_at text not null, updated_at text not null
            );
            create table if not exists provider_events (
              provider text primary key, state text not null, observed_at text not null, detail text
            );
            create table if not exists demo_farmers (id text primary key, display_name text not null, district text not null);
            create table if not exists demo_farms (id text primary key, owner_id text not null, name text not null, district text not null, latitude real not null, longitude real not null);
            create table if not exists demo_clusters (id text primary key, crop text not null, possible_problem text not null, district text not null, latitude real not null, longitude real not null, report_count integer not null);
            """)
            cursor = await db.execute("pragma table_info(app_notifications)")
            if "is_synthetic" not in {row[1] for row in await cursor.fetchall()}:
                await db.execute("alter table app_notifications add column is_synthetic integer not null default 0")
            await db.commit()

    async def seed_demo_workspace(self, data: dict, owner_id: str) -> None:
        """Idempotent, fixed-seed sample data. Never overwrites a farmer's edits."""
        await self.seed_synthetic(data["reports"])
        async with aiosqlite.connect(self.path) as db:
            for farmer in data["farmers"]:
                await db.execute("insert or ignore into demo_farmers values(?,?,?)", (farmer["id"], farmer["display_name"], farmer["district"]))
            for farm in data["farms"]:
                await db.execute("insert or ignore into demo_farms values(?,?,?,?,?,?)", (farm["id"], farm["owner_id"], farm["name"], farm["district"], farm["latitude"], farm["longitude"]))
            for cluster in data["geographic_clusters"]:
                district = next(row["district"] for row in data["reports"] if row["id"] in cluster["report_ids"])
                await db.execute("insert into demo_clusters values(?,?,?,?,?,?,?) on conflict(id) do update set report_count=excluded.report_count", (cluster["id"], cluster["crop"], cluster["possible_problem"], district, cluster["center"]["latitude"], cluster["center"]["longitude"], len(cluster["report_ids"])))
            cursor = await db.execute("select 1 from farm_profiles where owner_id=?", (owner_id,))
            if not await cursor.fetchone():
                profile = {"farm_name": "Synthetic demo farm", "village": "Shamshabad", "district": "Rangareddy", "latitude": 17.2517, "longitude": 78.3893, "area_acres": 12.4, "crop": "Cotton", "season": "kharif", "soil_type": "loam", "soil_ph": 7.1, "nitrogen_kg_ha": 270, "lab_status": {"N": "low"}, "irrigation": "rainfed", "is_synthetic": True}
                await db.execute("insert into farm_profiles values(?,?,?)", (owner_id, json.dumps(profile), now()))
            cursor = await db.execute("select 1 from crop_portfolio where owner_id=? limit 1", (owner_id,))
            if not await cursor.fetchone():
                for crop, field, area, status in (("Cotton", "North Field", 5.2, "watch"), ("Paddy", "East Plot", 4.1, "healthy"), ("Maize", "South Field", 3.1, "unknown")):
                    details = {"crop": crop, "field": field, "area_acres": area, "season": "kharif", "health_status": status, "next_action": "Synthetic demo entry; add real field observations to update guidance.", "is_synthetic": True}
                    await db.execute("insert into crop_portfolio values(?,?,?,?,?,?,?)", (str(uuid5(NAMESPACE_DNS, f"agrivision-demo-portfolio-{crop}")), owner_id, crop, field, json.dumps(details), now(), now()))
            sample_id = str(uuid5(NAMESPACE_DNS, "agrivision-demo-workspace-report"))
            from app.knowledge.catalog import local_finding
            from app.schemas.intelligence import AIStatus, CropHealthResult, RiskResult, WeatherResult
            finding, reference = local_finding("Cotton", "White insects are visible beneath cotton leaves")
            analysis = CropHealthResult(finding=finding, source=AIStatus.LOCAL_KNOWLEDGE, image_assessed=False, knowledge_ref=reference, analyzed_at=datetime.now(timezone.utc), limitation="Synthetic sample: text-only knowledge; no image was analyzed.")
            weather = WeatherResult(latitude=17.2517, longitude=78.3893, source="LOCAL KNOWLEDGE", stale=True)
            risk = RiskResult(individual_risk=30, community_risk=0, risk_factors=["Synthetic sample; no live weather or field assessment"], recommended_monitoring=["Inspect the field and verify with an agronomist."])
            await db.execute("insert or ignore into reports(id,owner_id,crop,field,district,symptom_description,notes,latitude,longitude,status,stage,possible_problem,severity,confidence,analysis_json,weather_json,risk_json,input_hash,created_at,is_synthetic) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)", (sample_id, owner_id, "Cotton", "Demo North Field", "Rangareddy", "White insects are visible beneath cotton leaves", "Synthetic sample observation", 17.2517, 78.3893, "completed", "complete", finding.possible_problem, finding.severity.value, finding.confidence, analysis.model_dump_json(), weather.model_dump_json(), risk.model_dump_json(), sample_id, data["metadata"]["as_of"]))
            for kind, title, body, target in (("demo_cluster", "Synthetic cotton cluster", "Synthetic development reports suggest a possible whitefly cluster near Shamshabad. These are not real farmer observations.", "/alerts"), ("demo_report", "Sample report ready", "A synthetic text-only crop report is ready to explore.", f"/result/{sample_id}")):
                identifier = str(uuid5(NAMESPACE_DNS, f"agrivision-demo-notification-{kind}"))
                await db.execute("insert or ignore into app_notifications(id,owner_id,kind,title,body,target_url,created_at,is_synthetic) values(?,?,?,?,?,?,?,1)", (identifier, owner_id, kind, title, body, target, data["metadata"]["as_of"]))
            await db.commit()

    async def demo_overview(self) -> dict:
        async with aiosqlite.connect(self.path) as db:
            counts = {}
            for name, table in (("farmers", "demo_farmers"), ("farms", "demo_farms"), ("reports", "reports"), ("clusters", "demo_clusters"), ("notifications", "app_notifications")):
                cursor = await db.execute(f"select count(*) from {table}")
                counts[name] = (await cursor.fetchone())[0]
            cursor = await db.execute("select crop,count(*) from reports where is_synthetic=1 group by crop order by count(*) desc limit 8")
            crops = [{"crop": row[0], "count": row[1]} for row in await cursor.fetchall()]
            cursor = await db.execute("select id,crop,possible_problem,district,latitude,longitude,report_count from demo_clusters order by report_count desc")
            clusters = [{"id": row[0], "crop": row[1], "possible_problem": row[2], "district": row[3], "latitude": row[4], "longitude": row[5], "report_count": row[6], "is_synthetic": True} for row in await cursor.fetchall()]
            return {"source": "SYNTHETIC DEMO NETWORK", "counts": counts, "crops": crops, "clusters": clusters}

    async def get_farm_profile(self, owner_id: str) -> dict | None:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("select profile_json,updated_at from farm_profiles where owner_id=?", (owner_id,))
            row = await cursor.fetchone()
            return {**json.loads(row[0]), "updated_at": row[1]} if row else None

    async def save_farm_profile(self, owner_id: str, profile: dict) -> dict:
        timestamp = now()
        async with aiosqlite.connect(self.path) as db:
            await db.execute("insert into farm_profiles(owner_id,profile_json,updated_at) values(?,?,?) on conflict(owner_id) do update set profile_json=excluded.profile_json,updated_at=excluded.updated_at", (owner_id, json.dumps(profile), timestamp))
            await db.commit()
        return {**profile, "updated_at": timestamp}

    async def list_portfolio(self, owner_id: str) -> list[dict]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("select id,details_json,created_at,updated_at from crop_portfolio where owner_id=? order by updated_at desc", (owner_id,))
            return [{**json.loads(row[1]), "id": row[0], "created_at": row[2], "updated_at": row[3]} for row in await cursor.fetchall()]

    async def save_crop(self, owner_id: str, details: dict, crop_id: str | None = None) -> dict:
        identifier = crop_id or str(uuid4())
        timestamp = now()
        async with aiosqlite.connect(self.path) as db:
            if crop_id:
                cursor = await db.execute("update crop_portfolio set crop=?,field=?,details_json=?,updated_at=? where id=? and owner_id=?", (details["crop"], details["field"], json.dumps(details), timestamp, identifier, owner_id))
                if cursor.rowcount == 0:
                    await db.rollback()
                    raise KeyError("crop_not_found")
                cursor = await db.execute("select created_at from crop_portfolio where id=? and owner_id=?", (identifier, owner_id))
                created_at = (await cursor.fetchone())[0]
            else:
                created_at = timestamp
                await db.execute("insert into crop_portfolio(id,owner_id,crop,field,details_json,created_at,updated_at) values(?,?,?,?,?,?,?)", (identifier, owner_id, details["crop"], details["field"], json.dumps(details), created_at, timestamp))
            await db.commit()
        return {**details, "id": identifier, "created_at": created_at, "updated_at": timestamp}

    async def delete_crop(self, owner_id: str, crop_id: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("delete from crop_portfolio where id=? and owner_id=?", (crop_id, owner_id))
            await db.commit()
            return cursor.rowcount > 0

    async def add_notification(self, owner_id: str, kind: str, title: str, body: str, target_url: str | None = None) -> dict:
        item = {"id": str(uuid4()), "kind": kind, "title": title, "body": body, "target_url": target_url, "created_at": now(), "read_at": None, "is_synthetic": False}
        async with aiosqlite.connect(self.path) as db:
            await db.execute("insert into app_notifications(id,owner_id,kind,title,body,target_url,created_at) values(?,?,?,?,?,?,?)", (item["id"], owner_id, kind, title, body, target_url, item["created_at"]))
            await db.commit()
        return item

    async def list_notifications(self, owner_id: str, limit: int = 50) -> list[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("select id,kind,title,body,target_url,created_at,read_at,is_synthetic from app_notifications where owner_id=? order by created_at desc limit ?", (owner_id, limit))
            return [dict(row) for row in await cursor.fetchall()]

    async def mark_notification_read(self, owner_id: str, notification_id: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("update app_notifications set read_at=coalesce(read_at,?) where id=? and owner_id=?", (now(), notification_id, owner_id))
            await db.commit()
            return cursor.rowcount > 0

    async def get_notification(self, owner_id: str, notification_id: str) -> dict | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("select id,kind,title,body,target_url,created_at,read_at,is_synthetic from app_notifications where id=? and owner_id=?", (notification_id, owner_id))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def market_cache_get(self, key: str, allow_stale: bool = False) -> tuple[dict, bool] | None:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("select result_json,expires_at from market_cache where cache_key=?", (key,))
            row = await cursor.fetchone()
            if not row:
                return None
            stale = row[1] <= now()
            return (json.loads(row[0]), stale) if allow_stale or not stale else None

    async def market_cache_put(self, key: str, data: dict, ttl_minutes: int) -> None:
        timestamp = now()
        expires = (datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)).isoformat()
        async with aiosqlite.connect(self.path) as db:
            await db.execute("insert into market_cache(cache_key,result_json,expires_at,updated_at) values(?,?,?,?) on conflict(cache_key) do update set result_json=excluded.result_json,expires_at=excluded.expires_at,updated_at=excluded.updated_at", (key, json.dumps(data), expires, timestamp))
            await db.commit()

    async def record_provider(self, provider: str, state: str, detail: str | None = None) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("insert into provider_events(provider,state,observed_at,detail) values(?,?,?,?) on conflict(provider) do update set state=excluded.state,observed_at=excluded.observed_at,detail=excluded.detail", (provider, state, now(), detail))
            await db.commit()

    async def provider_events(self) -> dict[str, dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("select provider,state,observed_at,detail from provider_events")
            return {row["provider"]: dict(row) for row in await cursor.fetchall()}
