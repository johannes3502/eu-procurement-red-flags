# Technische Dokumentation – Red Flags Procurement Governance

*Detaillierte Beschreibung der Architektur, Implementierung und Datenverarbeitung*

---

## 1. Systemarchitektur & Überblick

### 1.1 Komponenten-Stack

```
ETL-Pipeline (Python)
  ├─ Extract: Daten von drei Quellen (TED, CPI, WGI)
  ├─ Transform: Bereinigung, ISO-Mapping, Red-Flag-Berechnung
  └─ Load: Parquet-Export → später Exasol
       ↓
Data Warehouse (Sternschema)
  ├─ Faktentabelle: fact_tender
  └─ Dimensionen: Land (SCD Type 2, Role-Playing), CPV, Verfahrenstyp
       ↓
Analysis Layer (SQL + Python)
  ├─ mehrdimensionale Queries
  ├─ Red-Flag-Kombinationen
  └─ Visualisierungen (PPTX)
```

### 1.2 Projektstruktur

```
red-flags-procurement-governance/
├── doc/
│   ├── project.md              # Projektkonzept & Anforderungen
│   ├── doc.md                  # Technische Dokumentation (dieses Doc)
│   ├── data-model/             # Data Model Documents
│   │   ├── mer_model.md        # ME/R Model (Mermaid)
│   │   ├── measure_table.md    # Measure Table (FLOW/STOCK/VPU)
│   │   └── snowflake_variant.md # Snowflake Variant + Star-vs-Snowflake
│   └── profiling/
│       └── analysis/
│           └── analysis_results.md
├── src/
│   ├── acquisition/            # Datenquellen-Module (ted/cpi/wgi)
│   ├── processing/             # Transformations-Module
│   │   ├── config.py           # ETL-Config: Pfade, Thresholds, Spaltenlisten
│   │   ├── utils.py            # Shared Utilities
│   │   ├── ted/clean.py        # TED-spezifisch: 7 clean_ted_* + compute_red_flags()
│   │   ├── cpi/clean.py        # CPI-spezifisch: clean_cpi()
│   │   ├── wgi/clean.py        # WGI-spezifisch: clean_wgi()
│   │   ├── run_cleanup.py      # CLI-Orchestrierung
│   │   └── profiling/          # Data Profiling & Analyse
│   ├── dw/
│   │   └── ddl/
│   │       ├── create_star_schema.sql
│   │       └── insert_example_rows.sql
│   └── log/
├── data/
│   ├── raw/                    # Rohdaten (ted_<YYYY>.csv, cpi_raw.csv, wgi_raw.csv)
│   ├── lookup/
│   │   └── lookup_countries.csv # SPoT: alpha_2, alpha_3, is_target
│   └── processed/              # Bereinigte Daten (Parquet)
│       ├── ted/ted_clean.parquet
│       ├── cpi/cpi_clean.parquet
│       └── wgi/wgi_clean.parquet
└── logs/
```

---

## 2. Datenquellen & Ihre Integration

### 2.1 TED (Tenders Electronic Daily)

**URL:** https://data.europa.eu/data/datasets/ted-csv?locale=en  
**Format:** CSV (pro Jahr separate Datei)  
**Länderfeld:** `ISO_COUNTRY_CODE` (Auftraggeber), `WIN_COUNTRY_CODE` (Gewinner)  
**Zeitraum:** 2014–2023  
**Größe:** ~2,2 Mio. Zeilen für 4 Länder & 10 Jahre, ~5,36 GB raw → ~28 MB clean

**Wichtige Spalten:**
- `ID_AWARD`: Award-ID (Fact-PK)
- `ID_NOTICE_CAN`: Bekanntmachungs-ID (degenerierte Dimension)
- `ID_LOT`: Los-ID (degenerierte Dimension)
- `ISO_COUNTRY_CODE`: Auftraggeber-Land (Alpha‑2)
- `WIN_COUNTRY_CODE`: Gewinner-Land (z.T. mehrwertig mit `---`)
- `TOP_TYPE`: Verfahrenstyp (OPE/NIC/AWP/RES/…)
- `NUMBER_OFFERS`: Anzahl Bieter
- `AWARD_VALUE_EURO`: Zuschlagswert
- `VALUE_EURO`: Geschätzter Wert
- `CPV`: Common Procurement Vocabulary

### 2.2 CPI (Corruption Perceptions Index)

**Quelle:** Transparency International / HDX  
**Länderfeld:** `ISO3` (Alpha‑3) → Mapping via `lookup_countries.csv`  
**Zeitraum:** 2014–2023 | **Skala:** 0–100 | **Granularität:** Jährlich

