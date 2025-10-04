"""Indicator computation and AOI resolution logic."""
from __future__ import annotations

import json
import logging
from typing import Dict, Optional, Any

from .arcgis import ArcGISClient
from .config import Settings, get_settings
from .geo import geometry_centroid, haversine_km
from .layers import AOI_LAYERS, INDICATOR_LAYERS, get_state_abbreviation, get_state_full_name
from .model import (
    AOI,
    Aquifer,
    GroundWater,
    IndicatorSet,
    LULCPercentages,
    MGNREGAStats,
    Report,
    ReportMeta,
)

logger = logging.getLogger(__name__)

STUB_INDICATORS = {
    "lulc_pc": {"forest": 58, "cropland": 28, "built": 6, "water": 2},
    "gw": {
        "district_pre2019_m": 12.7,
        "pre_post_delta_m": 1.6,
        "stressed": True,
    },
    "aquifer": {"type": "Hard rock", "code": "HRK"},
}


class IndicatorService:
    """Main orchestrator that produces indicator bundles and reports."""

    def __init__(self, settings: Optional[Settings] = None, client: Optional[ArcGISClient] = None) -> None:
        self.settings = settings or get_settings()
        self.client = client or ArcGISClient(token=self.settings.arcgis_token)
        self._last_resolution_notes: list[str] = []

    # ------------------------------------------------------------------
    # AOI resolution
    # ------------------------------------------------------------------
    def resolve_aoi(
        self,
        state: str,
        district: Optional[str] = None,
        block: Optional[str] = None,
        village: Optional[str] = None,
    ) -> AOI:
        if not state:
            raise ValueError("State is required to resolve an AOI.")

        if self.settings.stub_mode:
            logger.debug("Resolving AOI via stub mode")
            return AOI(
                state=state,
                district=district,
                block=block or "N/A",
                village=village or "N/A",
                centroid_lat=17.1234,
                centroid_lon=78.5432,
                source_layer="stub",
            )

        self._last_resolution_notes = []
        context: Dict[str, Optional[str]] = {}

        state_feature = self._resolve_feature("state", state, context)
        if not state_feature:
            raise ValueError(f"State '{state}' not found.")
        self._update_context("state", state_feature, state, context)

        district_feature: Optional[dict] = None
        if district:
            if "district" in AOI_LAYERS:
                district_feature = self._resolve_feature("district", district, context)
                if district_feature:
                    self._update_context("district", district_feature, district, context)
                else:
                    self._last_resolution_notes.append(
                        f"District '{district}' not found; using state boundary for calculations."
                    )
            else:
                self._last_resolution_notes.append("District layer not configured; using state boundary.")

        block_feature: Optional[dict] = None
        if block:
            if "block" in AOI_LAYERS:
                block_feature = self._resolve_feature("block", block, context)
                if block_feature:
                    self._update_context("block", block_feature, block, context)
                else:
                    self._last_resolution_notes.append(
                        f'Block "{block}" not found; using higher-level boundary.'
                    )
            else:
                self._last_resolution_notes.append("Block layer not configured; skipping.")

        village_feature: Optional[dict] = None
        if village:
            if "village" in AOI_LAYERS:
                village_feature = self._resolve_feature("village", village, context)
                if village_feature:
                    self._update_context("village", village_feature, village, context)
                else:
                    self._last_resolution_notes.append(
                        f'Village "{village}" not found; using higher-level boundary.'
                    )
            else:
                self._last_resolution_notes.append("Village layer not configured; skipping.")

        best_feature, best_layer_key = self._select_best_feature(
            {
                "village": village_feature,
                "block": block_feature,
                "district": district_feature,
                "state": state_feature,
            }
        )
        if best_layer_key != "village":
            self._last_resolution_notes.append(f"AOI geometry resolved at {best_layer_key} level.")

        logger.debug("Computing centroid from feature: %s", best_feature.keys() if best_feature else None)
        centroid = geometry_centroid(best_feature)
        logger.debug("Computed centroid: %s", centroid)

        # Extract additional attributes
        additional_attrs = {}
        if best_feature:
            attrs = best_feature.get("attributes", {})
            # Extract useful metadata based on layer type
            if best_layer_key == "state":
                if "GA_sqkm" in attrs:
                    additional_attrs["geographic_area_sqkm"] = attrs["GA_sqkm"]
                if "State_Cens" in attrs:
                    additional_attrs["state_census_code"] = attrs["State_Cens"]
            elif best_layer_key == "district":
                if "st_area_sh" in attrs:
                    additional_attrs["area_sqkm"] = attrs["st_area_sh"]

        return AOI(
            state=context.get("state_name", state),
            district=context.get("district_name", district or "N/A"),
            block=context.get("block_name", block or "N/A"),
            village=context.get("village_name", village or "N/A"),
            centroid_lat=centroid[0] if centroid else None,
            centroid_lon=centroid[1] if centroid else None,
            source_layer=AOI_LAYERS[best_layer_key].url,
            area_sqkm=additional_attrs.get("area_sqkm"),
            census_code=additional_attrs.get("state_census_code"),
            additional_attributes=additional_attrs,
        )

    # ------------------------------------------------------------------
    # Indicator bundling
    # ------------------------------------------------------------------
    def build_indicator_bundle(self, aoi: AOI) -> IndicatorSet:
        if self.settings.stub_mode:
            return self._build_stub_bundle()

        gw = self._fetch_groundwater(aoi)
        aquifer = self._fetch_aquifer(aoi)
        lulc = self._fetch_lulc(aoi)
        mgnrega = self._fetch_mgnrega(aoi)

        return IndicatorSet(
            gw=gw,
            aquifer=aquifer,
            lulc_pc=lulc,
            mgnrega=mgnrega,
        )

    def _build_stub_bundle(self) -> IndicatorSet:
        logger.debug("Producing stub indicator bundle")
        lulc = LULCPercentages(classes=STUB_INDICATORS["lulc_pc"])
        gw = GroundWater(**STUB_INDICATORS["gw"])
        aquifer = Aquifer(**STUB_INDICATORS["aquifer"])
        mgnrega = MGNREGAStats()
        return IndicatorSet(
            lulc_pc=lulc,
            gw=gw,
            aquifer=aquifer,
            mgnrega=mgnrega,
        )

    def _fetch_groundwater(self, aoi: AOI) -> GroundWater:
        # First try to get district-level administrative groundwater data
        district_gw = self._fetch_district_groundwater(aoi)
        
        # Also get measurement-based groundwater data
        pre_monsoon = self._average_groundwater_layer("groundwater_pre_monsoon", aoi)
        during_monsoon = self._average_groundwater_layer("groundwater_during_monsoon", aoi)
        post_monsoon = self._average_groundwater_layer("groundwater_post_monsoon", aoi)

        primary_candidates = [post_monsoon, during_monsoon, pre_monsoon]
        primary = next((value for value in primary_candidates if value is not None), None)

        delta = None
        delta_pairs = [
            (post_monsoon, pre_monsoon),
            (during_monsoon, pre_monsoon),
        ]
        for newer, older in delta_pairs:
            if newer is not None and older is not None:
                delta = round(newer - older, 2)
                break

        stressed = primary >= self.settings.gw_stress_threshold_m if primary else None
        pre2019_value = primary

        # Merge district administrative data with measurement data
        return GroundWater(
            annual_extraction_mcm=district_gw.get("annual_extraction"),
            net_available_mcm=district_gw.get("net_available"),
            stage_of_development_pc=district_gw.get("stage_of_development"),
            category=district_gw.get("category"),
            district_pre2019_m=round(pre2019_value, 2) if pre2019_value else None,
            pre_post_delta_m=delta,
            stressed=stressed,
        )

    def _average_groundwater_layer(self, layer_key: str, aoi: AOI) -> Optional[float]:
        layer = INDICATOR_LAYERS.get(layer_key)
        if not layer:
            return None

        params = {"outFields": ",".join(layer.fields)}
        where_clauses = []

        if aoi.state and (layer.state_field or layer.parent_field):
            state_field = layer.state_field or layer.parent_field
            state_value = aoi.state.replace("'", "''")
            where_clauses.append(f"UPPER({state_field}) = UPPER('{state_value}')")

        if aoi.district and (layer.district_field or layer.name_field):
            district_field = layer.district_field or layer.name_field
            district_value = aoi.district.replace("'", "''")
            where_clauses.append(f"UPPER({district_field}) = UPPER('{district_value}')")

        where = " AND ".join(where_clauses) or "1=1"

        try:
            results = self.client.query_by_where(layer.url, where, additional_params=params)
        except Exception as exc:  # pragma: no cover
            logger.warning("Groundwater query failed for %s: %s", layer_key, exc)
            return None

        values: list[float] = []
        value_field = layer.value_field or "wl_mbgl"
        for feature in results:
            attrs = feature.get("attributes", {})
            value = attrs.get(value_field)
            if value is None:
                continue
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                continue

        if not values:
            return None

        return sum(values) / len(values)

    def _fetch_aquifer(self, aoi: AOI) -> Aquifer:
        if "aquifer" not in INDICATOR_LAYERS:
            logger.debug("Aquifer layer not configured; skipping.")
            return Aquifer()
        
        if not aoi.centroid_lat or not aoi.centroid_lon:
            logger.debug("AOI centroid not available; cannot query aquifer.")
            return Aquifer()
        
        layer = INDICATOR_LAYERS["aquifer"]
        params = {"outFields": "*"}
        
        # Use point geometry with 'within' spatial relationship for polygon layers
        # This finds polygons that contain the point
        params["geometryType"] = "esriGeometryPoint"
        params["spatialRel"] = "esriSpatialRelWithin"
        params["geometry"] = json.dumps({
            "x": aoi.centroid_lon,
            "y": aoi.centroid_lat,
            "spatialReference": {"wkid": 4326}
        })
        params["returnGeometry"] = "false"  # We only need attributes
        
        try:
            results = self.client.query(layer.url, params)
        except Exception as exc:
            logger.warning("Aquifer query failed: %s", exc)
            return Aquifer()

        if not results:
            logger.debug("No aquifer found at centroid location.")
            return Aquifer()

        attrs = results[0].get("attributes", {})
        aquifer_type = (
            attrs.get("aquifer")
            or attrs.get("aquifers")
            or attrs.get("aquifer_0")
            or attrs.get("systems")
        )
        aquifer_code = attrs.get("new_code_14") or attrs.get("newcode43")
        return Aquifer(
            type=aquifer_type,
            code=aquifer_code,
        )
    
    def _fetch_district_groundwater(self, aoi: AOI) -> Dict[str, Any]:
        """Extract groundwater metrics from district boundary layer."""
        if "district" not in AOI_LAYERS:
            return {}
        
        layer = AOI_LAYERS["district"]
        params = {"outFields": "*"}
        where_clauses = []
        
        # Use state abbreviation for district layer
        if aoi.state and layer.state_field:
            state_abbrev = get_state_abbreviation(aoi.state)
            if state_abbrev:
                where_clauses.append(f"{layer.state_field} = '{state_abbrev}'")
        
        if aoi.district and layer.name_field:
            district_value = aoi.district.replace("'", "''")
            where_clauses.append(f"{layer.name_field} = '{district_value}'")
        
        where = " AND ".join(where_clauses) or "1=1"
        
        try:
            results = self.client.query_by_where(layer.url, where, additional_params=params)
        except Exception as exc:
            logger.warning("District groundwater query failed: %s", exc)
            return {}
        
        if not results:
            return {}
        
        attrs = results[0].get("attributes", {})
        
        # Extract groundwater fields from district layer
        # Annual_Gro = Annual groundwater extraction
        # Ground_Wat = Groundwater availability
        # Net_Ground = Net groundwater availability
        # Stage_of_d = Stage of development percentage
        
        gw_data = {}
        
        # Try to extract annual extraction
        annual_extraction = attrs.get("Annual_Gro") or attrs.get("Annual_G00")
        if annual_extraction is not None:
            try:
                gw_data["annual_extraction"] = float(annual_extraction)
            except (TypeError, ValueError):
                pass
        
        # Net available groundwater
        net_available = attrs.get("Net_Ground") or attrs.get("Ground_Wat")
        if net_available is not None:
            try:
                gw_data["net_available"] = float(net_available)
            except (TypeError, ValueError):
                pass
        
        # Stage of development
        stage = attrs.get("Stage_of_d")
        if stage is not None:
            try:
                stage_val = float(stage)
                gw_data["stage_of_development"] = stage_val
                # Categorize based on stage of development
                if stage_val >= 100:
                    gw_data["category"] = "Over-exploited"
                elif stage_val >= 90:
                    gw_data["category"] = "Critical"
                elif stage_val >= 70:
                    gw_data["category"] = "Semi-critical"
                else:
                    gw_data["category"] = "Safe"
            except (TypeError, ValueError):
                pass
        
        return gw_data

    def _fetch_lulc(self, aoi: AOI) -> LULCPercentages:
        # Try to get state-level forest data first
        forest_data = self._fetch_state_forest_data(aoi)
        
        # For now, return forest data from state layer
        # In future, can add LULC raster analysis here
        return LULCPercentages(
            forest_area_sqkm=forest_data.get("forest_area"),
            forest_percentage=forest_data.get("forest_percentage"),
            scrub_area_sqkm=forest_data.get("scrub_area"),
            geographic_area_sqkm=forest_data.get("geographic_area"),
        )
    
    def _fetch_state_forest_data(self, aoi: AOI) -> Dict[str, Any]:
        """Extract forest cover data from state boundary layer."""
        if "state" not in AOI_LAYERS:
            return {}
        
        layer = AOI_LAYERS["state"]
        params = {"outFields": "*"}
        where_clauses = []
        
        if aoi.state and layer.name_field:
            state_value = aoi.state.replace("'", "''")
            where_clauses.append(f"{layer.name_field} = '{state_value}'")
        
        where = " AND ".join(where_clauses) or "1=1"
        
        try:
            results = self.client.query_by_where(layer.url, where, additional_params=params)
        except Exception as exc:
            logger.warning("State forest query failed: %s", exc)
            return {}
        
        if not results:
            return {}
        
        attrs = results[0].get("attributes", {})
        
        forest_data = {}
        
        # GA_sqkm = Geographic area
        ga = attrs.get("GA_sqkm")
        if ga is not None:
            try:
                forest_data["geographic_area"] = float(ga)
            except (TypeError, ValueError):
                pass
        
        # Forest_201 = Forest area 2019 (in sq km)
        forest_area = attrs.get("Forest_201")
        if forest_area is not None:
            try:
                forest_data["forest_area"] = float(forest_area)
            except (TypeError, ValueError):
                pass
        
        # Per_GA_201 = Percentage of geographic area under forest
        forest_pct = attrs.get("Per_GA_201")
        if forest_pct is not None:
            try:
                forest_data["forest_percentage"] = float(forest_pct)
            except (TypeError, ValueError):
                pass
        
        # Scrub2019 = Scrub area 2019
        scrub = attrs.get("Scrub2019")
        if scrub is not None:
            try:
                forest_data["scrub_area"] = float(scrub)
            except (TypeError, ValueError):
                pass
        
        return forest_data
    
    def _fetch_mgnrega(self, aoi: AOI) -> MGNREGAStats:
        """Extract MGNREGA employment statistics for the district."""
        if "mgnrega_workers" not in INDICATOR_LAYERS:
            logger.debug("MGNREGA workers layer not configured; skipping.")
            return MGNREGAStats()
        
        layer = INDICATOR_LAYERS["mgnrega_workers"]
        params = {"outFields": "*"}
        where_clauses = []
        
        # Query by state and district names (layer uses full names)
        if aoi.state and layer.state_field:
            state_value = aoi.state.replace("'", "''")
            where_clauses.append(f"{layer.state_field} = '{state_value}'")
        
        if aoi.district and layer.district_field:
            district_value = aoi.district.replace("'", "''")
            where_clauses.append(f"{layer.district_field} = '{district_value}'")
        
        where = " AND ".join(where_clauses) or "1=1"
        
        try:
            results = self.client.query_by_where(layer.url, where, additional_params=params)
        except Exception as exc:
            logger.warning("MGNREGA workers query failed: %s", exc)
            return MGNREGAStats()
        
        if not results:
            logger.debug("No MGNREGA data found for state=%s, district=%s", aoi.state, aoi.district)
            return MGNREGAStats()
        
        # Extract data from first matching district
        attrs = results[0].get("attributes", {})
        
        # Extract raw counts
        jobcards_applied = attrs.get("number_of_jobcards_applied_for")
        jobcards_issued = attrs.get("number_of_jobcards_issued")
        registered_total = attrs.get("registered_workers_total")
        registered_sc = attrs.get("registered_workers_sc")
        registered_st = attrs.get("registered_workers_st")
        registered_women = attrs.get("registered_workers_women")
        active_cards = attrs.get("number_of_active_job_cards")
        active_total = attrs.get("active_workers_total_workers")
        active_sc = attrs.get("active_workers_sc")
        active_st = attrs.get("active_workers_st")
        active_women = attrs.get("active_workers_women")
        
        # Compute derived metrics
        jobcard_issuance_rate = None
        if jobcards_applied and jobcards_applied > 0 and jobcards_issued is not None:
            jobcard_issuance_rate = round((jobcards_issued / jobcards_applied) * 100, 2)
        
        worker_activation_rate = None
        if registered_total and registered_total > 0 and active_total is not None:
            worker_activation_rate = round((active_total / registered_total) * 100, 2)
        
        women_participation = None
        if active_total and active_total > 0 and active_women is not None:
            women_participation = round((active_women / active_total) * 100, 2)
        
        return MGNREGAStats(
            jobcards_applied=jobcards_applied,
            jobcards_issued=jobcards_issued,
            registered_workers_total=registered_total,
            registered_workers_sc=registered_sc,
            registered_workers_st=registered_st,
            registered_workers_women=registered_women,
            active_job_cards=active_cards,
            active_workers_total=active_total,
            active_workers_sc=active_sc,
            active_workers_st=active_st,
            active_workers_women=active_women,
            jobcard_issuance_rate_pc=jobcard_issuance_rate,
            worker_activation_rate_pc=worker_activation_rate,
            women_participation_pc=women_participation,
        )

    def _feature_point(self, feature: dict) -> Optional[tuple[float, float]]:
        geometry = feature.get("geometry") if isinstance(feature, dict) else None
        if not geometry:
            return None

        if "y" in geometry and "x" in geometry:
            return geometry["y"], geometry["x"]

        coords = geometry.get("coordinates") if isinstance(geometry, dict) else None
        if isinstance(coords, (list, tuple)) and len(coords) >= 2:
            return coords[1], coords[0]

        return None

    def _resolve_feature(
        self,
        layer_key: str,
        name: Optional[str],
        context: Dict[str, Optional[str]],
    ) -> Optional[dict]:
        """Resolve a feature by querying the layer using fields defined in layer registry."""
        if layer_key not in AOI_LAYERS:
            return None
        
        layer = AOI_LAYERS[layer_key]
        params = {"outFields": "*"}
        where_clauses: list[str] = []

        # Use the name_field defined in the layer to match the provided name
        if name and layer.name_field:
            where_clauses.append(self._eq_clause(layer.name_field, name))

        # Filter by parent state if layer has state_field and context provides state info
        if layer.state_field and layer_key != "state":
            # Try both full name and abbreviation for state filtering
            state_full = context.get("state_name_full") or context.get("state_name")
            state_abbrev = context.get("state_name_abbrev")
            
            # Use whichever format matches the layer's expectation
            # If the state_field suggests it wants an abbreviation (e.g., "State" vs "state_name")
            # try abbreviation first, otherwise use full name
            state_value = state_abbrev if state_abbrev and len(state_abbrev) == 2 else state_full
            if state_value:
                where_clauses.append(self._eq_clause(layer.state_field, state_value))

        # Filter by parent district if layer has district_field and context provides district_name
        district_name = context.get("district_name")
        if layer.district_field and district_name and layer_key not in {"state", "district"}:
            where_clauses.append(self._eq_clause(layer.district_field, district_name))

        # Filter by parent_field if defined (for hierarchical lookups like block->district)
        if layer.parent_field:
            parent_value = context.get(layer.parent_field)
            if parent_value:
                where_clauses.append(self._eq_clause(layer.parent_field, str(parent_value)))

        where = " AND ".join(where_clauses) if where_clauses else "1=1"
        logger.debug("Querying %s layer with WHERE: %s", layer_key, where)

        try:
            results = self.client.query_by_where(layer.url, where, additional_params=params)
        except Exception as exc:  # pragma: no cover
            logger.warning("AOI lookup failed for %s (%s): %s", name or layer_key, layer_key, exc)
            return None

        if not results:
            logger.debug("No features found for %s with name=%s", layer_key, name)
            return None

        logger.debug("Found %d feature(s) for %s", len(results), layer_key)
        logger.debug("Feature keys: %s", results[0].keys() if results else None)
        if results and 'geometry' in results[0]:
            logger.debug("Geometry present: %s", type(results[0]['geometry']))
        if results and 'attributes' in results[0]:
            logger.debug("Attributes present with %d fields", len(results[0]['attributes']))
        
        # Temporary debug: dump first feature to file for inspection
        try:
            with open("debug_feature.json", "w") as f:
                json.dump(results[0], f, indent=2, default=str)
        except Exception:
            pass
        
        return results[0]

    def _update_context(
        self,
        layer_key: str,
        feature: dict,
        fallback_name: str,
        context: Dict[str, Optional[str]],
    ) -> None:
        """Extract values from the feature and store them in context for downstream filters."""
        layer = AOI_LAYERS[layer_key]
        attrs = feature.get("attributes", {})

        # Get the resolved name from the layer's name_field
        name_value = attrs.get(layer.name_field) if layer.name_field else None
        resolved_name = name_value or fallback_name

        # Store the canonical name for this level
        context[f"{layer_key}_name"] = resolved_name

        # For state layer, also store both full name and abbreviation
        if layer_key == "state":
            # Extract both formats from the feature if available
            full_name = attrs.get("State_FSI") or resolved_name
            abbrev = attrs.get("State_Name")
            
            # If we have full name but not abbreviation, look it up
            if full_name and not abbrev:
                abbrev = get_state_abbreviation(full_name)
            
            # If we have abbreviation but not full name, look it up
            if abbrev and not full_name:
                full_name = get_state_full_name(abbrev)
            
            # Store both formats for downstream use
            context["state_name_full"] = full_name
            context["state_name_abbrev"] = abbrev
            # Keep state_name as the canonical (full) version
            context["state_name"] = full_name

        # Store code if the layer defines a code_field
        if layer.code_field:
            code_value = attrs.get(layer.code_field)
            if code_value is not None:
                context[f"{layer_key}_code"] = str(code_value)

        # Store parent identifiers if the layer defines parent_field
        if layer.parent_field:
            parent_value = attrs.get(layer.parent_field)
            if parent_value is not None:
                context[layer.parent_field] = str(parent_value)

    def _select_best_feature(self, features: Dict[str, Optional[dict]]) -> tuple[dict, str]:
        for key in ("village", "block", "district", "state"):
            feature = features.get(key)
            if feature:
                return feature, key
        raise ValueError("AOI resolution failed; no matching features found.")

    def _eq_clause(self, field: str, value: str) -> str:
        safe_value = value.replace("'", "''")
        return f"UPPER({field}) = UPPER('{safe_value}')"

    # ------------------------------------------------------------------
    # Report assembly
    # ------------------------------------------------------------------
    def build_report(self, aoi: AOI, language: Optional[str] = None) -> Report:
        indicators = self.build_indicator_bundle(aoi)
        meta = ReportMeta(
            data_sources=self._collect_data_sources(),
            stub_mode=self.settings.stub_mode,
            notes=self._build_meta_notes(aoi, indicators),
        )

        narrative = None
        ai_analysis = None
        
        if self.settings.use_vertex:
            from .vertex import VertexClient

            vertex_client = VertexClient(self.settings)
            
            # Generate narrative if language is specified
            if language:
                narrative = vertex_client.make_narrative(aoi, indicators, language)
            
            # Always generate AI analysis for FRA recommendations
            ai_analysis = vertex_client.generate_ai_analysis(aoi, indicators)

        return Report(
            aoi=aoi,
            indicators=indicators,
            meta=meta,
            narrative=narrative,
            ai_analysis=ai_analysis,
        )

    def _collect_data_sources(self) -> list[str]:
        sources = []
        for key, layer in {**AOI_LAYERS, **INDICATOR_LAYERS}.items():
            sources.append(f"{key}:{layer.url}")
        return sources

    def _build_meta_notes(self, aoi: AOI, indicators: IndicatorSet) -> list[str]:
        notes = list(self._last_resolution_notes)
        if aoi.village in {None, "", "N/A"} and not any("village boundary" in note.lower() for note in notes):
            notes.append("Village boundary unavailable; report uses higher-level geometry.")
        if aoi.block in {None, "", "N/A"} and not any("block boundary" in note.lower() for note in notes):
            notes.append("Block boundary unavailable; report uses district context.")
        if not indicators.lulc_pc.classes:
            notes.append("LULC data unavailable; values omitted.")
        if indicators.gw.stressed is None:
            notes.append("Groundwater stress could not be evaluated.")
        if indicators.gw.pre_post_delta_m is None:
            notes.append("Groundwater change data unavailable; delta omitted.")
        return notes

    def _aoi_polygon(self, aoi: AOI) -> dict:
        # Placeholder polygon around centroid for intersect queries
        lat = aoi.centroid_lat or 0.0
        lon = aoi.centroid_lon or 0.0
        delta = 0.01
        return {
            "type": "Polygon",
            "coordinates": [
                [
                    [lon - delta, lat - delta],
                    [lon + delta, lat - delta],
                    [lon + delta, lat + delta],
                    [lon - delta, lat + delta],
                    [lon - delta, lat - delta],
                ]
            ],
        }


def build_report(
    state: str,
    district: str,
    block: str,
    village: str,
    language: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> Report:
    service = IndicatorService(settings=settings)
    aoi = service.resolve_aoi(state, district, block, village)
    return service.build_report(aoi, language=language)

