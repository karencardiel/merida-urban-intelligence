# Data Dictionary

## Geographic Dimension

### `dim_ageb`

**Grain:** One row per urban AGEB in the locality of Mérida.

| Column     | Type                         | Description                         |
| ---------- | ---------------------------- | ----------------------------------- |
| `CVE_AGEB` | VARCHAR(10)                  | Official AGEB geographic identifier |
| `ENTIDAD`  | INTEGER                      | Federal entity code                 |
| `MUN`      | INTEGER                      | Municipality code                   |
| `LOC`      | INTEGER                      | Locality code                       |
| `area_km2` | DOUBLE PRECISION             | AGEB area in square kilometers      |
| `geometry` | GEOMETRY(MULTIPOLYGON, 4326) | AGEB polygon geometry in WGS84      |

---

## Demographic Fact

### `fact_demografia`

**Grain:** One row per AGEB.

| Column              | Type             | Description                               |
| ------------------- | ---------------- | ----------------------------------------- |
| `CVE_AGEB`          | VARCHAR(10)      | AGEB identifier and foreign key           |
| `POBTOT`            | DOUBLE PRECISION | Total population                          |
| `POB0_14`           | DOUBLE PRECISION | Population aged 0–14                      |
| `POB15_64`          | DOUBLE PRECISION | Population aged 15–64                     |
| `POB65_MAS`         | DOUBLE PRECISION | Population aged 65 and over               |
| `PEA`               | DOUBLE PRECISION | Economically active population            |
| `PE_INAC`           | DOUBLE PRECISION | Economically inactive population          |
| `POCUPADA`          | DOUBLE PRECISION | Employed population                       |
| `PDESOCUP`          | DOUBLE PRECISION | Unemployed population                     |
| `VIVTOT`            | DOUBLE PRECISION | Total dwellings                           |
| `TVIVHAB`           | DOUBLE PRECISION | Total inhabited dwellings                 |
| `densidad_pob_km2`  | DOUBLE PRECISION | Population density per km²                |
| `tasa_pea`          | DOUBLE PRECISION | Economically active population rate       |
| `porcentaje_0_14`   | DOUBLE PRECISION | Percentage of population aged 0–14        |
| `porcentaje_15_64`  | DOUBLE PRECISION | Percentage of population aged 15–64       |
| `porcentaje_65_mas` | DOUBLE PRECISION | Percentage of population aged 65 and over |

---

## Economic Fact

### `fact_economia`

**Grain:** One row per AGEB.

| Column                          | Type             | Description                                                         |
| ------------------------------- | ---------------- | ------------------------------------------------------------------- |
| `CVE_AGEB`                      | VARCHAR(10)      | AGEB identifier and foreign key                                     |
| `total_establecimientos`        | DOUBLE PRECISION | Total number of establishments                                      |
| `comercio`                      | DOUBLE PRECISION | Establishments classified as commerce                               |
| `retail`                        | DOUBLE PRECISION | Establishments classified in SCIAN sector 46 (retail trade)         |
| `servicios`                     | DOUBLE PRECISION | Establishments classified as services                               |
| `otros`                         | DOUBLE PRECISION | Establishments outside the project commerce/services classification |
| `densidad_establecimientos_km2` | DOUBLE PRECISION | Establishment density per km²                                       |
| `densidad_comercio_km2`         | DOUBLE PRECISION | Commerce establishment density per km²                              |
| `densidad_retail_km2`            | DOUBLE PRECISION | Retail establishment density per km²                                |
| `densidad_servicios_km2`        | DOUBLE PRECISION | Service establishment density per km²                               |
| `establecimientos_por_1000_hab` | DOUBLE PRECISION | Establishments per 1,000 inhabitants                                |
| `actividad_dominante_codigo`    | VARCHAR(10)      | SCIAN code of the dominant economic activity                        |
| `actividad_dominante`           | VARCHAR(255)     | Name of the dominant economic activity                              |
| `cantidad_actividad_dominante`  | DOUBLE PRECISION | Number of establishments belonging to the dominant activity         |
---

## Traffic Accident Fact

### `fact_accidentes`

**Grain:** One row per AGEB.

| Column                           | Type             | Description                                                |
| -------------------------------- | ---------------- | ---------------------------------------------------------- |
| `CVE_AGEB`                       | VARCHAR(10)      | AGEB identifier and foreign key                            |
| `total_accidentes`               | DOUBLE PRECISION | Total georeferenced traffic accidents                      |
| `total_muertos`                  | DOUBLE PRECISION | Total deaths                                               |
| `total_heridos`                  | DOUBLE PRECISION | Total injured people                                       |
| `accidentes_tipo_1`              | DOUBLE PRECISION | Accidents classified as type 1                             |
| `accidentes_tipo_2`              | DOUBLE PRECISION | Accidents classified as type 2                             |
| `accidentes_tipo_4`              | DOUBLE PRECISION | Accidents classified as type 4                             |
| `accidentes_tipo_5`              | DOUBLE PRECISION | Accidents classified as type 5                             |
| `accidentes_tipo_6`              | DOUBLE PRECISION | Accidents classified as type 6                             |
| `accidentes_tipo_7`              | DOUBLE PRECISION | Accidents classified as type 7                             |
| `accidentes_tipo_8`              | DOUBLE PRECISION | Accidents classified as type 8                             |
| `accidentes_tipo_10`             | DOUBLE PRECISION | Accidents classified as type 10                            |
| `accidentes_tipo_11`             | DOUBLE PRECISION | Accidents classified as type 11                            |
| `densidad_accidentes_km2`        | DOUBLE PRECISION | Traffic accident density per km²                           |
| `accidentes_por_1000_hab`        | DOUBLE PRECISION | Traffic accidents per 1,000 inhabitants                    |
| `accidentes_por_establecimiento` | DOUBLE PRECISION | Traffic accidents relative to the number of establishments |

