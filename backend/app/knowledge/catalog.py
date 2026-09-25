"""Curated, non-diagnostic field knowledge. These are not official live observations."""

import re
from dataclasses import dataclass

from app.schemas.intelligence import CropHealthFinding, Severity, SpreadPotential

TNAU_IPM_INDEX = "https://agritech.tnau.ac.in/crop_protection/crop_prot_ipm.html"
ICAR_ADVISORY = "https://www.icar.gov.in/sites/default/files/2025-10/ICAR-En-Kharif-Agro-Advisories-for-Farmers-2025.pdf"
CATALOG_VERSION = "2026-09-26"


@dataclass(frozen=True)
class CropKnowledge:
    name: str
    stages: tuple[str, ...]
    seasons: tuple[str, ...]
    weather_sensitivity: tuple[str, ...]


@dataclass(frozen=True)
class KnowledgeIssue:
    crop: str
    name: str
    kind: str
    symptoms: tuple[str, ...]
    weather_sensitivity: tuple[str, ...]
    spread_potential: SpreadPotential
    prevention: tuple[str, ...]
    monitoring: tuple[str, ...]
    provenance: str = "AgriVision curated static knowledge; field verification required"
    reference_url: str = TNAU_IPM_INDEX
    reviewed_at: str = CATALOG_VERSION
    is_synthetic: bool = False


CROPS = {
    "paddy": CropKnowledge("Paddy", ("nursery", "tillering", "panicle", "grain filling"), ("kharif", "rabi"), ("prolonged leaf wetness", "standing water", "humid nights")),
    "cotton": CropKnowledge("Cotton", ("seedling", "vegetative", "flowering", "boll"), ("kharif",), ("hot dry spells", "humid canopy")),
    "maize": CropKnowledge("Maize", ("seedling", "vegetative", "tasseling", "grain filling"), ("kharif", "rabi"), ("warm humid spells", "water stress")),
    "chilli": CropKnowledge("Chilli", ("nursery", "vegetative", "flowering", "fruiting"), ("kharif", "rabi"), ("humidity", "heat stress")),
    "tomato": CropKnowledge("Tomato", ("nursery", "vegetative", "flowering", "fruiting"), ("kharif", "rabi"), ("leaf wetness", "irregular watering")),
    "groundnut": CropKnowledge("Groundnut", ("seedling", "flowering", "pegging", "pod fill"), ("kharif", "rabi"), ("waterlogging", "humid foliage")),
    "red gram": CropKnowledge("Red gram", ("seedling", "vegetative", "flowering", "pod fill"), ("kharif",), ("waterlogging", "dry flowering period")),
    "green gram": CropKnowledge("Green gram", ("seedling", "vegetative", "flowering", "pod fill"), ("kharif", "rabi"), ("humid foliage", "hot dry spells")),
    "black gram": CropKnowledge("Black gram", ("seedling", "vegetative", "flowering", "pod fill"), ("kharif", "rabi"), ("humid foliage", "hot dry spells")),
    "soybean": CropKnowledge("Soybean", ("seedling", "vegetative", "flowering", "pod fill"), ("kharif",), ("humid canopy", "waterlogging")),
    "turmeric": CropKnowledge("Turmeric", ("sprouting", "vegetative", "rhizome development"), ("kharif",), ("standing water", "high humidity")),
    "onion": CropKnowledge("Onion", ("nursery", "vegetative", "bulb development"), ("rabi", "kharif"), ("humid foliage", "dry heat")),
    "potato": CropKnowledge("Potato", ("sprouting", "vegetative", "tuber initiation", "bulking"), ("rabi",), ("cool wet weather", "water stress")),
    "wheat": CropKnowledge("Wheat", ("seedling", "tillering", "booting", "grain filling"), ("rabi",), ("cool humidity", "terminal heat")),
    "sorghum": CropKnowledge("Sorghum", ("seedling", "vegetative", "flowering", "grain filling"), ("kharif", "rabi"), ("humid foliage", "water stress")),
    "pearl millet": CropKnowledge("Pearl millet", ("seedling", "vegetative", "flowering", "grain filling"), ("kharif",), ("humid seedling period", "water stress")),
    "brinjal": CropKnowledge("Brinjal", ("nursery", "vegetative", "flowering", "fruiting"), ("kharif", "rabi"), ("humid canopy", "water stress")),
    "okra": CropKnowledge("Okra", ("seedling", "vegetative", "flowering", "fruiting"), ("kharif", "summer"), ("hot dry spells", "humid canopy")),
}

