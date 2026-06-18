OPEN SCHEMA JOHANNES_RAMSER;

IMPORT INTO JOHANNES_RAMSER.stg_ted
FROM LOCAL CSV FILE 'C:/Users/Johannes/uni/sose26/dw/red-flags-procurement-governance/data/processed/ted/ted_clean.csv'
ENCODING = 'UTF-8'
ROW SEPARATOR = 'LF'
COLUMN SEPARATOR = ','
COLUMN DELIMITER = '"'
SKIP = 1
ERRORS INTO JOHANNES_RAMSER.error_tbl REJECT LIMIT UNLIMITED;

IMPORT INTO JOHANNES_RAMSER.stg_cpi
FROM LOCAL CSV FILE 'C:/Users/Johannes/uni/sose26/dw/red-flags-procurement-governance/data/processed/cpi/cpi_clean.csv'
ENCODING = 'UTF-8'
ROW SEPARATOR = 'LF'
COLUMN SEPARATOR = ','
COLUMN DELIMITER = '"'
SKIP = 1
ERRORS INTO JOHANNES_RAMSER.error_tbl REJECT LIMIT UNLIMITED;

IMPORT INTO JOHANNES_RAMSER.stg_wgi
FROM LOCAL CSV FILE 'C:/Users/Johannes/uni/sose26/dw/red-flags-procurement-governance/data/processed/wgi/wgi_clean.csv'
ENCODING = 'UTF-8'
ROW SEPARATOR = 'LF'
COLUMN SEPARATOR = ','
COLUMN DELIMITER = '"'
SKIP = 1
ERRORS INTO JOHANNES_RAMSER.error_tbl REJECT LIMIT UNLIMITED;

SELECT 'stg_ted' AS "table", COUNT(*) AS "rows" FROM JOHANNES_RAMSER.stg_ted
UNION ALL
SELECT 'stg_cpi', COUNT(*) FROM JOHANNES_RAMSER.stg_cpi
UNION ALL
SELECT 'stg_wgi', COUNT(*) FROM JOHANNES_RAMSER.stg_wgi;

SELECT COUNT(*) AS import_errors FROM JOHANNES_RAMSER.error_tbl;
  