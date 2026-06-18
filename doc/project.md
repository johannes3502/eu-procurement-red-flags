# Mehrdimensionale Analyse von Auffälligkeiten in EU-Vergabedaten (TED) mit externen Governance‑Scores (CPI/WGI) – Ein Data‑Warehouse‑Ansatz

**Data-Warehouse-Projekt Sommersemester 2026**
**Autor:** Johannes, OTH Regensburg

---

## 1. Beschreibung

Öffentliche Aufträge machen rund **14 % des EU-Bruttoinlandsprodukts** aus – Steuergelder in enormem Umfang.
Potenzielle Auffälligkeiten („Red Flags“) wie Einzelbieterverfahren, nicht-offene Verfahren oder Direktvergaben ohne Vorankündigung sind oft über verschiedene Quellen verstreut.

Dieses Projekt integriert **EU-Vergabedaten (TED)** aus zehn Jahren (2014–2023) für vier ausgewählte Länder und reichert sie mit externen **Governance-Scores (CPI, WGI)** an.
In einem **Data Warehouse (Sternschema)** werden die Daten mehrdimensional analysiert, um Zusammenhänge zwischen Red Flags und Governance-Qualität aufzudecken.

---

## 2. Relevanz

- **Transparenz & Rechenschaft:** Vergabestellen, Rechnungshöfe und Journalisten erhalten ein datengestütztes Frühwarnsystem für wettbewerbsbeschränkende Praktiken.
- **Krisenforschung:** Zeigt, wie Pandemie oder geopolitische Ereignisse die Integrität öffentlicher Vergabe beeinflussen.
- **Governance-Forschung:** Überprüft empirisch den Zusammenhang zwischen wahrgenommener Korruption (CPI) / Governance (WGI) und tatsächlichen Vergabeauffälligkeiten.

---

## 3. Hauptdatenquelle: TED (Tenders Electronic Daily)

- **Inhalt:** Alle EU-weit ausgeschriebenen öffentlichen Aufträge oberhalb der Schwellenwerte.
- **Zugang:** Kostenloser CSV-Bulk-Download pro Jahr, CC BY 4.0.
- **Zeitraum:** 2014–2023 (10 Jahre).
- **Länderfilter:** Deutschland (DE), Dänemark (DK), Rumänien (RO), Ungarn (HU).
- **Wichtige Felder:**
  - `ID_NOTICE_CAN` (Bekanntmachungs-ID)
  - `ID_LOT` (Los-Nummer)
  - `WIN_COUNTRY_CODE` (ISO Alpha‑2, z. T. mehrwertig mit `---`-Separator)
  - `TOP_TYPE` (Verfahrenstyp: OPE = offen, NIC/AWP = ohne Aufruf)
  - `NUMBER_OFFERS` (Anzahl Bieter)
  - `AWARD_VALUE_EURO` (Zuschlagswert)
  - `VALUE_EURO` (geschätzter Wert)
  - `B_ACCELERATED` (99,16 % NULL → in Analyse gestrichen), `B_AWARDED_TO_A_GROUP`, `CPV`

---

## 4. Datenformat und Zugang

- **TED:** ZIP-Archiv mit CSV pro Jahr → automatisierter Download über Python (requests, ZIP-Streaming).
- **CPI:** Direkter CSV-Download (HDX). ISO‑3-Länderkennung, jährlich.
- **WGI:** Abruf über Weltbank-API (Python-Library `wbgapi`). Sechs Governance-Dimensionen, jährlich, numerische Länderkennung.

Alle Quellen werden vollautomatisch durch das Skript `src/download_data.py` bezogen und im Rohformat unter `data/raw/` abgelegt.

---

## 5. Schema (Entitätstypen und Hauptattribute)

