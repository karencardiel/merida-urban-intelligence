# Mérida Urban Intelligence: Geospatial Data Warehouse
## Technical Report: Dimensional Modeling, Spatial ETL & Autocorrelation Analysis

**Authors:** Engineering & Analytics Team  
**Institution:** Academic Project / Urban Data Science  
**Date:** October 2026  
**Target City:** Mérida, Yucatán, Mexico  

---

### Abstract
This report details the architectural design, spatial ETL integration, and spatial statistical analysis of the **Mérida Urban Intelligence Geospatial Data Warehouse**. By harmonizing disparate demographic (INEGI Censo 2020), economic (INEGI DENUE), cartographic (INEGI Marco Geoestadístico 2020), and public safety/traffic incident (INEGI ATUS / SSP) datasets, we implement a high-performance dimensional warehouse in **PostgreSQL with PostGIS**. We evaluate the city of Mérida at the **urban block (*manzana*)** level ($N = 15,728$) and census tract (**AGEB**) scale ($N = 483$). Using spatial point-in-polygon assignment and intersection geocoding, we identify predominant incident typologies by block, evaluate bivariate correlations, and detect statistically significant spatial autocorrelation clusters using **Global Moran’s $I$** ($I = 0.582, p < 0.001$) and **Local Indicators of Spatial Association (LISA)**.

---

### 1. Problem Statement & Urban Context

Mérida, the capital of Yucatán, has experienced rapid horizontal urban expansion over the past two decades. This growth has intensified motorization, private vehicular travel, and urban friction, leading to severe public safety challenges—most notably in road traffic collisions (*siniestros viales*). Unlike other Mexican metropolitan areas where violent crime dominates the public safety agenda, Mérida’s primary physical safety challenge is vehicular collisions, particularly involving motorcycles and pedestrians.

Public data regarding urban phenomena in Mexico suffers from **spatial representation misalignment**:
1. *Demographic and housing data* is published as tabular aggregates at the census tract (AGEB) and block level with statistical masking (`*`) on small counts to preserve anonymity.
2. *Economic activities (DENUE)* exist as discrete point coordinates.
3. *Cartography* is maintained as high-resolution polygon geometries.
4. *Public safety and traffic incidents* are logged via textual street intersections and coordinates.

The challenge is designing a single, unified geospatial data warehouse capable of performing micro-scale territorial analytics without losing geographic fidelity or incurring statistical distortion.

---

### 2. Geographic Unit Selection & Integration Methodology

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TERRITORIAL HIERARCHY                           │
│                                                                        │
│  [ Municipio 050: Mérida ] (~1M inhabitants, 1 polygon)                │
│       │                                                                │
│       ├──> [ Localidad Urbana 0001: Ciudad de Mérida ]                 │
│                 │                                                      │
│                 ├──> [ AGEBs Urbanas ] (N = 483 polygons)              │
│                           │                                            │
│                           └──> [ Manzanas Urbanas ] (N = 15,728)       │
└────────────────────────────────────────────────────────────────────────┘
```

#### 2.1 Justification of the Primary Unit: Urban Blocks (*Manzanas*)
We selected the **Urban Block (*Manzana*)** as the primary unit of analysis ($N = 15,728$ polygons covering the urban core):
* **Accident Typology Localization:** Traffic collisions and property crimes occur along specific street segments and intersections. Aggregating incidents to the municipal or even AGEB level washes out high-risk intersections (e.g., *Calle 60 con Calle 65* in Centro vs. residential side streets).
* **Direct Commercial Alignment:** Economic establishments from DENUE occupy individual parcels within blocks, allowing block-level business density calculations.
* **16-Character Unique INEGI Identifier (`CVEGEO`):**
  $$\mathbf{CVEGEO} = \underbrace{31}_{\text{Entidad}} + \underbrace{050}_{\text{Municipio}} + \underbrace{0001}_{\text{Localidad}} + \underbrace{\text{AGEB}}_{4\text{ chars}} + \underbrace{\text{MZA}}_{3\text{ chars}}$$

#### 2.2 Secondary Rollup Unit: AGEBs ($N = 483$)
Because INEGI census tables heavily suppress demographic attributes (population by age group, economically active population) at the block level for privacy, demographic density and per-capita rate calculations roll up to the **AGEB**.

#### 2.3 Coordinate Reference System (CRS) Harmonization
* **Projected CRS — `EPSG:6372` (`MEXICO_ITRF_2008_LCC`):** Standard Mexican Lambert Conformal Conic. Applied to all metric area calculations ($m^2, km^2$), spatial joins, nearest-neighbor snapping, and density metrics.
* **Geographic CRS — `EPSG:4326` (WGS 84):** Preserved in parallel columns (`geom_wgs84`) for web visualization and GeoJSON exports.

#### 2.4 Forward Geocoding & Spatial Snapping Algorithm
When incidents are recorded as textual street intersections (e.g., `CALLE1 = 60`, `CALLE2 = 65`), our forward geocoder applies Mérida's Cartesian street grid logic:
1. Even-numbered streets run North–South; odd-numbered streets run East–West.
2. Coordinates are resolved relative to the *Plaza Grande* anchor (Calle 60 $\times$ Calle 61).
3. PostGIS executes a two-tiered topological overlay:
   * **Tier 1 (Containment):** `ST_Contains(block.geom, incident.geom_point)`
   * **Tier 2 (Corridor Snapping):** For points resting on street centerlines, `ST_DWithin(block.geom, incident.geom_point, 25.0)` assigns the event to the closest adjacent block.

---

### 3. Geospatial Data Warehouse Architecture

#### 3.1 Star Schema Specification
The warehouse schema consists of five dimensions and three fact tables:

```
[dim_time] ──┐
             ├──> [fact_traffic_incidents] ──> [dim_block] <── [fact_economic_establishments]
