-- ============================================================================
-- Mérida Urban Intelligence: Geospatial Data Warehouse
-- 03_views.sql: Analytical Views for Block and AGEB Territorial KPIs
-- ============================================================================

-- ----------------------------------------------------------------------------
-- View 1: Block-Level Public Safety & Traffic Incident KPIs
-- Summarizes incident volume, typology breakdown, and severity for each block
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_block_incident_kpis AS
SELECT 
    b.cvegeo AS cvegeo_manzana,
    b.cve_ageb,
    b.cve_mza AS num_manzana,
    b.area_m2,
    COUNT(i.incident_id) AS total_accidentes,
    COUNT(CASE WHEN it.tipo_accidente = 'Colisión con motocicleta' THEN 1 END) AS choques_motocicleta,
    COUNT(CASE WHEN it.tipo_accidente = 'Colisión con peatón' THEN 1 END) AS atropellamientos,
    COUNT(CASE WHEN it.tipo_accidente = 'Colisión con vehículo' THEN 1 END) AS choques_automovil,
    COUNT(CASE WHEN it.tipo_accidente = 'Colisión con ciclista' THEN 1 END) AS choques_ciclista,
    COUNT(CASE WHEN it.tipo_accidente = 'Colisión con objeto fijo' THEN 1 END) AS choques_objeto_fijo,
    COUNT(CASE WHEN it.tipo_accidente = 'Volcadura' THEN 1 END) AS volcaduras,
    COUNT(CASE WHEN i.con_heridos = TRUE THEN 1 END) AS accidentes_con_heridos,
    COUNT(CASE WHEN i.con_fallecidos = TRUE THEN 1 END) AS accidentes_fatales,
    COUNT(CASE WHEN i.aliento_alcohol = TRUE THEN 1 END) AS accidentes_con_alcohol,
    COALESCE(MODE() WITHIN GROUP (ORDER BY it.tipo_accidente), 'Sin incidentes') AS tipo_accidente_predominante,
    ROUND((COUNT(i.incident_id)::NUMERIC / NULLIF(b.area_m2 / 1000000.0, 0)), 2) AS incidentes_por_km2,
    b.geom AS geom_block,
    b.geom_wgs84 AS geom_block_wgs84
FROM dim_block b
LEFT JOIN fact_traffic_incidents i ON b.cvegeo = i.cvegeo_manzana
LEFT JOIN dim_incident_type it ON i.tipo_id = it.tipo_id
GROUP BY b.cvegeo, b.cve_ageb, b.cve_mza, b.area_m2, b.geom, b.geom_wgs84;

-- ----------------------------------------------------------------------------
-- View 2: Block-Level Economic Activity Breakdown (DENUE)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_block_economic_kpis AS
SELECT 
    b.cvegeo AS cvegeo_manzana,
    b.cve_ageb,
    b.cve_mza AS num_manzana,
    COUNT(e.id_estab) AS total_establecimientos,
    COUNT(CASE WHEN d.sector_code = '46' THEN 1 END) AS comercio_menudeo,
    COUNT(CASE WHEN d.sector_code = '72' THEN 1 END) AS servicios_alimentos_hospedaje,
    COUNT(CASE WHEN d.sector_code IN ('43', '46') THEN 1 END) AS comercio_total,
    COUNT(CASE WHEN d.sector_code IN ('54', '52', '53') THEN 1 END) AS servicios_profesionales_financieros,
    ROUND((COUNT(e.id_estab)::NUMERIC / NULLIF(b.area_m2 / 1000000.0, 0)), 2) AS densidad_comercial_km2
FROM dim_block b
LEFT JOIN fact_economic_establishments e ON b.cvegeo = e.cvegeo_manzana
LEFT JOIN dim_economic_activity d ON e.codigo_act = d.codigo_act
GROUP BY b.cvegeo, b.cve_ageb, b.cve_mza, b.area_m2;

-- ----------------------------------------------------------------------------
-- View 3: Integrated Block Analytics (Safety + Economy)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_block_unified_analytics AS
SELECT 
    bk.cvegeo_manzana,
    bk.cve_ageb,
    bk.num_manzana,
    bk.area_m2,
    bk.total_accidentes,
    bk.choques_motocicleta,
    bk.atropellamientos,
    bk.choques_automovil,
    bk.accidentes_con_heridos,
    bk.accidentes_fatales,
    bk.tipo_accidente_predominante,
    bk.incidentes_por_km2,
    be.total_establecimientos,
    be.comercio_menudeo,
    be.servicios_alimentos_hospedaje,
    be.densidad_comercial_km2,
    ROUND(
        (bk.total_accidentes::NUMERIC / NULLIF(be.total_establecimientos, 0)) * 100.0, 
        2
    ) AS accidentes_por_100_establecimientos,
    bk.geom_block,
    bk.geom_block_wgs84
