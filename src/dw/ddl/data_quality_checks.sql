-- IMPORTANT: Set your schema in DBeaver before running. The default schema is 'procurement_governance'.

--
-- data_quality_checks.sql
-- Data Quality Checks, Entity Matching, Deduplication
--

-- ===========================================================================
-- A.1: error_info-Spalte hinzufügen
-- VOR dem ersten Run: Diese 3 Zeilen einzeln ausführen.
-- Bei Re-Run: Überspringen (Spalten existieren bereits).
-- ===========================================================================

-- ALTER TABLE stg_ted ADD COLUMN error_info VARCHAR(2000);
-- ALTER TABLE stg_cpi ADD COLUMN error_info VARCHAR(2000);
-- ALTER TABLE stg_wgi ADD COLUMN error_info VARCHAR(2000);

-- ===========================================================================
-- A.2: Duplikaterkennung innerhalb jeder Quelltabelle
-- ===========================================================================

-- stg_ted: Duplikate auf ID_AWARD (sollte Primary Key sein)
UPDATE stg_ted SET error_info = 'Duplicate ID_AWARD'
WHERE ID_AWARD IN (
    SELECT ID_AWARD FROM stg_ted
    GROUP BY ID_AWARD HAVING COUNT(*) > 1
);

-- stg_cpi: Duplikate auf (country_iso3, "YEAR")
UPDATE stg_cpi SET error_info = 'Duplicate country-year'
WHERE (country_iso3, "YEAR") IN (
    SELECT country_iso3, "YEAR" FROM stg_cpi
    GROUP BY country_iso3, "YEAR" HAVING COUNT(*) > 1
);

-- stg_wgi: Duplikate auf (country_iso3, "YEAR")
UPDATE stg_wgi SET error_info = 'Duplicate country-year'
WHERE (country_iso3, "YEAR") IN (
    SELECT country_iso3, "YEAR" FROM stg_wgi
    GROUP BY country_iso3, "YEAR" HAVING COUNT(*) > 1
);

-- Anzahl Duplikate ausgeben
SELECT 'stg_ted' AS src, COUNT(*) AS duplicates
FROM stg_ted WHERE error_info IS NOT NULL
UNION ALL
SELECT 'stg_cpi', COUNT(*) FROM stg_cpi WHERE error_info IS NOT NULL
UNION ALL
SELECT 'stg_wgi', COUNT(*) FROM stg_wgi WHERE error_info IS NOT NULL;


-- ===========================================================================
-- A.3: Weitere Fehler erkennen
-- ===========================================================================

-- Sentinel-Werte: AWARD_VALUE_EURO >= 1 Billion EUR sind Platzhalter
UPDATE stg_ted SET error_info = 'Sentinel value in AWARD_VALUE_EURO'
WHERE AWARD_VALUE_EURO >= 1000000000000
  AND error_info IS NULL;

-- NULL-CPV-Code
UPDATE stg_ted SET error_info = 'Missing CPV code'
WHERE cpv_code IS NULL
  AND error_info IS NULL;

-- Ungültige ISO-Country-Codes (nur DE, DK, RO, HU sind im Scope)
UPDATE stg_ted SET error_info = 'Invalid ISO_COUNTRY_CODE'
WHERE ISO_COUNTRY_CODE NOT IN ('DE', 'DK', 'RO', 'HU')
  AND error_info IS NULL;

-- Negativer Award-Wert (sollte nicht vorkommen)
UPDATE stg_ted SET error_info = 'Negative AWARD_VALUE_EURO'
WHERE AWARD_VALUE_EURO < 0
  AND error_info IS NULL;

-- NUMBER_OFFERS = 0 (gescheiterte Vergabe, kein Fehler aber auffällig)
UPDATE stg_ted SET error_info = 'Failed procurement (NUMBER_OFFERS=0)'
WHERE NUMBER_OFFERS = 0
  AND error_info IS NULL;

-- CPI außerhalb gültiger Range (0-100)
UPDATE stg_cpi SET error_info = 'CPI score out of range [0,100]'
WHERE cpi_score NOT BETWEEN 0 AND 100
  AND error_info IS NULL;

-- WGI-Dimensionen außerhalb erwarteter Range [-2.5, 2.5]
UPDATE stg_wgi SET error_info = 'WGI control_of_corruption out of range'
WHERE control_of_corruption NOT BETWEEN -2.5 AND 2.5
  AND error_info IS NULL;

UPDATE stg_wgi SET error_info = 'WGI government_effectiveness out of range'
WHERE government_effectiveness NOT BETWEEN -2.5 AND 2.5
  AND error_info IS NULL;

