"""
ETL Module for Demographic Data (INEGI Censo 2020)
Filters and cleans demographic indicators for Mérida city AGEBs.
"""
import zipfile
import pandas as pd
from src.config import RAW_DATA_DIR, PROCESSED_DATA_DIR, CVE_MUN, CVE_LOC


def process_merida_census(zip_filename="ageb_mza_urbana_31_cpv2020_csv.zip"):
    """
    Ingests and cleans INEGI Census 2020 for the city of Mérida.
    Handles statistical masking ('*' -> 0) and generates fact_ageb_demographics.
    """
    zip_path = RAW_DATA_DIR / zip_filename
    alt_csv_path = RAW_DATA_DIR / "censo_yucatan_2020.csv"
    
    if zip_path.exists():
        with zipfile.ZipFile(zip_path, 'r') as z:
            csv_target = [f for f in z.namelist() if f.endswith('.csv') and 'conjunto_de_datos' in f][0]
            with z.open(csv_target) as f:
                df = pd.read_csv(f, encoding='utf-8', low_memory=False)
    elif alt_csv_path.exists():
        df = pd.read_csv(alt_csv_path, encoding='utf-8', low_memory=False)
    else:
        raise FileNotFoundError(
            f"Census file not found in {RAW_DATA_DIR}. Expected {zip_filename} or censo_yucatan_2020.csv"
        )

    print("Filtering Census for Mérida urban core...")
    # Filter for Municipality 50 (Mérida) and Locality 1 (Mérida city)
    df_merida = df[
        (df["MUN"].astype(str).str.zfill(3) == CVE_MUN) &
        (df["LOC"].astype(str).str.zfill(4) == CVE_LOC)
    ].copy()

    # Filter for Total AGEB Urbana (MZA == 0)
    df_ageb = df_merida[
        (df_merida["NOM_LOC"] == "Total AGEB urbana") &
        (df_merida["MZA"] == 0)
    ].copy()

    # Construct unique 9-digit AGEB key (31 + 050 + 0001 + AGEB)
    df_ageb["cvegeo_ageb"] = "310500001" + df_ageb["AGEB"].astype(str).str.zfill(4)

    # Clean numeric indicators (masking '*' -> 0)
    numeric_cols = [
        "POBTOT", "POBFEM", "POBMAS", "POB0_14", "POB15_64",
        "POB65_MAS", "PEA", "PE_OCUPADA", "VIVTOT", "VPH_INTER"
    ]
    
    for col in numeric_cols:
        if col in df_ageb.columns:
            df_ageb[col] = pd.to_numeric(df_ageb[col], errors='coerce').fillna(0).astype(int)
        else:
            df_ageb[col] = 0

    fact_demographics = df_ageb[[
        "cvegeo_ageb", "POBTOT", "POBFEM", "POBMAS", "POB0_14",
        "POB15_64", "POB65_MAS", "PEA", "PE_OCUPADA", "VIVTOT", "VPH_INTER"
    ]].rename(columns=str.lower)

    out_path = PROCESSED_DATA_DIR / "fact_ageb_demographics.csv"
    fact_demographics.to_csv(out_path, index=False)
    print(f"Exported {len(fact_demographics)} AGEB demographic rows to {out_path}")

    return fact_demographics


if __name__ == "__main__":
    process_merida_census()
