# Mérida Urban Intelligence: Geospatial Data Warehouse

A reproducible geospatial Data Warehouse built with **PostgreSQL** and **PostGIS** for the city of **Mérida, Yucatán, Mexico**. Integrates demographic, economic, cartographic, and public safety/traffic incident datasets to compute territorial KPIs and analyze spatial autocorrelation patterns at the **urban block (*manzana*)** and **census tract (*AGEB*)** scales.

---

## 1. Project Overview & Geographic Unit Justification

### The Territorial Challenge
Urban datasets for Mexican municipalities originate from disparate public institutions and geographic representations:
* **Demographics (INEGI Censo 2020):** Tabular summaries at the AGEB and block level with statistical masking (`*`) on small cells.
* **Economics (INEGI DENUE):** Exact point coordinates of commercial establishments.
* **Cartography (INEGI Marco Geoestadístico 2020):** Polygon shapefiles (`31a.shp` for AGEBs, `31m.shp` for blocks, and `31e.shp` for road centerlines).
* **Public Safety (INEGI ATUS / SSP Yucatán):** Georeferenced street intersection incident logs with accident typologies, alcohol involvement, and temporal attributes.

### Defensible Unit of Analysis: Urban Blocks (*Manzanas*) with AGEB Rollup
* **Primary Analysis Unit:** **Urban Blocks (*Manzanas*)**, consisting of **15,728 polygons** covering the city of Mérida (`CVE_MUN = '050'`, `CVE_LOC = '0001'`).
  * *Rationale:* Enables micro-level spatial identification of high-risk accident intersections, specific accident types (motorcycle collisions, pedestrian hits, vehicle crashes), and immediate commercial density per block.
  * *Unique Identifier:* 16-character official INEGI code (`CVEGEO`):
    $$\underbrace{31}_{\text{Entidad}} \underbrace{050}_{\text{Municipio}} \underbrace{0001}_{\text{Localidad}} \underbrace{0126}_{\text{AGEB}} \underbrace{002}_{\text{Manzana}} \longrightarrow \mathbf{3105000010126002}$$
