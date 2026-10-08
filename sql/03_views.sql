-- ============================================================
-- Mérida Urban Intelligence
-- Data Warehouse - Analytical Views
-- ============================================================

-- ============================================================
-- 1. GENERAL AGEB SUMMARY
-- ============================================================

CREATE OR REPLACE VIEW vw_ageb_resumen AS
SELECT
    d."CVE_AGEB",
    d.area_km2,

    f."POBTOT",
    f.densidad_pob_km2,
    f.tasa_pea,

    e.total_establecimientos,
    e.densidad_establecimientos_km2,
    e.establecimientos_por_1000_hab,
    e.actividad_dominante_codigo,
    e.actividad_dominante,
    e.cantidad_actividad_dominante,

    a.total_accidentes,
    a.total_muertos,
    a.total_heridos,
    a.densidad_accidentes_km2,
    a.accidentes_por_1000_hab,
    a.accidentes_por_establecimiento

FROM dim_ageb d
JOIN fact_demografia f
    ON d."CVE_AGEB" = f."CVE_AGEB"
JOIN fact_economia e
    ON d."CVE_AGEB" = e."CVE_AGEB"
JOIN fact_accidentes a
    ON d."CVE_AGEB" = a."CVE_AGEB";


-- ============================================================
-- 2. DEMOGRAPHIC KPI SUMMARY
-- ============================================================

CREATE OR REPLACE VIEW vw_kpi_demografia AS
SELECT
    SUM("POBTOT") AS poblacion_total,
    SUM("PEA") AS pea_total,
    SUM("PE_INAC") AS poblacion_inactiva,
    SUM("POCUPADA") AS poblacion_ocupada,
    SUM("PDESOCUP") AS poblacion_desocupada
FROM fact_demografia;


-- ============================================================
-- 3. ECONOMIC KPI SUMMARY
-- ============================================================

CREATE OR REPLACE VIEW vw_kpi_economia AS
SELECT
    SUM(total_establecimientos) AS total_establecimientos,
    SUM(comercio) AS total_comercio,
    SUM(retail) AS total_retail,
    SUM(servicios) AS total_servicios,
    SUM(otros) AS total_otros,
    AVG(densidad_establecimientos_km2) AS densidad_promedio_establecimientos_km2,
    AVG(densidad_retail_km2) AS densidad_promedio_retail_km2
FROM fact_economia;


-- ============================================================
-- 4. PUBLIC SAFETY / TRAFFIC ACCIDENT KPI SUMMARY
-- ============================================================

CREATE OR REPLACE VIEW vw_kpi_accidentes AS
SELECT
    SUM(total_accidentes) AS total_accidentes,
    SUM(total_muertos) AS total_muertos,
    SUM(total_heridos) AS total_heridos,

    SUM(accidentes_tipo_1) AS tipo_1,
    SUM(accidentes_tipo_2) AS tipo_2,
    SUM(accidentes_tipo_4) AS tipo_4,
    SUM(accidentes_tipo_5) AS tipo_5,
    SUM(accidentes_tipo_6) AS tipo_6,
    SUM(accidentes_tipo_7) AS tipo_7,
    SUM(accidentes_tipo_8) AS tipo_8,
    SUM(accidentes_tipo_10) AS tipo_10,
    SUM(accidentes_tipo_11) AS tipo_11

FROM fact_accidentes;


-- ============================================================
-- 5. TOP AGEBs BY POPULATION DENSITY
-- ============================================================

CREATE OR REPLACE VIEW vw_top_densidad_poblacion AS
SELECT
    d."CVE_AGEB",
    d.area_km2,
    f."POBTOT",
    f.densidad_pob_km2
FROM dim_ageb d
JOIN fact_demografia f
    ON d."CVE_AGEB" = f."CVE_AGEB"
ORDER BY f.densidad_pob_km2 DESC;


-- ============================================================
-- 6. TOP AGEBs BY ESTABLISHMENT DENSITY
-- ============================================================

CREATE OR REPLACE VIEW vw_top_densidad_establecimientos AS
SELECT
    d."CVE_AGEB",
    d.area_km2,
    e.total_establecimientos,
    e.densidad_establecimientos_km2
FROM dim_ageb d
JOIN fact_economia e
    ON d."CVE_AGEB" = e."CVE_AGEB"
ORDER BY e.densidad_establecimientos_km2 DESC;


-- ============================================================
-- 7. TOP AGEBs BY ACCIDENT DENSITY
-- ============================================================

