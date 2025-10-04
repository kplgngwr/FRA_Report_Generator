from datetime import datetime

from app.model import (
    AOI,
    AccessKM,
    Aquifer,
    GroundWater,
    IndicatorSet,
    LULCPercentages,
    Report,
    ReportMeta,
    SiteCollection,
)


def build_default_report() -> Report:
    aoi = AOI(state="State", district="District", block="Block", village="Village")
    indicators = IndicatorSet(
        lulc_pc=LULCPercentages(classes={"forest": 50.0}),
        gw=GroundWater(district_pre2019_m=12.0, pre_post_delta_m=1.0, stressed=True),
        aquifer=Aquifer(type="Hard rock", code="HRK"),
        access_km=AccessKM(market=10.0, phc=15.0, school_sec=5.0, bank_post=7.0),
    )
    sites = SiteCollection()
    meta = ReportMeta(generated_at=datetime.utcnow(), data_sources=["test"], stub_mode=True)
    return Report(aoi=aoi, indicators=indicators, sites=sites, meta=meta)


def test_report_schema_serialization():
    report = build_default_report()
    payload = report.dict()
    assert payload["aoi"]["state"] == "State"
    assert payload["indicators"]["gw"]["stressed"] is True
    assert payload["meta"]["stub_mode"] is True


def test_indicator_defaults():
    indicators = IndicatorSet()
    assert indicators.lulc_pc.classes == {}
    assert indicators.gw.stressed is None