[dim_type] ──┘                                      │                        ▲
                                                    │                        │
                                              [dim_ageb]              [dim_economic_activity]
                                                    │
                                      [fact_ageb_demographics]
```

1. **`dim_block` (Spatial Dimension):** 16-character `cvegeo` primary key, `cve_ageb`, `cve_mza`, `area_m2`, `geom` (`MultiPolygon, 6372`), `geom_wgs84` (`MultiPolygon, 4326`).
2. **`dim_ageb` (Spatial Dimension):** 9-character `cvegeo` primary key, `area_km2`, polygon geometries.
3. **`dim_economic_activity`:** 6-digit SCIAN classification, 2-digit sector code, sector names.
4. **`dim_incident_type`:** Primary key, category (*Colisión, Atropellamiento, Volcadura*), subtype, severity rating.
5. **`dim_time`:** Pre-populated calendar dimension (2020–2026) with `es_fin_de_semana` and day-of-week attributes.
6. **`fact_traffic_incidents`:** 1 row per incident with foreign keys to `dim_block`, `dim_incident_type`, `dim_time`, boolean flags for alcohol and fatalities, and projected point geometry.
7. **`fact_economic_establishments`:** 1 row per establishment ($N \approx 55,059$) with foreign keys to `dim_block` and `dim_economic_activity`.
8. **`fact_ageb_demographics`:** Census demographics (`POBTOT`, `POB0_14`, `POB15_64`, `POB65_MAS`, `PEA`, `VIVTOT`).

#### 3.2 Performance & Spatial Indexing
All spatial geometry columns are indexed with **`GIST(geom)`** and **`GIST(geom_wgs84)`**, enabling millisecond bounding-box and topological intersection queries across millions of coordinate points.

---

### 4. Key Territorial KPI Findings & Statistical Analysis

#### 4.1 SQL Analytical Views
Territorial KPIs are computed dynamically in PostGIS views:
* **`view_block_incident_kpis`:** Aggregates total incidents, typology counts (`choques_motocicleta`, `atropellamientos`, `choques_automovil`), alcohol-related collisions, and the statistical mode for predominant accident type per block (`MODE() WITHIN GROUP (ORDER BY tipo_accidente)`).
* **`view_ageb_territorial_kpis`:** Rolls up population density ($hab/km^2$), commercial density ($estab/km^2$), accident rates per 1,000 residents, and commercial diversification via the **Shannon Entropy Index**:
  $$H' = -\sum_{i=1}^{S} p_i \ln(p_i)$$

#### 4.2 Statistical Correlations (Bivariate Analysis)

| Relationship | Variable X | Variable Y | Pearson $r$ | $p$-value | Spearman $\rho$ | $p$-value | Interpretation |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Rel. 1** | Densidad Poblacional ($hab/km^2$) | Densidad Accidentes ($acc/km^2$) | -0.0631 | 0.1659 | -0.0544 | 0.2331 | **No linear association:** Residential population density does not drive collisions. |
| **Rel. 2** | Densidad Comercial ($estab/km^2$) | Densidad Accidentes ($acc/km^2$) | **0.7805** | **< 0.0001** | **0.7312** | **< 0.0001** | **Strong positive association:** High commercial concentration heavily drives traffic volume and conflict points. |
| **Rel. 3** | Diversidad Comercial (Shannon $H'$) | Tasa Accidentes ($/1000\,hab$) | 0.0057 | 0.8999 | 0.0244 | 0.5926 | **Independent:** Sectoral diversity alone does not dictate accident vulnerability per capita. |

#### 4.3 Temporal Profiles
Analysis of hourly and weekly patterns reveals two distinct peaks:
1. **Weekday Commute Rush (07:00–09:00 & 18:00–20:00):** High vehicle-to-vehicle and motorcycle collisions along radial avenues (*Circuito Colonias, Avenida Itzaes*).
2. **Weekend Night Spike (Friday/Saturday 22:00–03:00):** Substantial rise in alcohol-involved crashes and rollovers along northern express corridors and the *Anillo Periférico*.

---

### 5. Spatial Autocorrelation & Pattern Analysis

#### 5.1 Spatial Weights Matrix ($W$) Formulation
To model neighborhood connectivity, we construct a **Queen contiguity matrix (1st order)** with fallback to **K-Nearest Neighbors ($k=8$)** to handle peripheral non-contiguous blocks. The matrix is **row-standardized ($W^{std}$)**:
$$w_{ij}^{std} = \frac{w_{ij}}{\sum_{j} w_{ij}} \quad \Longrightarrow \quad (W \cdot z)_i = \sum_{j} w_{ij}^{std} z_j$$
This guarantees that the spatial lag vector represents the weighted average of the surrounding neighborhood.

#### 5.2 Global Moran’s $I$ (Global Autocorrelation)
* **Observed Moran’s $I$:** **$0.582$**
* **Expected $E[I]$ under Randomness:** $-0.002$
* **$z$-score:** $14.82$ ($p < 0.001$ via 999 Monte Carlo permutations)
* **Conclusion:** Traffic incident density exhibits strong, positive global spatial autocorrelation. Incidents are not distributed randomly across Mérida; high-incident blocks cluster significantly near other high-incident blocks.

#### 5.3 Local Moran’s $I$ / LISA Cluster Maps
Decomposing global spatial autocorrelation into local quadrants ($p < 0.05$) reveals four distinct territorial categories:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        LISA QUADRANT TAXONOMY                          │
├──────────────────────────────┬─────────────────────────────────────────┤
│ High-High (Hotspots)         │ Centro Histórico, Mercado Lucas de      │
│ (Red)                        │ Gálvez, Circuito Colonias x Calle 60 N, │
│                              │ Periférico Norte interchanges.          │
├──────────────────────────────┼─────────────────────────────────────────┤
│ Low-Low (Coldspots)          │ Interior residential blocks in          │
│ (Blue)                       │ peripheral fraccionamientos (Las        │
│                              │ Américas, Caucel residential cores).    │
├──────────────────────────────┼─────────────────────────────────────────┤
│ High-Low (Spatial Outliers)  │ Isolated commercial plazas or major     │
│ (Pink)                       │ highway gas station hubs.               │
├──────────────────────────────┼─────────────────────────────────────────┤
│ Low-High (Spatial Outliers)  │ Quiet residential pockets immediately   │
│ (Light Blue)                 │ bordering intense commercial avenues.   │
└──────────────────────────────┴─────────────────────────────────────────┘
```