### 5.1 Rohdaten-Entität: `TED_Tender`
| Attribut | Typ | Beschreibung |
|----------|-----|-------------|
| `notice_id` | String | Eindeutige Bekanntmachungs-ID |
| `lot_id` | String | Los-Identifikation |
| `country_code` | String(2) | Land des Auftragnehmers (ISO Alpha‑2) |
| `year` | Integer | Jahr der Zuschlagserteilung |
| `procedure_type` | String | TOP_TYPE (OPE, NIC, AWP, …) |
| `number_offers` | Integer | Anzahl eingegangener Angebote |
| `award_value_eur` | Decimal | Zuschlagswert in Euro (Sentinel €10T entfernt, kein Clipping) |
| `estimated_value_eur` | Decimal | Geschätzter Auftragswert |
| `~~is_accelerated~~` | ~~Boolean~~ | ~~Beschleunigtes Verfahren~~ – **GESTRICHEN** (99,16 % NULL, nicht in Pipeline enthalten) |
| `is_awarded_to_group` | Boolean | Zuschlag an Bietergemeinschaft |
| `cpv_code` | String | Common Procurement Vocabulary |

Die Daten werden in der Transform-Phase um **Red-Flag-Indikatoren** und **Kombinationen** erweitert (siehe Abschnitt 9).

### 5.2 Governance-Stammdaten (CPI + WGI)
- **CPI:** `country_iso3`, `year`, `cpi_score` (0–100) – 0 % missing
- **WGI:** `country_iso3`, `year`, sechs Governance-Dimensionen – 0 % missing

Nach Mapping auf ISO Alpha‑2 und Integration in die Länderdimension werden sie als zeitabhängige Attribute geführt (SCD Type 2).

---

## 6. Zusätzliche Datenquellen und ihre Nützlichkeit

| Quelle | Warum integriert? |
|--------|------------------|
| **CPI** | Misst wahrgenommene Korruption. Ermöglicht Korrelationsanalysen: *„Je niedriger der CPI, desto höher die Single-Bidder-Quote?“* |
| **WGI** | Erfasst sechs Governance-Dimensionen (z. B. Regulierungsqualität, Rechtsstaatlichkeit). Zeigt differenzierte Muster: *„Hängt eine hohe Non-Open-Rate mit schwacher Regulierungsqualität zusammen?“* |

---

## 7. Größe (aktualisiert durch Profiling und Exasol-Load)

- **TED global:** ~8,5 Mio. Zeilen
- **TED (4 Länder, 2014–2023):** **2.207.161 Zeilen** (DE, DK, RO, HU) – exakt quantifiziert
- **Nach Dedup** (ID_AWARD als PK, CORRECTIONS-aware): Reduktion um 2–38 % je Jahr
- **Nach ETL (25 Spalten inkl. Red Flags):** **1.784.558 Zeilen** geladen in Exasol, **28,42 MB** (ted_clean.parquet)
- **CPI + WGI:** je 40 Zeilen (< 1 MB), 0 % missing
- **Gesamtschema in Exasol:** **28,43 MB** (Parquet-Quelle), davon 1.784.558 Zeilen in `stg_ted`

---

## 8. Dimensionen

| Fragewort | Dimension | Beschreibung |
|-----------|-----------|--------------|
| **When?** | Zeit | Jahr (SMALLINT), Quartal, Monat. **Krisenattribut:** `crisis_type` (keine Krise / COVID‑19 / Ukraine‑Krieg). |
| **Where?** | Land | Land des Zuschlagsempfängers (DE, DK, RO, HU). Inklusive **zeitabhängiger Governance-Scores** als beschreibende Attribute (SCD Type 2 über `valid_from_year`/`valid_to_year`). |
| **What?** | CPV‑Warengruppe | Klassifikation der Leistung, zero-padded 8‑stellig, mit Hierarchie: Division (2) → Group (3) → Class (4) → Code (8). |
| **How?** | Verfahrenstyp | `TOP_TYPE`-Code + deskriptiver Name + `transparency_level` (INT, 1–5). |

Die Governance-Scores sind **keine eigene Dimension**, sondern Attribute der Länderdimension – sie beschreiben die Governance-Qualität eines Landes zu einem bestimmten Jahr.

---

## 9. Red Flags und Kombinationen — Finale, datengestützte Definitionen

### 9.1 Einzelindikatoren (7 Red Flags → 5+1 nutzbar)

