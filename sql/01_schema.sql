-- ============================================================================
-- Mérida Urban Intelligence: Geospatial Data Warehouse
-- 01_schema.sql: DDL Specification for PostgreSQL with PostGIS
-- ============================================================================

-- 1. Enable PostGIS Spatial Extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- ----------------------------------------------------------------------------
-- 2. Geographic Dimensions
-- ----------------------------------------------------------------------------

-- Dimension: Áreas Geoestadísticas Básicas (AGEBs)
CREATE TABLE IF NOT EXISTS dim_ageb (
    cvegeo VARCHAR(9) PRIMARY KEY, -- Entidad (31) + Mun (050) + Loc (0001) + AGEB (4)
    cve_ent VARCHAR(2) NOT NULL DEFAULT '31',
    cve_mun VARCHAR(3) NOT NULL DEFAULT '050',
    cve_loc VARCHAR(4) NOT NULL DEFAULT '0001',
    cve_ageb VARCHAR(4) NOT NULL,
    area_km2 NUMERIC(10, 4) NOT NULL,
    geom GEOMETRY(MultiPolygon, 6372) NOT NULL,
    geom_wgs84 GEOMETRY(MultiPolygon, 4326) NOT NULL
);

-- Dimension: Urban Blocks (Manzanas) - The Target Unit of Analysis
CREATE TABLE IF NOT EXISTS dim_block (
    cvegeo VARCHAR(16) PRIMARY KEY, -- 31 + 050 + 0001 + AGEB (4) + MZA (3)
    cve_ent VARCHAR(2) NOT NULL DEFAULT '31',
    cve_mun VARCHAR(3) NOT NULL DEFAULT '050',
    cve_loc VARCHAR(4) NOT NULL DEFAULT '0001',
    cve_ageb VARCHAR(4) NOT NULL,
    cve_mza VARCHAR(3) NOT NULL,
    ambito VARCHAR(10) NOT NULL DEFAULT 'Urbana',
    tipomza VARCHAR(20) DEFAULT 'Típica',
    area_m2 NUMERIC(14, 2) NOT NULL,
    geom GEOMETRY(MultiPolygon, 6372) NOT NULL,
    geom_wgs84 GEOMETRY(MultiPolygon, 4326) NOT NULL
);

-- ----------------------------------------------------------------------------
-- 3. Thematic / Auxiliary Dimensions
-- ----------------------------------------------------------------------------

-- Dimension: Economic Activities (SCIAN)
CREATE TABLE IF NOT EXISTS dim_economic_activity (
    codigo_act VARCHAR(6) PRIMARY KEY,
    sector_code VARCHAR(2) NOT NULL,
    sector_name VARCHAR(150) NOT NULL,
    subsector_name VARCHAR(200),
    nombre_act VARCHAR(300) NOT NULL
);

-- Dimension: Incident / Accident Types (Public Safety & Traffic)
CREATE TABLE IF NOT EXISTS dim_incident_type (
    tipo_id SERIAL PRIMARY KEY,
    categoria VARCHAR(50) NOT NULL, -- Colisión, Atropellamiento, Volcadura, etc.
    tipo_accidente VARCHAR(100) UNIQUE NOT NULL,
    nivel_gravedad VARCHAR(20) NOT NULL -- Leve, Moderado, Grave, Fatal
);

-- Dimension: Time / Calendar
CREATE TABLE IF NOT EXISTS dim_time (
    time_id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL UNIQUE,
    anio SMALLINT NOT NULL,
    mes SMALLINT NOT NULL,
    mes_nombre VARCHAR(15) NOT NULL,
    dia SMALLINT NOT NULL,
    dia_semana VARCHAR(15) NOT NULL,
    es_fin_de_semana BOOLEAN NOT NULL,
    trimestre SMALLINT NOT NULL
);

-- ----------------------------------------------------------------------------
-- 4. Fact Tables
-- ----------------------------------------------------------------------------

-- Fact: Demographic and Housing Indicators (AGEB level)
CREATE TABLE IF NOT EXISTS fact_ageb_demographics (
    cvegeo_ageb VARCHAR(9) PRIMARY KEY REFERENCES dim_ageb(cvegeo) ON DELETE CASCADE,
    pobtot INTEGER NOT NULL DEFAULT 0,
    pobfem INTEGER NOT NULL DEFAULT 0,
    pobmas INTEGER NOT NULL DEFAULT 0,
    pob0_14 INTEGER NOT NULL DEFAULT 0,
    pob15_64 INTEGER NOT NULL DEFAULT 0,
    pob65_mas INTEGER NOT NULL DEFAULT 0,
    pea INTEGER NOT NULL DEFAULT 0,
    pe_ocupada INTEGER NOT NULL DEFAULT 0,
    vivtot INTEGER NOT NULL DEFAULT 0,
    vph_inter INTEGER NOT NULL DEFAULT 0
);

