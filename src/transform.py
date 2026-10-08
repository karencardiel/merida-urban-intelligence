"""Clean sources and aggregate to the selected geographic grain."""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import MultiPolygon
from .config import PROCESSED
from .extract import read_sources

CENSUS_COLUMNS = ['POBTOT','POB0_14','POB15_64','POB65_MAS','PEA','PE_INAC','POCUPADA','PDESOCUP','VIVTOT','TVIVHAB']
ACCIDENT_TYPES = [1,2,4,5,6,7,8,10,11]
SERVICE_SECTORS = {'48','49','51','52','53','54','55','56','61','62','71','72','81','93'}

def ratio(numerator, denominator, scale=1):
    return numerator.div(denominator.where(denominator > 0)).mul(scale)

def normalize_code(series, width):
    return series.astype('string').str.strip().str.upper().str.zfill(width)

def assign_points(points, polygons):
    joined = gpd.sjoin(points.to_crs(polygons.crs), polygons[['CVE_AGEB','geometry']], how='left', predicate='within')
    if joined.index.duplicated().any():
        raise ValueError('Spatial join assigned a point to multiple polygons; inspect polygon overlaps.')
    return joined

def build_processed():
    census, denue, polygons, locality, accidents = read_sources()
    PROCESSED.mkdir(parents=True,exist_ok=True)
    ageb = polygons[(polygons.CVE_ENT == '31') & (polygons.CVE_MUN == '050') & (polygons.CVE_LOC == '0001')].copy()
    ageb['CVE_AGEB'] = normalize_code(ageb.CVE_AGEB,4)
    if ageb.crs is None or not ageb.crs.is_projected:
        raise ValueError('Area requires the projected INEGI CRS.')
    if not ageb.geometry.is_valid.all() or ageb.geometry.is_empty.any() or ageb.CVE_AGEB.duplicated().any():
        raise ValueError('Invalid, empty or duplicated AGEB geography.')
    ageb['area_km2'] = ageb.geometry.area / 1_000_000
    if not ageb.area_km2.gt(0).all():
        raise ValueError('Nonpositive polygon area.')

    c = census[(census.ENTIDAD == 31) & (census.MUN == 50) & (census.LOC == 1) & (census.MZA == 0) & (census.NOM_LOC == 'Total AGEB urbana')].copy()
    c['CVE_AGEB'] = normalize_code(c.AGEB,4)
    for column in CENSUS_COLUMNS:
        c[column] = pd.to_numeric(c[column].replace('*',pd.NA), errors='coerce')
    if set(c.CVE_AGEB) != set(ageb.CVE_AGEB) or c.CVE_AGEB.duplicated().any():
        raise ValueError('Census and polygon geographic keys do not match one-to-one.')
    dw = ageb[['CVE_AGEB','area_km2','geometry']].merge(c[['CVE_AGEB','ENTIDAD','MUN','LOC','AGEB']+CENSUS_COLUMNS],on='CVE_AGEB',validate='one_to_one')
    dw['densidad_pob_km2'] = ratio(dw.POBTOT,dw.area_km2)
    dw['tasa_pea'] = ratio(dw.PEA,dw.PEA+dw.PE_INAC,100)
    for field, name in [('POB0_14','porcentaje_0_14'),('POB15_64','porcentaje_15_64'),('POB65_MAS','porcentaje_65_mas')]:
        dw[name] = ratio(dw[field],dw.POBTOT,100)

    # Preserve the original AGEB identifier integration. Unmatched codes are
    # evaluated by coordinates instead of being discarded without inspection.
    d = denue[(denue.cve_ent == 31) & (denue.cve_mun == 50) & (denue.cve_loc == 1)].copy()
    if d.id.duplicated().any():
        raise ValueError('Duplicate DENUE IDs require source review.')
    d['CVE_AGEB'] = normalize_code(d.ageb,4)
    d['source_ageb'] = d.CVE_AGEB
    unmatched = ~d.CVE_AGEB.isin(ageb.CVE_AGEB)
    candidates = d.loc[unmatched].copy()
    candidates['latitud'] = pd.to_numeric(candidates.latitud,errors='coerce')
    candidates['longitud'] = pd.to_numeric(candidates.longitud,errors='coerce')
    valid_coordinates = candidates.latitud.between(-90,90) & candidates.longitud.between(-180,180)
    candidates_valid = candidates.loc[valid_coordinates].drop(columns='CVE_AGEB')
    if len(candidates_valid):
        points = gpd.GeoDataFrame(candidates_valid,geometry=gpd.points_from_xy(candidates_valid.longitud,candidates_valid.latitud),crs=4326)
        recovered = assign_points(points,ageb)
        d.loc[recovered.index,'CVE_AGEB'] = recovered.CVE_AGEB
    d.loc[~d.CVE_AGEB.isin(ageb.CVE_AGEB),'CVE_AGEB'] = pd.NA
    d[['id','source_ageb','CVE_AGEB','latitud','longitud']].to_csv(PROCESSED/'denue_assignment_audit.csv',index=False)
    recovered_count = int((unmatched & d.CVE_AGEB.notna()).sum())
    economic_excluded = int(d.CVE_AGEB.isna().sum())
    d = d[d.CVE_AGEB.notna()].copy()
    d['sector_scian'] = d.codigo_act.astype('string').str[:2]
    d['categoria'] = np.select([d.sector_scian.isin(['43','46']),d.sector_scian.isin(SERVICE_SECTORS)],['Comercio','Servicios'],default='Otros')
    econ = d.groupby('CVE_AGEB').agg(total_establecimientos=('id','size'),comercio=('categoria',lambda s:s.eq('Comercio').sum()),retail=('sector_scian',lambda s:s.eq('46').sum()),servicios=('categoria',lambda s:s.eq('Servicios').sum()),otros=('categoria',lambda s:s.eq('Otros').sum())).reset_index()
    activities = d.groupby(['CVE_AGEB','codigo_act','nombre_act']).size().reset_index(name='cantidad_actividad_dominante')
    dominant = activities.sort_values(['CVE_AGEB','cantidad_actividad_dominante','codigo_act'],ascending=[True,False,True]).drop_duplicates('CVE_AGEB').rename(columns={'codigo_act':'actividad_dominante_codigo','nombre_act':'actividad_dominante'})
    dominant['actividad_dominante_codigo'] = dominant.actividad_dominante_codigo.astype('string')
    econ = econ.merge(dominant,on='CVE_AGEB',validate='one_to_one')
    dw = dw.merge(econ,on='CVE_AGEB',how='left',validate='one_to_one')
    econ_counts = ['total_establecimientos','comercio','retail','servicios','otros']
    dw[econ_counts] = dw[econ_counts].fillna(0).astype('int64')
    for count, density in [('total_establecimientos','densidad_establecimientos_km2'),('comercio','densidad_comercio_km2'),('retail','densidad_retail_km2'),('servicios','densidad_servicios_km2')]:
        dw[density] = ratio(dw[count],dw.area_km2)
    dw['establecimientos_por_1000_hab'] = ratio(dw.total_establecimientos,dw.POBTOT,1000)

    a = accidents[(accidents.EDO == 31) & (accidents.MPIO == 50)].copy()
    if a.ID.duplicated().any():
        raise ValueError('Duplicate ATUS IDs require source review.')
    a['LATITUD'] = pd.to_numeric(a.LATITUD,errors='coerce')
    a['LONGITUD'] = pd.to_numeric(a.LONGITUD,errors='coerce')
    valid_coordinates = a.LATITUD.between(-90,90) & a.LONGITUD.between(-180,180)
    if not valid_coordinates.all():
        raise ValueError('Invalid accident coordinates: review before integration.')
    # ATUS already provides official points. Reconstruct coordinates for
    # inspection, while using the shapefile geometry as the spatial authority.
    reconstructed = gpd.GeoSeries(gpd.points_from_xy(a.LONGITUD,a.LATITUD),crs=4326,index=a.index)
    official_points = a.to_crs(4326).geometry
    if not official_points.is_valid.all() or not official_points.geom_type.eq('Point').all():
        raise ValueError('Invalid official ATUS point geometry.')
    point_difference_m = official_points.to_crs(32616).distance(reconstructed.to_crs(32616))
    a = a.to_crs(4326)
    joined = assign_points(a,ageb)
    outside = joined[joined.CVE_AGEB.isna()].copy()
    local = locality[(locality.CVE_ENT=='31') & (locality.CVE_MUN=='050') & (locality.CVE_LOC=='0001')]
    local_test = gpd.sjoin(outside.drop(columns='index_right'),local[['CVEGEO','geometry']],how='left',predicate='within')
    outside.drop(columns='geometry').to_csv(PROCESSED/'accidentes_excluidos.csv',index=False)
    a = joined[joined.CVE_AGEB.notna()].copy()
    totals = a.groupby('CVE_AGEB').agg(total_accidentes=('ID','size'),total_muertos=('TOTMUERTOS','sum'),total_heridos=('TOTHERIDOS','sum'))
    type_counts = pd.crosstab(a.CVE_AGEB,a.TIPACCID)
    type_counts.columns = ['accidentes_tipo_'+str(int(x)) for x in type_counts.columns]
    accident_counts = ['accidentes_tipo_'+str(x) for x in ACCIDENT_TYPES]
    unexpected = set(type_counts.columns)-set(accident_counts)
    if unexpected:
        raise ValueError(f'New accident types require schema extension: {unexpected}')
    type_counts = type_counts.reindex(columns=accident_counts,fill_value=0)
    totals = totals.join(type_counts).reset_index()
    dw = dw.merge(totals,on='CVE_AGEB',how='left',validate='one_to_one')
    fields = ['total_accidentes','total_muertos','total_heridos']+accident_counts
    dw[fields] = dw[fields].fillna(0).astype('int64')
    dw['densidad_accidentes_km2'] = ratio(dw.total_accidentes,dw.area_km2)
    dw['accidentes_por_1000_hab'] = ratio(dw.total_accidentes,dw.POBTOT,1000)
    dw['accidentes_por_establecimiento'] = ratio(dw.total_accidentes,dw.total_establecimientos)
    a['periodo_dia'] = pd.cut(pd.to_numeric(a.HORA,errors='coerce'),bins=[-1,5,11,17,23],labels=['Madrugada','Mañana','Tarde','Noche']).astype('string').fillna('No especificado')
    temporal = a.groupby(['CVE_AGEB','ANIO','MES','periodo_dia'],observed=True).agg(total_accidentes=('ID','size'),total_muertos=('TOTMUERTOS','sum'),total_heridos=('TOTHERIDOS','sum')).reset_index()
    if temporal.total_accidentes.sum() != dw.total_accidentes.sum():
        raise ValueError('Temporal and geographic incident totals differ.')
    if not dw.total_accidentes.eq(dw[accident_counts].sum(axis=1)).all():
        raise ValueError('Accident types do not reconcile with total incidents.')
    dw = dw.sort_values('CVE_AGEB').reset_index(drop=True)
    for column in dw.select_dtypes(include='number'):
        if np.isinf(dw[column].to_numpy(dtype=float)).any():
            raise ValueError(f'Infinite metric: {column}')
    spatial = dw.to_crs(4326)
    spatial.geometry = spatial.geometry.map(lambda g:MultiPolygon([g]) if g.geom_type=='Polygon' else g)
    spatial.drop(columns='geometry').to_csv(PROCESSED/'dw_ageb.csv',index=False)
    temporal.sort_values(['CVE_AGEB','ANIO','MES','periodo_dia']).to_csv(PROCESSED/'accidentes_tiempo.csv',index=False)
    pd.DataFrame({'CVE_AGEB':spatial.CVE_AGEB,'geometry_wkt':spatial.geometry.to_wkt()}).to_csv(PROCESSED/'ageb_geometry.csv',index=False)
    spatial.to_file(PROCESSED/'dw_ageb.gpkg',layer='ageb_merida',driver='GPKG')
    quality = {'scope':'Urban AGEBs, entity 31, municipality 050, locality 0001','ageb_count':len(dw),'population':int(dw.POBTOT.sum()),'denue_candidates':int(unmatched.size),'denue_unmatched_codes':int(unmatched.sum()),'denue_recovered_by_coordinates':recovered_count,'denue_excluded':economic_excluded,'businesses':int(dw.total_establecimientos.sum()),'accidents_municipality':len(joined),'accidents_integrated':len(a),'accidents_excluded':len(outside),'excluded_accidents_inside_locality':int(local_test.CVEGEO.notna().sum()),'temporal_rows':len(temporal),'census_missing':{k:int(dw[k].isna().sum()) for k in CENSUS_COLUMNS},'census_year':2020,'accident_year':2024,'atus_geometry_authority':'Official shapefile point geometry; latitude/longitude points reconstructed for comparison only','max_coordinate_geometry_difference_m':float(point_difference_m.max())}
    (PROCESSED/'quality_summary.json').write_text(json.dumps(quality,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(quality,indent=2,ensure_ascii=False))
    return spatial, temporal