| # | Red Flag | Finale Berechnung | Coverage | Status |
|---|----------|-------------------|----------|--------|
| **F1** | **Single-Bidder** | `NUMBER_OFFERS == 1`, NULL → 0 | 60,4 % | ✅ **Kern‑Flag** |
| **F2** | **Estimate/Award Discrepancy** | `VALUE_EURO / AWARD_VALUE_EURO > 10.0`, NULL → 0 | 56,8 % | ✅ **Kern‑Flag** – Schwellwert 10.0 (Median 8,06; 2.0 wäre unbrauchbar) |
| **F3** | **No Prior Call** | `TOP_TYPE IN ('NIC', 'AWP')`, ~0,08 % NULL | 99,9 % | ✅ **Kern‑Flag** |
| ~~F4~~ | ~~Accelerated Procedure~~ | ~~`B_ACCELERATED == 'Y'`~~ | — | 🔴 **GESTRICHEN** – 99,16 % NULL |
| **F5** | **Award to Group** | `B_AWARDED_TO_A_GROUP == 'Y'`; NULL → `'N'`; ab 2016 nutzbar | 46,8 % (2016+) | ⚠️ **Teilweise** – 2014–2015 ausgeschlossen |
| **F6** | **Single-Bidder + High Value** | `NUMBER_OFFERS == 1 AND AWARD_VALUE_EURO > per‑year‑p95`; NULL → 0 | 57,1 % | ✅ **Kern‑Flag** – p95 per year, `<= 2` verworfen |
| **F7** | **Lot Fragmentation** | `NUMBER_AWARDS < LOTS_NUMBER * 0.5`; NULL → 0 | 96,2 % | ✅ **Voll nutzbar** |

**Wichtige Änderungen gegenüber dem ursprünglichen Konzept:**
- **F2** wurde von „Non-Open Procedure“ (`TOP_TYPE != "OPE"`) in „Estimate/Award Discrepancy“ (`VALUE_EURO / AWARD_VALUE_EURO > 10.0`) umdefiniert – datengestützt aus der Deep‑Dive‑Analyse. Ein Schwellwert von 2.0 hätte ~70–75 % aller Zeilen als auffällig markiert (Median VALUE/AWARD = 8,06).
- **F3** (`TOP_TYPE IN ('NIC', 'AWP')`) bleibt unverändert. Der fehlerhafte Wert `'DIRECT'` aus der Analyse-Dokumentation wurde korrigiert.
- **F4** ist gestrichen: 99,16 % NULL, selbst in den besten Jahren <1 % non‑NULL.
- **F5** nutzbar ab 2016 (2014–2015: 0 % und 0,04 % non‑NULL).
- **F6** verwendet `== 1` (nicht `<= 2`): die zusätzlichen ~2,2 % Zeilen mit genau 2 Bietern signalisieren keinen vollständig ausgeschalteten Wettbewerb. Per‑year‑p95 statt globalem p75.
- **F7** wurde von der Regel „> 5 Lose pro Bekanntmachung“ auf die feinere Metrik `NUMBER_AWARDS < LOTS_NUMBER * 0.5` umgestellt (1,03 % der Zeilen als hoch fragmentiert erkannt).

### 9.2 Mehrdimensionale Kombinationen

| Combo | Logik | Aussage |
|-------|-------|---------|
| `comb_single_discrepancy` | `F1 AND F2` | Einzelbieter + extrem überhöhte Schätzung → Schätzung diente evtl. zur Wettbewerbsabschreckung |
| `comb_single_non_open` | `F1 AND (TOP_TYPE != 'OPE')` | Einzelbieter in nicht-offenem Verfahren – direkt aus TOP_TYPE abgeleitet, nicht aus F2 (F2 ist jetzt Discrepancy) |
| `comb_no_call_high_value` | `F3 AND F6` | Direktvergabe ohne Aufruf bei sehr hohem Wert und nur einem Bieter |
| `comb_frag_single` | `F7 AND F1` | Viele Lose, nur ein Bieter → Lose evtl. auf diesen Bieter zugeschnitten |

**Hinweise:**
- Die ursprüngliche Kombination „Accelerated + Non-Open + Single-Bidder“ ist entfallen (F4 gestrichen).
- `comb_single_non_open` verwendet `TOP_TYPE != 'OPE'` direkt (nicht F2), da F2 von „Non-Open Procedure“ auf „Estimate/Award Discrepancy“ umdefiniert wurde.

---

## 10. Typische Queries (natürlichsprachig)