# name, kind, visible symptom phrases, weather sensitivity, spread potential
RAW_ISSUES: dict[str, list[tuple[str, str, str, str, str]]] = {
    "paddy": [("Rice blast", "disease", "spindle shaped leaf spots; grey centers; neck lesions", "humid nights; leaf wetness", "high"), ("Stem borer", "pest", "dead hearts; white ear heads; bore holes", "warm humid weather", "moderate"), ("Zinc deficiency", "nutrient", "bronze leaf patches; stunted tillers; yellowing", "waterlogged soil", "low")],
    "cotton": [("Whitefly activity", "pest", "yellowing leaves; curled leaves; sticky honeydew; tiny white insects under leaves", "hot dry spells", "high"), ("Pink bollworm", "pest", "rosette flowers; damaged bolls; entry holes", "warm conditions", "high"), ("Leaf curl syndrome", "disease", "upward leaf curling; thickened veins; stunted growth", "whitefly activity", "high")],
    "maize": [("Fall armyworm", "pest", "windowed leaves; ragged whorl; frass in whorl", "warm weather", "high"), ("Northern leaf blight", "disease", "long cigar shaped lesions; grey brown leaves", "humid leaf wetness", "moderate"), ("Nitrogen deficiency", "nutrient", "yellow lower leaves; v shaped yellowing; poor growth", "leaching after rain", "low")],
    "chilli": [("Thrips injury", "pest", "upward curling leaves; silvery streaks; distorted shoots", "warm dry weather", "moderate"), ("Leaf curl complex", "disease", "small curled leaves; stunting; distorted growth", "whitefly pressure", "high"), ("Anthracnose", "disease", "sunken fruit spots; dark fruit lesions; fruit rot", "humid wet weather", "moderate")],
    "tomato": [("Early blight", "disease", "concentric brown leaf spots; yellow lower leaves", "warm humid weather", "moderate"), ("Whitefly activity", "pest", "tiny white insects; sticky leaves; yellowing", "warm dry weather", "high"), ("Blossom end rot", "nutrient", "dark sunken blossom end; fruit rot; irregular watering", "water stress", "low")],
    "groundnut": [("Leaf miner", "pest", "folded leaflets; mined leaves; brown patches", "warm weather", "moderate"), ("Tikka leaf spot", "disease", "dark circular leaf spots; yellow halo; defoliation", "humid wet weather", "moderate"), ("Iron chlorosis", "nutrient", "yellow young leaves; green veins; pale canopy", "alkaline soil", "low")],
    "red gram": [("Pod borer", "pest", "holes in pods; damaged seeds; caterpillars", "warm flowering period", "moderate"), ("Fusarium wilt", "disease", "sudden wilting; brown vascular tissue; drying branches", "soil moisture stress", "low"), ("Zinc deficiency", "nutrient", "small pale leaves; shortened internodes; stunting", "alkaline soil", "low")],
    "green gram": [("Whitefly activity", "pest", "tiny white insects; yellow leaves; sticky foliage", "hot dry spells", "high"), ("Yellow mosaic", "disease", "yellow mosaic patches; mottled leaves; reduced growth", "whitefly pressure", "high"), ("Powdery mildew", "disease", "white powder on leaves; yellowing; leaf drop", "dry days humid nights", "moderate")],
    "black gram": [("Whitefly activity", "pest", "tiny white insects; yellow leaves; sticky foliage", "hot dry spells", "high"), ("Yellow mosaic", "disease", "yellow mosaic patches; mottled leaves; reduced growth", "whitefly pressure", "high"), ("Leaf spot", "disease", "brown leaf spots; yellow halo; leaf drop", "humid foliage", "moderate")],
    "soybean": [("Stem fly", "pest", "yellowing seedlings; stem tunneling; wilting", "warm weather", "moderate"), ("Soybean rust", "disease", "small brown pustules; leaf yellowing; early defoliation", "humid leaf wetness", "high"), ("Iron chlorosis", "nutrient", "yellow young leaves; green veins; pale canopy", "alkaline soil", "low")],
    "turmeric": [("Rhizome rot", "disease", "yellow shoots; soft rhizome; plant collapse", "waterlogged soil", "moderate"), ("Leaf blotch", "disease", "brown oval leaf spots; yellow margins; drying leaves", "humid leaf wetness", "moderate"), ("Nutrient yellowing", "nutrient", "uniform pale leaves; weak shoots; slow growth", "leaching after rain", "low")],
    "onion": [("Thrips injury", "pest", "silvery leaf streaks; curled tips; tiny insects", "hot dry weather", "moderate"), ("Purple blotch", "disease", "purple sunken leaf lesions; leaf tip drying", "humid leaf wetness", "moderate"), ("Potassium deficiency", "nutrient", "leaf tip scorch; weak bulb growth; yellow margins", "soil nutrient imbalance", "low")],
    "potato": [("Late blight", "disease", "water soaked leaf lesions; white growth underside; stem browning", "cool wet weather", "high"), ("Aphid activity", "pest", "clusters of small insects; curled leaves; sticky shoots", "mild dry weather", "moderate"), ("Boron deficiency", "nutrient", "distorted young leaves; hollow tubers; brittle stems", "soil nutrient imbalance", "low")],
    "wheat": [("Leaf rust", "disease", "orange brown leaf pustules; yellowing", "cool humid weather", "high"), ("Aphid activity", "pest", "small insects on ear heads; sticky leaves; yellowing", "mild dry weather", "moderate"), ("Nitrogen deficiency", "nutrient", "yellow lower leaves; poor tillering; pale canopy", "leaching after rain", "low")],
    "sorghum": [("Shoot fly", "pest", "dead heart seedlings; central shoot drying", "warm seedling period", "moderate"), ("Anthracnose", "disease", "red brown leaf spots; leaf blight; stalk lesions", "humid leaf wetness", "moderate"), ("Nitrogen deficiency", "nutrient", "yellow lower leaves; pale growth; weak tillers", "leaching after rain", "low")],
    "pearl millet": [("Downy mildew", "disease", "pale leaf streaks; downy growth; distorted ear heads", "humid seedling period", "high"), ("Shoot fly", "pest", "dead heart seedlings; central shoot drying", "warm seedling period", "moderate"), ("Iron deficiency", "nutrient", "yellow young leaves; green veins; pale canopy", "alkaline soil", "low")],
    "brinjal": [("Shoot and fruit borer", "pest", "wilted shoots; bore holes in fruit; frass", "warm weather", "moderate"), ("Bacterial wilt", "disease", "sudden wilting; vascular browning; plant collapse", "warm wet soil", "low"), ("Magnesium deficiency", "nutrient", "yellowing between veins on older leaves; leaf edge browning", "soil nutrient imbalance", "low")],
    "okra": [("Jassid injury", "pest", "yellow leaf margins; curled leaves; small hopping insects", "hot dry weather", "moderate"), ("Yellow vein mosaic", "disease", "yellow veins; mottled leaves; reduced fruiting", "whitefly pressure", "high"), ("Potassium deficiency", "nutrient", "leaf margin scorch; weak fruiting; yellow edges", "soil nutrient imbalance", "low")],
}