UPDATE stg_wgi SET error_info = 'WGI political_stability out of range'
WHERE political_stability NOT BETWEEN -2.5 AND 2.5
  AND error_info IS NULL;

UPDATE stg_wgi SET error_info = 'WGI rule_of_law out of range'
WHERE rule_of_law NOT BETWEEN -2.5 AND 2.5
  AND error_info IS NULL;

UPDATE stg_wgi SET error_info = 'WGI regulatory_quality out of range'
WHERE regulatory_quality NOT BETWEEN -2.5 AND 2.5
  AND error_info IS NULL;

UPDATE stg_wgi SET error_info = 'WGI voice_accountability out of range'
WHERE voice_accountability NOT BETWEEN -2.5 AND 2.5
  AND error_info IS NULL;

-- Fehlerstatistik pro Tabelle
SELECT 'stg_ted' AS src, error_info, COUNT(*) AS row_count
FROM stg_ted WHERE error_info IS NOT NULL
GROUP BY error_info
UNION ALL
SELECT 'stg_cpi', error_info, COUNT(*) FROM stg_cpi WHERE error_info IS NOT NULL GROUP BY error_info
UNION ALL
SELECT 'stg_wgi', error_info, COUNT(*) FROM stg_wgi WHERE error_info IS NOT NULL GROUP BY error_info
ORDER BY src, row_count DESC;


-- ===========================================================================
-- A.4: Entity-Matching über Quelltabellen hinweg
-- ===========================================================================

--
-- (a) Equal Join: TED-Land (Alpha-2) <-> CPI-Land (Alpha-3) via Lookup
--     Zählt, wie viele stg_ted-Zeilen einen CPI-Match finden
--
SELECT COUNT(*) AS ted_cpi_equal_join_matches
FROM stg_ted t
JOIN stg_cpi c ON t."YEAR" = c."YEAR"
WHERE t.ISO_COUNTRY_CODE = CASE c.country_iso3
    WHEN 'DEU' THEN 'DE'
    WHEN 'DNK' THEN 'DK'
    WHEN 'ROU' THEN 'RO'
    WHEN 'HUN' THEN 'HU'
END;

--
-- (a2) Equal Join: TED-Land (Alpha-2) <-> WGI-Land (Alpha-3) via Lookup
--
SELECT COUNT(*) AS ted_wgi_equal_join_matches
FROM stg_ted t
JOIN stg_wgi w ON t."YEAR" = w."YEAR"
WHERE t.ISO_COUNTRY_CODE = CASE w.country_iso3
    WHEN 'DEU' THEN 'DE'
    WHEN 'DNK' THEN 'DK'
    WHEN 'ROU' THEN 'RO'
    WHEN 'HUN' THEN 'HU'
END;

--
-- (a3) Equal Join: CPI <-> WGI (identische Kodierung Alpha-3)
--
SELECT COUNT(*) AS cpi_wgi_equal_join_matches
FROM stg_cpi c
JOIN stg_wgi w ON c.country_iso3 = w.country_iso3 AND c."YEAR" = w."YEAR";

--
-- (b) Levenshtein-Matching: Ländernamen in dim_country
--     Relevanz: Würde Tippfehler in country_name erkennen (z.B. 'Germany' vs 'Germnay').
--     Für unser Projekt mit 4 Ländern und standardisierten Codes kaum relevant.
--
SELECT d1.country_name AS name1, d2.country_name AS name2,
       edit_distance(d1.country_name, d2.country_name) AS distance
FROM dim_country d1, dim_country d2
WHERE d1.country_key < d2.country_key
  AND edit_distance(d1.country_name, d2.country_name) <= 2;

SELECT COUNT(*) AS levenshtein_match_count
FROM dim_country d1, dim_country d2
WHERE d1.country_key < d2.country_key
  AND edit_distance(d1.country_name, d2.country_name) <= 2;

--
-- (c) Soundex-Matching: Ländernamen die ähnlich klingen
--     Z.B. 'Germany' und 'Germany' haben gleichen Soundex
--
SELECT d1.country_name AS name1, d2.country_name AS name2,
       soundex(d1.country_name) AS soundex1, soundex(d2.country_name) AS soundex2
FROM dim_country d1, dim_country d2
WHERE d1.country_key < d2.country_key
  AND soundex(d1.country_name) = soundex(d2.country_name);

SELECT COUNT(*) AS soundex_match_count
FROM dim_country d1, dim_country d2
WHERE d1.country_key < d2.country_key
  AND soundex(d1.country_name) = soundex(d2.country_name);


-- ===========================================================================
-- A.5: False Positives / False Negatives
-- ===========================================================================

