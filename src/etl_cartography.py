"""
ETL Module for Cartographic Boundaries (Marco Geoestadístico 2020)
Extracts and validates Mérida urban blocks (manzanas) and AGEBs.
"""
import os
import zipfile
import geopandas as gpd
import pandas as pd
from src.config import (
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    CVE_MUN,
    CVE_LOC,
    SRID_PROJECTED,
    SRID_WGS84
)


def extract_merida_cartography(zip_filename="31_yucatan.zip"):
    """
    Extracts and filters AGEBs and Manzanas for the urban core of Mérida.
    Outputs cleaned files to data/processed.
    """
    zip_path = RAW_DATA_DIR / zip_filename
    if not zip_path.exists():
        raise FileNotFoundError(
            f"Cartography archive not found at {zip_path}. Please place {zip_filename} in data/raw/"
        )

    print("Extracting Cartography layers from ZIP...")
    
    # 1. Process Urban Blocks (Manzanas - 31m.shp)
    uri_blocks = f"zip://{zip_path}!conjunto_de_datos/31m.shp"
    gdf_all_blocks = gpd.read_file(uri_blocks)
    
    # Filter for City of Mérida
    gdf_merida_blocks = gdf_all_blocks[
        (gdf_all_blocks["CVE_MUN"] == CVE_MUN) &
        (gdf_all_blocks["CVE_LOC"] == CVE_LOC)
    ].copy()
    
    print(f"Loaded {len(gdf_merida_blocks)} urban blocks for Mérida city.")

    # Project to EPSG:6372 to calculate accurate planar area in m2
    gdf_merida_blocks = gdf_merida_blocks.to_crs(epsg=SRID_PROJECTED)
    gdf_merida_blocks["area_m2"] = gdf_merida_blocks.geometry.area.round(2)
    gdf_merida_blocks["geometry"] = gdf_merida_blocks.geometry.buffer(0) # Repair any self-intersections
    
    # Save WGS84 copy for web export
    gdf_blocks_wgs84 = gdf_merida_blocks.to_crs(epsg=SRID_WGS84)
    out_blocks = PROCESSED_DATA_DIR / "dim_block.geojson"
    gdf_blocks_wgs84.to_file(out_blocks, driver="GeoJSON")
    print(f"Saved cleaned blocks to {out_blocks}")

    # 2. Process Urban AGEBs (31a.shp)
    uri_agebs = f"zip://{zip_path}!conjunto_de_datos/31a.shp"
    gdf_all_agebs = gpd.read_file(uri_agebs)
    
    gdf_merida_agebs = gdf_all_agebs[
        (gdf_all_agebs["CVE_MUN"] == CVE_MUN) &
        (gdf_all_agebs["CVE_LOC"] == CVE_LOC)
    ].copy()
    
    print(f"Loaded {len(gdf_merida_agebs)} urban AGEBs for Mérida city.")

    gdf_merida_agebs = gdf_merida_agebs.to_crs(epsg=SRID_PROJECTED)
    gdf_merida_agebs["area_km2"] = (gdf_merida_agebs.geometry.area / 1_000_000.0).round(4)
    gdf_merida_agebs["geometry"] = gdf_merida_agebs.geometry.buffer(0)

    gdf_agebs_wgs84 = gdf_merida_agebs.to_crs(epsg=SRID_WGS84)
    out_agebs = PROCESSED_DATA_DIR / "dim_ageb.geojson"
    gdf_agebs_wgs84.to_file(out_agebs, driver="GeoJSON")
    print(f"Saved cleaned AGEBs to {out_agebs}")

    return gdf_merida_blocks, gdf_merida_agebs


if __name__ == "__main__":
    extract_merida_cartography()
