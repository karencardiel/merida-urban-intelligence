# Findings from the warehouse

## Geographic scope

Urban AGEBs of the locality of Mérida. ATUS was authorized by the instructor as the road-safety source.

## Totals

483 AGEBs; 921,771 residents; 54,995 businesses; 2,130 accidents.

## Correlations

- Pearson densidad_pob_km2 vs densidad_establecimientos_km2: coefficient 0.1595, p 0.0004349, n 483.
- Spearman densidad_pob_km2 vs densidad_establecimientos_km2: coefficient 0.4541, p 5.985e-26, n 483.
- Pearson densidad_pob_km2 vs densidad_accidentes_km2: coefficient 0.0920, p 0.04339, n 483.
- Spearman densidad_pob_km2 vs densidad_accidentes_km2: coefficient 0.1492, p 0.001007, n 483.
- Pearson densidad_establecimientos_km2 vs densidad_accidentes_km2: coefficient 0.2387, p 1.1e-07, n 483.
- Spearman densidad_establecimientos_km2 vs densidad_accidentes_km2: coefficient 0.4348, p 1.08e-23, n 483.

## Spatial associations

- densidad_pob_km2: Moran I 0.4743, permutation p 0.001; evidence of spatial clustering.
- densidad_accidentes_km2: Moran I 0.0994, permutation p 0.001; evidence of spatial clustering.
- Business density and neighboring accident density: bivariate Moran I 0.1218, permutation p 0.001. This statistic relates businesses in an area to accidents in neighboring areas.

## Interpretation cautions

- Spatial association does not establish causality.
- 2020 population, 2024 accidents and the DENUE snapshot are not a single contemporaneous year.
- LISA p-values are unadjusted exploratory results across multiple local tests.
- Global Moran includes disconnected components and islands; assess sensitivity if required.
- Densities share an area denominator and can show associations partly related to that denominator.
- Traffic accidents per resident are a territorial indicator, not an individual travel-risk estimate.
