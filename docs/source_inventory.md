# Source inventory

The instructor authorized replacing crime records with ATUS traffic accidents, as confirmed by the team. The analytical scope is road safety.

| Source      | Reference period                                         | Original grain                                                | Integration                                       |
| ----------- | -------------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------- |
| Census      | 2020                                                     | Mixed locality/AGEB/block summaries; select urban AGEB totals | Normalized AGEB key                               |
| Cartography | Census 2020                                              | Official AGEB and locality polygons                           | Fixed scope 31 / 050 / 0001                       |
| DENUE       | May 2026, release 05_2026; metadata reference 2026-05-20 | One establishment                                             | AGEB key; coordinate fallback for unmatched codes |
| ATUS        | 2024                                                     | One georeferenced traffic accident                            | Official points within AGEB polygons              |

## Verified DENUE metadata

* Identifier: MEX-INEGI.EEC2.05-DENUE-2026.
* Title: Directorio Estadístico Nacional de Unidades Económicas (DENUE) 05_2026.
* Modified and Temporal: 2026-05-20.
* Publisher: INEGI.
* Distribution: https://www.inegi.org.mx/app/descarga/?ti=6
* Original metadata member: metadatos/metadatos_denue.txt, preserved verbatim as docs/metadatos_denue.txt.
* Team download date: not recorded. Do not infer it from metadata modification dates, ZIP timestamps or establishment registration dates.

## Obtaining the original inputs

The original raw datasets are not included in this repository because of their size. The exact files used for the project are available in the team's Google Drive:

[Download raw datasets](https://drive.google.com/drive/folders/1Wfy9uiXtubHaJ84nkpUdyGkj9t7wHcut?usp=sharing)

Use the following original inputs for the ETL process:

* ageb_mza_urbana_31_cpv2020_csv.zip — Censo de Población y Vivienda 2020.
* 31_yucatan.zip — Marco Geoestadístico, Yucatán.
* denue_31_csv.zip — Directorio Estadístico Nacional de Unidades Económicas (DENUE), May 2026.
* atus_2024_shp.zip — Estadística de Accidentes de Tránsito Terrestre en Zonas Urbanas y Suburbanas (ATUS), 2024.

The exact unchanged archives used to produce the processed data are identified by their SHA-256 hashes below. A later release from a changing download portal is not equivalent to these inputs. If a historical file is no longer offered, obtain the original retained archive from the team and verify its hash.

* ageb_mza_urbana_31_cpv2020_csv.zip: 6044441 bytes; SHA-256 5cc69c7a9f0f248e1e19f960b4498a5459d4bedbc1bdc5dd7f98bfac44f99180.
* denue_31_csv.zip: 10832360 bytes; SHA-256 a47d4054f2cdeb5ebfce0da8ce1934cb830417174c504182b81964a329556536.
* 31_yucatan.zip: 50570164 bytes; SHA-256 c486f642edbae13e51e219374d15f432758d565f86bc83472e6ec2c70b1e8f81.
* atus_2024_shp.zip: 30598455 bytes; SHA-256 830bc6570b18197ba0016e76fd85ee545f7c8a3eddedc02049b995d00f3bdb32.

## Official sources

* *Censo de Población y Vivienda 2020:* https://www.inegi.org.mx/programas/ccpv/2020/#datos_abiertos
* *Marco Geoestadístico:* http://inegi.org.mx/app/biblioteca/ficha.html?upc=889463807469
* *Directorio Estadístico Nacional de Unidades Económicas (DENUE):* https://www.inegi.org.mx/app/descarga/default.html
* *Estadística de Accidentes de Tránsito Terrestre en Zonas Urbanas y Suburbanas (ATUS):* http://inegi.org.mx/programas/accidentes/#datos_abiertos
