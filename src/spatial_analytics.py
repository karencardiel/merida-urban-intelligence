"""
Phase 3: Spatial Analytics & Statistical Inference
Implements Pearson/Spearman correlations, Global Moran's I, LISA cluster maps,
and Bivariate Moran's I for Mérida blocks and AGEBs.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from src.config import PROCESSED_DATA_DIR, MAPS_DIR, FIGURES_DIR

try:
    import geopandas as gpd
    import libpysal
    from esda.moran import Moran, Moran_Local, Moran_BV
    from splot.esda import plot_moran, moran_scatterplot, lisa_cluster
    HAS_PYSAL = True
except ImportError:
    HAS_PYSAL = False


def compute_statistical_correlations(df_metrics):
    """
    Computes Pearson (linear) and Spearman (rank-order) correlation coefficients
    across territorial indicators.
    """
    print("Computing Pearson & Spearman correlations across indicators...")
    
    pairs = [
        ("densidad_poblacional_km2", "densidad_accidentes_km2", "Densidad Poblacional vs Densidad Accidentes"),
        ("densidad_establecimientos_km2", "densidad_accidentes_km2", "Densidad Comercial vs Densidad Accidentes"),
        ("indice_diversidad_shannon", "tasa_accidentes_por_1000_hab", "Diversidad Comercial vs Tasa Accidentes")
    ]
    
    results = []
    for var1, var2, label in pairs:
        if var1 in df_metrics.columns and var2 in df_metrics.columns:
            sub = df_metrics[[var1, var2]].dropna()
            r_pearson, p_pearson = stats.pearsonr(sub[var1], sub[var2])
            r_spearman, p_spearman = stats.spearmanr(sub[var1], sub[var2])
            
            results.append({
                "relationship": label,
                "var_x": var1,
                "var_y": var2,
                "pearson_r": round(r_pearson, 4),
                "pearson_p": round(p_pearson, 5),
                "spearman_rho": round(r_spearman, 4),
                "spearman_p": round(p_spearman, 5)
            })

    df_corr = pd.DataFrame(results)
    
    # Save correlation heatmap
    cols_to_plot = [
        "densidad_poblacional_km2",
        "densidad_establecimientos_km2",
        "densidad_accidentes_km2",
        "tasa_accidentes_por_1000_hab",
        "indice_diversidad_shannon"
    ]
    available_cols = [c for c in cols_to_plot if c in df_metrics.columns]
    if len(available_cols) >= 3:
        plt.figure(figsize=(8, 6))
        sns.heatmap(
            df_metrics[available_cols].corr(method='spearman'),
            annot=True,
            cmap="YlOrRd",
            fmt=".2f",
            linewidths=0.5
        )
        plt.title("Spearman Rank Correlation Matrix: Mérida Territorial Indicators")
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / "correlation_matrix.png", dpi=300)
        plt.close()
        print(f"Saved correlation heatmap to {FIGURES_DIR / 'correlation_matrix.png'}")

    return df_corr


def calculate_global_moran(gdf, column_name, spatial_weights="queen"):
    """
    Computes Global Moran's I to test for spatial autocorrelation.
    """
    if not HAS_PYSAL:
        print("libpysal and esda are required for Moran's I calculation.")
        return None

    gdf = gdf.dropna(subset=[column_name]).copy()
    
    if spatial_weights == "queen":
        w = libpysal.weights.Queen.from_dataframe(gdf, use_index=False)
    else:
        w = libpysal.weights.KNN.from_dataframe(gdf, k=6)
        
    w.transform = 'R'  # Row-standardized matrix

    y = gdf[column_name].values
    moran = Moran(y, w, permutations=999)
    
    print(f"--- Global Moran's I: {column_name} ---")
    print(f"Moran's I: {moran.I:.4f}")
    print(f"Expected I: {moran.EI:.4f}")
    print(f"p-value: {moran.p_sim:.5f}")
    print(f"z-score: {moran.z_sim:.4f}")
    
    # Plot and save Moran scatterplot
    fig, ax = moran_scatterplot(moran, aspect_equal=True)
    ax.set_title(f"Moran's I Scatterplot: {column_name} (I = {moran.I:.3f}, p = {moran.p_sim:.4f})")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / f"moran_scatterplot_{column_name}.png", dpi=300)
    plt.close()

    return {
        "variable": column_name,
        "moran_i": moran.I,
        "p_value": moran.p_sim,
        "z_score": moran.z_sim
    }


def calculate_lisa_clusters(gdf, column_name, p_threshold=0.05):
    """
    Computes Local Indicators of Spatial Association (LISA / Local Moran's I)
    to classify blocks or AGEBs into HH (Hotspots), LL (Coldspots), and spatial outliers.
    """
    if not HAS_PYSAL:
        return None

    gdf = gdf.dropna(subset=[column_name]).copy()
    w = libpysal.weights.Queen.from_dataframe(gdf, use_index=False)
    w.transform = 'R'

    y = gdf[column_name].values
    lm = Moran_Local(y, w, transformation='r', permutations=999)

    # Classify quadrants (1: HH, 2: LH, 3: LL, 4: HL)
    sig = lm.p_sim < p_threshold
    quads = lm.q
    
    labels = {1: "High-High (Hotspot)", 2: "Low-High (Outlier)", 3: "Low-Low (Coldspot)", 4: "High-Low (Outlier)"}
    gdf["lisa_cluster"] = [labels[q] if s else "Not Significant" for q, s in zip(quads, sig)]

    # Generate LISA cluster plot
    fig, ax = plt.subplots(figsize=(10, 10))
    lisa_cluster(lm, gdf, p=p_threshold, ax=ax, legend=True)
    ax.set_title(f"LISA Cluster Map: {column_name} (p < {p_threshold})")
    ax.set_axis_off()
    plt.tight_layout()
    plt.savefig(MAPS_DIR / f"lisa_clusters_{column_name}.png", dpi=300)
    plt.close()
    print(f"Saved LISA cluster map to {MAPS_DIR / f'lisa_clusters_{column_name}.png'}")

    return gdf


def calculate_bivariate_moran(gdf, var_x, var_y):
    """
    Computes Bivariate Moran's I evaluating spatial cross-correlation
    between var_x and the spatial lag of var_y.
    """
    if not HAS_PYSAL:
        return None

    gdf = gdf.dropna(subset=[var_x, var_y]).copy()
    w = libpysal.weights.Queen.from_dataframe(gdf, use_index=False)
    w.transform = 'R'

    x = gdf[var_x].values
    y = gdf[var_y].values
    moran_bv = Moran_BV(x, y, w, permutations=999)

    print(f"--- Bivariate Moran's I: {var_x} vs Lagged {var_y} ---")
    print(f"Bivariate I: {moran_bv.I:.4f}")
    print(f"p-value: {moran_bv.p_sim:.5f}")

    return {
        "var_x": var_x,
        "var_y": var_y,
        "bivariate_i": moran_bv.I,
        "p_value": moran_bv.p_sim
    }
