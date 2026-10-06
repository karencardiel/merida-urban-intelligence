"""
Configuration and paths for Mérida Urban Intelligence Geospatial Data Warehouse
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project directory paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = ROOT_DIR / "outputs"
MAPS_DIR = OUTPUTS_DIR / "maps"
FIGURES_DIR = OUTPUTS_DIR / "figures"
SQL_DIR = ROOT_DIR / "sql"

# Ensure output directories exist
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
MAPS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Coordinate Reference Systems
SRID_PROJECTED = 6372   # MEXICO_ITRF_2008_LCC (meters, for distances & areas)
SRID_WGS84 = 4326       # WGS 84 (Lon/Lat, for web mapping & GPS)

# Geographic filters for Mérida Urban Core
CVE_ENT = "31"          # Yucatán
CVE_MUN = "050"         # Mérida
CVE_LOC = "0001"        # City of Mérida

# PostgreSQL / PostGIS connection
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "merida_dw")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

DATABASE_URI = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)
