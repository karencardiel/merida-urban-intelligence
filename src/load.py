"""Transactional PostgreSQL load from named, validated CSV columns."""
import csv
import io
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine
from .config import ROOT,PROCESSED,database_url

KEYS = {'dim_ageb':['CVE_AGEB'],'fact_demografia':['CVE_AGEB'],'fact_economia':['CVE_AGEB'],'fact_accidentes':['CVE_AGEB'],'fact_accidentes_tiempo':['CVE_AGEB','anio','mes','periodo_dia']}

def quoted(name):
    return '"'+name.replace('"','""')+'"'

def run_load():
    engine = create_engine(database_url())
    csv_data = pd.read_csv(PROCESSED/'dw_ageb.csv',dtype={'CVE_AGEB':'string','AGEB':'string','actividad_dominante_codigo':'string'})
    geometries = pd.read_csv(PROCESSED/'ageb_geometry.csv',dtype={'CVE_AGEB':'string'})
    temporal = pd.read_csv(PROCESSED/'accidentes_tiempo.csv',dtype={'CVE_AGEB':'string'}).rename(columns={'ANIO':'anio','MES':'mes'})
    if csv_data.CVE_AGEB.duplicated().any() or geometries.CVE_AGEB.duplicated().any():
        raise ValueError('Duplicate AGEB keys.')
    if set(csv_data.CVE_AGEB) != set(geometries.CVE_AGEB) or not set(temporal.CVE_AGEB).issubset(set(csv_data.CVE_AGEB)):
        raise ValueError('Invalid geographic relationships.')
    if temporal.duplicated(KEYS['fact_accidentes_tiempo']).any():
        raise ValueError('Duplicate temporal grain.')
    if csv_data.total_accidentes.sum() != temporal.total_accidentes.sum():
        raise ValueError('Temporal total does not reconcile.')
    with engine.begin() as conn:
        conn.exec_driver_sql((ROOT/'sql/01_schema.sql').read_text())
        cursor = conn.connection.driver_connection.cursor()
        for table,keys in KEYS.items():
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",(table,))
            columns = [row[0] for row in cursor.fetchall()]
            if table == 'dim_ageb':
                frame = csv_data.merge(geometries,on='CVE_AGEB',validate='one_to_one').rename(columns={'geometry_wkt':'geometry'})
            elif table == 'fact_accidentes_tiempo':
                frame = temporal
            else:
                frame = csv_data
            missing = set(columns)-set(frame.columns)
            if missing:
                raise ValueError(f'{table}: missing export fields {missing}')
            frame = frame[columns]
            if frame[keys].isna().any().any():
                raise ValueError(f'{table}: null keys.')
            stage = 'stg_'+table
            definitions = ', '.join(quoted(c)+' TEXT' for c in columns)
            cursor.execute(f'CREATE TEMP TABLE {quoted(stage)} ({definitions}) ON COMMIT DROP')
            buffer = io.StringIO();frame.to_csv(buffer,index=False,header=False,na_rep='');buffer.seek(0)
            cursor.copy_expert(f"COPY {quoted(stage)} FROM STDIN WITH (FORMAT CSV, NULL '')", buffer)
            cursor.execute("SELECT column_name, data_type, udt_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",(table,))
            expressions=[]
            for column,datatype,udt in cursor.fetchall():
                field=quoted(column)
                if udt == 'geometry':
                    expressions.append(f'ST_Multi(ST_GeomFromText({field},4326))')
                elif datatype == 'integer':
                    expressions.append(f'{field}::integer')
                elif datatype == 'double precision':
                    expressions.append(f'{field}::double precision')
                else:
                    expressions.append(field)
            fields=', '.join(map(quoted,columns));key_fields=', '.join(map(quoted,keys))
            updates=', '.join(f'{quoted(c)}=EXCLUDED.{quoted(c)}' for c in columns if c not in keys)
            cursor.execute(f'INSERT INTO {quoted(table)} ({fields}) SELECT '+', '.join(expressions)+f' FROM {quoted(stage)} ON CONFLICT ({key_fields}) DO UPDATE SET {updates}')
            # Remove rows absent from the rebuilt current snapshot, after upsert.
            # Temporal table is replaced exactly; AGEB deletions are prohibited below.
            if table=='fact_accidentes_tiempo':
                condition=' AND '.join(f't.{quoted(k)}::text=s.{quoted(k)}' for k in keys)
                cursor.execute(f'DELETE FROM {quoted(table)} t WHERE NOT EXISTS (SELECT 1 FROM {quoted(stage)} s WHERE {condition})')
            cursor.execute(f'SELECT COUNT(*) FROM {quoted(table)}')
            count=cursor.fetchone()[0]
            if count != len(frame):
                raise ValueError(f'{table}: database has {count} rows, expected {len(frame)}; review stale geographic rows.')
        conn.exec_driver_sql((ROOT/'sql/03_views.sql').read_text())
        for file in ['sql/04_validation.sql']:
            cursor.execute((ROOT/file).read_text())
        cursor.close()
    engine.dispose()
    print('Warehouse loaded and validated in one transaction.')
