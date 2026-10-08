# Source inventory

The instructor authorized replacing crime records with ATUS traffic accidents, as confirmed by the team. The analytical scope is road safety.

| Source | Reference period | Original grain | Integration |
|---|---|---|---|
| Census | 2020 | Mixed locality/AGEB/block summaries; select urban AGEB totals | Normalized AGEB key |
| Cartography | Census 2020 | Official AGEB and locality polygons | Fixed scope 31 / 050 / 0001 |
| DENUE | May 2026, release 05_2026; metadata reference 2026-05-20 | One establishment | AGEB key; coordinate fallback for unmatched codes |
| ATUS | 2024 | One georeferenced traffic accident | Official points within AGEB polygons |

## Verified DENUE metadata

- Identifier: `MEX-INEGI.EEC2.05-DENUE-2026`.
- Title: Directorio Estadístico Nacional de Unidades Económicas (DENUE) 05_2026.
- Modified and Temporal: `2026-05-20`.
- Publisher: INEGI.
- Distribution: https://www.inegi.org.mx/app/descarga/?ti=6
- Original metadata member: `metadatos/metadatos_denue.txt`, preserved verbatim as `docs/metadatos_denue.txt`.
- Team download date: not recorded. Do not infer it from metadata modification dates, ZIP timestamps or establishment registration dates.

## Obtaining the original inputs

Use INEGI Census 2020 AGEB/block CSV results for Yucatán, 2020 Yucatán cartography, DENUE Yucatán May 2026 CSV, and the 2024 georeferenced ATUS shapefile. Source links are in README. Place the exact unchanged archives below in `data/raw/`. A later release from a changing download portal is not equivalent to these inputs. If a historical file is no longer offered, obtain the original retained archive from the team and verify its hash. This package excludes the large raw archives; they are still required to rerun ETL.

- `ageb_mza_urbana_31_cpv2020_csv.zip`: 6044441 bytes; SHA-256 `5cc69c7a9f0f248e1e19f960b4498a5459d4bedbc1bdc5dd7f98bfac44f99180`.
- `denue_31_csv.zip`: 10832360 bytes; SHA-256 `a47d4054f2cdeb5ebfce0da8ce1934cb830417174c504182b81964a329556536`.
- `31_yucatan.zip`: 50570164 bytes; SHA-256 `c486f642edbae13e51e219374d15f432758d565f86bc83472e6ec2c70b1e8f81`.
- `atus_2024_shp.zip`: 30598455 bytes; SHA-256 `830bc6570b18197ba0016e76fd85ee545f7c8a3eddedc02049b995d00f3bdb32`.
