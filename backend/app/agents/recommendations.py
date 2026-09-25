from app.knowledge.catalog import CROPS, normalize_crop
from app.schemas.phase3 import FarmProfileInput, FertilizerRecommendation, SeedRecommendation
from app.schemas.intelligence import WeatherResult


class SeedRecommendationAgent:
    """Curated characteristic guidance, never an invented commercial product."""

    def recommend(self, profile: FarmProfileInput, weather: WeatherResult | None = None) -> SeedRecommendation:
        missing = [name for name, value in [("crop", profile.crop), ("season", profile.season), ("soil type", profile.soil_type), ("irrigation", profile.irrigation)] if not value]
        crop = CROPS.get(normalize_crop(profile.crop or ""))
        if not crop:
            return SeedRecommendation(crop=profile.crop, suitability="insufficient_data", characteristics=["Select a locally certified, traceable variety for the intended crop."], considerations=["The crop is outside the curated suitability catalog; ask a local extension specialist."], missing_inputs=missing, provenance="AgriVision curated crop knowledge; local extension verification required")
        characteristics = ["Use certified, locally adapted seed with verified germination and lot traceability.", "Match variety maturity duration to the available growing window."]
        considerations = []
        season = (profile.season or "").casefold()
        if season and season not in crop.seasons:
            considerations.append(f"{profile.season} is outside the catalog's usual {crop.name} seasons ({', '.join(crop.seasons)}). Confirm local suitability.")
        if profile.irrigation and profile.irrigation.casefold() in {"rainfed", "none"}:
            characteristics.append("Prefer locally verified moisture-stress tolerance for rainfed conditions.")
        if profile.previous_crop and profile.previous_crop.casefold() == crop.name.casefold():
            considerations.append("Repeated cropping can increase pest or soil pressure; review rotation and field history.")
        if profile.soil_ph is not None and (profile.soil_ph < 6 or profile.soil_ph > 8):
            considerations.append("Recorded soil pH is outside a broad neutral range; check crop-specific local soil guidance.")
        if weather and weather.current and not weather.stale and weather.current.temperature_c >= 35:
            considerations.append("Current heat may affect establishment; verify planting timing locally.")
        if profile.budget_inr is not None:
            considerations.append("Compare certified seed availability and full establishment costs with your stated budget.")
        suitability = "insufficient_data" if missing else "needs_review" if considerations and any("outside" in item for item in considerations) else "potentially_suitable"
        return SeedRecommendation(crop=crop.name, suitability=suitability, characteristics=characteristics, considerations=considerations or ["Confirm variety release and local performance with an extension service."], missing_inputs=missing, provenance="AgriVision curated static crop seasons and general seed selection principles; no commercial product endorsement")


class FertilizerAgent:
    """Uses lab-reported interpretation; raw soil numbers have no universal cutoff."""

    def recommend(self, profile: FarmProfileInput) -> FertilizerRecommendation:
        values = {"N": profile.nitrogen_kg_ha, "P": profile.phosphorus_kg_ha, "K": profile.potassium_kg_ha}
        status: dict[str, str] = {}
        deficiencies: list[str] = []
        priorities: list[str] = []
        for nutrient, value in values.items():
            lab = profile.lab_status.get(nutrient)
            status[nutrient] = f"Lab marked {lab}" if lab else f"Recorded {value:g} kg/ha; lab interpretation needed" if value is not None else "Not measured"
            if lab == "low":
                deficiencies.append(f"Possible {nutrient} deficiency based on the supplied lab category")
                priorities.append(f"Ask an agronomist to review the {nutrient} result alongside crop stage and local soil guidance.")
        for nutrient, value in profile.micronutrients.items():
            lab = profile.lab_status.get(nutrient)
            status[nutrient] = f"Lab marked {lab}" if lab else f"Recorded {value:g}; unit and lab range needed"
            if lab == "low":
                deficiencies.append(f"Possible {nutrient} deficiency based on the supplied lab category")
                priorities.append(f"Verify {nutrient} with the testing laboratory before correction.")
        soil = []
        if profile.soil_ph is not None:
            soil.append(f"Recorded pH {profile.soil_ph:g}; interpret against crop and local soil guidance.")
            if profile.soil_ph < 6 or profile.soil_ph > 8:
                soil.append("pH is outside a broad neutral range and may alter nutrient availability.")
        if profile.previous_crop:
            soil.append(f"Previous crop: {profile.previous_crop}; include residue and rotation history in the nutrient plan.")
        if profile.irrigation:
            soil.append(f"Irrigation: {profile.irrigation}; consider water availability and nutrient loss risk.")
        missing = [name for name, value in [("crop", profile.crop), ("season", profile.season), ("soil type", profile.soil_type), ("pH", profile.soil_ph)] if value is None]
        if not profile.lab_status:
            missing.append("laboratory nutrient interpretation")
        if not priorities:
            priorities.append("Obtain or review a recent soil-test interpretation before changing fertilizer practice.")
        return FertilizerRecommendation(nutrient_status=status, possible_deficiencies=deficiencies, priorities=priorities, soil_considerations=soil or ["No soil measurements were provided."], general_direction=["Use locally verified crop-stage and soil-test guidance for any correction.", "Avoid applying a specific product or dose based only on this summary."], monitoring=["Record crop response and compare with a follow-up soil or tissue test when advised."], missing_inputs=missing, provenance="User-entered soil measurements and lab categories; AgriVision general, non-prescriptive interpretation")
