"""Vertex AI Gemini integration (optional)."""
from __future__ import annotations

import json
import logging
from typing import Optional
from datetime import datetime

from .config import Settings
from .model import AOI, IndicatorSet, Narrative, AIAnalysis

logger = logging.getLogger(__name__)


class VertexClient:
    MODEL_NAME = "gemini-1.5-flash-001"
    MODEL_FALLBACKS = (
        "gemini-1.5-flash",
        "gemini-1.0-pro",
        "gemini-pro",
    )
    DEFAULT_LOCATION = "us-central1"
    RESPONSE_MIME_TYPE = "application/json"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model = None
        self._model_name_in_use = None
        self._generation_config_cls = None
        self._location = None
        self._configure()

    def _configure(self) -> None:
        if not self.settings.use_vertex:
            logger.debug("USE_VERTEX disabled; skipping Vertex AI initialisation")
            return

        if not self.settings.gcp_project:
            logger.warning("GCP project not configured; Vertex integration disabled")
            return

        google_exceptions = None
        try:
            import vertexai  # type: ignore
            try:
                from vertexai.generative_models import GenerativeModel, GenerationConfig  # type: ignore
            except ImportError:  # pragma: no cover - compatibility fallback
                from vertexai.preview.generative_models import GenerativeModel, GenerationConfig  # type: ignore
            try:
                from google.api_core import exceptions as google_exceptions  # type: ignore
            except ImportError:
                google_exceptions = None
        except ImportError:  # pragma: no cover - runtime safeguard
            logger.warning(
                "google-cloud-aiplatform not installed; Vertex integration disabled"
            )
            return

        location = self.settings.gcp_location or self.DEFAULT_LOCATION

        try:
            vertexai.init(project=self.settings.gcp_project, location=location)
            self._generation_config_cls = GenerationConfig
            self._location = location
        except Exception as exc:  # pragma: no cover - network/credential issues
            logger.error("Vertex AI initialisation failed: %s", exc)
            self._model = None
            self._generation_config_cls = None
            self._location = None
            return

        candidates: list[str] = []
        primary = self.MODEL_NAME
        if primary:
            candidates.append(primary)
        for fallback in self.MODEL_FALLBACKS:
            if fallback not in candidates:
                candidates.append(fallback)

        for candidate in candidates:
            try:
                self._model = GenerativeModel(candidate)
                self._model_name_in_use = candidate
                logger.info(
                    "Vertex AI initialised for project %s in %s using model %s",
                    self.settings.gcp_project,
                    location,
                    candidate,
                )
                break
            except Exception as exc:
                if google_exceptions and isinstance(exc, google_exceptions.NotFound):
                    logger.warning("Vertex model %s unavailable: %s", candidate, exc)
                    continue
                logger.error("Failed to initialise Vertex model %s: %s", candidate, exc)
                self._model = None
                self._generation_config_cls = None
                self._location = None
                return
        else:
            logger.error("No accessible Vertex model found; Vertex integration disabled")
            self._model = None
            self._generation_config_cls = None
            self._location = None
            return

    def make_narrative(self, aoi: AOI, indicators: IndicatorSet, language: str) -> Narrative:
        if not self._model:
            return Narrative(
                language=language,
                provider="vertex-ai",
                content="Narrative generation not available in this environment.",
            )

        prompt = self._build_prompt(aoi, indicators, language)
        GenerationConfig = self._generation_config_cls
        config = None
        if GenerationConfig:
            config = GenerationConfig(
                response_mime_type=self.RESPONSE_MIME_TYPE,
                temperature=0.2,
            )

        try:
            if config is not None:
                response = self._model.generate_content(
                    prompt,
                    generation_config=config,
                )
            else:
                response = self._model.generate_content(prompt)
        except Exception as exc:  # pragma: no cover - network path
            logger.error("Vertex AI generation failed: %s", exc)
            return Narrative(
                language=language,
                provider="vertex-ai",
                content="Narrative generation failed.",
            )

        content = self._parse_response(response)
        return Narrative(language=language, provider="vertex-ai", content=content)

    def _build_prompt(self, aoi: AOI, indicators: IndicatorSet, language: str) -> str:
        payload = {
            "aoi": aoi.dict(),
            "indicators": indicators.dict(),
            "language": language,
            "instructions": "Provide a concise narrative summary of the indicators in the requested language.",
        }
        return json.dumps(payload)

    def _parse_response(self, response: object) -> Optional[str]:
        try:
            candidates = getattr(response, "candidates", None)
            if not candidates:
                return None
            content = candidates[0].content
            parts = getattr(content, "parts", []) if content else []
            if not parts:
                return None
            text = getattr(parts[0], "text", None)
            if not text:
                return None
            data = json.loads(text)
            return data.get("narrative") or text
        except Exception:  # pragma: no cover - defensive
            logger.exception("Failed to parse Vertex AI response")
            return None
    
    def _build_analysis_prompt(self, aoi: AOI, indicators: IndicatorSet) -> str:
        def percent(part: Optional[float], whole: Optional[float]) -> Optional[float]:
            if part is None or whole in (None, 0):
                return None
            try:
                return round((part / whole) * 100, 2)
            except ZeroDivisionError:
                return None

        mgnrega = indicators.mgnrega
        st_pct = percent(mgnrega.registered_workers_st, mgnrega.registered_workers_total)
        sc_pct = percent(mgnrega.registered_workers_sc, mgnrega.registered_workers_total)

        data_summary = {
            "aoi": {
                "state": aoi.state,
                "district": aoi.district,
                "block": aoi.block,
                "village": aoi.village,
            },
            "lulc": {
                "forest_percentage": indicators.lulc_pc.forest_percentage,
                "forest_area_sqkm": indicators.lulc_pc.forest_area_sqkm,
                "scrub_area_sqkm": indicators.lulc_pc.scrub_area_sqkm,
                "geographic_area_sqkm": indicators.lulc_pc.geographic_area_sqkm,
            },
            "groundwater": {
                "category": indicators.gw.category,
                "stage_of_development_pc": indicators.gw.stage_of_development_pc,
                "stressed": indicators.gw.stressed,
                "pre_post_delta_m": indicators.gw.pre_post_delta_m,
            },
            "aquifer": {
                "type": indicators.aquifer.type,
                "code": indicators.aquifer.code,
            },
            "mgnrega": {
                "worker_activation_rate_pc": mgnrega.worker_activation_rate_pc,
                "women_participation_pc": mgnrega.women_participation_pc,
                "st_workers_percentage": st_pct,
                "sc_workers_percentage": sc_pct,
            },
        }

        forest_pct_display = (
            f"{indicators.lulc_pc.forest_percentage:.2f}%"
            if indicators.lulc_pc.forest_percentage is not None
            else "unknown"
        )
        st_pct_display = f"{st_pct:.2f}%" if st_pct is not None else "unknown"

        lines = [
            "You are an expert analyst for the Forest Rights Act (FRA) and rural development in India.",
            f"Analyze the following data for {aoi.district} district, {aoi.state}.",
            "",
            "DATA:",
            json.dumps(data_summary, indent=2, ensure_ascii=False),
            "",
            "ANALYSIS REQUIREMENTS:",
            "1. FRA RECOMMENDATION:",
            f"   - Assess FRA recognition suitability considering forest cover ({forest_pct_display}) and ST participation ({st_pct_display}).",
            "   - Provide one of: Highly Recommended, Recommended, Conditionally Recommended, Not Recommended.",
            "   - Include a short justification.",
            "2. KEY FINDINGS:",
            "   - List 4-6 specific data insights with numbers.",
            "3. DEVELOPMENT PRIORITIES:",
            "   - Suggest 3-5 actionable interventions tied to the data (groundwater, forest cover, livelihoods).",
            "4. RISK FACTORS:",
            "   - Identify 2-4 environmental or social risks grounded in the indicators.",
            "5. OPPORTUNITIES:",
            "   - Highlight 2-4 opportunities leveraging area strengths.",
            "6. SUMMARY:",
            "   - Provide a concise 3-4 sentence executive summary.",
            "7. CONFIDENCE:",
            "   - State High, Medium, or Low depending on data completeness.",
            "",
            "Return ONLY valid JSON in this exact format:",
            "{",
            '  "fra_recommendation": "string",',
            '  "key_findings": ["string", "string"],',
            '  "development_priorities": ["string", "string"],',
            '  "risk_factors": ["string", "string"],',
            '  "opportunities": ["string", "string"],',
            '  "summary": "string",',
            '  "confidence": "High|Medium|Low"',
            "}",
        ]

        return "\n".join(lines)


    def generate_ai_analysis(self, aoi: AOI, indicators: IndicatorSet) -> AIAnalysis:
        """Generate comprehensive AI analysis with FRA recommendations and development insights."""
        if not self._model:
            return AIAnalysis(
                summary="AI analysis not available in this environment.",
                confidence="Low",
                model_used="none"
            )

        prompt = self._build_analysis_prompt(aoi, indicators)
        GenerationConfig = self._generation_config_cls
        config = None
        if GenerationConfig:
            config = GenerationConfig(
                response_mime_type=self.RESPONSE_MIME_TYPE,
                temperature=0.3,
                max_output_tokens=2048,
            )

        try:
            if config is not None:
                response = self._model.generate_content(
                    prompt,
                    generation_config=config,
                )
            else:
                response = self._model.generate_content(prompt)
        except Exception as exc:  # pragma: no cover - network path
            logger.error("Vertex AI analysis generation failed: %s", exc)
            return AIAnalysis(
                summary="AI analysis generation failed.",
                confidence="Low",
                model_used=self.MODEL_NAME
            )

        analysis_data = self._parse_analysis_response(response)
        return AIAnalysis(
            **analysis_data,
            generated_at=datetime.utcnow().replace(microsecond=0),
            model_used=self.MODEL_NAME
        )

    def _parse_analysis_response(self, response: object) -> dict:
        """Parse AI analysis response into structured data."""
        try:
            candidates = getattr(response, "candidates", None)
            if not candidates:
                return self._get_fallback_analysis()
            
            content = candidates[0].content
            parts = getattr(content, "parts", []) if content else []
            if not parts:
                return self._get_fallback_analysis()
            
            text = getattr(parts[0], "text", None)
            if not text:
                return self._get_fallback_analysis()
            
            # Parse JSON response
            data = json.loads(text)
            
            # Validate required fields
            required_fields = ["fra_recommendation", "key_findings", "development_priorities", 
                             "risk_factors", "opportunities", "summary", "confidence"]
            for field in required_fields:
                if field not in data:
                    data[field] = [] if field.endswith("s") and field != "confidence" else "Not available"
            
            return data
            
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from Vertex AI analysis response")
            return self._get_fallback_analysis()
        except Exception:  # pragma: no cover - defensive
            logger.exception("Failed to parse Vertex AI analysis response")
            return self._get_fallback_analysis()
    
    def _get_fallback_analysis(self) -> dict:
        """Return fallback analysis when AI generation fails."""
        return {
            "fra_recommendation": "Unable to generate recommendation - manual review required",
            "key_findings": ["AI analysis unavailable"],
            "development_priorities": ["Require manual assessment"],
            "risk_factors": ["Data incomplete"],
            "opportunities": ["Further analysis needed"],
            "summary": "AI analysis could not be completed. Please review data manually.",
            "confidence": "Low"
        }














