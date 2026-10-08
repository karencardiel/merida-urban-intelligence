"""Read original archives without changing them."""
from zipfile import ZipFile
import hashlib
import json
import pandas as pd
import geopandas as gpd
from .config import RAW, PROCESSED

def csv_from_zip(path, member=None, encoding='utf-8'):
    with ZipFile(path) as archive:
        if member is None:
            members = [n for n in archive.namelist() if n.endswith('.csv') and 'conjunto_de_datos' in n]
            if len(members) != 1:
                raise ValueError(f'Expected one dataset CSV in {path.name}: {members}')
            member = members[0]
        with archive.open(member) as source:
            return pd.read_csv(source, encoding=encoding, low_memory=False)

def read_sources():
    census = csv_from_zip(RAW/'ageb_mza_urbana_31_cpv2020_csv.zip')
    denue = csv_from_zip(RAW/'denue_31_csv.zip','conjunto_de_datos/denue_inegi_31_.csv','latin-1')
    geo = RAW/'31_yucatan.zip'
    polygons = gpd.read_file(f'zip://{geo}!conjunto_de_datos/31a.shp')
    locality = gpd.read_file(f'zip://{geo}!conjunto_de_datos/31l.shp')
    accidents_path = RAW/'atus_2024_shp.zip'
    with ZipFile(accidents_path) as archive:
        members = [n for n in archive.namelist() if n.endswith('.shp')]
        if len(members) != 1:
            raise ValueError(f'Expected one ATUS shapefile: {members}')
    accidents = gpd.read_file(f'zip://{accidents_path}!{members[0]}')
    PROCESSED.mkdir(parents=True,exist_ok=True)
    files=[RAW/'ageb_mza_urbana_31_cpv2020_csv.zip',RAW/'denue_31_csv.zip',geo,accidents_path]
    fingerprints=[]
    for path in files:
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):
                digest.update(block)
        fingerprints.append({'filename':path.name,'bytes':path.stat().st_size,'sha256':digest.hexdigest()})
    (PROCESSED/'source_manifest.json').write_text(json.dumps(fingerprints,indent=2)+'\n')
    return census, denue, polygons, locality, accidents
