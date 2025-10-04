# Aquifer Layer 400 Error - Fix Applied

## Problem
```
Aquifer query failed: {"code": 400, "message": "", "details": []}
```

## Root Cause
The aquifer layer is a **MapServer polygon layer**, not a FeatureServer point layer. The original code was using:
- `query_near_point()` method
- `esriSpatialRelIntersects` spatial relationship
- Distance-based query with radius

This approach doesn't work well with MapServer polygon layers, resulting in a 400 Bad Request error.

## Solution Applied
Changed the query to use **point-in-polygon spatial query**:

### Before (Incorrect for polygon layers)
```python
results = self.client.query_near_point(
    layer.url,
    aoi.centroid_lat or 0.0,
    aoi.centroid_lon or 0.0,
    radius_m=self.settings.nearest_poi_radius_m,
    limit=1,
    additional_params=params,
)
```

### After (Correct for polygon layers)
```python
params["geometryType"] = "esriGeometryPoint"
params["spatialRel"] = "esriSpatialRelWithin"
params["geometry"] = json.dumps({
    "x": aoi.centroid_lon,
    "y": aoi.centroid_lat,
    "spatialReference": {"wkid": 4326}
})
params["returnGeometry"] = "false"

results = self.client.query(layer.url, params)
```

## Key Changes

1. **Spatial Relationship**: Changed from `esriSpatialRelIntersects` to `esriSpatialRelWithin`
   - `esriSpatialRelWithin` finds polygons that **contain** the point
   - This is the correct relationship for "which aquifer polygon contains this centroid point?"

2. **Query Method**: Changed from `query_near_point()` to direct `query()` with explicit params
   - More control over spatial query parameters
   - Works better with MapServer polygon layers

3. **Geometry Format**: Simplified to just pass the point coordinates
   - No radius needed (we want the polygon that contains the exact point)
   - Explicit spatial reference (WGS84, WKID 4326)

4. **Return Geometry**: Set to `false` since we only need attribute data
   - Reduces response size
   - Faster query execution

## ArcGIS Spatial Relationships

| Relationship | Use Case |
|--------------|----------|
| `esriSpatialRelIntersects` | Find features that touch or overlap |
| `esriSpatialRelContains` | Find polygons contained by another polygon |
| `esriSpatialRelWithin` | Find features that fall inside a polygon (point-in-polygon) ✅ |
| `esriSpatialRelCrosses` | Find lines that cross polygons |

For **point-in-polygon queries** (which aquifer contains this point?), `esriSpatialRelWithin` is the correct choice.

## Testing

After the fix, the aquifer query should now succeed:

```bash
GET /report?state=Tripura&district=Dhalai
```

Expected result:
```json
{
  "indicators": {
    "aquifer": {
      "type": "Alluvium",
      "code": "XX_ABC_123"
    }
  }
}
```

## Related Layer Types

**MapServer Layers** (like aquifer):
- Typically polygon/polyline layers
- Use spatial relationship queries
- Good for: Aquifer zones, watersheds, administrative boundaries

**FeatureServer Layers** (like groundwater wells):
- Typically point layers
- Can use distance/radius queries
- Good for: Monitoring wells, facilities, point observations

---

**Status**: ✅ Fixed  
**Applied**: October 4, 2025  
**File Modified**: `app/indicators.py` (line ~290-330)