-- Levenshtein-Matches, die Soundex NICHT findet (False Negatives für Soundex)
SELECT d1.country_name AS name1, d2.country_name AS name2,
       edit_distance(d1.country_name, d2.country_name) AS lev_dist,
       soundex(d1.country_name) AS sx1, soundex(d2.country_name) AS sx2
FROM dim_country d1, dim_country d2
WHERE d1.country_key < d2.country_key
  AND edit_distance(d1.country_name, d2.country_name) <= 2
  AND soundex(d1.country_name) != soundex(d2.country_name);

-- Soundex-Matches, die Levenshtein NICHT findet (False Positives für Soundex)
SELECT d1.country_name AS name1, d2.country_name AS name2,
       soundex(d1.country_name) AS sx,
       edit_distance(d1.country_name, d2.country_name) AS lev_dist
FROM dim_country d1, dim_country d2
WHERE d1.country_key < d2.country_key
  AND soundex(d1.country_name) = soundex(d2.country_name)
  AND edit_distance(d1.country_name, d2.country_name) > 2;

/*
Bewertung:
Für unser Projekt mit standardisierten ISO-Ländercodes (Alpha-2, Alpha-3) ist
Equal Join die korrekte Matching-Methode. Levenshtein und Soundex sind bei
standardisierten Codes nicht sinnvoll, da sie nur Tippfehler in Freitextfeldern
(wie country_name) erkennen können. Die 4 Ländernamen sind so unterschiedlich,
dass weder Levenshtein noch Soundex False Matches produzieren.
False Positives wären z.B. 'Romania' ~ 'Rumänien' via Soundex, aber das ist
kein relevanter Use Case für unser Projekt.
*/


-- ===========================================================================
-- A.6: Gewählte Matching-Methode: Equal Join
-- ===========================================================================

-- CPI + WGI werden via (country_iso3, year) per Equal Join zusammengeführt.
-- TED wird via Alpha-2 <-> Alpha-3 Mapping (Fallunterscheidung) gejoint.
-- Dies ist die exakte, semantisch korrekte Methode für Code-basierte Attribute.


-- ===========================================================================
-- A.7: Nicht-gematchte Zeilen integrieren
-- ===========================================================================

-- TED-Zeilen ohne CPI/WGI-Match (z.B. winner_country ohne Governance-Daten):
SELECT COUNT(*) AS ted_without_cpi_match
FROM stg_ted t
WHERE NOT EXISTS (
    SELECT 1 FROM stg_cpi c
    WHERE c."YEAR" = t."YEAR"
      AND c.country_iso3 = CASE t.ISO_COUNTRY_CODE
          WHEN 'DE' THEN 'DEU' WHEN 'DK' THEN 'DNK'
          WHEN 'RO' THEN 'ROU' WHEN 'HU' THEN 'HUN'
      END
);

-- CPI-Zeilen ohne TED-Match (theoretisch irrelevant, da CPI 40 Zeilen, TED 1.78M)
SELECT COUNT(*) AS cpi_without_ted_match
FROM stg_cpi c
WHERE NOT EXISTS (
    SELECT 1 FROM stg_ted t
    WHERE t."YEAR" = c."YEAR"
      AND t.ISO_COUNTRY_CODE = CASE c.country_iso3
          WHEN 'DEU' THEN 'DE' WHEN 'DNK' THEN 'DK'
          WHEN 'ROU' THEN 'RO' WHEN 'HUN' THEN 'HU'
      END
);

/*
Strategie:
- TED-Zeilen ohne CPI/WGI-Match werden trotzdem in fact_tender geladen.
  Der Join auf dim_country liefert dann NULL für Governance-Attribute.
- CPI/WGI-Zeilen ohne TED-Match werden trotzdem als SCD Type 2 in
  dim_country gespeichert (erhalten eine eigene country_key-Zeile).
*/


-- ===========================================================================
-- A.8: Zusammenfassung — fehlerhafte vs. saubere Zeilen
-- ===========================================================================

SELECT 'stg_ted' AS src,
       COUNT(*) AS total,
       SUM(CASE WHEN error_info IS NULL THEN 1 ELSE 0 END) AS clean,
       SUM(CASE WHEN error_info IS NOT NULL THEN 1 ELSE 0 END) AS erroneous
FROM stg_ted
UNION ALL
SELECT 'stg_cpi', COUNT(*),
       SUM(CASE WHEN error_info IS NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN error_info IS NOT NULL THEN 1 ELSE 0 END)
FROM stg_cpi
UNION ALL
SELECT 'stg_wgi', COUNT(*),
       SUM(CASE WHEN error_info IS NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN error_info IS NOT NULL THEN 1 ELSE 0 END)
FROM stg_wgi;