def _make_issue(crop: str, row: tuple[str, str, str, str, str]) -> KnowledgeIssue:
    name, kind, symptoms, weather, spread = row
    if kind == "pest":
        prevention = ("Inspect representative plants regularly and record pest pressure.", "Maintain field hygiene and avoid unnecessary broad-spectrum sprays.")
        monitoring = ("Check affected and unaffected rows every 2–3 days.", "Record pest counts or trap observations where appropriate.")
    elif kind == "disease":
        prevention = ("Use healthy planting material and keep field tools clean.", "Improve drainage and canopy airflow where practical.")
        monitoring = ("Mark affected plants and check spread after humid or wet periods.", "Photograph new lesions for expert comparison.")
    else:
        prevention = ("Use a recent soil or tissue test before changing nutrients.", "Avoid blanket fertilizer application without local advice.")
        monitoring = ("Compare new and older leaves across representative plants.", "Track growth after reviewing water and soil conditions.")
    return KnowledgeIssue(crop, name, kind, tuple(part.strip() for part in symptoms.split(";")), tuple(part.strip() for part in weather.split(";")), SpreadPotential(spread), prevention, monitoring)


ISSUES = tuple(_make_issue(crop, row) for crop, rows in RAW_ISSUES.items() for row in rows)


def normalize_crop(crop: str) -> str:
    return crop.strip().casefold().replace("pigeon pea", "red gram").replace("rice", "paddy")


