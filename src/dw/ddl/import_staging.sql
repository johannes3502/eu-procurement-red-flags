-- ============================================================================
-- Challenge 3 — IMPORT Commands for Exasol
-- Author: Johannes, OTH Regensburg
-- ============================================================================
-- Prerequisite: Export cleaned parquet files to CSV (one-time Python step)
--   python -c "import pandas as pd;
--   pd.read_parquet('data/processed/ted/ted_clean.parquet')
--     .to_csv('data/processed/ted/ted_clean.csv', index=False);
--   pd.read_parquet('data/processed/cpi/cpi_clean.parquet')
--     .to_csv('data/processed/cpi/cpi_clean.csv', index=False);
--   pd.read_parquet('data/processed/wgi/wgi_clean.parquet')
--     .to_csv('data/processed/wgi/wgi_clean.csv', index=False)"
-- ============================================================================

-- ----------------------------------------------------------------------------
-- IMPORT stg_ted — ~1.78M rows, ~28 MB CSV
-- ----------------------------------------------------------------------------
IMPORT INTO stg_ted
FROM LOCAL CSV FILE 'data/processed/ted/ted_clean.csv'
ENCODING = 'UTF-8'
ROW SEPARATOR = 'LF'
COLUMN SEPARATOR = ','
COLUMN DELIMITER = '"'
SKIP = 1;

-- ----------------------------------------------------------------------------
-- IMPORT stg_cpi — 40 rows, negligible size
-- ----------------------------------------------------------------------------
IMPORT INTO stg_cpi
FROM LOCAL CSV FILE 'data/processed/cpi/cpi_clean.csv'
ENCODING = 'UTF-8'
ROW SEPARATOR = 'LF'
COLUMN SEPARATOR = ','
COLUMN DELIMITER = '"'
SKIP = 1;

-- ----------------------------------------------------------------------------
-- IMPORT stg_wgi — 40 rows, negligible size
-- ----------------------------------------------------------------------------
IMPORT INTO stg_wgi
FROM LOCAL CSV FILE 'data/processed/wgi/wgi_clean.csv'
ENCODING = 'UTF-8'
ROW SEPARATOR = 'LF'
COLUMN SEPARATOR = ','
COLUMN DELIMITER = '"'
SKIP = 1;
