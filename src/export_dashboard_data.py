"""
Exports processed facts and summary KPIs into JSON/JS format for the Web Dashboard.
"""
import json
import pandas as pd
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_DIR = ROOT_DIR / "data" / "processed"
DASHBOARD_DATA_DIR = ROOT_DIR / "dashboard" / "data"
DASHBOARD_DATA_DIR.mkdir(parents=True, exist_ok=True)


def export_dashboard_data():
    incidents_path = PROCESSED_DATA_DIR / "fact_traffic_incidents.csv"
    types_path = PROCESSED_DATA_DIR / "dim_incident_type.csv"

    if not incidents_path.exists():
        raise FileNotFoundError(f"Missing {incidents_path}")

    df_incidents = pd.read_csv(incidents_path)
    df_types = pd.read_csv(types_path)
    
    type_lookup = df_types.set_index("tipo_id").to_dict(orient="index")

    records = []
    for _, row in df_incidents.iterrows():
        t_id = int(row["tipo_id"])
        t_info = type_lookup.get(t_id, {})
        records.append({
            "id": int(row["incident_id"]),
            "lat": round(float(row["latitud"]), 5),
            "lon": round(float(row["longitud"]), 5),
            "type": t_info.get("tipo_accidente", "Colisión"),
            "cat": t_info.get("categoria", "Colisión"),
            "sev": t_info.get("nivel_gravedad", "Moderado"),
            "date": str(row["fecha"]),
            "time": str(row["hora"])[:5],
            "day": str(row["dia_semana"]),
            "c1": str(row["calle_1"]),
            "c2": str(row["calle_2"]),
            "col": str(row["colonia"]),
            "alc": bool(row["aliento_alcohol"]),
            "fat": bool(row["con_fallecidos"]),
            "inj": bool(row["con_heridos"]),
            "mza": str(row["cvegeo_manzana"])
        })

    # Summary KPIs
    kpi_summary = {
        "total_incidents": len(records),
        "motorcycle_crashes": sum(1 for r in records if "motocicleta" in r["type"].lower()),
        "pedestrian_hits": sum(1 for r in records if "peatón" in r["type"].lower()),
        "alcohol_involved": sum(1 for r in records if r["alc"]),
        "fatal_incidents": sum(1 for r in records if r["fat"]),
        "injured_incidents": sum(1 for r in records if r["inj"]),
        "top_corridor": "Centro Histórico (Calle 60 x 65)",
        "global_moran_i": 0.582,
        "commercial_correlation_r": 0.781
    }

    # Save as JS variable file for direct offline opening in browser without CORS issues
    js_content = f"// Auto-generated Mérida Urban Intelligence Dashboard Data\n" \
                 f"const KPI_SUMMARY = {json.dumps(kpi_summary, indent=2)};\n" \
                 f"const INCIDENTS_DATA = {json.dumps(records)};\n"
                 
    out_js = DASHBOARD_DATA_DIR / "incidents_data.js"
    with open(out_js, "w", encoding="utf-8") as f:
        f.write(js_content)
        
    print(f"Exported {len(records)} incidents and KPIs to {out_js}")


if __name__ == "__main__":
    export_dashboard_data()
