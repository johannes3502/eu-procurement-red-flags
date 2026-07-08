-- import_staging.sql
-- Manual import of CSV files into staging tables (for DBeaver / SQL client).
-- Prefer setup_and_load.py for automated Parquet-based loading.
--
-- Prerequisites:
--   1. Run create_staging_tables.sql first
--   2. Adjust file paths below to point to your data/processed/*.csv files
--
-- Schema: procurement_governance (or set your schema in DBeaver)

IMPORT INTO stg_ted
FROM LOCAL CSV FILE 'data/processed/ted/ted_clean.csv'
ENCODING = 'UTF-8'
ROW SEPARATOR = 'LF'
COLUMN SEPARATOR = ','
COLUMN DELIMITER = '"'
SKIP = 1
ERRORS INTO error_tbl REJECT LIMIT UNLIMITED;

IMPORT INTO stg_cpi
FROM LOCAL CSV FILE 'data/processed/cpi/cpi_clean.csv'
ENCODING = 'UTF-8'
ROW SEPARATOR = 'LF'
COLUMN SEPARATOR = ','
COLUMN DELIMITER = '"'
SKIP = 1
ERRORS INTO error_tbl REJECT LIMIT UNLIMITED;

IMPORT INTO stg_wgi
FROM LOCAL CSV FILE 'data/processed/wgi/wgi_clean.csv'
ENCODING = 'UTF-8'
ROW SEPARATOR = 'LF'
COLUMN SEPARATOR = ','
COLUMN DELIMITER = '"'
SKIP = 1
ERRORS INTO error_tbl REJECT LIMIT UNLIMITED;

SELECT 'stg_ted' AS "table", COUNT(*) AS "rows" FROM stg_ted
UNION ALL
SELECT 'stg_cpi', COUNT(*) FROM stg_cpi
UNION ALL
SELECT 'stg_wgi', COUNT(*) FROM stg_wgi;

SELECT COUNT(*) AS import_errors FROM error_tbl;
