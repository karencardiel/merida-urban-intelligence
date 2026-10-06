"""
ETL Module for Economic Establishments (INEGI DENUE)
Filters establishments in Mérida, assigns them to urban blocks, and populates dimensions.
"""
import zipfile
import pandas as pd
import geopandas as gpd
from src.config import (
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    CVE_MUN,
    CVE_LOC,
    SRID_PROJECTED,
    SRID_WGS84
)
from src.geocoding import snap_points_to_blocks


def process_merida_denue(zip_filename="denue_31_csv.zip"):
    """
    Ingests DENUE records for Mérida, maps them to urban blocks, and exports facts/dimensions.
    """
    zip_path = RAW_DATA_DIR / zip_filename
    if not zip_path.exists():
        raise FileNotFoundError(f"DENUE zip file not found at {zip_path}")

    print("Extracting DENUE dataset...")
    with zipfile.ZipFile(zip_path, "r") as z:
        with z.open("conjunto_de_datos/denue_inegi_31_.csv") as f:
            df = pd.read_csv(f, encoding="latin-1", low_memory=False)

    print(f"Total DENUE records for Yucatán: {len(df)}")
    
    # Filter for Municipality 50 (Mérida) and Locality 1 (Mérida city)
    df_merida = df[
        (df["cve_mun"].astype(str).str.zfill(3) == CVE_MUN) &
        (df["cve_loc"].astype(str).str.zfill(4) == CVE_LOC)
    ].copy()

    print(f"Filtered {len(df_merida)} establishments in Mérida city.")

    # 1. Build dim_economic_activity
    dim_scian = df_merida[[
        "codigo_act", "nombre_act"
    ]].drop_duplicates().copy()
    dim_scian["codigo_act"] = dim_scian["codigo_act"].astype(str).str.zfill(6)
    dim_scian["sector_code"] = dim_scian["codigo_act"].str[:2]
    dim_scian["sector_name"] = dim_scian["sector_code"].map({
        "11": "Agricultura, cría y explotación de animales",
        "21": "Minería",
        "22": "Generación y distribución de electricidad, agua y gas",
        "23": "Construcción",
        "31": "Industrias manufactureras",
        "32": "Industrias manufactureras",
        "33": "Industrias manufactureras",
        "43": "Comercio al por mayor",
        "46": "Comercio al por menor",
        "48": "Transportes, correos y almacenamiento",
        "49": "Transportes, correos y almacenamiento",
        "51": "Información en medios masivos",
        "52": "Servicios financieros y de seguros",
        "53": "Servicios inmobiliarios y de alquiler",
        "54": "Servicios profesionales, científicos y técnicos",
        "55": "Corporativos",
        "56": "Servicios de apoyo a los negocios y manejo de residuos",
        "61": "Servicios educativos",
        "62": "Servicios de salud y de asistencia social",
        "71": "Servicios artísticos, culturales y deportivos",
        "72": "Servicios de alojamiento temporal y preparación de alimentos",
        "81": "Otros servicios excepto actividades gubernamentales"
    }).fillna("Otras actividades económicas")
    dim_scian["subsector_name"] = dim_scian["nombre_act"].str[:50]

    out_scian = PROCESSED_DATA_DIR / "dim_economic_activity.csv"
    dim_scian.to_csv(out_scian, index=False)
    print(f"Exported {len(dim_scian)} economic activity codes to {out_scian}")

    # 2. Build GeoDataFrame and map to blocks
    geometry = gpd.points_from_xy(df_merida["longitud"], df_merida["latitud"], crs="EPSG:4326")
    gdf_denue = gpd.GeoDataFrame(df_merida, geometry=geometry)

    # Load block polygons for spatial join
    blocks_path = PROCESSED_DATA_DIR / "dim_block.geojson"
    if blocks_path.exists():
        gdf_blocks = gpd.read_file(blocks_path)
        print("Performing spatial join: DENUE points to Mérida blocks...")
        gdf_denue = snap_points_to_blocks(gdf_denue, gdf_blocks)
    else:
        print("Blocks file not found; generating fallback cvegeo from DENUE manzana field.")
        gdf_denue["cvegeo_manzana"] = (
            "310500001" +
            gdf_denue["ageb"].astype(str).str.zfill(4) +
            gdf_denue["manzana"].astype(str).str.zfill(3)
        )

    fact_denue = pd.DataFrame({
        "id_estab": gdf_denue["id"],
        "clee": gdf_denue["clee"],
        "nom_estab": gdf_denue["nom_estab"],
        "codigo_act": gdf_denue["codigo_act"].astype(str).str.zfill(6),
        "per_ocu_estrato": gdf_denue["per_ocu"],
        "cvegeo_manzana": gdf_denue.get("cvegeo_manzana", None),
        "cve_ageb": gdf_denue["ageb"].astype(str).str.zfill(4),
        "latitud": gdf_denue["latitud"],
        "longitud": gdf_denue["longitud"]
    })

    out_denue = PROCESSED_DATA_DIR / "fact_economic_establishments.csv"
    fact_denue.to_csv(out_denue, index=False)
    print(f"Exported {len(fact_denue)} establishments to {out_denue}")

    return fact_denue, dim_scian


if __name__ == "__main__":
    process_merida_denue()