CREATE OR REPLACE VIEW vw_top_densidad_accidentes AS
SELECT
    d."CVE_AGEB",
    d.area_km2,
    a.total_accidentes,
    a.densidad_accidentes_km2
FROM dim_ageb d
JOIN fact_accidentes a
    ON d."CVE_AGEB" = a."CVE_AGEB"
ORDER BY a.densidad_accidentes_km2 DESC;


-- ============================================================
-- 8. CORRELATION DATASET
-- ============================================================

CREATE OR REPLACE VIEW vw_correlaciones AS
SELECT
    d."CVE_AGEB",
    f.densidad_pob_km2,
    e.densidad_establecimientos_km2,
    a.densidad_accidentes_km2
FROM dim_ageb d
JOIN fact_demografia f
    ON d."CVE_AGEB" = f."CVE_AGEB"
JOIN fact_economia e
    ON d."CVE_AGEB" = e."CVE_AGEB"
JOIN fact_accidentes a
    ON d."CVE_AGEB" = a."CVE_AGEB";


-- ============================================================
-- 9. ACCIDENTS RELATIVE TO BUSINESS ACTIVITY
-- ============================================================

CREATE OR REPLACE VIEW vw_accidentes_negocios AS
SELECT
    d."CVE_AGEB",
    e.total_establecimientos,
    a.total_accidentes,
    a.accidentes_por_establecimiento
FROM dim_ageb d
JOIN fact_economia e
    ON d."CVE_AGEB" = e."CVE_AGEB"
JOIN fact_accidentes a
    ON d."CVE_AGEB" = a."CVE_AGEB";


-- ============================================================
-- 10. AGEBS WITH HIGH ACCIDENT DENSITY
-- ============================================================

CREATE OR REPLACE VIEW vw_accidentes_alta_densidad AS
SELECT
    d."CVE_AGEB",
    d.area_km2,
    a.total_accidentes,
    a.densidad_accidentes_km2
FROM dim_ageb d
JOIN fact_accidentes a
    ON d."CVE_AGEB" = a."CVE_AGEB"
WHERE a.densidad_accidentes_km2 >= (
    SELECT
        PERCENTILE_CONT(0.5)
        WITHIN GROUP (
            ORDER BY densidad_accidentes_km2
        )
    FROM fact_accidentes
);


-- ============================================================
-- 11. FULL ANALYTICAL DATASET
-- ============================================================

DROP VIEW IF EXISTS vw_analisis_ageb;
CREATE VIEW vw_analisis_ageb AS
SELECT d.*, f."POBTOT",
    f."POB0_14",
    f."POB15_64",
    f."POB65_MAS",
    f."PEA",
    f."PE_INAC",
    f."POCUPADA",
    f."PDESOCUP",
    f."VIVTOT",
    f."TVIVHAB",
    f.densidad_pob_km2,
    f.tasa_pea,
    f.porcentaje_0_14,
    f.porcentaje_15_64,
    f.porcentaje_65_mas,
    e.total_establecimientos,
    e.comercio,
    e.retail,
    e.servicios,
    e.otros,
    e.densidad_establecimientos_km2,
    e.densidad_comercio_km2,
    e.densidad_retail_km2,
    e.densidad_servicios_km2,
    e.establecimientos_por_1000_hab,
    e.actividad_dominante_codigo,
    e.actividad_dominante,
    e.cantidad_actividad_dominante,
    a.total_accidentes,
    a.total_muertos,
    a.total_heridos,
    a.accidentes_tipo_1,
    a.accidentes_tipo_2,
    a.accidentes_tipo_4,
    a.accidentes_tipo_5,
    a.accidentes_tipo_6,
    a.accidentes_tipo_7,
    a.accidentes_tipo_8,
    a.accidentes_tipo_10,
    a.accidentes_tipo_11,
    a.densidad_accidentes_km2,
    a.accidentes_por_1000_hab,
    a.accidentes_por_establecimiento
FROM dim_ageb d
JOIN fact_demografia f ON d."CVE_AGEB"=f."CVE_AGEB"
JOIN fact_economia e ON d."CVE_AGEB"=e."CVE_AGEB"
JOIN fact_accidentes a ON d."CVE_AGEB"=a."CVE_AGEB";

CREATE OR REPLACE VIEW vw_accidentes_tiempo AS
SELECT "CVE_AGEB",anio,mes,periodo_dia,total_accidentes,total_muertos,total_heridos
FROM fact_accidentes_tiempo;
