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
```

### 4. Daten herunterladen

Die Daten werden **automatisch** von den folgenden Quellen heruntergeladen:

**TED (Tenders Electronic Daily):**
```bash
# Siehe: data/raw/ted/
# Manueller Download: https://data.europa.eu/data/datasets/ted-csv?locale=en
```

**CPI (Corruption Perceptions Index):**
```bash
# Siehe: data/raw/cpi/
# Manueller Download: https://data.humdata.org/dataset/.../global-cpi-all.csv
```

**WGI (Worldwide Governance Indicators):**
```bash
# Siehe: data/raw/wgi/
# Manueller Download: https://databank.worldbank.org/source/worldwide-governance-indicators
```

**Für die ersten Tests:** Ein Beispiel-TED-Jahr 2022 liegt vor unter `data/raw/ted/2022.csv`

---

## 📁 Projektstruktur

```
red-flags-procurement-governance/
├── project.md                    # 📌 Projektkonzept (Anforderungen, Datenquellen)
├── README.md                     # 👈 DU BIST HIER – Benutzerhandbuch
├── TECHNICAL.md                  # 🔧 Technische Dokumentation
├── exasol.md                     # Exasol-Datenbankdokumentation
│
├── create_presentation.py        # 🎨 Präsentationsgenerator (PowerPoint)
├── test_redflags.py              # ✅ Red-Flag-Analyse & Tests
├── flag7_10_analyse.py           # 🔬 Spezifische Analyse (Flags 7 & 10)
│
├── src/                          # Quellcode-Architektur
│   ├── data_aquisition/          # 📥 Datenquellen-Module
│   │   ├── ted/                  # TED-Download & -Parsing
│   │   ├── cpi/                  # CPI-Download & -Parsing
│   │   └── wgi/                  # WGI-Download & -Parsing
│   │
│   ├── data_processing/          # 🔄 Transformations-Module
│   │   └── lookup_countries.csv  # ISO-Länder-Mapping
│   │
│   ├── dw/                       # 🏢 Data Warehouse (Sternschema)
│   │   └── [Geplant: DDL, Loader, Views]
│   │
│   ├── log/                      # 📝 Logging
│   │   ├── __init__.py
│   │   └── logger.py             # Zentrale Logging-Funktion
│   │
│   └── utils/                    # 🛠️ Hilfsfunktionen
│       └── [Geplant: Utility-Module]
│
├── data/                         # 💾 Daten
│   ├── raw/                      # Rohdaten (unverarbeitet)
│   │   ├── ted/                  # TED-CSVs (pro Jahr)
│   │   │   └── 2022.csv          # ✅ Beispiel-Datei
│   │   ├── cpi/                  # CPI-CSVs
│   │   └── wgi/                  # WGI-CSVs
│   │
│   └── processed/                # Verarbeitete Daten (DWH-ready)
│       └── [Fact- & Dimension-CSVs nach Transform]
│
├── temp/                         # 📂 Temporäre Dateien & Zwischenergebnisse
├── logs/                         # 📊 Anwendungs-Logs
└── tests/                        # ✅ Unit & Integration Tests
```

---

## 💻 Verwendung der Scripts

### Test: Red Flags in TED-2022-Daten

```bash
python test_redflags.py
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

## 📊 Ausgabe & Analyseergebnisse

Nach der Pipeline-Verarbeitung entstehen:

1. **CSV-Exports** (`data/processed/`)
   - `fact_tender.csv` – Alle Vergabevorgänge mit Red Flags
   - `dim_*.csv` – Dimensionstabellen

2. **PowerPoint-Präsentation** (`presentation.pptx`)
   - 12 Folien mit visuellen Ergebnissen

3. **Logs** (`logs/application.log`)
   - Detaillierte ETL-Schritte, Fehler, Performance-Metriken

---

## 🛠️ Projektstruktur & Entwicklung

### Momentaner Status

✅ **Abgeschlossen:**
- Projektkonzept (`project.md`)
- Red-Flag-Berechnung (`test_redflags.py`)
- Präsentationsgenerator (`create_presentation.py`)
- Lookup-Tabelle (`src/data_processing/lookup_countries.csv`)

🚧 **In Bearbeitung:**
- Data Warehouse Schema (Sternschema-DDL)
- ETL-Pipeline-Module (`src/data_aquisition/`, `src/data_processing/`)
- DWH-Loader (`src/dw/`)

📋 **Geplant:**
- Exasol-Integration
- Airflow-Automatisierung
- Dashboard (Tableau/PowerBI)
- ML-basierte Anomalieerkennung

---

## 📚 Weitere Dokumentation

- **Detaillierte Projektanforderungen:** Siehe [project.md](project.md)
- **Technische Implementation:** Siehe [TECHNICAL.md](TECHNICAL.md)
- **Exasol-Setup:** Siehe [exasol.md](exasol.md)

---

## 🔐 Datenquellen-Lizenzen

| Quelle | Lizenz | URL |
|--------|--------|-----|
| TED (CSV) | CC BY 4.0 | https://data.europa.eu/data/datasets/ted-csv |
| CPI | CC BY 4.0 | https://data.humdata.org/dataset/... |
| WGI | CC BY 4.0 | https://www.worldbank.org/en/.../wgi |

---

## 💬 Häufig gestellte Fragen (FAQ)

**F: Wie lange dauert die Datenverarbeitung?**
> A: Für ein Jahr TED-Daten (4 Länder): ~5–10 Minuten auf Standard-Hardware. Full Load (10 Jahre): ~1 Stunde.

**F: Kann ich die Analyse nur auf ein Land beschränken?**
> A: Ja! Bearbeite `src/data_processing/lookup_countries.csv` und entferne die nicht benötigten Länder.

**F: Wie kann ich eine neue Red Flag hinzufügen?**
> A: Füge in `test_redflags.py` eine neue Bedingung hinzu und berechne mit `.sum()` / `.apply()`.

**F: Wo werden die Logs gespeichert?**
> A: In `logs/application.log` und optional `logs/errors.log`.

**F: Kann ich die Pipeline automatisieren?**
> A: Ja! Nutze Airflow oder einfache Cron-Jobs / Windows Task Scheduler.

---

## 👨‍💻 Entwickler-Notes

### Abhängigkeiten überprüfen
```bash
pip list | grep -E "pandas|requests|pptx"
```

### Tests ausführen
```bash
pytest tests/ -v
```

### Logs anzeigen (live)
```bash
tail -f logs/application.log       # Linux/Mac
Get-Content logs/application.log -Tail 50 -Wait  # Windows PowerShell
```

### Virtual Environment deaktivieren
```bash
deactivate
```

---

## 📧 Support & Kontakt

Bei Fragen oder Fehlern:
1. Überprüfe [project.md](project.md) für Anforderungen
2. Siehe [TECHNICAL.md](TECHNICAL.md) für technische Details
3. Erstelle ein Issue auf GitHub

---

## 📄 Lizenz

MIT License – Siehe LICENSE-Datei

---

**Autor:** Johannes, OTH Regensburg  
**Semester:** SoSe 2026  
**Fach:** Data Warehouse Projekt 