def match_issue(crop: str, symptoms: str) -> tuple[KnowledgeIssue | None, float]:
    tokens = set(re.findall(r"[a-z]{3,}", symptoms.casefold()))
    candidates = [item for item in ISSUES if item.crop == normalize_crop(crop)]
    ranked = []
    for item in candidates:
        clue_tokens = set(re.findall(r"[a-z]{3,}", " ".join((item.name, *item.symptoms)).casefold()))
        overlap = len(tokens & clue_tokens)
        name_hit = item.name.casefold() in symptoms.casefold()
        ranked.append((overlap + (3 if name_hit else 0), item))
    if not ranked:
        return None, 0.0
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    score, issue = ranked[0]
    if score == 0:
        return None, 0.0
    return issue, min(0.55, round(0.28 + score * 0.045, 2))


def local_finding(crop: str, symptoms: str) -> tuple[CropHealthFinding, str | None]:
    issue, confidence = match_issue(crop, symptoms)
    if issue is None:
        return CropHealthFinding(
            possible_problem="Unclear field symptoms", confidence=0.2, severity=Severity.LOW,
            symptoms=[symptoms[:250]], possible_causes=["Several pest, disease, nutrient, or weather causes remain possible."],
            immediate_actions=["Take clear photographs and inspect more plants in the field."],
            precautions=["Do not apply treatment based on this limited result alone."],
            monitoring=["Record whether symptoms spread over the next 2–3 days."],
            expert_verification="Ask a local crop specialist to examine the plant and field context.",
            spread_potential=SpreadPotential.UNKNOWN,
        ), None
    return CropHealthFinding(
        possible_problem=issue.name, confidence=confidence,
        severity=Severity.MODERATE if issue.kind != "nutrient" else Severity.LOW,
        symptoms=list(issue.symptoms),
        possible_causes=[f"Possible {issue.kind} pattern; other causes can look similar.", f"Sensitivity: {', '.join(issue.weather_sensitivity)}."],
        immediate_actions=["Inspect several affected and unaffected plants.", *issue.monitoring[:1]],
        precautions=["This match uses text and curated knowledge, not image analysis.", "Confirm with a qualified local agronomist before treatment."],
        monitoring=list(issue.monitoring),
        expert_verification="Expert verification is recommended, especially if symptoms spread or yield is threatened.",
        spread_potential=issue.spread_potential,
    ), f"catalog:{CATALOG_VERSION}:{issue.crop}:{issue.name.casefold().replace(' ', '-') }"
