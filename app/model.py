"""Pydantic data models for the DSS report."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field


class AOI(BaseModel):
    state: str
    district: str
    block: str
    village: str
    centroid_lat: Optional[float] = None
    centroid_lon: Optional[float] = None
    source_layer: Optional[str] = None
    # Additional context from resolved features
    area_sqkm: Optional[float] = None
    census_code: Optional[str] = None
    additional_attributes: Dict[str, Any] = Field(default_factory=dict)


class LULCPercentages(BaseModel):
    classes: Dict[str, float] = Field(default_factory=dict)
    # State-level forest data
    forest_area_sqkm: Optional[float] = None
    forest_percentage: Optional[float] = None
    scrub_area_sqkm: Optional[float] = None
    geographic_area_sqkm: Optional[float] = None


class GroundWater(BaseModel):
    # District-level groundwater metrics
    annual_extraction_mcm: Optional[float] = None  # Annual groundwater extraction (Million Cubic Meters)
    net_available_mcm: Optional[float] = None  # Net available groundwater
    stage_of_development_pc: Optional[float] = None  # Percentage of groundwater development
    category: Optional[str] = None  # Safe/Semi-critical/Critical/Over-exploited
    # Legacy fields
    district_pre2019_m: Optional[float] = None
    pre_post_delta_m: Optional[float] = None
    stressed: Optional[bool] = None


class Aquifer(BaseModel):
    type: Optional[str] = None
    code: Optional[str] = None


class MGNREGAStats(BaseModel):
    """MGNREGA employment statistics at district level."""
    jobcards_applied: Optional[int] = None
    jobcards_issued: Optional[int] = None
    registered_workers_total: Optional[int] = None
    registered_workers_sc: Optional[int] = None
    registered_workers_st: Optional[int] = None
    registered_workers_women: Optional[int] = None
    active_job_cards: Optional[int] = None
    active_workers_total: Optional[int] = None
    active_workers_sc: Optional[int] = None
    active_workers_st: Optional[int] = None
    active_workers_women: Optional[int] = None
    # Computed percentages
    jobcard_issuance_rate_pc: Optional[float] = None  # (issued/applied) * 100
    worker_activation_rate_pc: Optional[float] = None  # (active/registered) * 100
    women_participation_pc: Optional[float] = None  # (women/total) * 100


class IndicatorSet(BaseModel):
    lulc_pc: LULCPercentages = Field(default_factory=LULCPercentages)
    gw: GroundWater = Field(default_factory=GroundWater)
    aquifer: Aquifer = Field(default_factory=Aquifer)
    mgnrega: MGNREGAStats = Field(default_factory=MGNREGAStats)


class Narrative(BaseModel):
    language: str
    content: Optional[str] = None
    provider: Optional[str] = None


class AIAnalysis(BaseModel):
    """AI-generated analysis and recommendations for FRA and development interventions."""
    fra_recommendation: Optional[str] = None  # FRA eligibility recommendation
    key_findings: List[str] = Field(default_factory=list)  # Key insights from data
    development_priorities: List[str] = Field(default_factory=list)  # Recommended interventions
    risk_factors: List[str] = Field(default_factory=list)  # Environmental/social risks
    opportunities: List[str] = Field(default_factory=list)  # Development opportunities
    summary: Optional[str] = None  # Overall assessment
    confidence: Optional[str] = None  # Confidence level (High/Medium/Low)
    generated_at: Optional[datetime] = None
    model_used: Optional[str] = None


class ReportMeta(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.utcnow().replace(microsecond=0))
    data_sources: List[str] = Field(default_factory=list)
    stub_mode: bool = False
    notes: List[str] = Field(default_factory=list)


class Report(BaseModel):
    aoi: AOI
    indicators: IndicatorSet
    meta: ReportMeta
    narrative: Optional[Narrative] = None
    ai_analysis: Optional[AIAnalysis] = None
