"""Export safe static crop knowledge for the PWA app shell."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.knowledge.catalog import CATALOG_VERSION, CROPS, ISSUES  # noqa: E402


def main() -> None:
    output = ROOT / "public" / "knowledge" / "essential-crops.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": CATALOG_VERSION,
        "source": "CURATED STATIC KNOWLEDGE",
        "notice": "Offline field reference only. This is not a diagnosis or live local advisory.",
        "crops": [
            {"name": crop.name, "stages": crop.stages, "seasons": crop.seasons,
             "issues": [{"name": issue.name, "symptoms": issue.symptoms, "monitoring": issue.monitoring} for issue in ISSUES if issue.crop == key]}
            for key, crop in CROPS.items()
        ],
    }
    output.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Exported {len(data['crops'])} crops to {output}")


if __name__ == "__main__":
    main()
