"""Layer registry placeholders to be updated with real ArcGIS services."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


# State name mapping: Full Name <-> Abbreviation
STATE_NAME_MAPPING = {
    # Full name to abbreviation
    "Andaman and Nicobar Islands": "AN",
    "Andhra Pradesh": "AP",
    "Arunachal Pradesh": "AR",
    "Assam": "AS",
    "Bihar": "BR",
    "Chandigarh": "CH",
    "Chhattisgarh": "CT",
    "Dadra and Nagar Haveli and Daman and Diu": "DN",
    "Delhi": "DL",
    "Goa": "GA",
    "Gujarat": "GJ",
    "Haryana": "HR",
    "Himachal Pradesh": "HP",
    "Jammu and Kashmir": "JK",
    "Jharkhand": "JH",
    "Karnataka": "KA",
    "Kerala": "KL",
    "Ladakh": "LA",
    "Lakshadweep": "LD",
    "Madhya Pradesh": "MP",
    "Maharashtra": "MH",
    "Manipur": "MN",
    "Meghalaya": "ML",
    "Mizoram": "MZ",
    "Nagaland": "NL",
    "Odisha": "OR",
    "Puducherry": "PY",
    "Punjab": "PB",
    "Rajasthan": "RJ",
    "Sikkim": "SK",
    "Tamil Nadu": "TN",
    "Telangana": "TG",
    "Tripura": "TR",
    "Uttar Pradesh": "UP",
    "Uttarakhand": "UT",
    "West Bengal": "WB",
}

# Reverse mapping: Abbreviation to Full Name
STATE_ABBREV_TO_FULL = {v: k for k, v in STATE_NAME_MAPPING.items()}


def get_state_abbreviation(full_name: str) -> Optional[str]:
    """Convert full state name to abbreviation."""
    return STATE_NAME_MAPPING.get(full_name)


def get_state_full_name(abbreviation: str) -> Optional[str]:
    """Convert state abbreviation to full name."""
    return STATE_ABBREV_TO_FULL.get(abbreviation.upper())


@dataclass(slots=True)
class Layer:
    """Definition for a feature layer used by the report generator."""

    name: str
    url: str
    fields: List[str]
    state_field: Optional[str] = None
    district_field: Optional[str] = None
    description: Optional[str] = None
    name_field: Optional[str] = None
    parent_field: Optional[str] = None
    code_field: Optional[str] = None
    value_field: Optional[str] = None


# ---------------------------------------------------------------------------
# AOI layers (state -> district -> block -> village hierarchy)
# ---------------------------------------------------------------------------
AOI_LAYERS: Dict[str, Layer] = {
    "state": Layer(
        name="state",
        url="https://services5.arcgis.com/73n8CSGpSSyHr1T9/arcgis/rest/services/state_boundary/FeatureServer/0",
        fields=[
            "FID",
            "shape_leng",
            "State_Name",   # stored as two-letter abbreviation (e.g., "TR")
            "State_Cens",   # census/state code string used by other layers
            "State_FSI",    # full state name (e.g., "Tripura")
            "GA_sqkm",
            "VDF2019",
            "MDF2019",
            "OF2019",
            "Forest_201",
            "Per_GA_201",
            "Forest_200",
            "Ch_wrt2017",
            "Ch_per",
            "Scrub2019",
            "TC2019",
            "Fcount_RFA",
            "Extent_TOF",
            "Per_FTC_St",
            "Per_GA_Sta",
            "RFA_GW_as_",
            "nfa_orfa",
            "F_FC_Outsid",
            "st_area_sh",
            "st_length_",
            "Shape__Area",
            "Shape__Length",
            "GlobalID",
            "geometry",
        ],
        description="India state boundaries from Living Atlas service.",
        name_field="State_FSI",
        state_field="State_FSI",        # expects full state name (e.g., "Tripura")
        code_field="State_Cens",        # census/state code (e.g. "21")
    ),
    
        "district": Layer(
        name="district",
        url="https://services5.arcgis.com/73n8CSGpSSyHr1T9/arcgis/rest/services/district_boundary/FeatureServer/0",
        fields=[
            "FID",
            "District",         # input as district name (e.g., "Dhalai")
            "State",            # input as state-abbreviation (e.g., "TR" for Tripura)
            "Annual_Gro",
            "Annual_G00",
            "Annual_Rep",
            "Natural_Di",
            "Projected_",
            "Ground_Wat",
            "Net_Ground",
            "Annual_Dra",
            "Stage_of_d",
            "st_area_sh",
            "st_length_",
            "Shape__Area",
            "Shape__Length",
            "GlobalID",
            "geometry",
        ],
        description="District boundaries with groundwater assessment attributes.",
        name_field="District",      # expects district name as in the dataset
        state_field="State",        # scopes district lookup using the state abbreviation
    ),
    
    "village": Layer(
        name="village",
        url="https://livingatlas.esri.in/server/rest/services/IAB2024/IAB_Village_2024/MapServer/0",
        fields=[
            "objectid",
            "id",
            "name",                 # complete village name
            "subdistrict",
            "District",             # district name (e.g., "Dhalai")
            "State",                # complete state name (e.g., "Tripura")
            "country",
            "censusname",
            "villagename_locallang",
            "lgd_villagename",
            "lgd_villagecode",
            "lgd_subdistrictcode",
            "lgd_districtcode",
            "lgd_statecode",        # code for state (e.g., "16" for Tripura)
            "censuscode2001",
            "censuscode2011",
            "censuscode2021",
            "level_2011",
            "tru_2011",
            "shape",
        ],
        description="India village boundaries (Living Atlas 2024).",
        name_field="name",                      # village name as published in the Living Atlas layer
        parent_field="lgd_subdistrictcode",     # LGD subdistrict code for relational filtering
        code_field="lgd_villagecode",
        state_field="State",                     # scopes district using complete state name
        district_field="district",
    ),
}

# Indicator layers
INDICATOR_LAYERS: Dict[str, Layer] = {
    "groundwater_pre_monsoon": Layer(
        name="groundwater_pre_monsoon",
        url="https://livingatlas.esri.in/server1/rest/services/Water/Pre_Post_Monsoon_Water_Level_Depth/FeatureServer/1",
        fields=[
            "objectid",
            "state_",               # complete state name (e.g., "Tripura")
            "district_name",        # district name (e.g., "Dhalai")
            "block_",
            "village_name",         # village name (e.g., "Some Village")
            "lat",
            "long",
            "date_",
            "dtwl_",                # depth to water level (latest, mbgl)
        ],
        description="Pre-monsoon groundwater depth measurements (latest, mbgl).",
        name_field="district_name",
        parent_field="state_",
        state_field="state_",
        district_field="district_name",
        value_field="dtwl_",
    ),

    "groundwater_during_monsoon": Layer(
        name="groundwater_during_monsoon",
        url="https://livingatlas.esri.in/server1/rest/services/Water/Pre_Post_Monsoon_Water_Level_Depth/FeatureServer/2",
        fields=[
            "objectid",
            "State",            # complete state name (e.g., "Tripura")
            "district_name",    # district name (e.g., "Dhalai")
            "block_",
            "village_name",     # village name (e.g., "Some Village")
            "lat",
            "long",
            "date_",
            "wl_mbgl",          # during-monsoon water level (mbgl)
        ],
        description="During-monsoon groundwater depth measurements (mbgl).",
        name_field="district_name",
        parent_field="state",
        state_field="State",
        district_field="district_name",
        value_field="wl_mbgl",
    ),

    "groundwater_post_monsoon": Layer(
        name="groundwater_post_monsoon",
        url="https://livingatlas.esri.in/server1/rest/services/Water/Pre_Post_Monsoon_Water_Level_Depth/FeatureServer/3",
        fields=[
            "objectid",
            "State",            # complete state name (e.g., "Tripura")
            "district_name",    # district name (e.g., "Dhalai")
            "block_",
            "village_name",     # village name (e.g., "Some Village")
            "lat",
            "long",
            "date_",
            "wl_mbgl",          # post-monsoon water level (mbgl)
        ],
        description="Post-monsoon groundwater depth measurements (mbgl).",
        name_field="district_name",
        parent_field="state",
        state_field="State",
        district_field="district_name",
        value_field="wl_mbgl",
    ),
    
    "aquifer": Layer(
        name="aquifer",
        url="https://livingatlas.esri.in/server1/rest/services/Water/Major_Aquifers/MapServer/0",
        fields=[
            "objectid",
            "state_name",       # complete state name (e.g., "Tripura")
            "new_code_14",
            "aquifer",          # aquifer type (e.g., "Alluvium")
            "newcode43",
            "aquifer_0",        # Younger Alluvium (Clay/Silt/Sand/ Calcareous concretions)
            "systems",
            "zone_m",
            "mbgl",
            "avg_mbgl",
            "yield_gw",
            "m3_per_day",
            "per_cm",
            "pa_order",
            
        ],
        description="Major aquifer polygons with lithology and recharge attributes.",
        name_field="state_name",
        code_field="new_code_14",
        state_field="state_name",
        value_field="aquifer",
    ),
    
    
    "rural_facilities": Layer(
        name="rural_facilities",
        url="https://livingatlas.esri.in/server1/rest/services/PMGSY/IN_PMGSY_RuralFacilities_2021/MapServer/0",
        fields=[
            "objectid",
            "facility_id",
            "facilityname",
            "facilitycat",
            "hab_id",
            "habname",
            "block_id",
            "block",
            "dist_id",
            "District",  
            "state_id",
            "State",
            "geometry",
        ],
        description="Rural facilities (Agro, Education, Medical, Transport/Admin) across India.",
        name_field="facilityname",
        state_field="State",
        district_field="District",
    ),
    
    "mgnrega_workers": Layer(
        name="mgnrega_workers",
        url="https://livingatlas.esri.in/server1/rest/services/MGNREGA/IN_DT_CategoryWiseHHWorkers/MapServer/0",
        fields=[
            "objectid",
            "district_name",
            "state_name",
            "lgd_district_code",
            "census_code_2011",
            "number_of_jobcards_applied_for",
            "number_of_jobcards_issued",
            "registered_workers_sc",
            "registered_workers_st",
            "registered_workers_oth",
            "registered_workers_total",
            "registered_workers_women",
            "number_of_active_job_cards",
            "active_workers_sc",
            "active_workers_st",
            "active_workers_oth",
            "active_workers_total_workers",
            "active_workers_women",
            "shape",
            "st_area(shape)",
            "st_perimeter(shape)",
        ],
        description="MGNREGA district-wise employment statistics including job cards and worker categories.",
        name_field="district_name",
        state_field="state_name",
        district_field="district_name",
    ),
}


def list_all_layers() -> Dict[str, Dict[str, Layer]]:
    """Convenience helper for debugging and documentation."""

    return {
        "aoi": AOI_LAYERS,
        "indicator": INDICATOR_LAYERS,
    }


















