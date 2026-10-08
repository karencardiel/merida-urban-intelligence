# Verification

- The ETL was executed from original archives in a clean Python process, including a repeat run with pandas 2.3.3.
- 483 unique AGEBs, population 921771, businesses 54995, accidents 2130, exclusions 141, temporal groups 1988.
- Economic and accident count columns have no missing values; numeric exports have no infinite ratios; temporal counts and event-type counts reconcile.
- Official geometries were converted to WGS84 MultiPolygon for export. Area uses the original projected cartography.
- The original notebook code was also executed independently against the supplied archives in this environment and produced 2130 integrated accidents. Its saved output was 2132. The exact cause of this difference is not established; source state or software environment may differ. Do not copy prior saved results into the final report.
- Analysis logic was tested with database reads mocked and outputs directed to a temporary directory. The test exercised six correlation calculations, global/local/bivariate Moran, five maps and output tables. These temporary products are not delivered as warehouse-derived results.
- Python modules compile; all five SQL scripts parse as PostgreSQL syntax. psql metacommands were excluded from syntax parsing.
- Live PostgreSQL/PostGIS load and idempotence were not executed in this environment. Run the load twice locally, run SQL validation, then run analysis against the populated database. Docker Compose configuration has not been executed here.
- requirements.lock.txt records the tested Python analysis dependencies; Python 3.12 is recommended. Notebook UI dependency JupyterLab can be installed separately.
- The final 4–6 page PDF report, exact DENUE release/download metadata and team Git contributions remain pending.
