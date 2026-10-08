-- ============================================================
-- Mérida Urban Intelligence
-- Data Warehouse - Schema
-- ============================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================
-- DIMENSION: AGEB
-- Geographic unit: urban AGEBs of Mérida locality
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_ageb (
    "CVE_AGEB" VARCHAR(10) PRIMARY KEY,
    "ENTIDAD" INTEGER,
    "MUN" INTEGER,
    "LOC" INTEGER,
    area_km2 DOUBLE PRECISION,
    geometry GEOMETRY(MULTIPOLYGON, 4326)
);

CREATE INDEX IF NOT EXISTS idx_dim_ageb_geometry
ON dim_ageb
USING GIST (geometry);


-- ============================================================
-- FACT: DEMOGRAPHY
-- Grain: one row per AGEB
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_demografia (
    "CVE_AGEB" VARCHAR(10) PRIMARY KEY,

    "POBTOT" DOUBLE PRECISION,
    "POB0_14" DOUBLE PRECISION,
    "POB15_64" DOUBLE PRECISION,
    "POB65_MAS" DOUBLE PRECISION,

    "PEA" DOUBLE PRECISION,
    "PE_INAC" DOUBLE PRECISION,
    "POCUPADA" DOUBLE PRECISION,
    "PDESOCUP" DOUBLE PRECISION,

    "VIVTOT" DOUBLE PRECISION,
    "TVIVHAB" DOUBLE PRECISION,

    densidad_pob_km2 DOUBLE PRECISION,
    tasa_pea DOUBLE PRECISION,

    porcentaje_0_14 DOUBLE PRECISION,
    porcentaje_15_64 DOUBLE PRECISION,
    porcentaje_65_mas DOUBLE PRECISION,

    FOREIGN KEY ("CVE_AGEB")
        REFERENCES dim_ageb("CVE_AGEB")
);


-- ============================================================
-- FACT: ECONOMY
-- Grain: one row per AGEB
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_economia (
    "CVE_AGEB" VARCHAR(10) PRIMARY KEY,

    total_establecimientos DOUBLE PRECISION,
    comercio DOUBLE PRECISION,
    retail DOUBLE PRECISION,
    servicios DOUBLE PRECISION,
    otros DOUBLE PRECISION,

    densidad_establecimientos_km2 DOUBLE PRECISION,
    densidad_comercio_km2 DOUBLE PRECISION,
    densidad_retail_km2 DOUBLE PRECISION,
    densidad_servicios_km2 DOUBLE PRECISION,

    establecimientos_por_1000_hab DOUBLE PRECISION,

    actividad_dominante_codigo VARCHAR(10),
    actividad_dominante VARCHAR(255),
    cantidad_actividad_dominante DOUBLE PRECISION,

    FOREIGN KEY ("CVE_AGEB")
        REFERENCES dim_ageb("CVE_AGEB")
);


-- ============================================================
-- FACT: TRAFFIC ACCIDENTS
-- Grain: one row per AGEB
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_accidentes (
    "CVE_AGEB" VARCHAR(10) PRIMARY KEY,

    total_accidentes DOUBLE PRECISION,
    total_muertos DOUBLE PRECISION,
    total_heridos DOUBLE PRECISION,

    accidentes_tipo_1 DOUBLE PRECISION,
    accidentes_tipo_2 DOUBLE PRECISION,
    accidentes_tipo_4 DOUBLE PRECISION,
    accidentes_tipo_5 DOUBLE PRECISION,
    accidentes_tipo_6 DOUBLE PRECISION,
    accidentes_tipo_7 DOUBLE PRECISION,
    accidentes_tipo_8 DOUBLE PRECISION,
    accidentes_tipo_10 DOUBLE PRECISION,
    accidentes_tipo_11 DOUBLE PRECISION,

    densidad_accidentes_km2 DOUBLE PRECISION,
    accidentes_por_1000_hab DOUBLE PRECISION,
    accidentes_por_establecimiento DOUBLE PRECISION,

    FOREIGN KEY ("CVE_AGEB")
        REFERENCES dim_ageb("CVE_AGEB")
);

-- ============================================================
-- 5. TEMPORAL TRAFFIC ACCIDENT FACT
-- Grain: one row per AGEB × month × time period
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_accidentes_tiempo (
    "CVE_AGEB" VARCHAR(10),
    ANIO INTEGER,
    MES INTEGER,
    periodo_dia VARCHAR(20),

    total_accidentes DOUBLE PRECISION,
    total_muertos DOUBLE PRECISION,
    total_heridos DOUBLE PRECISION,

    PRIMARY KEY ("CVE_AGEB", ANIO, MES, periodo_dia),

    FOREIGN KEY ("CVE_AGEB")
        REFERENCES dim_ageb("CVE_AGEB")
);
