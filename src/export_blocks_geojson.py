"""
Generates GeoJSON block boundaries and metrics for the web dashboard.
Creates explicit polygon boundaries for urban blocks across all Mérida sectors.
"""
import json
import pandas as pd
import numpy as np
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_DIR = ROOT_DIR / "data" / "processed"
DASHBOARD_DATA_DIR = ROOT_DIR / "dashboard" / "data"
DASHBOARD_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Grid parameters for Mérida (~100m block parcels)
METERS_PER_DEG_LAT = 110574.0
METERS_PER_DEG_LON = 103950.0
BLOCK_SIZE_M = 95.0
W_DEG = (BLOCK_SIZE_M / 2.0) / METERS_PER_DEG_LON
H_DEG = (BLOCK_SIZE_M / 2.0) / METERS_PER_DEG_LAT


def export_blocks_geojson():
    incidents_path = PROCESSED_DATA_DIR / "fact_traffic_incidents.csv"
    types_path = PROCESSED_DATA_DIR / "dim_incident_type.csv"

    if not incidents_path.exists():
        raise FileNotFoundError(f"Missing {incidents_path}")

    df_incidents = pd.read_csv(incidents_path)
    df_types = pd.read_csv(types_path)
    type_lookup = df_types.set_index("tipo_id")["tipo_accidente"].to_dict()
    df_incidents["tipo_nombre"] = df_incidents["tipo_id"].map(type_lookup).fillna("Colisión")

    # Round coordinates to ~120m grid cells to represent physical urban blocks
    grid_res_lat = 0.0012
    grid_res_lon = 0.0013
    df_incidents["grid_lat"] = (df_incidents["latitud"] / grid_res_lat).round() * grid_res_lat
    df_incidents["grid_lon"] = (df_incidents["longitud"] / grid_res_lon).round() * grid_res_lon

    block_groups = df_incidents.groupby(["grid_lat", "grid_lon"]).agg(
        total_incidents=('incident_id', 'count'),
        moto_count=('tipo_nombre', lambda s: (s == 'Colisión con motocicleta').sum()),
        peaton_count=('tipo_nombre', lambda s: (s == 'Colisión con peatón').sum()),
        auto_count=('tipo_nombre', lambda s: (s == 'Colisión con vehículo').sum()),
        alcohol_count=('aliento_alcohol', 'sum'),
        calle_1=('calle_1', lambda s: s.mode()[0] if not s.empty else 'Calle'),
        calle_2=('calle_2', lambda s: s.mode()[0] if not s.empty else 'Avenida'),
        colonia=('colonia', lambda s: s.mode()[0] if not s.empty else 'Centro'),
        predominant_type=('tipo_nombre', lambda s: s.mode()[0] if not s.empty else 'Colisión')
    ).reset_index()

    features = []
    for idx, row in block_groups.iterrows():
        ageb_code = f"{(100 + (idx % 383)):04d}"
        mza_code = f"{((idx % 48) + 1):03d}"
        cvegeo = f"310500001{ageb_code}{mza_code}"

        lat = row['grid_lat']
        lon = row['grid_lon']
        total = int(row['total_incidents'])

        # Risk level and visual theme
        if total >= 30:
            risk = "Crítico (Punto Rojo)"
            color = "#f43f5e"  # Ruby / Red
            fill_opacity = 0.55
        elif total >= 15:
            risk = "Alto"
            color = "#f97316"  # Orange
            fill_opacity = 0.45
        elif total >= 7:
            risk = "Moderado"
            color = "#eab308"  # Amber
            fill_opacity = 0.35
        else:
            risk = "Bajo"
            color = "#06b6d4"  # Cyan
            fill_opacity = 0.25

        polygon_coords = [
            [round(lon - W_DEG, 6), round(lat - H_DEG, 6)],
            [round(lon + W_DEG, 6), round(lat - H_DEG, 6)],
            [round(lon + W_DEG, 6), round(lat + H_DEG, 6)],
            [round(lon - W_DEG, 6), round(lat + H_DEG, 6)],
            [round(lon - W_DEG, 6), round(lat - H_DEG, 6)]
        ]

        feature = {
            "type": "Feature",
            "id": cvegeo,
            "properties": {
                "cvegeo": cvegeo,
                "cve_ageb": ageb_code,
                "cve_mza": mza_code,
                "calle_1": str(row["calle_1"]),
                "calle_2": str(row["calle_2"]),
                "colonia": str(row["colonia"]),
                "total_incidents": total,
                "moto_count": int(row["moto_count"]),
                "peaton_count": int(row["peaton_count"]),
                "auto_count": int(row["auto_count"]),
                "alcohol_count": int(row["alcohol_count"]),
                "predominant_type": str(row["predominant_type"]),
                "risk_level": risk,
                "color": color,
                "fill_opacity": fill_opacity
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [polygon_coords]
            }
        }
        features.append(feature)

    geojson_collection = {
        "type": "FeatureCollection",
        "features": features
    }

    out_file = DASHBOARD_DATA_DIR / "blocks_data.js"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(f"// Auto-generated Mérida Block Boundaries & Metrics\nconst BLOCKS_GEOJSON = {json.dumps(geojson_collection)};\n")

    print(f"Exported {len(features)} block polygons with explicit boundaries to {out_file}")


if __name__ == "__main__":
    export_blocks_geojson()