### 2.3 WGI (Worldwide Governance Indicators)

**Quelle:** World Bank (`wbgapi`, `db=3`)  
**Sechs Dimensionen:** `control_of_corruption`, `government_effectiveness`, `political_stability`, `rule_of_law`, `regulatory_quality`, `voice_accountability`  
**Skala:** ca. -2,5 bis +2,5 | **Granularität:** Jährlich

### 2.4 Länder-Mapping (`data/lookup/lookup_countries.csv`)

```csv
country_name,alpha_2,alpha_3,is_target
Germany,DE,DEU,true
Denmark,DK,DNK,true
Romania,RO,ROU,true
Hungary,HU,HUN,true
```

---

## 3. Red Flags – Finale Definitionen

| Flag | Name | Berechnung | NULL-Strategie | Status |
|------|------|-----------|---------------|--------|
| **F1** | Single-Bidder | `NUMBER_OFFERS == 1` | NULL → False | ✅ Kern (60,4 %) |
| **F2** | Estimate/Award Discrepancy | `VALUE_EURO / AWARD_VALUE_EURO > 10.0` | NULL → False | ✅ Kern (56,8 %) |
| **F3** | No Prior Call | `TOP_TYPE IN ('NIC', 'AWP')` | ~0,08 % NULL → False | ✅ Kern (99,9 %) |
| ~~F4~~ | ~~Accelerated Procedure~~ | — | — | 🔴 Gestrichen (99,16 % NULL) |
| **F5** | Award to Group | `B_AWARDED_TO_A_GROUP == 'Y'` | NULL → 'N'; 2014–2015 hard False | ⚠️ Teilweise (46,8 % ab 2016) |
| **F6** | Single-Bidder + High Value | `F1 AND AWARD_VALUE_EURO > per-year-p95` | NULL → False | ✅ Kern (57,1 %) |
| **F7** | Lot Fragmentation | `NUMBER_AWARDS < LOTS_NUMBER * 0.5` | NULL → False | ✅ Voll (96,2 %) |

### 3.2 Kombinationen

| Kombination | Logik | Aussage |
|-------------|-------|---------|
| `comb_single_discrepancy` | `F1 AND F2` | Einzelbieter + überhöhte Schätzung |
| `comb_single_non_open` | `F1 AND (TOP_TYPE != 'OPE')` | Einzelbieter in nicht-offenem Verfahren |
| `comb_no_call_high_value` | `F3 AND F6` | Direktvergabe ohne Aufruf, hoher Wert |
| `comb_frag_single` | `F7 AND F1` | Losfragmentierung + Einzelbieter |

---

## 4. Data Warehouse (Sternschema)

### 4.1 Faktentabelle: `fact_tender`

**Primärschlüssel:** `award_id` (natürlicher Schlüssel `ID_AWARD`, CORRECTIONS-aware Dedup).

| Spalte | Typ | Bedeutung |
|--------|-----|----------|
| `award_id` | VARCHAR(100) | Natürlicher PK (aus TED) |
| `id_notice_can` | VARCHAR(100) | Degenerierte Dimension (kein FK) |
| `id_lot` | VARCHAR(100) | Degenerierte Dimension (kein FK) |
| `year` | SMALLINT | Jahr (embedded — kein dim_time) |
| `crisis_type` | VARCHAR(50) | keine Krise / COVID-19 / Ukraine-Krieg |
| `country_key` | INTEGER | FK → dim_country (Auftraggeber-Land) |
| `winner_country_key` | INTEGER | FK → dim_country (Gewinner-Land, Role-Playing) |
| `cpv_key` | INTEGER | FK → dim_cpv |
| `procedure_key` | INTEGER | FK → dim_procedure_type |
| `award_value_eur` | DECIMAL(18,2) | Zuschlagswert (Sentinel €10T entfernt, kein Clipping) |
| `value_eur` | DECIMAL(18,2) | Geschätzter Wert (für F2) |
| `number_offers` | SMALLINT | Anzahl Angebote |
| `lots_number` | INTEGER | Anzahl Lose |
| `number_awards` | INTEGER | Anzahl Zuschläge |
| `F1` | BOOLEAN | Single-Bidder |
| `F2` | BOOLEAN | Estimate/Award Discrepancy (> 10.0) |
| `F3` | BOOLEAN | No Prior Call (NIC/AWP) |
| `F5` | BOOLEAN | Award to Group (ab 2016) |
| `F6` | BOOLEAN | Single-Bidder + High Value |
| `F7` | BOOLEAN | Lot Fragmentation |
| `comb_single_discrepancy` | BOOLEAN | F1 AND F2 |
| `comb_single_non_open` | BOOLEAN | F1 AND (TOP_TYPE != 'OPE') |
| `comb_no_call_high_value` | BOOLEAN | F3 AND F6 |
| `comb_frag_single` | BOOLEAN | F7 AND F1 |

