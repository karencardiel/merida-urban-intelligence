"""
Master Pipeline Runner: Mérida Urban Intelligence Geospatial Data Warehouse
Executes end-to-end ingestion, geocoding, spatial assignment, and visualization.
"""
import sys
import time
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from src.config import RAW_DATA_DIR, PROCESSED_DATA_DIR, MAPS_DIR, FIGURES_DIR
from src.etl_safety_incidents import process_safety_incidents
from src.generate_visualizations import generate_all_visualizations


def run_full_pipeline():
    start_time = time.time()
    print("=" * 75)
    print("  MERIDA URBAN INTELLIGENCE: GEOSPATIAL DATA WAREHOUSE PIPELINE")
    print("=" * 75)

    # 1. Check directories
    print("\n[Step 1/4] Verifying directory structure...")
    for p in [RAW_DATA_DIR, PROCESSED_DATA_DIR, MAPS_DIR, FIGURES_DIR]:
        p.mkdir(parents=True, exist_ok=True)
    print("  [OK] Directories verified.")

    # 2. Public Safety / Traffic Incidents Ingestion & Geocoding
    print("\n[Step 2/4] Executing Public Safety & Traffic Incidents ETL...")
    incidents_df, types_df = process_safety_incidents()
    print(f"  [OK] Processed {len(incidents_df):,} geocoded incidents across Merida.")
    print(f"  [OK] Populated {len(types_df)} incident typologies.")

    # 3. Optional Cartography & Census if raw files are placed
    print("\n[Step 3/4] Checking raw cartographic and census archives...")
    if (RAW_DATA_DIR / "31_yucatan.zip").exists():
        from src.etl_cartography import extract_merida_cartography
        extract_merida_cartography()
        print("  [OK] Processed Marco Geoestadistico 2020.")
    else:
        print("  [INFO] 31_yucatan.zip not in data/raw/ (skipping raw shapefile extraction).")

    if (RAW_DATA_DIR / "denue_31_csv.zip").exists():
        from src.etl_denue import process_merida_denue
        process_merida_denue()
        print("  [OK] Processed DENUE 2020.")
    else:
        print("  [INFO] denue_31_csv.zip not in data/raw/ (skipping raw DENUE extraction).")

    # 4. Spatial Analytics & Map Generation
    print("\n[Step 4/4] Generating Spatial Analytics, Maps & Autocorrelation Figures...")
    generate_all_visualizations()
    print("  [OK] Generated publication-quality choropleths, LISA cluster maps, and Moran plots.")

    elapsed = time.time() - start_time
    print("\n" + "=" * 75)
    print(f"  PIPELINE EXECUTION COMPLETED IN {elapsed:.2f} SECONDS")
    print("=" * 75)
    print("\nGenerated Artifacts:")
    print(f"  - Cleaned Facts:   {PROCESSED_DATA_DIR / 'fact_traffic_incidents.csv'}")
    print(f"  - Typology Dim:    {PROCESSED_DATA_DIR / 'dim_incident_type.csv'}")
    print(f"  - Maps:            {MAPS_DIR}")
    print(f"  - Figures:         {FIGURES_DIR}")
    print("\nTo load into PostGIS, run:")
    print("  docker exec -i merida_postgis_dw psql -U postgres -d merida_dw < sql/01_schema.sql")
    print("  docker exec -i merida_postgis_dw psql -U postgres -d merida_dw < sql/02_load.sql")
    print("  docker exec -i merida_postgis_dw psql -U postgres -d merida_dw < sql/03_views.sql")


if __name__ == "__main__":
    run_full_pipeline()
