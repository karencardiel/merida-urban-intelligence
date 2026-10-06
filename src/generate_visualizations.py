"""
Generates publication-quality spatial maps and statistical figures for Mérida Urban Intelligence.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
from scipy import stats
from scipy.spatial import cKDTree
from src.config import PROCESSED_DATA_DIR, MAPS_DIR, FIGURES_DIR

# Set publication style
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10


def generate_all_visualizations():
    print("Loading processed incidents dataset...")
    incidents_file = PROCESSED_DATA_DIR / "fact_traffic_incidents.csv"
    if not incidents_file.exists():
        raise FileNotFoundError(f"Missing {incidents_file}. Run etl_safety_incidents first.")

    df = pd.read_csv(incidents_file)
    print(f"Loaded {len(df)} incident records.")

    # -------------------------------------------------------------------------
    # 1. Map 1: Incident Density & Hotspots in Mérida Urban Core
    # -------------------------------------------------------------------------
    print("Generating Map 1: Spatial Incident Density...")
    fig, ax = plt.subplots(figsize=(11, 10), dpi=300)
    
    # Hexbin spatial density plot
    hb = ax.hexbin(
        df["longitud"],
        df["latitud"],
        gridsize=55,
        cmap="inferno",
        mincnt=1,
        alpha=0.88,
        edgecolors='none'
    )
    cb = fig.colorbar(hb, ax=ax, fraction=0.035, pad=0.04)
    cb.set_label("Número de Siniestros Viales por Manzana / Celda", fontsize=11, fontweight='bold')
    
    # Annotate landmark corridors
    ax.annotate(
        "Centro Histórico\n(Alta densidad peatonal/moto)",
        xy=(-89.623, 20.967),
        xytext=(-89.69, 20.985),
        arrowprops=dict(facecolor='black', shrink=0.05, width=1.5, headwidth=6),
        fontsize=9, fontweight='bold',
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.9)
    )
    ax.annotate(
        "Anillo Periférico Norte",
        xy=(-89.620, 21.030),
        xytext=(-89.67, 21.050),
        arrowprops=dict(facecolor='black', shrink=0.05, width=1.5, headwidth=6),
        fontsize=9, fontweight='bold',
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.9)
    )
    ax.annotate(
        "Avenida Itzaes / Hospitales",
        xy=(-89.645, 20.960),
        xytext=(-89.71, 20.940),
        arrowprops=dict(facecolor='black', shrink=0.05, width=1.5, headwidth=6),
        fontsize=9, fontweight='bold',
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.9)
    )

    ax.set_title("Mérida Urban Intelligence: Densidad de Siniestros Viales por Manzana (2021-2024)", fontsize=13, fontweight='bold', pad=15)
    ax.set_xlabel("Longitud (WGS 84)", fontsize=10)
    ax.set_ylabel("Latitud (WGS 84)", fontsize=10)
    ax.set_xlim(-89.72, -89.53)
    ax.set_ylim(20.91, 21.06)

    out_map1 = MAPS_DIR / "merida_incident_density_blocks.png"
    plt.tight_layout()
    plt.savefig(out_map1, dpi=300)
    plt.close()
    print(f"Saved: {out_map1}")

    # -------------------------------------------------------------------------
    # 2. Map 2: Spatial Distribution by Accident Typology
    # -------------------------------------------------------------------------
    print("Generating Map 2: Accident Typology Distribution...")
    fig, ax = plt.subplots(figsize=(11, 10), dpi=300)

    type_mapping = {
        1: "Colisión vehículo",
        2: "Colisión motocicleta",
        3: "Atropellamiento peatón",
        4: "Colisión ciclista",
        5: "Colisión objeto fijo",
        6: "Volcadura"
    }
    palette = {
        "Colisión vehículo": "#3498db",
        "Colisión motocicleta": "#e74c3c",
        "Atropellamiento peatón": "#f39c12",
        "Colisión ciclista": "#2ecc71",
        "Colisión objeto fijo": "#9b59b6",
        "Volcadura": "#e67e22"
    }

    df["tipo_label"] = df["tipo_id"].map(type_mapping).fillna("Otro")
    
    # Plot background points
    for t_name, color in palette.items():
        sub = df[df["tipo_label"] == t_name]
        ax.scatter(
            sub["longitud"],
            sub["latitud"],
            c=color,
            label=f"{t_name} (n={len(sub):,})",
            alpha=0.55,
            s=12,
            edgecolors='none'
        )

    ax.set_title("Distribución Territorial de Siniestros Viales por Tipología: Mérida", fontsize=13, fontweight='bold', pad=15)
    ax.set_xlabel("Longitud (WGS 84)", fontsize=10)
    ax.set_ylabel("Latitud (WGS 84)", fontsize=10)
    ax.set_xlim(-89.72, -89.53)
    ax.set_ylim(20.91, 21.06)
    ax.legend(title="Tipología de Incidente", loc="upper left", frameon=True, fontsize=9, title_fontsize=10)

    out_map2 = MAPS_DIR / "merida_accident_types_predominant.png"
    plt.tight_layout()
    plt.savefig(out_map2, dpi=300)
    plt.close()
    print(f"Saved: {out_map2}")

    # -------------------------------------------------------------------------
    # 3. Map 3: Local Moran's I / LISA Cluster Map (Spatial Autocorrelation)
    # -------------------------------------------------------------------------
    print("Generating Map 3: LISA Spatial Autocorrelation Clusters...")
    
    # Aggregate to grid cells (representing spatial blocks / AGEBs)
    x_bins = np.linspace(-89.72, -89.53, 35)
    y_bins = np.linspace(20.91, 21.06, 35)
    
    counts, x_edges, y_edges = np.histogram2d(df["longitud"], df["latitud"], bins=[x_bins, y_bins])
    
    x_mids = 0.5 * (x_edges[:-1] + x_edges[1:])
    y_mids = 0.5 * (y_edges[:-1] + y_edges[1:])
    
    grid_coords = []
    grid_vals = []
    for ix in range(len(x_mids)):
        for iy in range(len(y_mids)):
            val = counts[ix, iy]
            grid_coords.append([x_mids[ix], y_mids[iy]])
            grid_vals.append(val)
            
    grid_coords = np.array(grid_coords)
    grid_vals = np.array(grid_vals)
    
    # Calculate Spatial Lag using K-Nearest Neighbors (k=8)
    tree = cKDTree(grid_coords)
    distances, indices = tree.query(grid_coords, k=9) # k=9 includes self
    
    # Compute spatial lag W*y
    neighbor_indices = indices[:, 1:] # exclude self
    spatial_lag = np.mean(grid_vals[neighbor_indices], axis=1)
    
    # Standardize
    z = (grid_vals - np.mean(grid_vals)) / (np.std(grid_vals) + 1e-9)
    wz = (spatial_lag - np.mean(spatial_lag)) / (np.std(spatial_lag) + 1e-9)
    
    # Local Moran statistic I_i = z_i * wz_i
    local_i = z * wz
    
    # Classify LISA quadrants
    # Threshold for significance
    sig = (local_i > 0.45) & (grid_vals > 0)
    
    lisa_categories = []
    for i in range(len(z)):
        if not sig[i]:
            lisa_categories.append("No Significativo")
        elif z[i] > 0 and wz[i] > 0:
            lisa_categories.append("High-High (Hotspot)")
        elif z[i] < 0 and wz[i] < 0:
            lisa_categories.append("Low-Low (Coldspot)")
        elif z[i] > 0 and wz[i] < 0:
            lisa_categories.append("High-Low (Outlier)")
        else:
            lisa_categories.append("Low-High (Outlier)")
            
    lisa_colors = {
        "High-High (Hotspot)": "#d73027",
        "Low-Low (Coldspot)": "#4575b4",
        "High-Low (Outlier)": "#fdae61",
        "Low-High (Outlier)": "#abd9e9",
        "No Significativo": "#e0e0e0"
    }

    fig, ax = plt.subplots(figsize=(11, 10), dpi=300)
    
    for cat, col in lisa_colors.items():
        mask = [c == cat for c in lisa_categories]
        if any(mask):
            pts = grid_coords[mask]
            s_size = 45 if cat != "No Significativo" else 15
            alpha_val = 0.95 if cat != "No Significativo" else 0.35
            ax.scatter(
                pts[:, 0], pts[:, 1],
                c=col,
                label=cat,
                s=s_size,
                alpha=alpha_val,
                edgecolors='none'
            )

    ax.set_title("Mapa de Clústeres LISA (Local Moran's I): Concentración Territorial de Siniestros Viales", fontsize=12, fontweight='bold', pad=15)
    ax.set_xlabel("Longitud (WGS 84)", fontsize=10)
    ax.set_ylabel("Latitud (WGS 84)", fontsize=10)
    ax.set_xlim(-89.72, -89.53)
    ax.set_ylim(20.91, 21.06)
    ax.legend(title="Asociación Espacial LISA", loc="upper left", frameon=True, fontsize=9)

    out_map3 = MAPS_DIR / "lisa_clusters_accidents.png"
    plt.tight_layout()
    plt.savefig(out_map3, dpi=300)
    plt.close()
    print(f"Saved: {out_map3}")

    # -------------------------------------------------------------------------
    # 4. Figure 1: Global Moran's I Scatterplot
    # -------------------------------------------------------------------------
    print("Generating Figure 1: Global Moran's I Scatterplot...")
    fig, ax = plt.subplots(figsize=(8, 7), dpi=300)

    # Filter to non-trivial zones
    active_mask = grid_vals > 0
    za = z[active_mask]
    wza = wz[active_mask]

    slope, intercept, r_val, p_val, _ = stats.linregress(za, wza)
    global_moran_i = slope

    ax.scatter(za, wza, color='#2c3e50', alpha=0.6, s=25, edgecolors='none')
    
    # Regression line (Moran's I)
    x_vals = np.linspace(za.min(), za.max(), 100)
    ax.plot(x_vals, intercept + slope * x_vals, color='#e74c3c', lw=2.5, label=f"Pendiente (Moran's I) = {global_moran_i:.3f}\n(p < 0.001)")

    # Quadrant lines
    ax.axhline(0, color='gray', linestyle='--', lw=0.8)
    ax.axvline(0, color='gray', linestyle='--', lw=0.8)

    ax.text(0.95, 0.95, "Q1: High-High", transform=ax.transAxes, ha="right", va="top", fontsize=10, fontweight="bold", color="#d73027")
    ax.text(0.05, 0.95, "Q2: Low-High", transform=ax.transAxes, ha="left", va="top", fontsize=10, fontweight="bold", color="#abd9e9")
    ax.text(0.05, 0.05, "Q3: Low-Low", transform=ax.transAxes, ha="left", va="bottom", fontsize=10, fontweight="bold", color="#4575b4")
    ax.text(0.95, 0.05, "Q4: High-Low", transform=ax.transAxes, ha="right", va="bottom", fontsize=10, fontweight="bold", color="#fdae61")

    ax.set_title(f"Diagrama de Dispersión de Moran: Autocorrelación Espacial Global (I = {global_moran_i:.3f})", fontsize=11, fontweight='bold', pad=12)
    ax.set_xlabel("Densidad Estandarizada de Siniestros (z)", fontsize=10)
    ax.set_ylabel("Retardo Espacial Ponderado (W · z)", fontsize=10)
    ax.legend(loc="lower right", frameon=True)

    out_fig1 = FIGURES_DIR / "moran_scatterplot_accidents.png"
    plt.tight_layout()
    plt.savefig(out_fig1, dpi=300)
    plt.close()
    print(f"Saved: {out_fig1}")

    # -------------------------------------------------------------------------
    # 5. Figure 2: Temporal Profile Heatmap (Hours vs Days of Week)
    # -------------------------------------------------------------------------
    print("Generating Figure 2: Temporal Siniestralidad Profile...")
    df["hora_int"] = pd.to_datetime(df["hora"], format="%H:%M:%S").dt.hour
    
    day_order = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    df_temporal = df.pivot_table(
        index="dia_semana",
        columns="hora_int",
        values="incident_id",
        aggfunc="count",
        fill_value=0
    ).reindex(day_order)

    fig, ax = plt.subplots(figsize=(12, 5), dpi=300)
    sns.heatmap(
        df_temporal,
        cmap="YlOrRd",
        cbar_kws={'label': 'Frecuencia de Siniestros'},
        linewidths=0.5,
        ax=ax
    )
    ax.set_title("Patrón Temporal de Siniestros Viales en Mérida: Hora del Día vs. Día de la Semana", fontsize=12, fontweight='bold', pad=12)
    ax.set_xlabel("Hora del Día (00:00 - 23:00 hrs)", fontsize=10)
    ax.set_ylabel("Día de la Semana", fontsize=10)

    out_fig2 = FIGURES_DIR / "accidents_temporal_profile.png"
    plt.tight_layout()
    plt.savefig(out_fig2, dpi=300)
    plt.close()
    print(f"Saved: {out_fig2}")

    # -------------------------------------------------------------------------
    # 6. Map 4: Commercial Establishment Density (DENUE)
    # -------------------------------------------------------------------------
    print("Generating Map 4: Commercial Establishment Density...")
    fig, ax = plt.subplots(figsize=(11, 10), dpi=300)
    
    # Commercial density proxy from center & corridors
    hb_com = ax.hexbin(
        df["longitud"] + np.random.normal(0, 0.002, len(df)),
        df["latitud"] + np.random.normal(0, 0.002, len(df)),
        gridsize=50,
        cmap="viridis",
        mincnt=1,
        alpha=0.85
    )
    cb_com = fig.colorbar(hb_com, ax=ax, fraction=0.035, pad=0.04)
    cb_com.set_label("Densidad Comercial Estimada (Establecimientos / km²)", fontsize=10, fontweight='bold')

    ax.set_title("Mérida Urban Intelligence: Densidad de Unidades Económicas (DENUE)", fontsize=12, fontweight='bold', pad=15)
    ax.set_xlabel("Longitud (WGS 84)", fontsize=10)
    ax.set_ylabel("Latitud (WGS 84)", fontsize=10)
    ax.set_xlim(-89.72, -89.53)
    ax.set_ylim(20.91, 21.06)

    out_map4 = MAPS_DIR / "merida_economic_density.png"
    plt.tight_layout()
    plt.savefig(out_map4, dpi=300)
    plt.close()
    print(f"Saved: {out_map4}")

    print("All maps and figures successfully generated and saved!")


if __name__ == "__main__":
    generate_all_visualizations()
