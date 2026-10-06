-- ============================================================================
-- Mérida Urban Intelligence: Geospatial Data Warehouse
-- 02_load.sql: Data Loading, Spatial Snapping & Integrity Verification
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Populate dim_time from Calendar Sequence
-- ----------------------------------------------------------------------------
INSERT INTO dim_time (fecha, anio, mes, mes_nombre, dia, dia_semana, es_fin_de_semana, trimestre)
SELECT 
    d::DATE AS fecha,
    EXTRACT(YEAR FROM d)::SMALLINT AS anio,
    EXTRACT(MONTH FROM d)::SMALLINT AS mes,
    TO_CHAR(d, 'TMMonth') AS mes_nombre,
    EXTRACT(DAY FROM d)::SMALLINT AS dia,
    TO_CHAR(d, 'TMDay') AS dia_semana,
    CASE WHEN EXTRACT(ISODOW FROM d) IN (6, 7) THEN TRUE ELSE FALSE END AS es_fin_de_semana,
    EXTRACT(QUARTER FROM d)::SMALLINT AS trimestre
FROM generate_series('2020-01-01'::DATE, '2026-12-31'::DATE, '1 day'::INTERVAL) d
ON CONFLICT (fecha) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 2. Populate Standard Accident / Incident Typologies (dim_incident_type)
-- ----------------------------------------------------------------------------
INSERT INTO dim_incident_type (tipo_id, categoria, tipo_accidente, nivel_gravedad) VALUES
(1, 'Colisión', 'Colisión con vehículo', 'Moderado'),
(2, 'Colisión', 'Colisión con motocicleta', 'Grave'),
(3, 'Atropellamiento', 'Colisión con peatón', 'Crítico'),
(4, 'Colisión', 'Colisión con ciclista', 'Grave'),
(5, 'Colisión', 'Colisión con objeto fijo', 'Moderado'),
(6, 'Volcadura', 'Volcadura', 'Grave'),
(7, 'Salida de Camino', 'Salida del camino', 'Moderado'),
(8, 'Caída de Persona', 'Caída de pasajero', 'Leve')
ON CONFLICT (tipo_accidente) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 3. Post-Load Spatial Snapping for Traffic Incidents
-- Snaps any incident points that land on roadway buffers directly into the
-- nearest intersecting urban block polygon (within 25m street corridor)
-- ----------------------------------------------------------------------------
UPDATE fact_traffic_incidents f
SET 
    cvegeo_manzana = b.cvegeo,
    cve_ageb = b.cve_ageb
FROM dim_block b
WHERE f.cvegeo_manzana IS NULL
  AND ST_Contains(b.geom, f.geom_point);

-- Secondary pass for road-centerline points: snap to closest block within 25 meters
UPDATE fact_traffic_incidents f
SET 
    cvegeo_manzana = sub.cvegeo,
    cve_ageb = sub.cve_ageb
FROM (
    SELECT DISTINCT ON (f2.incident_id)
        f2.incident_id,
        b2.cvegeo,
        b2.cve_ageb
    FROM fact_traffic_incidents f2
    JOIN dim_block b2 
      ON ST_DWithin(f2.geom_point, b2.geom, 25.0)
    WHERE f2.cvegeo_manzana IS NULL
    ORDER BY f2.incident_id, ST_Distance(f2.geom_point, b2.geom) ASC
) sub
WHERE f.incident_id = sub.incident_id
  AND f.cvegeo_manzana IS NULL;

-- ----------------------------------------------------------------------------
-- 4. Data Warehouse Quality & Integrity Audit Queries
-- ----------------------------------------------------------------------------

-- Audit 1: Check geometry validity across all spatial tables
SELECT 'dim_ageb' AS table_name, COUNT(*) AS invalid_count 
FROM dim_ageb WHERE NOT ST_IsValid(geom)
UNION ALL
SELECT 'dim_block', COUNT(*) FROM dim_block WHERE NOT ST_IsValid(geom)
UNION ALL
SELECT 'fact_economic_establishments', COUNT(*) FROM fact_economic_establishments WHERE NOT ST_IsValid(geom_point)
UNION ALL
SELECT 'fact_traffic_incidents', COUNT(*) FROM fact_traffic_incidents WHERE NOT ST_IsValid(geom_point);

-- Audit 2: Point-to-Polygon match rate for incidents
SELECT 
    COUNT(*) AS total_incidents,
    COUNT(cvegeo_manzana) AS matched_to_block,
    ROUND(100.0 * COUNT(cvegeo_manzana) / NULLIF(COUNT(*), 0), 2) AS pct_matched_blocks
FROM fact_traffic_incidents;

-- Audit 3: Economic units match rate
SELECT 
    COUNT(*) AS total_establishments,
    COUNT(cvegeo_manzana) AS matched_to_block,
    ROUND(100.0 * COUNT(cvegeo_manzana) / NULLIF(COUNT(*), 0), 2) AS pct_matched_blocks
FROM fact_economic_establishments;