* **Secondary Analytical Unit:** **AGEB (*Área Geoestadística Básica*)**, consisting of **483 urban polygons**.
  * *Rationale:* Overcomes census privacy masking for demographic ratios (PEA, dependency ratios, internet access) and provides the sample size ($N = 483$) required for inferential spatial autocorrelation (**Global Moran's I**, **LISA**).

---

## 2. Dimensional Model Architecture (Star Schema)

The data warehouse implements a spatial star schema in PostgreSQL with PostGIS:

```
                    ┌────────────────────────┐
                    │        dim_time        │
                    ├────────────────────────┤
                    │ PK time_id             │
                    │    fecha (Date)        │
                    │    anio / mes / dia    │
                    │    dia_semana          │
                    │    es_fin_de_semana    │
                    └───────────┬────────────┘
                                │
┌────────────────────────┐      │      ┌───────────────────────────────┐
│ dim_economic_activity  │      │      │       dim_incident_type       │
├────────────────────────┤      │      ├───────────────────────────────┤
│ PK codigo_act (SCIAN)  │      │      │ PK tipo_id                    │
│    sector_code         │      │      │    categoria                  │
│    sector_name         │      │      │    tipo_accidente             │
│    subsector_name      │      │      │    nivel_gravedad             │
└───────────┬────────────┘      │      └───────────────┬───────────────┘
            │                   │                      │
            │                   │                      │
┌───────────▼────────────────┐  │  ┌───────────────────▼───────────────┐
│fact_economic_establishments│  │  │       fact_traffic_incidents      │
├────────────────────────────┤  │  ├───────────────────────────────────┤
│ PK id_estab                │  │  │ PK incident_id                    │
│ FK cvegeo_manzana          │  └──┼──> FK time_id                     │
│ FK codigo_act              │     │ FK cvegeo_manzana                 │
│    per_ocu_estrato         │     │ FK tipo_id                        │
│    geom_point (EPSG:6372)  │     │    con_heridos / con_fallecidos   │
│    geom_point_wgs84 (4326) │     │    aliento_alcohol                │
└───────────┬────────────────┘     │    geom_point (EPSG:6372)         │
            │                      │    geom_point_wgs84 (4326)        │
            │         ┌────────────▼──────────┐│
            └────────>│       dim_block       │<┘
                      ├───────────────────────┤
                      │ PK cvegeo (16 chars)  │
                      │ FK cve_ageb ──────────┼────────┐
                      │    cve_mza            │        │
                      │    area_m2            │        │
                      │    geom (EPSG:6372)   │        │
                      │    geom_wgs84 (4326)  │        │
                      └───────────────────────┘        │
                                                       │
                      ┌───────────────────────┐        │
                      │        dim_ageb       │<───────┘
                      ├───────────────────────┤
                      │ PK cvegeo (9 chars)   │
                      │    cve_ageb           │
                      │    area_km2           │
                      │    geom (EPSG:6372)   │
                      └───────────▲───────────┘
                                  │
                      ┌───────────┴───────────┐
                      │fact_ageb_demographics │
                      ├───────────────────────┤
                      │ PK/FK cvegeo_ageb     │
                      │    pobtot             │
                      │    pob0_14 / pob15_64 │
                      │    pob65_mas / pea    │
                      │    vivtot / vph_inter │
                      └───────────────────────┘
```

---

## 3. Coordinate Reference Systems (CRS) Harmonization

* **Projected CRS — `EPSG:6372` (`MEXICO_ITRF_2008_LCC`):**
  * Official Mexican projection (Lambert Conformal Conic).
  * Used for all metric calculations: polygon area ($m^2$, $km^2$), spatial distance, 25-meter road snapping buffers, and density denominators.
* **Geographic CRS — `EPSG:4326` (WGS 84):**
  * Stored concurrently as `geom_wgs84` / `geom_point_wgs84` for web visualization (Leaflet, Mapbox, Folium, QGIS) and GeoJSON outputs.

---

## 4. Analytical Views & Territorial KPI Formulas

All KPIs are computed directly in PostgreSQL/PostGIS views without querying raw files:

### 1. `view_block_incident_kpis` (Block Level)
* **Incident Volume & Typologies:**
  * `total_accidentes`: Total events per block.
  * Breakdown: `choques_motocicleta`, `atropellamientos`, `choques_automovil`, `volcaduras`.
  * `tipo_accidente_predominante`: Statistical mode ($\text{MODE}()$) of accident types per block.
* **Incident Density:**
  $$\text{incidentes\_por\_km2} = \frac{\text{total\_accidentes}}{\text{area\_m2} / 1\,000\,000}$$

### 2. `view_ageb_territorial_kpis` (AGEB Level Rollup)
* **Demographic Density:**
  $$\text{densidad\_pob} = \frac{\text{pobtot}}{\text{area\_km2}}$$
* **Commercial Density:**
  $$\text{densidad\_econ} = \frac{\text{total\_establecimientos}}{\text{area\_km2}}$$
* **Traffic Incident Rate:**
  $$\text{tasa\_accidentes\_1k} = \frac{\text{total\_accidentes}}{\text{pobtot}} \times 1,000$$
* **Commercial Diversity (Shannon Entropy Index):**
  $$H' = -\sum_{i=1}^{S} p_i \ln(p_i)$$
  where $p_i$ is the share of establishments in SCIAN 2-digit sector $i$.

### 3. `view_high_risk_accident_blocks`
Filters the top 100 collision hotspots in Mérida with their predominant accident typology and commercial density.

---

## 5. Spatial Analytics Methodology

1. **Statistical Correlation Analysis:**
   * Computes bivariate **Pearson ($r$)** (linear) and **Spearman ($\rho$)** (rank-order) correlation coefficients across:
     * *Relationship 1:* Population Density vs. Incident Density.
     * *Relationship 2:* Commercial Establishment Density vs. Incident Density.
     * *Relationship 3:* Commercial Diversity (Shannon) vs. Incident Rate per 1,000 residents.
2. **Spatial Weights Matrix ($W$):**
   * **Queen Contiguity (1st order):** Polygons sharing edges or vertices are considered neighbors.
   * **Row-standardization ($W^{std}$):** Ensures the spatial lag vector $W \cdot y$ represents the weighted neighborhood average.
3. **Global Moran's $I$:**
   * Tests for global spatial autocorrelation against the null hypothesis of spatial randomness ($p$-value via 999 Monte Carlo permutations).
4. **Local Moran's $I$ / LISA Cluster Maps:**
   * Identifies statistically significant local spatial clusters ($p < 0.05$):
     * **High-High (Hotspots):** Blocks/AGEBs with high incident rates surrounded by high rates.
     * **Low-Low (Coldspots):** Blocks/AGEBs with low rates surrounded by low rates.
     * **High-Low / Low-High (Spatial Outliers):** Anomalies and transitional urban zones.
5. **Bivariate Moran's $I$:**
   * Evaluates spatial cross-correlation between commercial density ($X$) and neighboring traffic incidents ($W \cdot Y$).

---

## 6. Setup & Execution Instructions

### Prerequisites
* Docker & Docker Compose
* Python 3.10+

### Step 1: Clone and Configure Environment
```bash
git clone https://github.com/karencardiel/merida-urban-intelligence.git
cd merida-urban-intelligence

# Copy environment variables
cp .env.example .env

# Install Python dependencies
pip install -r requirements.txt
```

### Step 2: Launch PostGIS Container
```bash
cd docker
docker compose up -d
cd ..
```
Verify PostgreSQL is running on `localhost:5432` with PostGIS enabled.

### Step 3: Initialize Database Schema
```bash
cd sql
docker exec -i merida_postgis_dw psql -U postgres -d merida_dw < sql/01_schema.sql
```

### Step 4: Run Spatial ETL Pipeline
```bash
# 1. Extract cartography (Manzanas & AGEBs)
python -m src.etl_cartography

# 2. Extract and clean Censo 2020 demographics
python -m src.etl_census

# 3. Ingest DENUE and assign establishments to blocks
python -m src.etl_denue

# 4. Ingest/generate geocoded safety incidents and snap to blocks
python -m src.etl_safety_incidents
```

### Step 5: Execute Load & Spatial Snapping Procedures
```bash
docker exec -i merida_postgis_dw psql -U postgres -d merida_dw < sql/02_load.sql
docker exec -i merida_postgis_dw psql -U postgres -d merida_dw < sql/03_views.sql
```

### Step 6: Execute Spatial Analytics & Export Visualizations
```bash
python -m src.spatial_analytics
```
Outputs (correlation heatmaps, Moran scatterplots, and LISA cluster maps) will be generated in `outputs/figures/` and `outputs/maps/`.

---

## 7. Directory Layout

```
merida-urban-intelligence/
├── data/
│   ├── raw/                  # Source archives (.zip, .csv - gitignored)
│   └── processed/            # Cleaned GeoJSONs and CSVs
├── docker/
│   └── docker-compose.yml    # PostgreSQL 16 + PostGIS 3.4 container
├── docs/
│   └── data_dictionary.md    # Complete metadata & variable specifications
├── notebooks/
│   └── 01_exploracion_censo.ipynb  # Exploratory demographic & spatial analysis
├── outputs/
│   ├── figures/              # Correlation matrices & Moran scatterplots
│   └── maps/                 # High-resolution LISA & hotspot maps
├── sql/
│   ├── 01_schema.sql         # DDL: Extensions, tables, foreign keys, GIST indexes
│   ├── 02_load.sql           # Post-load snapping, staging, and audit queries
│   └── 03_views.sql          # Analytical views for block & AGEB KPIs
├── src/
│   ├── __init__.py
│   ├── config.py             # Paths, database URI, and SRID constants
│   ├── geocoding.py          # Intersection geocoder & spatial snapping
│   ├── etl_cartography.py    # Marco Geoestadístico 2020 extraction
│   ├── etl_census.py         # Censo 2020 extraction & cleaning
│   ├── etl_denue.py          # DENUE extraction & block assignment
│   ├── etl_safety_incidents.py # Incident geocoding & block-level assignment
│   └── spatial_analytics.py  # Moran's I, LISA, and correlation pipeline
├── .env.example              # Database credentials template
├── .gitignore                # Ignored cache, data/raw, and OS files
├── README.md                 # Full project documentation
└── requirements.txt          # Python dependencies
```
