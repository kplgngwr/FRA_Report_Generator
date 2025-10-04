# Layer Configuration Guide

This guide explains how to configure layers in `app/layers.py` so the report engine knows:
- **Which field to query** when matching user input (e.g., state name)
- **Which fields to filter by** for hierarchical lookups (state → district → block → village)
- **Which fields to extract** for the output report

---

## Layer Definition Fields

Each `Layer` in the registry has these key properties:

### Core Fields
- **`name`**: Internal identifier (e.g., `"state"`, `"district"`)
- **`url`**: ArcGIS REST endpoint (FeatureServer or MapServer layer)
- **`fields`**: List of attribute names to request from the service
- **`description`**: Human-readable purpose

### Query & Filter Fields
- **`name_field`**: The attribute to match when user provides a name
  - Example: `name_field="State_FSI"` means when user passes `state=Tripura`, query `WHERE State_FSI = 'Tripura'`
  
- **`state_field`**: The attribute holding state name/code for filtering child layers
  - Example: District layer with `state_field="State"` will filter `WHERE State = 'Tripura'` when resolving districts within Tripura
  
- **`district_field`**: The attribute holding district name/code for filtering child layers
  - Example: Village layer with `district_field="district"` will filter `WHERE district = 'Pune'`
  
- **`code_field`**: The attribute holding a unique code/ID for this feature
  - Used to extract codes for context (e.g., state census code)
  
- **`parent_field`**: The attribute linking this layer to its parent (for hierarchical lookups)
  - Example: Block layer with `parent_field="DISTRICT_ID"` will filter `WHERE DISTRICT_ID = <resolved_district_id>`
  
- **`value_field`**: The attribute holding the numeric value for indicator layers
  - Example: Groundwater layer with `value_field="wl_mbgl"` extracts depth measurements

---

## How the Report Engine Uses These Fields

### 1. AOI Resolution (State → District → Block → Village)

When user calls `/report?state=Tripura&district=Dhalai`:

1. **State lookup**:
   - Query: `WHERE UPPER(State_FSI) = UPPER('Tripura')` (uses `name_field`)
   - Extract: `State_FSI`, `State_Cens` values
   - Store in context: `state_name="Tripura"`, `state_code="21"`

2. **District lookup**:
   - Query: `WHERE UPPER(District) = UPPER('Dhalai') AND UPPER(State) = UPPER('TR')` 
     - Uses district layer's `name_field="District"` for matching "Dhalai"
     - Uses district layer's `state_field="State"` to filter by parent state
   - Extract: District attributes
   - Store in context: `district_name="Dhalai"`

3. **Geometry selection**:
   - Uses the most specific feature found (village > block > district > state)
   - Computes centroid for proximity queries

### 2. Indicator Layer Queries

For indicator layers (groundwater, aquifer, access, etc.):

- **Filter by AOI**: Uses `state_field` and `district_field` to scope results
  - Example: Groundwater layer with `state_field="state"` and `district_field="district_name"` 
  - Query: `WHERE UPPER(state) = UPPER('Tripura') AND UPPER(district_name) = UPPER('Dhalai')`

- **Extract values**: Uses `value_field` to get numeric measurements
  - Example: `value_field="wl_mbgl"` pulls groundwater depth in meters below ground level

- **Aggregate**: Computes averages, counts, or other aggregations across matching features

---

## Configuration Examples

### Example 1: State Layer
```python
"state": Layer(
    name="state",
    url="https://services.../state_boundary/FeatureServer/0",
    fields=["FID", "State_FSI", "State_Name", "State_Cens", "geometry"],
    name_field="State_FSI",      # Match user input against full state name
    code_field="State_Cens",     # Extract census code for context
    description="India state boundaries",
)
```
- User passes `state=Tripura` → Queries `WHERE State_FSI = 'Tripura'`
- Extracts `State_FSI` and `State_Cens` into context

