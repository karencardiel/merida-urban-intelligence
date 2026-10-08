-- Per-area indicators: densities must not be summed across areas.
SELECT * FROM vw_analisis_ageb ORDER BY "CVE_AGEB";
-- Geographic totals and pooled ratios; null denominator protects empty bases.
SELECT SUM(f."POBTOT") AS population,
 SUM(f."POBTOT")/NULLIF(SUM(d.area_km2),0) AS population_per_km2,
 100*SUM(f."PEA") FILTER (WHERE f."PE_INAC" IS NOT NULL)/NULLIF(SUM(f."PEA"+f."PE_INAC"),0) AS pea_percent,
 SUM(e.total_establecimientos) AS businesses,
 SUM(e.total_establecimientos)/NULLIF(SUM(d.area_km2),0) AS businesses_per_km2,
 1000*SUM(e.total_establecimientos)/NULLIF(SUM(f."POBTOT"),0) AS businesses_per_1000_residents,
 SUM(e.retail)/NULLIF(SUM(d.area_km2),0) AS retail_per_km2,
 SUM(e.servicios)/NULLIF(SUM(d.area_km2),0) AS services_per_km2,
 SUM(a.total_accidentes) AS accidents,
 1000*SUM(a.total_accidentes)/NULLIF(SUM(f."POBTOT"),0) AS accidents_per_1000_residents,
 SUM(a.total_accidentes)/NULLIF(SUM(e.total_establecimientos),0) AS accidents_per_business
FROM dim_ageb d JOIN fact_demografia f USING ("CVE_AGEB")
JOIN fact_economia e USING ("CVE_AGEB") JOIN fact_accidentes a USING ("CVE_AGEB");
SELECT anio,mes,periodo_dia,SUM(total_accidentes) AS accidents
FROM fact_accidentes_tiempo GROUP BY anio,mes,periodo_dia ORDER BY anio,mes,periodo_dia;
