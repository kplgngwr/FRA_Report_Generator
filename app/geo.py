"""Geospatial helper utilities."""
from __future__ import annotations

import math
from typing import Iterable, Optional, Tuple

from shapely.geometry import shape

EARTH_RADIUS_KM = 6371.0088


def geometry_centroid(feature: dict) -> Optional[Tuple[float, float]]:
    """Return centroid (lat, lon) for a GeoJSON-like or Esri JSON feature."""

    geometry = feature.get("geometry") if isinstance(feature, dict) else None
    if not geometry:
        return None

    try:
        # Convert Esri JSON geometry to GeoJSON if needed
        geojson_geom = _esri_to_geojson(geometry)
        geom = shape(geojson_geom)
    except Exception as e:
        return None

    centroid = geom.centroid
    return centroid.y, centroid.x


def _esri_to_geojson(esri_geom: dict) -> dict:
    """Convert Esri JSON geometry to GeoJSON format."""
    
    # If it has "rings", it's an Esri polygon
    if "rings" in esri_geom:
        return {
            "type": "Polygon",
            "coordinates": esri_geom["rings"]
        }
    
    # If it has "paths", it's an Esri polyline
    if "paths" in esri_geom:
        return {
            "type": "LineString" if len(esri_geom["paths"]) == 1 else "MultiLineString",
            "coordinates": esri_geom["paths"][0] if len(esri_geom["paths"]) == 1 else esri_geom["paths"]
        }
    
    # If it has "x" and "y", it's an Esri point
    if "x" in esri_geom and "y" in esri_geom:
        return {
            "type": "Point",
            "coordinates": [esri_geom["x"], esri_geom["y"]]
        }
    
    # Already GeoJSON or unknown format, return as-is
    return esri_geom


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance between two WGS84 points in kilometers."""

    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, (lat1, lon1, lat2, lon2))
    d_lat = lat2_rad - lat1_rad
    d_lon = lon2_rad - lon1_rad

    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(d_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def min_distance_km(base: Tuple[float, float], points: Iterable[Tuple[float, float]]) -> Optional[float]:
    """Compute the minimum Haversine distance between a base point and a set of points."""

    base_lat, base_lon = base
    distances = [haversine_km(base_lat, base_lon, lat, lon) for lat, lon in points]
    if not distances:
        return None
    return min(distances)


def simplify_polygon(feature: dict, tolerance: float = 0.0005) -> Optional[dict]:
    """Return a simplified version of the feature geometry (GeoJSON-like)."""

    geometry = feature.get("geometry") if isinstance(feature, dict) else None
    if not geometry:
        return None

    try:
        simplified = shape(geometry).simplify(tolerance, preserve_topology=True)
    except Exception:
        return None

    return json_geometry(simplified)


def json_geometry(geom) -> dict:
    """Convert a shapely geometry back into a GeoJSON-like dict."""

    mapping = geom.__geo_interface__
    return dict(mapping)
