"""Deterministic synthetic network used only by local development adapters."""

import random
from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_DNS, uuid5

from app.knowledge.catalog import CROPS, RAW_ISSUES

SEED = 260926
CLUSTERS = (
    ("Shamshabad", "Rangareddy", 17.2517, 78.3893, "cotton", "Whitefly activity"),
    ("Medchal", "Medchal", 17.6300, 78.4800, "paddy", "Rice blast"),
    ("Warangal", "Warangal", 17.9689, 79.5941, "chilli", "Thrips injury"),
    ("Nizamabad", "Nizamabad", 18.6725, 78.0941, "turmeric", "Rhizome rot"),
    ("Karimnagar", "Karimnagar", 18.4386, 79.1288, "maize", "Fall armyworm"),
    ("Khammam", "Khammam", 17.2473, 80.1514, "cotton", "Pink bollworm"),
    ("Mahbubnagar", "Mahbubnagar", 16.7488, 77.9850, "groundnut", "Tikka leaf spot"),
    ("Adilabad", "Adilabad", 19.6641, 78.5320, "soybean", "Soybean rust"),
)


def generate_demo_data(seed: int = SEED, as_of: datetime | None = None) -> dict:
    rng = random.Random(seed)
    anchor = as_of or datetime(2026, 9, 26, 8, 0, tzinfo=timezone.utc)
    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=timezone.utc)
    farmers: list[dict] = []
    farms: list[dict] = []
    reports: list[dict] = []
    clusters: list[dict] = []
    for cluster_index, (village, district, lat, lon, primary_crop, issue) in enumerate(CLUSTERS):
        cluster_report_ids = []
        for farmer_index in range(24):
            user_id = str(uuid5(NAMESPACE_DNS, f"agrivision-demo-user-{cluster_index}-{farmer_index}"))
            farm_id = str(uuid5(NAMESPACE_DNS, f"agrivision-demo-farm-{cluster_index}-{farmer_index}"))
            farmer_lat = round(lat + rng.uniform(-0.035, 0.035), 6)
            farmer_lon = round(lon + rng.uniform(-0.035, 0.035), 6)
            farmers.append({"id": user_id, "display_name": f"Synthetic Farmer {len(farmers) + 1:03d}", "district": district, "is_synthetic": True})
            farms.append({"id": farm_id, "owner_id": user_id, "name": f"Synthetic Farm {len(farms) + 1:03d}", "village": village, "district": district, "latitude": farmer_lat, "longitude": farmer_lon, "area_acres": round(rng.uniform(1.5, 12), 1), "is_synthetic": True})
            for report_index in range(2):
                crop = primary_crop if report_index == 0 or farmer_index < 8 else rng.choice(list(CROPS))
                issue_row = next((row for row in RAW_ISSUES[crop] if row[0] == issue), None) if crop == primary_crop else None
                issue_row = issue_row or rng.choice(RAW_ISSUES[crop])
                problem, _, symptom_phrases, _, _ = issue_row
                report_id = str(uuid5(NAMESPACE_DNS, f"agrivision-demo-report-{cluster_index}-{farmer_index}-{report_index}"))
                recent_hours = rng.randint(2, 110) if crop == primary_crop else rng.randint(24, 300)
                created_at = (anchor - timedelta(hours=recent_hours)).isoformat()
                severity = rng.choice(["low", "moderate", "moderate", "high"])
                reports.append({
                    "id": report_id, "owner_id": user_id, "farm_id": farm_id, "crop": crop.title(),
                    "field": f"Plot {report_index + 1}", "district": district, "symptom_description": symptom_phrases.split(";")[0].strip(),
                    "latitude": round(farmer_lat + rng.uniform(-0.003, 0.003), 6),
                    "longitude": round(farmer_lon + rng.uniform(-0.003, 0.003), 6),
                    "possible_problem": problem, "severity": severity,
                    "confidence": round(rng.uniform(0.69, 0.91), 2), "created_at": created_at,
                    "is_synthetic": True,
                })
                if crop == primary_crop and problem == issue:
                    cluster_report_ids.append(report_id)
        clusters.append({"id": str(uuid5(NAMESPACE_DNS, f"agrivision-demo-cluster-{cluster_index}")), "district": district, "crop": primary_crop.title(), "possible_problem": issue, "center": {"latitude": lat, "longitude": lon}, "report_ids": cluster_report_ids, "is_synthetic": True})
    return {"metadata": {"seed": seed, "as_of": anchor.isoformat(), "is_synthetic": True, "purpose": "development demonstration only"}, "crops": [{"name": crop.name, "stages": crop.stages, "seasons": crop.seasons, "is_synthetic": False} for crop in CROPS.values()], "farmers": farmers, "farms": farms, "reports": reports, "geographic_clusters": clusters, "outbreak_scenarios": [{"cluster_id": cluster["id"], "crop": cluster["crop"], "possible_problem": cluster["possible_problem"], "is_synthetic": True} for cluster in clusters]}