1. *„Wie entwickelte sich die Single-Bidder-Quote in den vier Ländern im Vergleich zum CPI‑Trend über die Jahre 2014–2023?“*
2. *„Welche CPV‑Hauptgruppen zeigten in Ungarn die höchste Rate an Estimate/Award Discrepancies (F2) mit überhöhten Schätzungen?“*
3. *„Vergleiche die Häufigkeit der Kombination ‚No Prior Call + Single-Bidder High Value‘ vor und während der COVID‑19‑Pandemie in Rumänien und Deutschland.“*
4. *„Gibt es einen Zusammenhang zwischen der Fragmentierungsrate (Flag 7) und dem WGI‑Wert für ‚Regulatory Quality‘ auf Länderebene?“*
5. *„Zeigen Länder mit niedrigerem CPI eine höhere Rate an Estimate/Award Discrepancy (F2 > 10,0)?“*

---

## 11. Datenmodell (Sternschema)

```text
                    ┌───────────────────┐
                    │    dim_country    │
                    ├───────────────────┤
                    │ country_key       │◄──────────────────┐
                    │ country_code      │                   │
                    │ country_name      │                   │
                    │ cpi_score         │                   │
                    │ wgi_* (6×)        │                   │
                    │ valid_from_year   │                   │
                    │ valid_to_year     │                   │
                    └───────────────────┘                   │
                                                            │
┌──────────────┐    ┌────────────────────────┐    ┌──────────────────┐
│  dim_cpv     │    │      fact_tender       │    │ dim_procedure_type│
├──────────────┤    ├────────────────────────┤    ├──────────────────┤
│ cpv_key      │◄───┤ cpv_key (FK)           │    │ procedure_key    │
│ cpv_code     │    │ procedure_key (FK)     │───►│ procedure_code   │
│ cpv_division │    ├────────────────────────┤    │ procedure_name   │
│ cpv_group    │    │ award_id (PK)          │    │ transparency_lvl │
│ cpv_class    │    │ id_notice_can (deg.)   │    │ is_open          │
└──────────────┘    │ id_lot (deg.)          │    └──────────────────┘
                    │ country_key (FK)       │──┐  (Auftraggeber)
                    │ winner_country_key (FK)│──┤  (Gewinner)
                    │ year (SMALLINT)        │  │
                    │ crisis_type (VARCHAR)  │  │
                    │ award_value_eur        │  │
                    │ value_eur              │  │
                    │ number_offers          │  │
                    │ lots_number            │  │
                    │ number_awards          │  │
                    │ F1, F2, F3, F5–F7      │  │
                    │ comb_* (4×)            │  │
                    └────────────────────────┘  │
                                                │
                    ┌───────────────────────────┘
                    ▼
              dim_country (Role-Playing)
```

- **Faktentabelle:** `fact_tender` – ein Eintrag pro **ID_AWARD** (nach CORRECTIONS-aware Dedup). `ID_NOTICE_CAN` und `ID_LOT` als **degenerierte Dimensionen**.
- **Dimensionen:** Kein `dim_time` (Exercise-Vorgabe: Jahr + crisis_type direkt in fact), Land (SCD Type 2 mit CPI/WGI), CPV (mit Hierarchie), Verfahrenstyp.
- **Role-Playing:** `dim_country` wird zweimal referenziert: `country_key` = Auftraggeber-Land (`ISO_COUNTRY_CODE`), `winner_country_key` = Gewinner-Land (geparst aus `WIN_COUNTRY_CODE`).
- **Red Flags:** 6 Flags (F1–F3, F5–F7) + 4 Kombinationen. F4 gestrichen.
- **AWARD_VALUE_EURO:** Nur Sentinel-Entfernung (62 Zeilen mit exakt €10T → NaN). Kein Clipping — echte Auftragswerte bleiben unverändert.

**Snowflake-Erweiterung (optional):**
Das Sternschema kann durch Auslagerung der CPV‑Hierarchie (Division → Group → Class) oder eine separate Governance-Tabelle in ein **Snowflake-Schema** überführt werden. Für die geplanten Analysen bietet das Sternschema jedoch ausreichend Performance und bleibt einfacher wartbar.

---

## 12. Krisen-Dimension

- **Attribut in `fact_tender`:** `crisis_type` mit den Ausprägungen `'keine Krise'` (2014–2019), `'COVID-19'` (2020–2021), `'Ukraine-Krieg'` (2022–2023). Keine separate `dim_time`-Tabelle (Exercise-Vorgabe); `year` und `crisis_type` sind direkt in die Faktentabelle eingebettet.
- Die Zuordnung erfolgt **jahresweise**; das ist hinreichend genau, da auch die Governance-Scores nur jährlich vorliegen und die Analysen auf Jahresaggregate abzielen.
- Bei Bedarf kann die Granularität später auf Monate verfeinert werden.

