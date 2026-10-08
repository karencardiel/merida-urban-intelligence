"""Shared paths and database connection settings."""
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import URL
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env', override=False)
RAW = ROOT / 'data/raw'
PROCESSED = ROOT / 'data/processed'
OUTPUTS = ROOT / 'outputs'
def database_url():
    supplied = os.getenv('DATABASE_URL')
    if supplied:
        return supplied
    return URL.create('postgresql+psycopg2', username=os.getenv('POSTGRES_USER','postgres'),
        password=os.getenv('POSTGRES_PASSWORD','postgres'), host=os.getenv('POSTGRES_HOST','localhost'),
        port=int(os.getenv('POSTGRES_PORT','5432')), database=os.getenv('POSTGRES_DB','merida_urban_intelligence'))
