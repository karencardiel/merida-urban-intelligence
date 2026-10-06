# Data Dictionary: Mérida Urban Intelligence Data Warehouse

## Overview
This document specifies the metadata, attributes, data types, sources, and definitions for all dimensions, facts, and analytical views stored in the **Mérida Urban Intelligence Geospatial Data Warehouse**.

---

## 1. Geographic Dimensions

### `dim_block` (Manzanas Urbanas)
* **Source:** INEGI Marco Geoestadístico 2020 (`31m.shp`)
* **Primary Geographic Unit:** Urban Block (*Manzana*)
* **Total Records (City of Mérida):** 15,728 polygons

| Column Name | Data Type | Constraint | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `cvegeo` | VARCHAR(16) | PRIMARY KEY | Unique 16-character INEGI block code (Entidad + Municipio + Localidad + AGEB + Manzana) | `3105000010126002` |
| `cve_ent` | VARCHAR(2) | NOT NULL | State code (`31` for Yucatán) | `31` |
| `cve_mun` | VARCHAR(3) | NOT NULL | Municipality code (`050` for Mérida) | `050` |
| `cve_loc` | VARCHAR(4) | NOT NULL | Locality code (`0001` for Mérida city) | `0001` |
| `cve_ageb` | VARCHAR(4) | NOT NULL | 4-character statistical AGEB code | `0126` |
| `cve_mza` | VARCHAR(3) | NOT NULL | 3-digit block number within the AGEB | `002` |
| `ambito` | VARCHAR(10) | NOT NULL | Geographic scope (`Urbana` / `Rural`) | `Urbana` |
| `tipomza` | VARCHAR(20) | NULL | Type of block (e.g. `Típica`, `Glorieta`, `Parque`) | `Típica` |
| `area_m2` | NUMERIC(14,2)| NOT NULL | Calculated polygon area in square meters (EPSG:6372) | `12450.75` |
| `geom` | GEOMETRY(Polygon, 6372) | NOT NULL | Projected polygon geometry in `MEXICO_ITRF_2008_LCC` | Polygon |
| `geom_wgs84` | GEOMETRY(Polygon, 4326) | NOT NULL | Unprojected polygon geometry in WGS 84 (Lon/Lat) | Polygon |

---

### `dim_ageb` (Áreas Geoestadísticas Básicas)
* **Source:** INEGI Marco Geoestadístico 2020 (`31a.shp`)
* **Total Records (City of Mérida):** 483 urban polygons

| Column Name | Data Type | Constraint | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `cvegeo` | VARCHAR(9) | PRIMARY KEY | Unique 9-character AGEB identifier (`310500001` + `cve_ageb`) | `3105000010126` |
| `cve_ageb` | VARCHAR(4) | NOT NULL | 4-character AGEB identifier | `0126` |
| `cve_mun` | VARCHAR(3) | NOT NULL | Municipality code (`050`) | `050` |
| `cve_loc` | VARCHAR(4) | NOT NULL | Locality code (`0001`) | `0001` |
| `area_km2` | NUMERIC(10,4)| NOT NULL | Total surface area in square kilometers | `0.8521` |
| `geom` | GEOMETRY(Polygon, 6372) | NOT NULL | Projected polygon boundary in EPSG:6372 | Polygon |
| `geom_wgs84` | GEOMETRY(Polygon, 4326) | NOT NULL | WGS 84 boundary in EPSG:4326 | Polygon |

---

## 2. Demographic Facts

### `fact_ageb_demographics`
* **Source:** INEGI Censo de Población y Vivienda 2020 (`ageb_mza_urbana_31_cpv2020`)
* **Granularity:** 1 record per urban AGEB ($N = 483$)

| Column Name | Data Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `cvegeo_ageb` | VARCHAR(9) | PK / FK -> `dim_ageb` | Foreign key referencing `dim_ageb.cvegeo` |
| `pobtot` | INTEGER | NOT NULL | Total resident population |
| `pobfem` | INTEGER | NOT NULL | Total female population |
| `pobmas` | INTEGER | NOT NULL | Total male population |
| `pob0_14` | INTEGER | DEFAULT 0 | Population aged 0 to 14 years |
| `pob15_64` | INTEGER | DEFAULT 0 | Working age population (15 to 64 years) |
| `pob65_mas` | INTEGER | DEFAULT 0 | Senior population (65 years and older) |
| `pea` | INTEGER | DEFAULT 0 | Economically Active Population (*Población Económicamente Activa*) |
| `pe_ocupada` | INTEGER | DEFAULT 0 | Employed population |
| `vivtot` | INTEGER | DEFAULT 0 | Total dwellings / housing units |
| `vph_inter` | INTEGER | DEFAULT 0 | Occupied private dwellings with internet access |

---

## 3. Economic Dimensions & Facts

### `dim_economic_activity` (SCIAN Classification)
* **Source:** INEGI Sistema de Clasificación Industrial de América del Norte (SCIAN)

| Column Name | Data Type | Constraint | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `codigo_act` | VARCHAR(6) | PRIMARY KEY | 6-digit SCIAN classification code | `461110` |
| `sector_code` | VARCHAR(2) | NOT NULL | 2-digit SCIAN Sector (e.g. `46` = Comercio al por menor) | `46` |
| `sector_name` | VARCHAR(120)| NOT NULL | Sector name | `Comercio al por menor` |
| `subsector_name` | VARCHAR(150)| NOT NULL | Subsector description | `Comercio al por menor de abarrotes y alimentos` |
| `nombre_act` | VARCHAR(250)| NOT NULL | Complete activity description | `Comercio al por menor en tiendas de abarrotes` |

---