---

## 13. Limitationen

- **Nur EU-Schwellenwerte:** Kleinere Aufträge unterhalb der EU-Schwellenwerte fehlen.
- **Jährliche Governance-Scores:** CPI und WGI sind nicht unterjährig verfügbar, daher können saisonale Muster nicht mit Governance korreliert werden.
- **Keine Kausalität:** Statistische Zusammenhänge erlauben keine Aussagen über Ursache und Wirkung.
- **Datenqualität TED:** In **64,83 %** der vergleichbaren Zeilen liegt der geschätzte Wert (`VALUE_EURO`) über dem Zuschlagswert (`AWARD_VALUE_EURO`) – ein erwartbares Muster (Schätzung vor Vergabe, Zuschlag darunter). `AWARD_VALUE_EURO` wird als die autoritative Metrik verwendet.
- **Red-Flag-Coverage:** Nur ca. 46 % der Zeilen können alle 6 nutzbaren Flags berechnen; dies ist durch NULL‑Raten in `NUMBER_OFFERS` (39,6 %) und `AWARD_VALUE_EURO` (42,6 %) bedingt.
- **ID_LOT:** 100 % NULL in 2014 – der komposite Schlüssel `(ID_NOTICE_CAN, ID_LOT)` ist über den gesamten Zeitraum nicht nutzbar.

---

## 14. Zeitungs-Schlagzeile

> *„Forscher der OTH Regensburg decken auf: In EU-Staaten mit schwacher Governance ist die Quote intransparenter Direktvergaben dreimal so hoch – Pandemiejahre verstärken den Effekt.“*

---

## 15. Persönlicher Bezug

Öffentliche Vergabe ist die zentrale Schnittstelle zwischen Staat und Privatwirtschaft. Mich fasziniert die Frage, wie sich institutionelle Rahmenbedingungen (gemessen durch CPI/WGI) in alltäglichen Vergabevorgängen niederschlagen – und ob Krisen Governance-Schwächen sichtbarer machen. Die Arbeit mit realen, offenen Daten gibt mir die Chance, dieses Spannungsfeld datenbasiert zu erkunden.

---

## 16. Durchgeführte Analysen & Implementierung

| Analyse / Modul | Datei(en) | Ergebnis |
|---------|-----------|----------|
| Data Profiling (Datenqualität) | `src/processing/profiling/profile_raw_data.py` | NULL-Raten, Wertebereiche, Spaltenabdeckung pro Jahr |
| Deep‑Dive 1: Dedup & Granularität | `profiling/analysis_1_dedup.py` | **ID_AWARD als Fact-PK**; CORRECTIONS-aware Dedup-Strategie |
| Deep‑Dive 2: Extreme Geldwerte | `profiling/analysis_2_monetary.py` | Sentinel-Entfernung (€10 B.), kein Clipping — echte Werte unverändert |
| Deep‑Dive 3: WIN_COUNTRY_CODE | `profiling/analysis_3_country_codes.py` | **Any‑Segment‑Parser** für 88.744 mehrwertige Codes (98,63 % Coverage) |
| Deep‑Dive 4: Red‑Flag‑Machbarkeit | `profiling/analysis_4_red_flags.py` | **F4 gestrichen**, F5 ab 2016, F6 mit per‑year‑p95 |
| Schwachstellenanalyse | manuell (Architekt) | **F2 10.0**, **F3 NIC/AWP**, **F6 ==1** final verifiziert |
| Data Preparation Plan | `plans/data-preparation-for-warehouse.md` | Vollständige ETL-Spezifikation mit allen Regeln |
| **ETL‑Config** (zentrale Konstanten) | `src/processing/config.py` | Pfade, Thresholds, Spaltenlisten, Exasol-Type-Map |
| **Shared‑Utilities** (Wiederverwendbare Helfer) | `src/processing/utils.py` | Country-Lookup, TED-CSV-Loader, p95, Parquet-Export, CSV-Export, Step-Logging |
| **Cleanup‑Modul TED** | `src/processing/ted/clean.py` | 7 clean_ted_*() + compute_red_flags() |
| **Cleanup‑Modul CPI** | `src/processing/cpi/clean.py` | clean_cpi() |
| **Cleanup‑Modul WGI** | `src/processing/wgi/clean.py` | clean_wgi() |
| **Orchestrierung** (alle Datensätze) | `src/processing/run_cleanup.py` | CLI‑Pipeline: --years, --ted-input-dir, --cpi-input, --wgi-input, --output-dir. Produziert Parquet + CSV |

