"""
Geocoding and Spatial Snapping Utilities for Mérida Urban Intelligence
"""
import re
import numpy as np
import pandas as pd

try:
    import geopandas as gpd
    from shapely.geometry import Point
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False

# Geographic center anchor: Plaza Grande (Calle 60 x Calle 61, Centro, Mérida)
CENTRO_LAT = 20.9673
CENTRO_LON = -89.6237
METERS_PER_DEG_LAT = 110574.0
METERS_PER_DEG_LON = 103950.0
BLOCK_SIZE_METERS = 100.0  # Approx average block length in Mérida grid


def parse_street_number(street_text):
    """Extract numeric street identifier from textual input."""
    if not street_text or pd.isna(street_text):
        return None
    match = re.search(r'\b(\d{1,3})\b', str(street_text))
    return int(match.group(1)) if match else None


def geocode_merida_grid_intersection(calle_ns, calle_ew, jitter_meters=5.0):
    """
    Geocode a street intersection based on Mérida's Cartesian urban street grid.
    Even-numbered streets run North-South (higher numbers to the West).
    Odd-numbered streets run East-West (higher numbers to the South).
    
    Center Reference: Calle 60 (N-S) & Calle 61 (E-W) at Plaza Grande.
    """
    n1 = parse_street_number(calle_ns)
    n2 = parse_street_number(calle_ew)
    
    if n1 is None or n2 is None:
        # Fallback to Centro anchor with random neighborhood dispersion
        lat = CENTRO_LAT + np.random.uniform(-0.02, 0.02)
        lon = CENTRO_LON + np.random.uniform(-0.02, 0.02)
        return lat, lon

    # Identify which is N-S (even) and which is E-W (odd)
    if n1 % 2 == 0 and n2 % 2 != 0:
        c_even, c_odd = n1, n2
    elif n1 % 2 != 0 and n2 % 2 == 0:
        c_even, c_odd = n2, n1
    else:
        c_even, c_odd = n1, n2

    # Calculate offset in meters from Plaza Grande (60 x 61)
    # Higher even numbers are to the West (negative Lon)
    # Higher odd numbers are to the South (negative Lat)
    delta_x_meters = -1.0 * (c_even - 60) * BLOCK_SIZE_METERS
    delta_y_meters = -1.0 * (c_odd - 61) * BLOCK_SIZE_METERS

    # Apply small realistic jitter for intersection width
    jitter_x = np.random.uniform(-jitter_meters, jitter_meters)
    jitter_y = np.random.uniform(-jitter_meters, jitter_meters)

    lat = CENTRO_LAT + ((delta_y_meters + jitter_y) / METERS_PER_DEG_LAT)
    lon = CENTRO_LON + ((delta_x_meters + jitter_x) / METERS_PER_DEG_LON)

    return round(float(lat), 7), round(float(lon), 7)


def snap_points_to_blocks(points_gdf, blocks_gdf, max_distance_meters=35.0):
    """
    Topologically matches point coordinates to urban block polygons.
    
    Phase 1: Strict containment (within/intersects).
    Phase 2: Nearest neighbor snapping for points landing on street corridors.
    """
    if not HAS_GEOPANDAS:
        raise ImportError("geopandas is required for spatial snapping")

    # Ensure projected CRS for distance calculations (meters)
    pts = points_gdf.to_crs(epsg=6372).copy()
    blks = blocks_gdf.to_crs(epsg=6372).copy()

    # Retain only key columns from blocks
    blks_subset = blks[['cvegeo', 'cve_ageb', 'cve_mza', 'geometry']]

    # 1. Point-in-polygon join
    joined = gpd.sjoin(pts, blks_subset, how='left', predicate='within')
    joined = joined.rename(columns={'cvegeo': 'cvegeo_manzana'})

    # 2. Nearest block fallback for boundary/street points
    unmatched_mask = joined['cvegeo_manzana'].isna()
    if unmatched_mask.any():
        unmatched_pts = joined[unmatched_mask].drop(
            columns=['cvegeo_manzana', 'cve_ageb_right', 'cve_mza', 'index_right'],
            errors='ignore'
        )
        
        nearest_joined = gpd.sjoin_nearest(
            unmatched_pts,
            blks_subset,
            how='left',
            max_distance=max_distance_meters
        )
        
        joined.loc[unmatched_mask, 'cvegeo_manzana'] = nearest_joined['cvegeo'].values
        if 'cve_ageb_right' in nearest_joined.columns:
            joined.loc[unmatched_mask, 'cve_ageb'] = nearest_joined['cve_ageb_right'].values
        elif 'cve_ageb' in nearest_joined.columns:
            joined.loc[unmatched_mask, 'cve_ageb'] = nearest_joined['cve_ageb'].values

    # Clean join index columns
    joined = joined.drop(columns=['index_right', 'cve_ageb_right'], errors='ignore')
    
    # Return in WGS 84
    return joined.to_crs(epsg=4326)