### Example 2: District Layer
```python
"district": Layer(
    name="district",
    url="https://services.../district_boundary/FeatureServer/0",
    fields=["FID", "District", "State", "geometry"],
    name_field="District",       # Match user's district name
    state_field="State",         # Filter by parent state abbreviation
    description="District boundaries",
)
```
- User passes `district=Dhalai` with context `state_name="Tripura"` 
- Queries `WHERE District = 'Dhalai' AND State = 'TR'`
  - **Note**: If state layer stores "Tripura" but district layer expects "TR", you need to:
    - Either store the abbreviation in context during state resolution, OR
    - Use a mapping/lookup to convert full name to abbreviation

### Example 3: Groundwater Indicator Layer
```python
"groundwater": Layer(
    name="groundwater",
    url="https://livingatlas.../Water_Level_Depth/FeatureServer/0",
    fields=["objectid", "state", "district_name", "wl_mbgl"],
    state_field="state",          # Filter by state (expects full name)
    district_field="district_name", # Filter by district name
    value_field="wl_mbgl",        # Extract water level measurement
    description="Pre-monsoon groundwater depth",
)
```
- Queries `WHERE state = 'Tripura' AND district_name = 'Dhalai'`
- Extracts `wl_mbgl` values and computes average depth

### Example 4: Village Layer with Parent Linking
```python
"village": Layer(
    name="village",
    url="https://livingatlas.../IAB_Village_2024/MapServer/0",
    fields=["name", "district", "state", "lgd_subdistrictcode"],
    name_field="name",                    # Match village name
    state_field="state",                  # Filter by state name
    district_field="district",            # Filter by district name
    parent_field="lgd_subdistrictcode",   # Link to parent subdistrict
    code_field="lgd_villagecode",         # Extract village code
    description="Village boundaries",
)
```
- Queries `WHERE name = 'SomeVillage' AND state = 'Tripura' AND district = 'Dhalai'`
- If parent block was resolved, also filters `AND lgd_subdistrictcode = <block_code>`

---

## Tuning Guidelines

### 1. Field Name Mismatches
If different layers use different field names for the same concept:
- **State name**: One layer uses `State_FSI` (full name), another uses `State` (abbreviation)
- **Solution**: Use the exact field name in each layer's configuration
- **Tip**: Store both full name and abbreviation in context during state resolution if needed

### 2. Hierarchical Filtering
For child layers that need parent context:
- Set `state_field` to the attribute holding state identifier
- Set `district_field` to the attribute holding district identifier
- The engine will automatically add `WHERE state_field = <resolved_state>` filters

### 3. Value Extraction
For indicator layers returning measurements:
- Set `value_field` to the numeric attribute
- The engine will extract and aggregate those values

### 4. Missing Layers
If a layer is unavailable or commented out:
- The engine gracefully skips it
- Reports include a note like "District layer not configured; using state boundary"

---

## Validation Checklist

Before deploying a new layer configuration:

1. ✅ **Verify field names** in the ArcGIS REST service metadata
   - Visit `<layer_url>?f=json` to see actual field names and types

2. ✅ **Test matching logic** with known data
   - Example: If your state layer has `State_FSI="Tripura"`, set `name_field="State_FSI"`

3. ✅ **Check parent filters** for hierarchical layers
   - District layer's `state_field` must match the attribute holding state identifier
   - Verify the format (full name vs. abbreviation vs. code)

4. ✅ **Confirm value fields** for indicators
   - Ensure `value_field` points to a numeric column (not text or ID)

5. ✅ **Add debug logging** if needed
   - The engine logs `WHERE` clauses at DEBUG level
   - Use `--log-config logging.conf` to see query details

---

## Quick Reference: Field Mapping Flow

```
User Input → name_field → WHERE clause
  ↓
Context extraction → code_field, parent_field → Stored for child lookups
  ↓
Child layer query → state_field, district_field → Filter by parent
  ↓
Value extraction → value_field → Aggregated into indicators
```

---

For questions or issues, check the DEBUG logs to see the exact WHERE clauses being generated.