Alle Ergebnisse sind konsolidiert in [`doc/profiling/analysis/analysis_results.md`](red-flags-procurement-governance/doc/profiling/analysis/analysis_results.md).

---

## 17. Aktueller Projektstatus

| Bereich | Status |
|--------|--------|
| Konzept & Design | ✅ Abgeschlossen |
| Automatisierter Daten-Download (TED/CPI/WGI) | ✅ Abgeschlossen |
| Data Profiling (Datenqualitätsanalyse) | ✅ Abgeschlossen |
| 4 Deep‑Dive‑Analysen (Dedup, Monetary, Country, Flags) | ✅ Abgeschlossen |
| Red‑Flag‑Definitionen (final, datengestützt) | ✅ Abgeschlossen |
| Data Preparation Plan (vollständige ETL-Spezifikation) | ✅ Abgeschlossen |
| **ETL‑Core** (`config.py` + `utils.py` + `ted/clean.py` + `cpi/clean.py` + `wgi/clean.py` + `run_cleanup.py`) | ✅ Abgeschlossen — `run_cleanup.py` produziert Parquet + CSV |
| **Exasol DDL + Automation** (`setup_and_load.py` — DDL, Parquet-Load via `import_from_pandas()`, INSERTs, Verify) | ✅ Abgeschlossen — alle 7 Tabellen erstellt, 1.784.558 TED-Zeilen + CPI/WGI geladen, 2 Beispielzeilen pro Star-Schema-Tabelle |
| **Nativer IMPORT FROM LOCAL CSV (Challenge 3)** | ✅ Abgeschlossen — `import_staging.sql` enthält die nativen IMPORT-Statements; ausgeführt in DBeaver, 1,784,558 + 40 + 40 Zeilen geladen, `error_tbl` enthält 0 Fehler |
| **Data Quality & Entity Matching (Challenge 4)** | ✅ Abgeschlossen — `data_quality_checks.sql`: error_info-Spalten, Duplikaterkennung, Sentinel-Entfernung, Entity-Matching (Equal/Levenshtein/Soundex), FP/FN-Analyse |
| **MERGE & Data Integration (Challenge 4)** | ✅ Abgeschlossen — `merge_dimensions.sql`: MERGE dim_procedure_type + dim_cpv, SCD Type 2 dim_country (INSERT+UPDATE), INSERT fact_tender mit Role-Playing-Join |
| **Analytical Queries (Challenge 4)** | ✅ Abgeschlossen — `analytical_queries.sql`: 7 Queries (ROLLUP, Window AVG, RANK, CORR/STDDEV_POP, Skyline PREFERRING, Krisenvergleich, Lot-Fragmentierung) |
| **Workbook Challenge 4** | ✅ Abgeschlossen — `exercises/Challenge4.md` vollständig ausgefüllt (Name, Titel, 5 Data-Transformation-Antworten, MERGE-Kommando, 7 Queries) |
| SQL-Ausführung auf Exasol | 📋 Ausstehend — Skripte müssen in DBeaver auf dem Uni-VPN-Exasol ausgeführt werden |

**Nächste Schritte:**
- SQL-Skripte in DBeaver auf Uni-VPN-Exasol ausführen (data_quality_checks → merge_dimensions → analytical_queries)
- Workbook → PDF exportieren und via ELO einreichen
- ggf. Visualisierung in Tableau/Power BI/Superset

---

*Stand: Juni 2026 (vierte Revision)*
*Challenge 4 abgeschlossen — Data Quality Checks, MERGE/SCD2-Integration, 7 analytische Queries (ROLLUP, Window, RANK, CORR/STDDEV, Skyline, Krisenvergleich, Fragmentierung). SQL-Skripte bereit zur Ausführung in DBeaver auf Uni-VPN-Exasol.*