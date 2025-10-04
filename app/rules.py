"""Rule-based deterministic site recommendation engine."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .config import Settings, get_settings
from .model import AOI, IndicatorSet, Site, SiteCollection


@dataclass(slots=True)
class RuleOutcome:
    site_type: str
    reason: str
    score: float
    index: int


class SiteRulesEngine:
    """Applies deterministic rules to derive site suggestions."""

    OFFSETS = [
        (-0.01, 0.01),
        (0.01, -0.01),
        (0.015, 0.015),
        (-0.02, -0.005),
        (0.005, 0.02),
    ]

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def suggest(self, aoi: AOI, indicators: IndicatorSet) -> SiteCollection:
        outcomes = list(self._evaluate_rules(indicators))
        return self._materialize_sites(aoi, outcomes)

    def _evaluate_rules(self, indicators: IndicatorSet) -> Iterable[RuleOutcome]:
        lulc = indicators.lulc_pc.classes
        cropland_pct = lulc.get("cropland", 0.0)
        forest_pct = lulc.get("forest", 0.0)
        built_pct = lulc.get("built", 0.0)

        if cropland_pct >= 20:
            yield RuleOutcome("farm_pond", "Cropland share supports on-farm storage", min(cropland_pct / 100, 1.0), 0)
            if cropland_pct >= 35:
                yield RuleOutcome("farm_pond", "High cropland intensity warrants additional pond", min(cropland_pct / 80, 1.0), 1)

        if indicators.gw.stressed:
            yield RuleOutcome("check_dam", "Groundwater stress suggests recharge structures", 0.9, 0)
            yield RuleOutcome("percolation_tank", "Groundwater stress suggests recharge structures", 0.85, 1)

        if forest_pct < 10 and built_pct < 15:
            yield RuleOutcome("nala_bund", "Open terrain suitable for nala bunding", 0.7, 0)

    def _materialize_sites(self, aoi: AOI, outcomes: List[RuleOutcome]) -> SiteCollection:
        collection = SiteCollection()
        base_lat = aoi.centroid_lat or 0.0
        base_lon = aoi.centroid_lon or 0.0

        village_label = (aoi.village or "aoi").lower()
        slug = self._slugify(village_label)

        for outcome in outcomes:
            lat_offset, lon_offset = self._offset(outcome.index)
            site = Site(
                site_type=outcome.site_type,
                site_id=f"{slug}_{outcome.site_type}_{outcome.index}",
                suitability=round(outcome.score, 3),
                latitude=round(base_lat + lat_offset, 6),
                longitude=round(base_lon + lon_offset, 6),
                notes=outcome.reason,
            )
            getattr(collection, outcome.site_type).append(site)

        return collection

    def _offset(self, index: int) -> tuple[float, float]:
        return self.OFFSETS[index % len(self.OFFSETS)]

    def _slugify(self, value: str) -> str:
        cleaned = "".join(ch if ch.isalnum() else "_" for ch in value)
        compact = "_".join(filter(None, cleaned.split("_")))
        return compact or "aoi"
