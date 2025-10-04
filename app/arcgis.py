"""ArcGIS REST API client utilities."""
from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

import requests

logger = logging.getLogger(__name__)


class ArcGISError(RuntimeError):
    """Raised when the ArcGIS service returns an error response."""


@dataclass(slots=True)
class ArcGISClient:
    """Simple ArcGIS REST API client with pagination and retry logic."""

    token: Optional[str] = None
    timeout: int = 30
    max_retries: int = 5
    backoff_factor: float = 0.6
    _session: requests.Session = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._session = requests.Session()

    def query(self, url: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a paginated query against an ArcGIS feature layer."""

        payload = dict(params or {})
        payload.setdefault("where", "1=1")
        payload.setdefault("outFields", "*")
        payload.setdefault("resultOffset", 0)
        payload.setdefault("resultRecordCount", 2000)
        payload.setdefault("returnGeometry", "true")
        payload.setdefault("outSR", 4326)
        payload["f"] = "json"

        items: List[Dict[str, Any]] = []
        offset = int(payload.get("resultOffset", 0) or 0)

        # Ensure we call the /query endpoint even if the caller passed the layer root URL
        request_url = url if url.rstrip("/").endswith("/query") else f"{url.rstrip('/')}/query"

        while True:
            payload["resultOffset"] = offset
            page = self._request(request_url, payload)
            features = page.get("features", [])
            items.extend(features)

            exceeded = page.get("exceededTransferLimit", False)
            if not exceeded or not features:
                break

            offset += len(features)

        return items

    def query_by_where(
        self,
        url: str,
        where: str,
        out_fields: str = "*",
        additional_params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        params = dict(additional_params or {})
        params["where"] = where
        params["outFields"] = out_fields
        return self.query(url, params)

    def query_intersect_polygon(
        self,
        url: str,
        polygon_geojson: Dict[str, Any],
        spatial_relationship: str = "esriSpatialRelIntersects",
        additional_params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        params = dict(additional_params or {})
        params.setdefault("geometryType", "esriGeometryPolygon")
        params.setdefault("spatialRel", spatial_relationship)
        params["geometry"] = json.dumps(
            {
                "rings": polygon_geojson["coordinates"],
                "spatialReference": {"wkid": 4326},
            }
        )
        return self.query(url, params)

    def query_near_point(
        self,
        url: str,
        lat: float,
        lon: float,
        radius_m: float,
        order_by_fields: Optional[str] = None,
        limit: Optional[int] = None,
        additional_params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        params = dict(additional_params or {})
        params.setdefault("geometryType", "esriGeometryPoint")
        params.setdefault("distance", radius_m)
        params.setdefault("units", "esriMeters")
        params.setdefault("spatialRel", "esriSpatialRelIntersects")
        params["geometry"] = json.dumps(
            {
                "x": lon,
                "y": lat,
                "spatialReference": {"wkid": 4326},
            }
        )
        if order_by_fields:
            params["orderByFields"] = order_by_fields
        if limit:
            params["resultRecordCount"] = limit

        return self.query(url, params)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the ArcGIS REST endpoint with retry handling."""

        attempt = 0
        while True:
            attempt += 1
            payload = dict(params)
            if self.token:
                payload["token"] = self.token

            response = self._session.post(url, data=payload, timeout=self.timeout)

            if response.status_code in {429, 500, 502, 503, 504}:
                if attempt > self.max_retries:
                    logger.error("Max retries exceeded for %s", url)
                    response.raise_for_status()
                self._sleep(attempt)
                continue

            response.raise_for_status()
            data = response.json()

            if "error" in data:
                raise ArcGISError(json.dumps(data["error"]))

            return data

    def _sleep(self, attempt: int) -> None:
        base = self.backoff_factor * (2 ** (attempt - 1))
        jitter = random.uniform(0, base / 2)
        time.sleep(base + jitter)