> **F4 gestrichen** (99,16 % NULL). **Kein dim_time** (Exercise-Vorgabe: year + crisis_type direkt in fact). **Role-Playing:** dim_country wird zweimal referenziert.

### 4.2 Dimensionen

**dim_country** (SCD Type 2):
```
country_key (INTEGER IDENTITY, PK)
country_code (CHAR(2))    — DE, DK, RO, HU
country_name (VARCHAR(100))
cpi_score (SMALLINT)      — 0–100
control_of_corruption (DECIMAL(5,2))
government_effectiveness (DECIMAL(5,2))
political_stability (DECIMAL(5,2))
rule_of_law (DECIMAL(5,2))
regulatory_quality (DECIMAL(5,2))
voice_accountability (DECIMAL(5,2))
valid_from_year (SMALLINT)
valid_to_year (SMALLINT)
```

**dim_cpv:**
```
cpv_key (INTEGER IDENTITY, PK)
cpv_code (CHAR(8))        — z.B. "03110000"
cpv_division (VARCHAR(4)) — z.B. "03"
cpv_group (VARCHAR(4))    — z.B. "031"
cpv_class (VARCHAR(4))    — z.B. "0311"
```

**dim_procedure_type:**
```
procedure_key (INTEGER IDENTITY, PK)
procedure_code (VARCHAR(20))    — OPE, NIC, AWP, RES, …
procedure_name (VARCHAR(100))   — Open procedure, Negotiated w/o call, …
transparency_level (SMALLINT)   — 1 (niedrig) bis 5 (hoch)
is_open (BOOLEAN)
```

### 4.3 Joins

```sql
SELECT 
  ft.award_id,
  dc_a.country_code AS contracting_country,
  dc_w.country_code AS winner_country,
  ft.year,
  ft.crisis_type,
  dc_a.cpi_score,
  ft.award_value_euro,
  ft.F1,
  ft.F2,
  ft.comb_single_non_open
FROM fact_tender ft
JOIN dim_country dc_a ON ft.country_key = dc_a.country_key         -- Auftraggeber
JOIN dim_country dc_w ON ft.winner_country_key = dc_w.country_key  -- Gewinner
JOIN dim_cpv dcpv ON ft.cpv_key = dcpv.cpv_key
JOIN dim_procedure_type dpt ON ft.procedure_key = dpt.procedure_key
WHERE ft.year BETWEEN 2014 AND 2023
  AND dc_a.country_code IN ('DE', 'DK', 'HU', 'RO');
```

---

## 5. ETL-Pipeline – Implementierung

### 5.2 Transform-Phase

**TED-Pipeline (8 Schritte in [`run_cleanup.py`](src/processing/run_cleanup.py)):**

1. **Laden** — `utils.load_ted_csvs()` lädt per-year CSVs
2. **Länderfilter** — `clean_ted_filter_countries()` → DE, DK, RO, HU
3. **Dedup** — `clean_ted_dedup()` CORRECTIONS-aware
4. **Sentinel-Entfernung** — `clean_ted_remove_sentinels()` 62× exakt €10T → NaN; echte Werte bleiben
5. **Winner-Parse** — `clean_ted_parse_winner()` Multi-Value `WIN_COUNTRY_CODE`
6. **CPV-Normalisierung** — `clean_ted_normalize_cpv()` Zero-Pad auf 8 Digits
7. **Spaltenauswahl** — `clean_ted_select_columns()` auf 15 Kernspalten
8. **Red Flags** — `compute_red_flags()` F1–F3, F5–F7 + 4 Kombinationen

**CPI/WGI-Pipelines:** Laden → clean → export (kürzer als TED).

**Ausgabe:** Drei Parquet-Dateien:
- `data/processed/ted/ted_clean.parquet` (~28 MB)
- `data/processed/cpi/cpi_clean.parquet` (~2,5 KB)
- `data/processed/wgi/wgi_clean.parquet` (~7,8 KB)

**Aufruf:**
```bash
python -m src.processing.run_cleanup
python -m src.processing.run_cleanup --years 2020 2021 2022 --log-level DEBUG
```

---

## 6. Analyse-Queries (mehrdimensional)