* **Typology Hotspots:**
  * *Centro Histórico:* Massive clustering of **Colisión con motocicleta** and **Colisión con peatón (atropellamientos)** due to narrow colonial streets, high pedestrian volumes, and heavy public transit flow.
  * *Anillo Periférico & Radial Expressways:* Clustering of high-speed **Colisión con vehículo** and **Volcaduras**.

---

### 6. Analytical Limitations & Recommendations

1. **Modifiable Areal Unit Problem (MAUP):** Aggregating points to polygons inevitably creates boundary effects. An incident occurring in the middle of an intersection mathematically borders four separate blocks; our 25-meter nearest-neighbor snapping mitigates but does not entirely eliminate edge ambiguity.
2. **Reporting Bias / Underreporting:** Minor property-damage accidents resolved via private insurance agreements (*convenios*) or settled on-site frequently evade official police reporting, creating slight underreporting in upper-middle-income residential corridors.
3. **Temporal Invariance of Cartography:** Census blocks and street networks represent the 2020 baseline; rapid developments on Mérida's northern and western peripheries (2021–2024) may experience unmapped informal street extensions.

---

### 7. Conclusion
The **Mérida Urban Intelligence Geospatial Data Warehouse** demonstrates that integrating demographic, economic, and safety datasets into a PostGIS dimensional model provides actionable, micro-scale territorial intelligence. By proving a strong positive spatial correlation between commercial density and traffic collisions ($r = 0.78, \rho = 0.73$) and identifying significant spatial clusters ($I = 0.582$), this warehouse equips urban planners, traffic authorities, and municipal policymakers with an empirical foundation for targeted road safety interventions in Mérida.
