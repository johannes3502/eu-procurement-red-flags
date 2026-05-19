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
-- Source file inspection (Exercise Sheet 3, Exercise 1.1–1.2):
--   TED CSV:      UTF-8 encoding, LF line endings, comma-separated, quoted strings
--   CPI CSV:      UTF-8 encoding, LF line endings, comma-separated, quoted strings
--   WGI CSV:      UTF-8 encoding, LF line endings, comma-separated, quoted strings
--   Line endings confirmed via Notepad++ status bar. 
--   Encoding confirmed via hex inspection (no BOM at file start).
--   All columns are explicitly named in the header row (SKIP = 1).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- IMPORT stg_ted (25 columns: 15 base + 10 flags)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS error_tbl;

IMPORT INTO stg_ted
FROM LOCAL CSV FILE 'data/processed/ted/ted_clean.csv'
ENCODING = 'UTF-8'
ROW SEPARATOR = 'LF'
COLUMN SEPARATOR = ','
COLUMN DELIMITER = '"'
SKIP = 1
ERRORS INTO error_tbl REJECT LIMIT UNLIMITED IGNORE CERTIFICATE;

-- ----------------------------------------------------------------------------
-- IMPORT stg_cpi (3 columns)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS error_tbl;

IMPORT INTO stg_cpi
FROM LOCAL CSV FILE 'data/processed/cpi/cpi_clean.csv'
ENCODING = 'UTF-8'
ROW SEPARATOR = 'LF'
COLUMN SEPARATOR = ','
COLUMN DELIMITER = '"'
SKIP = 1
ERRORS INTO error_tbl REJECT LIMIT UNLIMITED IGNORE CERTIFICATE;

-- ----------------------------------------------------------------------------
-- IMPORT stg_wgi (8 columns)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS error_tbl;

IMPORT INTO stg_wgi
FROM LOCAL CSV FILE 'data/processed/wgi/wgi_clean.csv'
ENCODING = 'UTF-8'
ROW SEPARATOR = 'LF'
COLUMN SEPARATOR = ','
COLUMN DELIMITER = '"'
SKIP = 1
ERRORS INTO error_tbl REJECT LIMIT UNLIMITED IGNORE CERTIFICATE;