-- Fact: Economic Establishments (DENUE)
CREATE TABLE IF NOT EXISTS fact_economic_establishments (
    id_estab BIGINT PRIMARY KEY,
    clee VARCHAR(35),
    nom_estab VARCHAR(250) NOT NULL,
    codigo_act VARCHAR(6) REFERENCES dim_economic_activity(codigo_act),
    per_ocu_estrato VARCHAR(50),
    cvegeo_manzana VARCHAR(16) REFERENCES dim_block(cvegeo) ON DELETE SET NULL,
    cve_ageb VARCHAR(4) NOT NULL,
    latitud NUMERIC(10, 7) NOT NULL,
    longitud NUMERIC(10, 7) NOT NULL,
    geom_point GEOMETRY(Point, 6372) NOT NULL,
    geom_point_wgs84 GEOMETRY(Point, 4326) NOT NULL
);

-- Fact: Public Safety & Traffic Incidents
CREATE TABLE IF NOT EXISTS fact_traffic_incidents (
    incident_id BIGSERIAL PRIMARY KEY,
    cvegeo_manzana VARCHAR(16) REFERENCES dim_block(cvegeo) ON DELETE SET NULL,
    cve_ageb VARCHAR(4),
    tipo_id INTEGER REFERENCES dim_incident_type(tipo_id),
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    dia_semana VARCHAR(15) NOT NULL,
    calle_1 VARCHAR(150),
    calle_2 VARCHAR(150),
    colonia VARCHAR(150),
    con_heridos BOOLEAN DEFAULT FALSE,
    con_fallecidos BOOLEAN DEFAULT FALSE,
    aliento_alcohol BOOLEAN DEFAULT FALSE,
    latitud NUMERIC(10, 7) NOT NULL,
    longitud NUMERIC(10, 7) NOT NULL,
    geom_point GEOMETRY(Point, 6372) NOT NULL,
    geom_point_wgs84 GEOMETRY(Point, 4326) NOT NULL
);

-- ----------------------------------------------------------------------------
-- 5. Spatial & Foreign Key Indices (GIST)
-- ----------------------------------------------------------------------------

-- Spatial indices for polygons
CREATE INDEX IF NOT EXISTS idx_dim_ageb_geom ON dim_ageb USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_dim_ageb_geom_wgs84 ON dim_ageb USING GIST(geom_wgs84);
CREATE INDEX IF NOT EXISTS idx_dim_block_geom ON dim_block USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_dim_block_geom_wgs84 ON dim_block USING GIST(geom_wgs84);

-- Spatial indices for points
CREATE INDEX IF NOT EXISTS idx_fact_denue_geom ON fact_economic_establishments USING GIST(geom_point);
CREATE INDEX IF NOT EXISTS idx_fact_denue_geom_wgs84 ON fact_economic_establishments USING GIST(geom_point_wgs84);
CREATE INDEX IF NOT EXISTS idx_fact_incidents_geom ON fact_traffic_incidents USING GIST(geom_point);
CREATE INDEX IF NOT EXISTS idx_fact_incidents_geom_wgs84 ON fact_traffic_incidents USING GIST(geom_point_wgs84);

-- Standard B-Tree indices on Foreign Keys and lookups
CREATE INDEX IF NOT EXISTS idx_dim_block_ageb ON dim_block(cve_ageb);
CREATE INDEX IF NOT EXISTS idx_fact_denue_manzana ON fact_economic_establishments(cvegeo_manzana);
CREATE INDEX IF NOT EXISTS idx_fact_denue_act ON fact_economic_establishments(codigo_act);
CREATE INDEX IF NOT EXISTS idx_fact_incidents_manzana ON fact_traffic_incidents(cvegeo_manzana);
CREATE INDEX IF NOT EXISTS idx_fact_incidents_tipo ON fact_traffic_incidents(tipo_id);
CREATE INDEX IF NOT EXISTS idx_fact_incidents_fecha ON fact_traffic_incidents(fecha);
