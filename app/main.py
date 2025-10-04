"""FastAPI application entrypoint."""
from __future__ import annotations

import csv
import io
import logging
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.encoders import jsonable_encoder

from .config import Settings, get_settings
from .indicators import IndicatorService
from .model import Report

logger = logging.getLogger(__name__)

app = FastAPI(title="DSS Report Generation Bot", version="0.1.0")


def get_indicator_service(settings: Settings = Depends(get_settings)) -> IndicatorService:
    return IndicatorService(settings=settings)


@app.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "ok",
        "stub_mode": settings.stub_mode,
        "use_vertex": settings.use_vertex,
    }


@app.get("/aoi/resolve")
def resolve_aoi(
    state: str = Query(...),
    district: Optional[str] = Query(None),
    block: Optional[str] = Query(None),
    village: Optional[str] = Query(None),
    service: IndicatorService = Depends(get_indicator_service),
) -> JSONResponse:
    try:
        aoi = service.resolve_aoi(state, district, block, village)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return JSONResponse(content=jsonable_encoder(aoi))


@app.get("/report")
def get_report(
    state: str = Query(...),
    district: Optional[str] = Query(None),
    block: Optional[str] = Query(None),
    village: Optional[str] = Query(None),
    lang: str | None = Query(None, alias="lang"),
    service: IndicatorService = Depends(get_indicator_service),
) -> JSONResponse:
    try:
        aoi = service.resolve_aoi(state, district, block, village)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        report: Report = service.build_report(aoi, language=lang)
    except Exception as exc:  # pragma: no cover
        logger.exception("Report generation failed")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}") from exc
    return JSONResponse(content=jsonable_encoder(report))


@app.get("/export/indicators.csv")
def export_indicators(
    state: str = Query(...),
    district: Optional[str] = Query(None),
    block: Optional[str] = Query(None),
    village: Optional[str] = Query(None),
    service: IndicatorService = Depends(get_indicator_service),
) -> StreamingResponse:
    report = _resolve_report(service, state, district, block, village)
    csv_bytes = _indicators_to_csv(report)
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=indicators.csv"},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_report(
    service: IndicatorService,
    state: str,
    district: Optional[str],
    block: Optional[str],
    village: Optional[str],
) -> Report:
    try:
        aoi = service.resolve_aoi(state, district, block, village)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return service.build_report(aoi)


def _indicators_to_csv(report: Report) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["indicator", "key", "value"])

    indicators = report.indicators
    writer.writerow(["lulc_pc", "json", jsonable_encoder(indicators.lulc_pc.classes)])

    gw = indicators.gw.dict()
    for key, value in gw.items():
        writer.writerow(["groundwater", key, value])

    aquifer = indicators.aquifer.dict()
    for key, value in aquifer.items():
        writer.writerow(["aquifer", key, value])

    mgnrega = indicators.mgnrega.dict()
    for key, value in mgnrega.items():
        writer.writerow(["mgnrega", key, value])

    return buffer.getvalue().encode("utf-8")
