import unittest
import numpy as np
import pandas as pd
import geopandas as gpd
from src.config import PROCESSED

class ProcessedDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dw=pd.read_csv(PROCESSED/'dw_ageb.csv',dtype={'CVE_AGEB':str})
        cls.temporal=pd.read_csv(PROCESSED/'accidentes_tiempo.csv',dtype={'CVE_AGEB':str})
    def test_grain_and_geographic_relationships(self):
        self.assertEqual(len(self.dw),483)
        self.assertFalse(self.dw.CVE_AGEB.duplicated().any())
        self.assertFalse(self.temporal.duplicated(['CVE_AGEB','ANIO','MES','periodo_dia']).any())
        self.assertTrue(set(self.temporal.CVE_AGEB).issubset(set(self.dw.CVE_AGEB)))
    def test_measures_reconcile(self):
        self.assertEqual(self.dw.total_accidentes.sum(),self.temporal.total_accidentes.sum())
        types=self.dw.filter(regex='^accidentes_tipo_')
        self.assertTrue(self.dw.total_accidentes.eq(types.sum(axis=1)).all())
        self.assertTrue(self.dw.total_establecimientos.eq(self.dw.comercio+self.dw.servicios+self.dw.otros).all())
        self.assertTrue(self.dw.retail.le(self.dw.comercio).all())
    def test_missing_and_ratio_policy(self):
        self.assertFalse(self.dw[['total_establecimientos','retail','total_accidentes']].isna().any().any())
        values=self.dw.select_dtypes('number').to_numpy(dtype=float)
        self.assertFalse(np.isinf(values).any())
        self.assertTrue(self.dw.loc[self.dw.POBTOT.eq(0),'accidentes_por_1000_hab'].isna().all())
    def test_spatial_export(self):
        gdf=gpd.read_file(PROCESSED/'dw_ageb.gpkg')
        self.assertEqual(gdf.crs.to_epsg(),4326)
        self.assertTrue(gdf.geometry.geom_type.eq('MultiPolygon').all())
        self.assertTrue(gdf.geometry.is_valid.all())
        self.assertTrue(gdf.area_km2.gt(0).all())

if __name__=='__main__':unittest.main()
