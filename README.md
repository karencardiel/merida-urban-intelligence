# Mérida Urban Intelligence

A reproducible geospatial Data Warehouse for the urban locality of Mérida, Yucatán. It integrates population, businesses and road-safety events by official urban AGEB to compare territorial indicators and explore spatial associations.

The instructor authorized ATUS traffic accidents as the replacement for the crime dataset. All event indicators describe road safety; they must not be labeled as crimes.

## Environment and execution

Use Python 3.12 and Docker Compose. Run commands from the repository root.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock.txt
pip install "jupyterlab>=4,<5"
cp .env.example .env
docker compose up -d --wait
python -m src.pipeline all
```

On Windows activate the environment with `.venv\Scripts\Activate.ps1`. If port 5432 is occupied, change `POSTGRES_PORT` in `.env`; both Docker and Python use it. The default credentials are for a local academic database.

Individual stages are `python -m src.pipeline etl`, `python -m src.pipeline load` and `python -m src.pipeline analyze`. The notebook calls the same modules and contains no separate implementation. `DATABASE_URL`, if supplied, overrides the individual database settings.

The loader creates the schema, upserts the current snapshot and validates it in one transaction. Repeated runs update existing measures instead of failing on duplicate keys. A changed geographic scope that leaves stale AGEB rows fails validation and requires an intentional migration. The temporal fact is synchronized to the current snapshot. Docker does not automatically load processed CSVs during database initialization.

Optional psql route, after ETL, from the repository root:

```bash
psql -h localhost -p 5432 -U postgres -d merida_urban_intelligence -f sql/02_load.sql
```

This script creates schema, loads data, creates views and validates in one transaction. Enter the password when prompted. Adjust port, user and database to match `.env`.

## Original sources

Download the four original ZIP archives from [Google Drive — Raw data](https://drive.google.com/drive/folders/1Wfy9uiXtubHaJ84nkpUdyGkj9t7wHcut) and place them in `data/raw/` before running the pipeline.

Keep the archives compressed and preserve their original filenames. The ETL reads them directly and never overwrites raw bytes. These files are excluded from Git and provided separately for reproducibility.

| Archive | Source and original grain | Variables |
|---|---|---|
| `ageb_mza_urbana_31_cpv2020_csv.zip` | [INEGI Census 2020](https://www.inegi.org.mx/programas/ccpv/2020/#datos_abiertos), mixed locality, AGEB and block summaries | Geographic codes, population, age groups, PEA, inactive population, housing |
| `31_yucatan.zip` | [INEGI Census 2020 cartography](https://www.inegi.org.mx/app/biblioteca/ficha.html?upc=889463807469), official geographic features | Urban AGEB and locality polygons, CRS, identifiers |
| `denue_31_csv.zip` | [INEGI DENUE, May 2026](https://www.inegi.org.mx/app/descarga/default.html), one establishment | ID, SCIAN activity, personnel size, coordinates, geographic codes |
| `atus_2024_shp.zip` | [INEGI ATUS 2024](https://www.inegi.org.mx/programas/accidentes/#datos_abiertos), one georeferenced traffic accident | ID, type, year/month/day/hour, injuries, deaths, coordinates and official point geometry |

The supplied DENUE archive is release **05_2026 (May 2026)**. Its original metadata identifies `MEX-INEGI.EEC2.05-DENUE-2026` and reports Modified/Temporal **2026-05-20**. The metadata is preserved in `docs/metadatos_denue.txt`. This reference date is not the team's download date, which was not recorded. Establishment registration dates are not the snapshot date. Original archive names, sizes and SHA-256 hashes are preserved in `docs/source_manifest.json`; see `docs/source_inventory.md` for retrieval instructions. Raw archives are excluded from Git but must be retained for reproduction.

## Geographic strategy

Candidate units are municipality, locality, urban AGEB and block. The municipality is too coarse for comparing neighborhoods. Locality is also too coarse for internal patterns. Blocks provide finer detail but increase confidentiality gaps and sparse-event instability. Urban AGEB offers official polygons and direct Census aggregates while retaining internal spatial variation.

The scope is entity 31, municipality 050, locality 0001: 483 urban AGEBs. `CVE_AGEB` alone is valid as a key inside this explicitly fixed locality; expansion requires a composite geographic key such as CVEGEO. Population uses AGEB summary rows, not a mixture of block and AGEB totals.

Polygons are checked for uniqueness, valid nonempty geometry and projected CRS. Area is calculated from the original projected INEGI geometry in square meters and converted to km². PostGIS stores WGS84 MultiPolygon geometry, with a GiST index.

DENUE is integrated by normalized AGEB codes. Establishments with unmatched codes are tested using their coordinates; unresolved records are audited and excluded. ATUS latitude/longitude points are reconstructed for inspection, but the official shapefile point geometry is the authority. Points are reprojected to the polygon CRS and joined with `within`. Boundary points receive no arbitrary nearest-area assignment. Unassigned events are retained in an exclusion audit and tested against the locality polygon.

## ETL and warehouse

`extract.py` reads archives; `transform.py` cleans types, integrates geography and aggregates; `load.py` loads PostgreSQL; `analysis.py` reads only warehouse views and tables; `pipeline.py` coordinates stages.

Census suppression `*` becomes null, never zero. Zero establishment/event counts mean no records assigned to the selected area after integration, not guaranteed absence in the real world. Denominator zero yields null. Dominant SCIAN activity is the most frequent activity in an AGEB, with ties resolved by ascending activity code. Retail is SCIAN 46; commerce includes 43 and 46. Services use the explicit sector list in `transform.py`, including public administration 93, which is a project grouping that must be interpreted accordingly.

| Table | Grain | Key and role |
|---|---|---|
| `dim_ageb` | One urban AGEB | Geographic key, identifiers, area, PostGIS geometry |
| `fact_demografia` | AGEB at Census 2020 snapshot | AGEB PK/FK; demographic counts and ratios |
| `fact_economia` | AGEB at supplied DENUE snapshot | AGEB PK/FK; establishment categories and dominant activity |
| `fact_accidentes` | AGEB for ATUS 2024 | AGEB PK/FK; counts, event types and rates |
| `fact_accidentes_tiempo` | AGEB × year × month × day period | Composite PK; AGEB FK; events, deaths and injuries |

The temporal table supports monthly/day-period distribution; type counts are retained separately by AGEB. Type-by-month cross-tabulation is not retained, so this model supports the requested distributions separately. Extend the fact grain if a joint type/time analysis is required. Event time is retained as fact attributes; a separate time dimension is an optional extension, not a requirement for this snapshot model.

See `docs/data_dictionary.md` and `docs/warehouse_model.mmd`.

## KPI definitions

| Indicator | Per-area formula |
|---|---|
| Population | Census total |
| Population density | Population / area km² |
| PEA rate | PEA / (PEA + inactive population) × 100 |
| Age groups | 0–14, 15–64, 65+ counts and percentages of population |
| Businesses | Integrated DENUE establishment count |
| Business density | Businesses / area km² |
| Businesses per 1,000 residents | Businesses / population × 1,000 |
| Retail density | SCIAN 46 count / area km² |
| Service density | Project service-sector count / area km² |
| Dominant activity | Most frequent SCIAN activity within the area |
| Accidents | Assigned ATUS event count |
| Accident rate | Accidents / population × 1,000 |
| Type/time distribution | AGEB type counts; year/month/day-period totals |
| Accidents relative to business activity | Accidents / businesses |

Population and event counts can be summed. Densities and percentages are not additive: compute pooled ratios from summed numerators and denominators. `sql/05_kpi_queries.sql` contains example queries. The PEA ratio uses rows with both PEA and inactive population observed when pooling.

## Spatial analysis and outputs

Three indicator pairs are evaluated with Pearson and Spearman: population/business density, population/accident density, business/accident density. Pearson describes a linear relationship; Spearman describes a rank relationship and is less sensitive to extreme magnitudes. Their conventional p-values assume independent observations; geographic dependence limits interpretation.

Global Moran is calculated for population and accident density, LISA for both, and bivariate Moran for local business density against neighboring accident density. All variables use a single AGEB-ordered dataset and Queen contiguity with row-standardized weights, seed 42 and 999 permutations. Queen treats shared vertices or edges as neighbors. Disconnected components remain separate; islands have zero lag and receive the explicit local label `No neighbors`. LISA at p < 0.05 is exploratory and is not corrected for multiple comparisons. Fixed seeds improve repeatability within the pinned environment; library changes can still affect spatial or permutation results.

Maps, correlations, LISA tables, spatial results and a findings draft are generated under `outputs/` after `analyze`. They are never computed directly from processed CSVs. Read the results before writing the technical report; `outputs/findings.md` is supporting material, not the required 4–6 page PDF.

## Quality and limitations

The ETL exports `quality_summary.json`, DENUE assignment decisions and excluded accidents. PostgreSQL validates geometry, row counts, keys, category totals and temporal reconciliation. Foreign keys enforce geographic relationships.

Population 2020, accidents 2024 and DENUE May 2026 have different reference dates. Rates use the Census population as an explicit denominator rather than a current-year estimate. Accidents per resident are territorial comparisons, not individual travel-risk estimates. Official cartography may not cover more recent expansion. Sparse areas can have unstable ratios. Common area denominators can affect density correlations. Observed statistical association does not establish causality.

## Collaboration and final submission

Keep the original repository and commit history. Each team member should commit their own substantive code, analysis or documentation changes; do not manufacture historical contributions. The final submission requires this reproducible repository and a 4–6 page PDF containing the problem, geography, warehouse architecture, selected KPIs, maps, findings and limitations. The DENUE release is verified from the original archive. The technical report is included in `docs/BI_E2_Merida_Report.pdf`. The original download date was not recorded. Collaboration must still be evidenced by real individual contributions in this same repository.

## Repository structure and final artifacts

- `src/`: modular extraction, geographic transformation, transactional loading and analysis.
- `sql/`: schema, alternative psql load, views, validation and KPI queries.
- `notebooks/`: source/geography exploration and pipeline entry point.
- `docs/`: source inventory, original DENUE metadata, archive fingerprints, data dictionary, model diagram and technical report.
- `data/raw/`: place the four unchanged original archives here; excluded from Git.
- `data/processed/`: validated geographic/temporal exports and integration audits.
- `outputs/`: final analytical tables, maps, figures and findings.
- `dashboard/merida-dashboard.html`: standalone English dashboard with embedded data/images and Poppins; open directly in a browser. It is a fixed export and must be regenerated when analytical results change.
- `tests/`: checks of processed grain, counts, missing-value policy and geography.

Run the processed-data checks after ETL:

```bash
python -m unittest discover -s tests -v
```

On Apple Silicon, the Compose service uses `platform: linux/amd64` for the selected PostGIS image. Docker Desktop or a compatible Docker engine such as OrbStack must be running. If `python` is unavailable before environment creation, use `python3.12 -m venv .venv`.