FROM view_block_incident_kpis bk
JOIN view_block_economic_kpis be ON bk.cvegeo_manzana = be.cvegeo_manzana;

-- ----------------------------------------------------------------------------
-- View 4: Territorial Rollup per AGEB (Demographics + Economy + Safety)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_ageb_territorial_kpis AS
WITH sector_proportions AS (
    SELECT 
        e.cve_ageb,
        d.sector_code,
        COUNT(*)::NUMERIC AS count_s,
        SUM(COUNT(*)) OVER (PARTITION BY e.cve_ageb)::NUMERIC AS total_ageb_estabs
    FROM fact_economic_establishments e
    JOIN dim_economic_activity d ON e.codigo_act = d.codigo_act
    GROUP BY e.cve_ageb, d.sector_code
),
shannon_entropy AS (
    SELECT 
        cve_ageb,
        -1.0 * SUM((count_s / total_ageb_estabs) * LN(count_s / total_ageb_estabs)) AS shannon_diversity_index
    FROM sector_proportions
    WHERE total_ageb_estabs > 0
    GROUP BY cve_ageb
),
accidents_ageb AS (
    SELECT 
        cve_ageb,
        COUNT(incident_id) AS total_accidentes,
        COUNT(CASE WHEN con_heridos = TRUE OR con_fallecidos = TRUE THEN 1 END) AS total_accidentes_graves
    FROM fact_traffic_incidents
    GROUP BY cve_ageb
),
economy_ageb AS (
    SELECT 
        cve_ageb,
        COUNT(id_estab) AS total_establecimientos
    FROM fact_economic_establishments
    GROUP BY cve_ageb
)
SELECT 
    a.cvegeo AS cvegeo_ageb,
    a.cve_ageb,
    a.area_km2,
    demo.pobtot,
    demo.pob0_14,
    demo.pob15_64,
    demo.pob65_mas,
    demo.pea,
    demo.vivtot,
    demo.vph_inter,
    ROUND((demo.pobtot::NUMERIC / NULLIF(a.area_km2, 0)), 2) AS densidad_poblacional_km2,
    COALESCE(eco.total_establecimientos, 0) AS total_establecimientos,
    ROUND((COALESCE(eco.total_establecimientos, 0)::NUMERIC / NULLIF(a.area_km2, 0)), 2) AS densidad_establecimientos_km2,
    ROUND((COALESCE(eco.total_establecimientos, 0)::NUMERIC / NULLIF(demo.pobtot, 0)) * 1000.0, 2) AS establecimientos_por_1000_hab,
    ROUND(COALESCE(sh.shannon_diversity_index, 0)::NUMERIC, 4) AS indice_diversidad_shannon,
    COALESCE(acc.total_accidentes, 0) AS total_accidentes,
    COALESCE(acc.total_accidentes_graves, 0) AS total_accidentes_graves,
    ROUND((COALESCE(acc.total_accidentes, 0)::NUMERIC / NULLIF(demo.pobtot, 0)) * 1000.0, 2) AS tasa_accidentes_por_1000_hab,
    ROUND((COALESCE(acc.total_accidentes, 0)::NUMERIC / NULLIF(a.area_km2, 0)), 2) AS densidad_accidentes_km2,
    a.geom,
    a.geom_wgs84
FROM dim_ageb a
LEFT JOIN fact_ageb_demographics demo ON a.cvegeo = demo.cvegeo_ageb
LEFT JOIN economy_ageb eco ON a.cve_ageb = eco.cve_ageb
LEFT JOIN shannon_entropy sh ON a.cve_ageb = sh.cve_ageb
LEFT JOIN accidents_ageb acc ON a.cve_ageb = acc.cve_ageb;

-- ----------------------------------------------------------------------------
-- View 5: Top 100 High-Risk Accident Hotspot Blocks in Mérida
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_high_risk_accident_blocks AS
SELECT 
    cvegeo_manzana,
    cve_ageb,
    num_manzana,
    total_accidentes,
    choques_motocicleta,
    atropellamientos,
    choques_automovil,
    accidentes_con_heridos,
    accidentes_fatales,
    tipo_accidente_predominante,
    total_establecimientos,
    densidad_comercial_km2,
    incidentes_por_km2,
    geom_block,
    geom_block_wgs84
FROM view_block_unified_analytics
WHERE total_accidentes > 0
ORDER BY total_accidentes DESC, incidentes_por_km2 DESC
LIMIT 100;
