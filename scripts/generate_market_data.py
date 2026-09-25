"""Generate fixed, dated, explicitly synthetic mandi examples for offline demos."""

import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 260927
END_DATE = date(2026, 8, 31)
MANDIS = [
    ("Bowenpally", "Hyderabad", 17.45, 78.47),
    ("Gudimalkapur", "Hyderabad", 17.38, 78.43),
    ("Shamshabad", "Rangareddy", 17.25, 78.39),
    ("Medchal", "Medchal", 17.63, 78.48),
    ("Warangal", "Warangal", 17.97, 79.59),
    ("Karimnagar", "Karimnagar", 18.44, 79.13),
    ("Nizamabad", "Nizamabad", 18.67, 78.09),
    ("Khammam", "Khammam", 17.25, 80.15),
    ("Mahbubnagar", "Mahbubnagar", 16.75, 77.99),
    ("Adilabad", "Adilabad", 19.66, 78.53),
]
COMMODITIES = ["Cotton", "Paddy", "Maize", "Chilli", "Tomato", "Groundnut", "Red gram", "Green gram", "Black gram", "Soybean", "Turmeric", "Onion", "Potato", "Wheat", "Sorghum", "Pearl millet"]


def generate(seed: int = SEED) -> dict:
    rng = random.Random(seed)
    records = []
    for commodity_index, commodity in enumerate(COMMODITIES):
        # Arbitrary demo baseline. It is never represented as an observed mandi price.
        baseline = 1200 + commodity_index * 325
        for mandi_index, (mandi, district, latitude, longitude) in enumerate(MANDIS):
            series_base = baseline + mandi_index * 33
            drift = rng.uniform(-5, 5)
            for day in range(30):
                modal = round(max(100, series_base + drift * day + rng.uniform(-55, 55)))
                spread = round(80 + rng.uniform(10, 95))
                records.append({
                    "commodity": commodity, "variety": "Unspecified demo variety", "state": "Telangana",
                    "district": district, "mandi": mandi, "min_price": max(1, modal - spread),
                    "max_price": modal + spread, "modal_price": modal,
                    "date": (END_DATE - timedelta(days=29 - day)).isoformat(),
                    "latitude": latitude, "longitude": longitude,
                    "source": "FALLBACK", "is_synthetic": True,
                    "provenance": "AgriVision fixed-seed synthetic market demonstration; not an official mandi quote",
                })
    return {"metadata": {"seed": seed, "last_date": END_DATE.isoformat(), "is_synthetic": True, "provenance": "Synthetic demonstration only; no official prices imported"}, "records": records}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("backend/app/knowledge/market_demo.json"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    data = generate()
    args.output.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(data['records'])} synthetic dated market observations to {args.output}")


if __name__ == "__main__":
    main()
