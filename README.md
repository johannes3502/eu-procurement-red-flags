# Red Flags in EU-Vergabedaten & Governance-Qualität

**Ein Data-Warehouse-Projekt zur mehrdimensionalen Analyse von Auffälligkeiten in öffentlichen Ausschreibungen**

![Status](https://img.shields.io/badge/status-in%20development-blue)
![Python](https://img.shields.io/badge/python-3.9%2B-green)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## 📋 Überblick

Dieses Projekt analysiert **Auffälligkeiten in EU-Vergabedaten (TED)** und korreliert sie mit **Governance-Qualitätsindikatoren** (CPI, WGI) für vier europäische Länder über den Zeitraum 2014–2023.

### Das Problem
Öffentliche Aufträge machen rund **14% des EU-BIP** aus – Steuergeld in enormem Ausmaß. Potenzielle Red Flags wie:
- **Einzelbieter-Verfahren** (mangelnder Wettbewerb)
- **Nicht-offene Verfahren** (geringe Transparenz)
- **Direktvergaben ohne Vorankündigung** (hohes Korruptionsrisiko)

...sind oft dezentral verstreut. Ziel dieses Projekts: **Zentrale Analyse mit externen Governance-Scores** → Frühwarnsystem für Prüfbehörden.

### Der Ansatz
**Data Warehouse mit Sternschema:**
- **Faktentabelle**: TED-Vergabevorgänge mit 8 definierten Red Flags
- **Dimensionen**: Zeit (inkl. Krisen), Land, Warengruppe, Verfahrenstyp, Governance-Scores
- **Mehrdimensionale Queries**: Korrelation zwischen Red Flags und Governance-Qualität

### Länder & Zeitraum
| Land | Kategorie | CPI-Bereich |
|------|-----------|------------|
| 🇩🇰 **Dänemark (DK)** | Positivkontrolle | ~90 (sehr sauber) |
| 🇩🇪 **Deutschland (DE)** | Benchmark (Mitte) | ~75 |
| 🇷🇴 **Rumänien (RO)** | Dauerhaft niedrig | ~45 |
| 🇭🇺 **Ungarn (HU)** | Fallend | 55 → 40 |

**Zeitraum:** 2014–2023 (10 Jahre), mit **Krisen-Dimensionen:**
- 2014–2019: Keine Krise
- 2020–2021: COVID-19-Pandemie
- 2022–2023: Ukraine-Krieg

---

## 🎯 Die 8 Red Flags

| # | Name | Beschreibung | Risikolevel |
|---|------|-----------|-----------|
| **1** | Single-Bidder | Nur ein Bieter eingegangen | 🔴 **KERN** |
| **2** | Non-Open Procedure | Nicht-offenes Verfahren (z.B. Verhandlung) | 🔴 **KERN** |
| **3** | No Prior Call | Direktvergabe ohne Vorankündigung | 🔴 **KERN** |
| 4 | Accelerated Procedure | Beschleunigtes Verfahren | 🟠 Explorativ |
| 5 | Award to Group | Zuschlag an Bietergemeinschaft | 🟠 Explorativ |
| 6 | High Value/Low Bidders | Hoher Wert + ≤2 Bieter | 🟠 Explorativ |
| 7 | Tax Haven Winner | Gewinner aus Steueroase | 🟠 Explorativ |
| **8** | High Lot Fragmentation | >5 Lose pro Ausschreibung | 🔴 **KERN** |

**Multidimensionale Kombinationen:**
- Single-Bidder + Non-Open Procedure
- No Prior Call + High Value/Low Bidders
- Accelerated + Non-Open + Single-Bidder (Trias)
- High Lot Fragmentation + Single-Bidder

---

## 🚀 Quick Start

### 1. Projekt klonen & ins Verzeichnis wechseln

```bash
git clone https://github.com/YOUR_REPO/red-flags-procurement-governance.git
cd red-flags-procurement-governance
```

### 2. Virtuelle Umgebung erstellen & aktivieren

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell/CMD):**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Abhängigkeiten installieren

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**requirements.txt Inhalt:**
```txt
pandas>=1.3.0
numpy>=1.20.0
requests>=2.25.0
python-pptx>=0.6.20
matplotlib>=3.4.0
openpyxl>=3.6.0
wbgapi>=2.0.0
```

### 4. Daten herunterladen

Das Projekt enthält ein **automatisiertes Download-Skript**, das alle Rohdaten
selbstständig von den Quellen bezieht:

```bash
python src/download_data.py
```

**Was das Skript macht:**

| Schritt | Quelle | Ziel |
|---------|--------|------|
| 1 | TED (Tenders Electronic Daily) | `data/raw/ted/ted_<YYYY>.csv` für 2014–2023 |
| 2 | CPI (Corruption Perceptions Index) | `data/raw/cpi/cpi_raw.csv` |
| 3 | WGI (Worldwide Governance Indicators) | `data/raw/wgi/wgi_raw.csv` |

- Bereits vorhandene Dateien werden **übersprungen** (außer mit `--force`).
- Bei Download-Fehlern läuft das Skript weiter und gibt am Ende eine
  Zusammenfassung aus.
- Alle Schritte werden in `logs/download_data.log` und auf der Konsole protokolliert.

**Erzwingen eines kompletten Neu-Downloads:**

```bash
python src/download_data.py --force
```

**Für die ersten Tests:** Ein Beispiel-TED-Jahr 2022 liegt vor unter `data/raw/ted/2022.csv`


### 5. ETL-Cleanup-Pipeline ausführen

Nach dem Download bereinigt die Pipeline alle Rohdaten, wendet die Red-Flag-Logik an, und exportiert das Ergebnis als **Parquet-Dateien** in `data/processed/`:

```bash
# Vollständige Pipeline (TED + CPI + WGI)
python -m src.processing.run_cleanup

# Nur bestimmte Jahre
python -m src.processing.run_cleanup --years 2020 2021 2022

# Mit Debug-Logging
python -m src.processing.run_cleanup --log-level DEBUG
```

**Was passiert dabei?**

| Schritt | Dataset | Funktion | Output |
|---------|---------|----------|--------|
| 1 | **TED** | `ted/clean.py` — 7 Reinigungsschritte + Red Flags | `data/processed/ted/ted_clean.parquet` |
| 2 | **CPI** | `cpi/clean.py` — Filter auf Ziel-Länder + Umbenennung | `data/processed/cpi/cpi_clean.parquet` |
| 3 | **WGI** | `wgi/clean.py` — Filter auf Ziel-Länder + Spaltenauswahl | `data/processed/wgi/wgi_clean.parquet` |

Alle Logs landen in `logs/run_cleanup.log`.

---

## 📁 Projektstruktur

```
red-flags-procurement-governance/
├── README.md                     # 👈 DU BIST HIER – Benutzerhandbuch
├── doc/                          # 📚 Dokumentation
│   ├── project.md                # Projektkonzept
│   ├── doc.md                    # Technische Dokumentation
│   ├── profiling/                # 📊 Data Profiling Reports (auto-generiert)
│   └── ...
│
├── src/                          # Quellcode
│   ├── download_data.py          # 📥 Automatisierter Rohdaten-Download (TED/CPI/WGI)
│   ├── test_redflags.py          # ✅ Red-Flag-Prototyp
│   ├── acquisition/              # 📥 Datenquellen-Module
│   │   ├── ted/download.py
│   │   ├── cpi/download.py
│   │   └── wgi/download.py
│   ├── processing/               # 🔄 ETL-Transform
│   │   ├── config.py             # Pfade, Thresholds, Spaltenlisten
│   │   ├── utils.py              # Shared: Country-Lookup, TED-Loader, p95, Export
│   │   ├── run_cleanup.py        # CLI-Orchestrierung (──years,──ted-input-dir, …)
│   │   ├── ted/clean.py          # TED-spezifisch: clean_ted_*() (7 Fns) + compute_red_flags()
│   │   ├── cpi/clean.py          # CPI-spezifisch: clean_cpi()
│   │   ├── wgi/clean.py          # WGI-spezifisch: clean_wgi()
│   │   ├── profiling/            # 📊 Data Profiling
│   │   │   ├── profile_raw_data.py
│   │   │   └── profiling_utils.py
│   │   └── __init__.py
│   ├── dw/                       # 🏢 Data Warehouse (geplant)
│   ├── log/logger.py             # 📝 Logging
│   └── utils/
│
├── data/                         # 💾 Daten
│   ├── lookup/
│   │   └── lookup_countries.csv  # ✅ Referenzdaten (versioniert via .gitignore-Exception)
│   ├── raw/                      # Rohdaten (unverarbeitet, ignoriert)
│   │   ├── ted/ted_<YYYY>.csv    # TED-CSVs (2014–2023)
│   │   ├── cpi/cpi_raw.csv
│   │   └── wgi/wgi_raw.csv
│   └── processed/                # Verarbeitete Daten (ignoriert)
│       ├── ted/ted_clean.parquet
│       ├── cpi/cpi_clean.parquet
│       └── wgi/wgi_clean.parquet
│
├── logs/                         # 📊 Anwendungs-Logs
├── temp/                         # 📂 Temporäre Dateien
└── tests/
```

---

## 💻 Verwendung der Scripts

### Test: Red Flags in TED-2022-Daten

```bash
python src/test_redflags.py
```

**Ausgabe-Beispiel:**
```
Geladene Zeilen: 245,892

=== KERN-RED FLAGS (1-3) – zeilenbasiert ===
1. Single-Bidder                 42,195 Treffer  (Beispiele: [Notice-ID1, Notice-ID2, ...])
2. Non-Open Procedure           102,334 Treffer
3. No Prior Call                 28,456 Treffer

=== EXPLORATIVE RED FLAGS (4-7) – zeilenbasiert ===
4. Accelerated Procedure         15,678 Treffer
5. Award to Group                18,923 Treffer
6. High Value/Low Bidders        12,345 Treffer
7. Tax Haven Winner                   0 Treffer

=== FLAG 8: LOS-FRAGMENTIERUNG (Notice-Ebene) ===
8. High Lot Fragmentation (>5 Lose): 3,456 von 45,123 Notices (7.7%)
```

### Präsentation generieren

```bash
python create_presentation.py
```

**Output:** `presentation.pptx` (12 Folien mit Grafiken, Tabellen, Diagrammen)

### Data Profiling – Automatisierte Datenqualitätsanalyse

Extrahiert einen umfassenden **8‑Kategorien-Qualitätsreport** für alle Rohdaten (CPI, WGI, TED 2014–2023) als Markdown-Dateien:

```bash
python src/processing/profiling/profile_raw_data.py
```

**Output:** Markdown-Reports in [`doc/profiling/`](doc/profiling/):
| Report | Beschreibung |
|--------|-------------|
| `profile_cpi_<DATUM>.md` | Profiling des Corruption Perceptions Index |
| `profile_wgi_<DATUM>.md` | Profiling der Worldwide Governance Indicators |
| `profile_ted_<YYYY>_<DATUM>.md` | Profiling eines TED-Jahres (2014–2023) |

**Geprüfte Qualitätskategorien:**
1. **Basic Info** – Zeilen, Spalten, Speicherverbrauch
2. **Datentypen** – Spaltentypen & Speichereffizienz
3. **Fehlende Werte** – Null-Raten pro Spalte
4. **Duplikate** – Konfigurierbare Schlüsselspalten
5. **Ausreißer** – IQR-basierte Erkennung in numerischen Spalten
6. **Wertebereiche** – Min, Max, Mean, Median, Unique-Counts
7. **Text-Qualität** – Längenanalyse für Textspalten
8. **Logische Konsistenz** – Quellenspezifische Plausibilitätsregeln

**Beispiel-Erkenntnisse aus dem Profiling:**
- CPI: 2.494 Zeilen, 10 Spalten, keine fehlenden Werte, keine Duplikate
- WGI: 42 Zeilen (4 Länder × 10 Jahre), vollständig
- TED 2016: 556.084 Zeilen, 75 Spalten, ~1,9 GB RAM-Auslastung
- TED: `VALUE_EURO <= AWARD_VALUE_EURO` wird in ~73% der Zeilen verletzt (interessantes Datenqualitätssignal)

**Architektur:** Aufgeteilt in zwei Module:
- [`profiling_utils.py`](src/data_processing/profiling_utils.py) – Generische, wiederverwendbare Profiling-Funktionen (8 Kategorien, kein Quellbezug)
- [`profile_raw_data.py`](src/data_processing/profile_raw_data.py) – Quellspezifische Logik (Spaltendefinitionen, Konsistenzregeln) + Orchestrierung (`main()`)

**Logging:** Alle Schritte werden via [`src/log/logger.py`](src/log/logger.py) in `logs/` und auf der Konsole protokolliert.

### Detaillierte Flag-Analyse

```bash
python flag7_10_analyse.py
```

**Output:** Statistische Auswertung von Flags 7 (Preisabweichung) & 10 (Los-Fragmentierung)

---

## 🔍 Beispiel-Queries (SQL)

Sobald die Daten im Data Warehouse sind:

### Query 1: Single-Bidder-Quote pro Land & Jahr

```sql
SELECT 
  country_code,
  year,
  COUNT(*) AS gesamt,
  SUM(flag_1_single_bidder) AS single_bidder_count,
  ROUND(100 * SUM(flag_1_single_bidder) / COUNT(*), 2) AS quote_pct
FROM fact_tender
GROUP BY country_code, year
ORDER BY country_code, year;
```

**Beispiel-Ergebnis:**
| country_code | year | gesamt | single_bidder_count | quote_pct |
|---|---|---|---|---|
| DE | 2022 | 18,234 | 3,245 | 17.78 |
| DK | 2022 | 2,145 | 156 | 7.27 |
| HU | 2022 | 5,678 | 1,892 | 33.31 |
| RO | 2022 | 8,923 | 3,101 | 34.76 |

### Query 2: Krisen-Effekt auf Red-Flag-Raten

```sql
SELECT 
  country_code,
  crisis_type,
  ROUND(100 * SUM(flag_1_single_bidder) / COUNT(*), 2) AS single_bidder_pct,
  ROUND(100 * SUM(flag_2_non_open) / COUNT(*), 2) AS non_open_pct
FROM fact_tender
GROUP BY country_code, crisis_type
ORDER BY country_code, crisis_type;
```

### Query 3: Korrelation CPI ↔ Red Flags

```sql
SELECT 
  dc.country_code,
  dc.cpi_score,
  AVG(CAST(ft.flag_1_single_bidder AS FLOAT)) * 100 AS avg_single_bidder_pct,
  AVG(CAST(ft.flag_2_non_open AS FLOAT)) * 100 AS avg_non_open_pct
FROM fact_tender ft
JOIN dim_country dc ON ft.country_key = dc.country_key
GROUP BY dc.country_code
ORDER BY dc.cpi_score DESC;
```

---

## 📊 Ausgabe & Pipeline-Ergebnisse

Nach der Pipeline-Verarbeitung entstehen:

1. **Parquet-Exports** (`data/processed/{ted,cpi,wgi}/*_clean.parquet`)
   - TED: Bereinigt + Red-Flags
   - CPI: Gefiltert + umbenannt
   - WGI: Gefiltert + Spaltenauswahl

2. **Logs** (`logs/run_cleanup.log`)
   - Detaillierte ETL-Schritte, Row-Counts, Flag-Frequenzen

---

## 🛠️ Projektstatus

✅ **Abgeschlossen:**
- Datenherunterlad (Download-Skript für TED/CPI/WGI)
- ETL-Core: Config + Utils + per-Dataset Clean-Submodule + Orchestrierung
- Data Profiling (automatisierte Qualitätsanalyse)
- Lookup-Tabelle (`data/lookup/lookup_countries.csv`)

📋 **Geplant:**
- Data Warehouse Schema (Sternschema-DDL)
- Dimension Builder + Faktentabelle
- DWH-Loader (`src/dw/`)
- Exasol-Integration
- Airflow-Automatisierung
- Dashboard (Tableau/PowerBI)

---

## 📚 Weitere Dokumentation

- **Projektkonzept:** [`project.md`](doc/project.md)
- **Technische Dokumentation:** [`doc.md`](doc/doc.md)
- **Data Warehouse Plan:** [`plans/data-preparation-for-warehouse.md`](../plans/data-preparation-for-warehouse.md)

---

## 🔐 Datenquellen-Lizenzen

| Quelle | Lizenz | URL |
|--------|--------|-----|
| TED (CSV) | CC BY 4.0 | https://data.europa.eu/data/datasets/ted-csv |
| CPI | CC BY 4.0 | https://data.humdata.org/ |
| WGI | CC BY 4.0 | https://www.worldbank.org/en/publication/worldwide-governance-indicators |

---

## 💬 Häufig gestellte Fragen (FAQ)

**F: Wie starte ich die Cleanup-Pipeline?**
> A: `python -m src.data_processing.run_cleanup` (nachdem `python src/download_data.py` die Rohdaten geholt hat).

**F: Wie lange dauert die Verarbeitung?**
> A: TED 10 Jahre (4 Länder): ~20–30 Minuten. CPI + WGI: <1 Minute.

**F: Kann ich nur bestimmte Jahre verarbeiten?**
> A: Ja, mit `--years 2020 2021 2022`.

**F: Warum Parquet statt CSV?**
> A: Parquet ist komprimierter (~80 % weniger Speicher), typ-sicherer und schneller im Laden. Siehe [`doc/doc.md`](doc/doc.md#52-transform-phase) für Details.

**F: Kann ich die Pipeline automatisieren?**
> A: Ja! Nutze Airflow oder einfache Cron-Jobs / Windows Task Scheduler.

---

## 👨‍💻 Entwickler-Notes

### Abhängigkeiten überprüfen
```bash
pip list | grep -E "pandas|requests|pptx|wbgapi"
```

### Logs anzeigen (live)
```bash
tail -f logs/run_cleanup.log                      # Linux/Mac
Get-Content logs/run_cleanup.log -Tail 50 -Wait   # Windows PowerShell
```

### Virtual Environment aktivieren/deaktivieren
```bash
venv\Scripts\activate     # Windows
source venv/bin/activate  # Linux/Mac
deactivate                # deaktivieren
```

---

## 📄 Lizenz

MIT License – Siehe LICENSE-Datei

---

**Autor:** Johannes, OTH Regensburg
**Semester:** SoSe 2026
**Fach:** Data Warehouse Projekt