**Query 1: Single-Bidder-Rate pro Land & Jahr**
```sql
SELECT 
  dc.country_code,
  ft.year,
  COUNT(*) AS total,
  SUM(CAST(ft.F1 AS INT)) AS single_bidder,
  ROUND(100.0 * SUM(CAST(ft.F1 AS INT)) / COUNT(*), 2) AS sb_pct
FROM fact_tender ft
JOIN dim_country dc ON ft.country_key = dc.country_key
WHERE ft.year BETWEEN 2014 AND 2023
GROUP BY dc.country_code, ft.year
ORDER BY dc.country_code, ft.year;
```

**Query 2: Gewinner-Land ≠ Auftraggeber-Land (Cross-Border)**
```sql
SELECT 
  dc_a.country_code AS contracting,
  dc_w.country_code AS winner,
  COUNT(*) AS awards
FROM fact_tender ft
JOIN dim_country dc_a ON ft.country_key = dc_a.country_key
JOIN dim_country dc_w ON ft.winner_country_key = dc_w.country_key
WHERE dc_a.country_code != dc_w.country_code
GROUP BY dc_a.country_code, dc_w.country_code
ORDER BY awards DESC;
```

**Query 3: Korrelation CPI mit Single-Bidder-Rate**
```sql
SELECT 
  dc.country_code,
  dc.cpi_score,
  ft.year,
  ROUND(100.0 * SUM(CAST(ft.F1 AS INT)) / COUNT(*), 2) AS sb_pct,
  ROUND(100.0 * SUM(CAST(ft.F3 AS INT)) / COUNT(*), 2) AS nopc_pct
FROM fact_tender ft
JOIN dim_country dc ON ft.country_key = dc.country_key
GROUP BY dc.country_code, ft.year
ORDER BY dc.country_code, ft.year;
```

---

## 7. Performance & Optimierungen

### 7.1 Datenbank-Indizes

```sql
CREATE INDEX idx_fact_country ON fact_tender(country_key);
CREATE INDEX idx_fact_winner_country ON fact_tender(winner_country_key);
CREATE INDEX idx_fact_year ON fact_tender(year);
CREATE INDEX idx_fact_cpv ON fact_tender(cpv_key);
CREATE INDEX idx_fact_procedure ON fact_tender(procedure_key);
CREATE INDEX idx_fact_flags ON fact_tender(F1, F2, F3);
CREATE INDEX idx_country_code ON dim_country(country_code);
CREATE INDEX idx_cpv_code ON dim_cpv(cpv_code);
```

### 7.2 Speichermanagement

Die TED-Pipeline verarbeitet ~2,2 Mio. Zeilen über 8 Clean-Schritte. `del` + `gc.collect()` zwischen jedem Schritt hält den Memory-Peak bei ~3–4 GB statt ~7 GB.

---

## 8. Logging & Fehlerbehandlung

**Log-Pfade:** `logs/application.log`, `logs/run_cleanup.log`  
**Retry-Logik:** `requests.Session` mit `Retry`-Adapter (3 Versuche, exponentielles Backoff)  
**Fehlende Dateien:** Werden übersprungen (Log-Warnung), Pipeline läuft weiter

---

## 9. Auslieferung

```bash
# 1. Rohdaten herunterladen
python src/download_data.py

# 2. ETL-Cleanup-Pipeline
python -m src.processing.run_cleanup

# 3. Mit Optionen
python -m src.processing.run_cleanup --years 2020 2021 2022 --log-level DEBUG
```

---

## 10. Deep-Dive Analyse-Ergebnisse

| Entscheidung | Empfehlung | Begründung |
|-------------|-----------|-----------|
| **Fact Primary Key** | `ID_AWARD` mit CORRECTIONS-aware Dedup | `ID_LOT` 2014 zu 100% NULL |
| **Sentinel-Entfernung** | €1T Threshold (fängt exakt €10T) | 62 Zeilen, alle DE 2016–2017; kein Clipping |
| **WIN_COUNTRY_CODE** | "Any segment match" | 98,63 % Coverage bei Multi-Value |
| **F4 (B_ACCELERATED)** | **DROP** | 99,16 % NULL |
| **F5 (Group Award)** | Behalten, 2014–2015 ausschließen | 0 % in 2014, ab 2016 ~46–62 % verfügbar |

---

## 11. Erweiterungspunkte

1. **Exasol-Migration**: Parquet → echte DB-Verbindung
2. **Dimension Builder**: `build_dim_country.py`, `build_dim_cpv.py` etc.
3. **Airflow-Automatisierung**: Tägliche/wöchentliche Läufe
4. **Dashboard**: Tableau/PowerBI für Live-Analysen

---

*Stand: 2026-05-19 (nach Audit-Fixes)*
