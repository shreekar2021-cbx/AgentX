"""Write reproducible, explicitly synthetic Phase 2 development data."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.knowledge.demo_generator import SEED, generate_demo_data  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--as-of", type=datetime.fromisoformat, default=datetime.fromisoformat("2026-09-26T08:00:00+00:00"))
    parser.add_argument("--output", type=Path, default=Path("backend/.data/demo_data.json"))
    args = parser.parse_args()
    data = generate_demo_data(args.seed, args.as_of)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote {len(data['farmers'])} synthetic farmers, {len(data['farms'])} farms, {len(data['reports'])} reports, and {len(data['geographic_clusters'])} clusters to {args.output}")


if __name__ == "__main__":
    main()