### `fact_economic_establishments` (DENUE)
* **Source:** INEGI Directorio Estadístico Nacional de Unidades Económicas (DENUE 2020-2024)
* **Granularity:** 1 record per physical economic establishment ($N \approx 55,059$ in Mérida)

| Column Name | Data Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `id_estab` | BIGINT | PRIMARY KEY | Official INEGI establishment identifier |
| `clee` | VARCHAR(32) | UNIQUE | Key of the Economic Establishment Registry (*CLEE*) |
| `nom_estab` | VARCHAR(200)| NOT NULL | Commercial or establishment trade name |
| `codigo_act` | VARCHAR(6) | FK -> `dim_economic_activity` | 6-digit SCIAN activity code |
| `per_ocu_estrato`| VARCHAR(50) | NOT NULL | Employee headcount bracket (e.g. `0 a 5 personas`, `6 a 10 personas`) |
| `cvegeo_manzana`| VARCHAR(16) | FK -> `dim_block` | Block containing the establishment (Spatial join via coordinates) |
| `cve_ageb` | VARCHAR(4) | NOT NULL | AGEB identifier |
| `latitud` | NUMERIC(10,7)| NOT NULL | Decimal latitude coordinate (WGS 84) |
| `longitud` | NUMERIC(10,7)| NOT NULL | Decimal longitude coordinate (WGS 84) |
| `geom_point` | GEOMETRY(Point, 6372) | NOT NULL | Projected point location in EPSG:6372 |

---

## 4. Public Safety / Traffic Incidents Layer

### `dim_incident_type`
* **Source:** INEGI ATUS / SSP Yucatán incident taxonomy

| Column Name | Data Type | Constraint | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `tipo_id` | SERIAL | PRIMARY KEY | Unique accident / incident type identifier | `1` |
| `categoria` | VARCHAR(50) | NOT NULL | Broad category (`Colisión`, `Atropellamiento`, `Volcadura`, `Especial`) | `Colisión` |
| `tipo_accidente`| VARCHAR(80) | UNIQUE | Specific accident subtype | `Colisión con motocicleta` |
| `nivel_gravedad`| VARCHAR(20) | NOT NULL | Severity rating (`Leve`, `Moderado`, `Grave`, `Crítico`) | `Grave` |

---

### `fact_traffic_incidents`
* **Source:** Geocoded road traffic incidents (*hechos de tránsito / ATUS / SSP*)
* **Granularity:** 1 record per geocoded incident

| Column Name | Data Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `incident_id` | BIGSERIAL | PRIMARY KEY | Unique incident identifier |
| `cvegeo_manzana`| VARCHAR(16) | FK -> `dim_block` | Block polygon where incident occurred (Point-in-polygon match) |
| `cve_ageb` | VARCHAR(4) | NOT NULL | AGEB code containing the block |
| `tipo_id` | INTEGER | FK -> `dim_incident_type` | Accident typology key |
| `fecha` | DATE | NOT NULL | Incident date (`YYYY-MM-DD`) |
| `hora` | TIME | NOT NULL | Incident time (`HH:MI:SS`) |
| `dia_semana` | VARCHAR(15) | NOT NULL | Day of the week (`Lunes`, `Martes`, etc.) |
| `calle_1` | VARCHAR(100)| NULL | Primary street / avenue |
| `calle_2` | VARCHAR(100)| NULL | Intersecting street / cross street |
| `colonia` | VARCHAR(100)| NULL | Neighborhood / Colonia |
| `con_heridos` | BOOLEAN | DEFAULT FALSE | Flag indicating injured victims |
| `con_fallecidos`| BOOLEAN | DEFAULT FALSE | Flag indicating fatal victims |
| `aliento_alcohol`| BOOLEAN | DEFAULT FALSE | Flag indicating driver alcohol involvement |
| `latitud` | NUMERIC(10,7)| NOT NULL | Decimal latitude coordinate (EPSG:4326) |
| `longitud` | NUMERIC(10,7)| NOT NULL | Decimal longitude coordinate (EPSG:4326) |
| `geom_point` | GEOMETRY(Point, 6372) | NOT NULL | Projected point location in EPSG:6372 |

---

## 5. Analytical Views & Territorial KPI Formulas

### `view_block_incident_kpis`
Consolidates incident metrics per block ($N = 15,728$):
* `total_accidentes`: $\sum \text{incidents}$
* `choques_motocicleta`: $\sum \text{incidents where type is Colisión con motocicleta}$
* `atropellamientos`: $\sum \text{incidents where type is Colisión con peatón}$
* `accidentes_graves`: $\sum \text{incidents with fatal or injured victims}$
* `tipo_accidente_predominante`: Statistical mode ($\text{MODE}$) of accident types per block.
* `incidente_densidad_km2`: $\frac{\text{total\_accidentes}}{\text{area\_m2} / 1\,000\,000}$

### `view_ageb_territorial_kpis`
Rollup view integrating demographics, commerce, and safety per AGEB ($N = 483$):
1. **Densidad Poblacional ($hab/km^2$):**
   $$\text{densidad\_pob} = \frac{\text{pobtot}}{\text{area\_km2}}$$
2. **Densidad de Unidades Económicas ($estab/km^2$):**
   $$\text{densidad\_econ} = \frac{\text{total\_establecimientos}}{\text{area\_km2}}$$
3. **Tasa de Siniestralidad Vial ($accidentes / 1,000\,hab$):**
   $$\text{tasa\_accidentes\_1k} = \frac{\text{total\_accidentes}}{\text{pobtot}} \times 1,000$$
4. **Diversidad Comercial (Shannon Entropy Index $H'$):**
   $$H' = -\sum_{i=1}^{S} p_i \ln(p_i)$$
   where $p_i$ is the proportion of establishments in SCIAN sector $i$.