---

# Relationships

The warehouse follows a star-schema structure centered on the AGEB geographic unit.

```text
                    dim_ageb
                       |
          +------------+------------+
          |            |            |
          v            v            v
 fact_demografia  fact_economia  fact_accidentes
```

Each fact table contains one record per AGEB and references `dim_ageb` through `CVE_AGEB`.

The geographic dimension also contains the PostGIS geometry used for spatial analysis and mapping.

---

# Geographic Strategy

The project uses **urban AGEBs belonging to the locality of Mérida** as the common analytical unit.

The selected geographic dataset contains **483 AGEBs**.

This unit was selected because:

* It is an official INEGI geographic unit.
* Census data is available at AGEB level.
* DENUE establishments can be associated with AGEBs.
* Georeferenced traffic accidents can be spatially joined to the AGEB polygons.
* It provides enough spatial detail for local spatial analysis.

The municipality of Mérida contains more AGEBs, but the analysis is restricted to the locality of Mérida (`CVE_LOC = 0001`) to maintain geographic consistency between the datasets.

---

# Main Sources

| Dataset                            | Source | Main use                                 |
| ---------------------------------- | ------ | ---------------------------------------- |
| Censo de Población y Vivienda 2020 | INEGI  | Demographic indicators                   |
| Marco Geoestadístico 2020          | INEGI  | AGEB polygons and geographic identifiers |
| DENUE                              | INEGI  | Economic establishments                  |
| ATUS 2024                          | INEGI  | Georeferenced traffic accidents          |

---

# Main Derived Indicators

### Population Density

```text
Population Density = Total Population / AGEB Area (km²)
```

### Economically Active Population Rate

```text
PEA Rate = Economically Active Population / Relevant Population Base
```

### Establishment Density

```text
Establishment Density = Total Establishments / AGEB Area (km²)
```

### Establishments per 1,000 Residents

```text
Establishments per 1,000 = Total Establishments / Population × 1,000
```

### Traffic Accident Density

```text
Accident Density = Total Traffic Accidents / AGEB Area (km²)
```

### Traffic Accident Rate

```text
Accidents per 1,000 = Total Traffic Accidents / Population × 1,000
```

### Traffic Accidents Relative to Business Activity

```text
Accidents per Establishment =
Total Traffic Accidents / Total Establishments
```

---

# Data Quality and Assumptions

* Raw datasets are preserved separately and are not modified during the ETL process.
* Missing Census values represented by `*` were converted to missing values rather than assuming zero.
* AGEB identifiers were preserved in their original format, including alphanumeric identifiers such as `021A` and `295A`.
* Traffic accident coordinates were converted into spatial points and spatially joined to the selected AGEB polygons.
* Traffic accidents outside the Mérida locality were excluded from the AGEB-level analytical dataset but remain in the raw source.
* The final analytical warehouse contains 483 AGEBs.
* Spatial geometries in PostgreSQL/PostGIS use EPSG:4326.
* Area calculations were performed using the original projected INEGI cartographic CRS before conversion to EPSG:4326.
* Correlation and spatial association results describe statistical relationships and should not be interpreted as causal effects.


## Temporal traffic accident fact

### `fact_accidentes_tiempo`

Grain: one AGEB × year × month × day period. This table stores month and period attributes directly, without a separate time dimension.

| Column | Type | Description |
|---|---|---|
| CVE_AGEB | VARCHAR(10) | Geographic FK and composite PK component |
| anio | INTEGER | Year, composite PK component |
| mes | INTEGER | Month, composite PK component |
| periodo_dia | VARCHAR(20) | Composite PK component: Madrugada 00–05, Mañana 06–11, Tarde 12–17, Noche 18–23, or No especificado |
| total_accidentes | DOUBLE PRECISION | Event count |
| total_muertos | DOUBLE PRECISION | Reported deaths |
| total_heridos | DOUBLE PRECISION | Reported injuries |

## Scope and transformation details

The instructor authorized ATUS in place of crime data. Every event measure refers to traffic accidents. The canonical current diagram is `warehouse_model.mmd` and its regenerated PNG.

PEA rate is PEA / (PEA + PE_INAC) × 100. Activity dominance is resolved once, using count descending and code ascending for ties. Retail is SCIAN 46. The services grouping is specified in `src/transform.py`. Null suppressed Census values remain null; zero count means no assigned source record. Safe ratios return null for nonpositive denominators.

The municipality includes 526 urban AGEBs; the selected locality includes 483. Source-event exclusions, DENUE assignment decisions and current integration counts are regenerated in `data/processed/quality_summary.json` and audit CSVs. Geographic identifiers are normalized and are scoped to one locality; use CVEGEO for expansion.

Separate type and temporal summaries are supported; a joint event-type-by-month query would require extending the retained grain.
