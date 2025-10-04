import requests
import json

print("Testing enhanced DSS Report with MGNREGA data...\n")

response = requests.get("http://127.0.0.1:8000/report", params={"state": "Tripura", "district": "Dhalai"})
print("Status Code:", response.status_code)

if response.status_code == 200:
    data = response.json()
    print("\n" + "="*80)
    print("ENHANCED DSS REPORT - Dhalai, Tripura")
    print("="*80)
    
    # AOI Information
    print("\n📍 AREA OF INTEREST:")
    aoi = data.get("aoi", {})
    print(f"  Location: {aoi.get('district')}, {aoi.get('state')}")
    print(f"  Centroid: {aoi.get('centroid_lat'):.4f}°N, {aoi.get('centroid_lon'):.4f}°E")
    if aoi.get('area_sqkm'):
        print(f"  Area: {aoi.get('area_sqkm'):.2f} sq km")
    
    # Indicators
    indicators = data.get("indicators", {})
    
    # Forest/LULC Data
    print("\n🌳 FOREST COVER (State-level):")
    lulc = indicators.get("lulc_pc", {})
    if lulc.get("forest_area_sqkm"):
        print(f"  Forest Area: {lulc.get('forest_area_sqkm'):.2f} sq km")
        print(f"  Forest %: {lulc.get('forest_percentage'):.2f}%")
        print(f"  Scrub Area: {lulc.get('scrub_area_sqkm'):.2f} sq km")
        print(f"  Geographic Area: {lulc.get('geographic_area_sqkm'):.2f} sq km")
    
    # Groundwater Data
    print("\n💧 GROUNDWATER (District-level):")
    gw = indicators.get("gw", {})
    if gw.get("annual_extraction_mcm"):
        print(f"  Annual Extraction: {gw.get('annual_extraction_mcm'):.2f} MCM")
        print(f"  Net Available: {gw.get('net_available_mcm'):.2f} MCM")
        print(f"  Development Stage: {gw.get('stage_of_development_pc'):.2f}%")
        print(f"  Category: {gw.get('category')}")
    if gw.get("district_pre2019_m"):
        print(f"  Water Level (measurement): {gw.get('district_pre2019_m'):.2f} m")
    
    # Aquifer
    print("\n🏔️ AQUIFER:")
    aquifer = indicators.get("aquifer", {})
    if aquifer.get("type"):
        print(f"  Type: {aquifer.get('type')}")
        print(f"  Code: {aquifer.get('code')}")
    
    # Access to Facilities
    print("\n🏥 ACCESS TO FACILITIES:")
    access = indicators.get("access_km", {})
    if access.get("market"):
        print(f"  Nearest Market: {access.get('market'):.2f} km")
    if access.get("phc"):
        print(f"  Nearest PHC/Health: {access.get('phc'):.2f} km")
    if access.get("school_sec"):
        print(f"  Nearest School: {access.get('school_sec'):.2f} km")
    if access.get("bank_post"):
        print(f"  Nearest Bank/Post: {access.get('bank_post'):.2f} km")
    
    # MGNREGA Employment Data
    print("\n👷 MGNREGA EMPLOYMENT STATISTICS:")
    mgnrega = indicators.get("mgnrega", {})
    if mgnrega.get("jobcards_applied"):
        print(f"  Job Cards Applied: {mgnrega.get('jobcards_applied'):,}")
        print(f"  Job Cards Issued: {mgnrega.get('jobcards_issued'):,}")
        if mgnrega.get("jobcard_issuance_rate_pc"):
            print(f"  Issuance Rate: {mgnrega.get('jobcard_issuance_rate_pc'):.2f}%")
    
    if mgnrega.get("registered_workers_total"):
        print(f"\n  Total Registered Workers: {mgnrega.get('registered_workers_total'):,}")
        print(f"    - SC: {mgnrega.get('registered_workers_sc'):,}")
        print(f"    - ST: {mgnrega.get('registered_workers_st'):,}")
        print(f"    - Women: {mgnrega.get('registered_workers_women'):,}")
    
    if mgnrega.get("active_workers_total"):
        print(f"\n  Total Active Workers: {mgnrega.get('active_workers_total'):,}")
        print(f"    - SC: {mgnrega.get('active_workers_sc'):,}")
        print(f"    - ST: {mgnrega.get('active_workers_st'):,}")
        print(f"    - Women: {mgnrega.get('active_workers_women'):,}")
        if mgnrega.get("worker_activation_rate_pc"):
            print(f"  Worker Activation Rate: {mgnrega.get('worker_activation_rate_pc'):.2f}%")
        if mgnrega.get("women_participation_pc"):
            print(f"  Women Participation: {mgnrega.get('women_participation_pc'):.2f}%")
    
    # Sites
    print("\n🚧 RECOMMENDED INTERVENTION SITES:")
    sites = data.get("sites", {})
    if sites.get("farm_pond"):
        print(f"  Farm Ponds: {len(sites['farm_pond'])} sites")
    if sites.get("check_dam"):
        print(f"  Check Dams: {len(sites['check_dam'])} sites")
    
    # Metadata
    print("\n📋 REPORT METADATA:")
    meta = data.get("meta", {})
    print(f"  Generated: {meta.get('generated_at')}")
    print(f"  Notes: {', '.join(meta.get('notes', []))}")
    
    print("\n" + "="*80)
    print("\n✅ Full JSON Response:")
    print(json.dumps(data, indent=2))
else:
    print("\n❌ Error Response:")
    print(json.dumps(response.json(), indent=2))

