# Technische Dokumentation – Red Flags Procurement Governance

*Detaillierte Beschreibung der Architektur, Implementierung und Datenverarbeitung*

---

## 1. Systemarchitektur & Überblick

### 1.1 Komponenten-Stack

```
ETL-Pipeline (Python)
  ├─ Extract: Daten von drei Quellen (TED, CPI, WGI)
  ├─ Transform: Bereinigung, ISO-Mapping, Red-Flag-Berechnung
  └─ Load: Datenbank (aktuell: CSV-basiert, später Exasol)
       ↓
Data Warehouse (Sternschema)
  ├─ Faktentabelle: fact_tender
  └─ Dimensionen: Zeit, Land, CPV, Verfahrenstyp, Governance
       ↓
Analysis Layer (SQL + Python)
  ├─ mehrdimensionale Queries
  ├─ Red-Flag-Kombinationen
  └─ Visualisierungen (PPTX)
```

### 1.2 Projektstruktur

```
red-flags-procurement-governance/
├── project.md                  # Projektkonzept & Anforderungen (bleibt unverändert)
├── README.md                   # Benutzerhandbuch (aktualisiert)
├── TECHNICAL.md                # Dieses Dokument
├── create_presentation.py      # Präsentationsgenerator (PowerPoint)
├── test_redflags.py            # Red-Flag-Analyse & Tests
├── flag7_10_analyse.py         # Spezifische Flags 7 & 10 Analyse
├── src/
│   ├── data_aquisition/        # Datenquellen-Module (geplant/erweiterbar)
│   │   ├── ted/                # TED-Daten-Acquisition
│   │   ├── cpi/                # CPI-Daten-Acquisition
│   │   └── wgi/                # WGI-Daten-Acquisition
│   ├── data_processing/        # Transformations-Module
│   │   └── lookup_countries.csv # ISO-Länder-Mapping (Alpha-2: DK, DE, RO, HU)
│   ├── dw/                     # Data Warehouse Layer (Sternschema)
│   ├── log/                    # Logging-Modul
│   │   ├── __init__.py
│   │   └── logger.py           # Zentrale Logging-Konfiguration
│   └── utils/                  # Hilfsfunktionen
├── data/
│   ├── raw/                    # Rohdaten (unverarbeitet)
│   │   ├── ted/2022.csv        # TED-Daten (Beispiel-Jahr)
│   │   ├── cpi/                # CPI-Jahres-CSVs
│   │   └── wgi/                # WGI-Jahres-CSVs
│   └── processed/              # Verarbeitete Daten (DWH-ready)
├── temp/                       # Temporäre Dateien, Zwischenergebnisse
└── tests/                      # Unit & Integration Tests
```

---

## 2. Datenquellen & Ihre Integration

### 2.1 TED (Tenders Electronic Daily)

**URL:** https://data.europa.eu/data/datasets/ted-csv?locale=en

**Format:** CSV (pro Jahr separate Datei)  
**Länderfeld:** `WIN_COUNTRY_CODE` (ISO 3166-1 Alpha-2, z. B. `DE`)  
**Zeitraum:** 2006–2023 (in diesem Projekt: 2014–2023)  
**Größe:** ~1,6–2,2 Mio. Zeilen für 4 Länder & 10 Jahre, ~200–300 MB

**Wichtige Spalten:**
- `ID_NOTICE_CAN`: Eindeutige Bekanntmachungs-ID
- `ID_LOT`: Los-Identifikator
- `WIN_COUNTRY_CODE`: Land des Zuschlagsempfängers
- `TOP_TYPE`: Verfahrenstyp (OPE=Open, NIC=No Prior Call, AWP=Award w/o Publication, etc.)
- `NUMBER_OFFERS`: Anzahl eingegangener Angebote
- `AWARD_VALUE_EURO`: Zuschlagswert in Euro
- `VALUE_EURO`: Geschätzter Wert
- `B_ACCELERATED`: Flag für beschleunigtes Verfahren (Y/N)
- `B_AWARDED_TO_A_GROUP`: Flag für Zuschlag an Bietergemeinschaft (Y/N)
- `CPV`: Common Procurement Vocabulary (Klassifikation von Waren/Dienstleistungen)

### 2.2 CPI (Corruption Perceptions Index)

**URL:** https://data.humdata.org/dataset/fb4adde0-93d5-4ff9-befc-4a6916c1181b/resource/a6a4e225-50bb-4abf-958c-c37e3c3b380b/download/global-cpi-all.csv

**Format:** CSV  
**Länderfeld:** `ISO3` (ISO 3166-1 Alpha-3, z. B. `DEU`)  
**Zeitraum:** 1995–2023 (in diesem Projekt: 2014–2023)  
**Granularität:** Jährlich  
**Skala:** 0 (hochkorrupt) bis 100 (sehr sauber)

**Mapping-Transformation:**
```
Alpha-3 (z. B. DEU) → Alpha-2 (z. B. DE) via lookup_countries.csv
```

### 2.3 WGI (Worldwide Governance Indicators)

**URL:** https://databank.worldbank.org/source/worldwide-governance-indicators

**Format:** CSV (Download über API oder manuell)  
**Länderfeld:** `code` (numerisch, z. B. `276` für Deutschland)  
**Zeitraum:** 1996–2023 (in diesem Projekt: 2014–2023)  
**Granularität:** Jährlich  
**Dimensionen:**
- Rule of Law
- Control of Corruption
- Regulatory Quality
- Voice and Accountability
- Government Effectiveness
- Political Stability

**Skala:** ca. -2,5 (schwach) bis +2,5 (stark)

**Mapping-Transformation:**
```
Numerisch (z. B. 276) → Alpha-2 (z. B. DE) via lookup_countries.csv
```

### 2.4 Länder-Mapping (lookup_countries.csv)

**Inhalt:**
```csv
country_name,alpha_2
Germany,DE
Hungary,HU
Romania,RO
Denmark,DK
```

**Funktion:**
- Zentrales Lookup für alle ISO-Konversionen
- Ermöglicht deterministische Joins über `Land + Jahr`
- Reduziert auf 4 Länder (Positiv-, Benchmark-, Negativ-Beispiele)

---

## 3. Red Flags – Berechnung & Implementierung

### 3.1 Red-Flag-Definition (8 Indikatoren)

| Flag | Name | Berechnung | Datenquelle | Ebene | Status |
|------|------|-----------|-------------|--------|--------|
| **1** | **Single-Bidder** | `NUMBER_OFFERS == 1` | TED | Zeile | **KERN** |
| **2** | **Non-Open Procedure** | `TOP_TYPE != "OPE"` | TED | Zeile | **KERN** |
| **3** | **No Prior Call** | `TOP_TYPE IN ('NIC', 'AWP')` | TED | Zeile | **KERN** |
| 4 | Accelerated Procedure | `B_ACCELERATED == "Y"` | TED | Zeile | explorativ |
| 5 | Award to Group | `B_AWARDED_TO_A_GROUP == "Y"` | TED | Zeile | explorativ |
| 6 | High Value / Low Bidders | `AWARD_VALUE_EURO >= Q3 AND NUMBER_OFFERS <= 2` | TED | Zeile | explorativ |
| 7 | Tax Haven Winner | `WIN_COUNTRY_CODE IN (EU-Steueroasen-Liste)` | TED | Zeile | explorativ |
| **8** | **High Lot Fragmentation** | `LOT_COUNT_PER_NOTICE > 5` | TED | Notice | **KERN** |

### 3.2 Implementierung in Python (test_redflags.py)

```python
import pandas as pd

# Laden der TED-Daten
file_path = r"C:\...\data\raw\ted\2022.csv"
df = pd.read_csv(file_path, encoding='utf-8', low_memory=False)

# Kern-Red Flags (zeilenbasiert)
mask1 = df['NUMBER_OFFERS'] == 1                          # Flag 1
mask2 = df['TOP_TYPE'] != "OPE"                           # Flag 2
mask3 = df['TOP_TYPE'].isin(['NIC', 'AWP'])              # Flag 3

# Explorative Red Flags
mask4 = df['B_ACCELERATED'] == "Y"                        # Flag 4
mask5 = df['B_AWARDED_TO_A_GROUP'] == "Y"               # Flag 5

high_value_threshold = df['AWARD_VALUE_EURO'].quantile(0.75)
mask6 = (df['AWARD_VALUE_EURO'] >= high_value_threshold) & (df['NUMBER_OFFERS'] <= 2)  # Flag 6

tax_havens = ['KY', 'BM', 'VG', 'BS', 'BB', 'SC', 'MU', 'CH']
mask7 = df['WIN_COUNTRY_CODE'].isin(tax_havens)          # Flag 7

# Flag 8: Notice-basiert
lot_counts = df.groupby('ID_NOTICE_CAN')['ID_LOT'].nunique()
high_lot_notices = lot_counts[lot_counts > 5].index       # Flag 8

# Ausgabe
print(f"Single-Bidder: {mask1.sum()} Treffer")
print(f"Non-Open: {mask2.sum()} Treffer")
print(f"No Prior Call: {mask3.sum()} Treffer")
# ...
```

### 3.3 Red-Flag-Kombinationen (mehrdimensionale Risikosignaturen)

**Vier Kern-Kombinationen:**

| Kombination | Logik | SQL-Bedingung |
|-------------|-------|--------------|
| **Single-Bidder + Non-Open** | Wettbewerb faktisch ausgeschaltet | `mask1 AND mask2` |
| **No Prior Call + High Value/Low Bidders** | Direktvergabe hoher Wert, kaum Bieter | `mask3 AND mask6` |
| **Accelerated + Non-Open + Single-Bidder** | Perfekte Red-Flag-Trias | `mask4 AND mask2 AND mask1` |
| **High Lot Fragmentation + Single-Bidder** | Lose möglicherweise auf einen Anbieter zugeschnitten | `(notice in high_lot_notices) AND mask1` |

**Implementierung:**
```python
# Kombinationen
comb1 = (mask1) & (mask2)
comb2 = (mask3) & (mask6)
comb3 = (mask4) & (mask2) & (mask1)
comb4 = df['ID_NOTICE_CAN'].isin(high_lot_notices) & mask1

# Zählung
print(f"Single-Bidder + Non-Open: {comb1.sum()}")
print(f"No Prior Call + High Value/Low Bidders: {comb2.sum()}")
# ...
```

---

## 4. Data Warehouse (Sternschema)

### 4.1 Faktentabelle: `fact_tender`

**Primärschlüssel:** Komposite aus Fremdschlüsseln (Denormalisierung zu Performance)

**Spalten:**

| Spalte | Typ | Bedeutung |
|--------|-----|----------|
| `id_tender_key` | INT | Surrogate Key (Auto-increment) |
| `id_notice_can` | VARCHAR | TED-Referenz (natürlicher Schlüssel, joinable) |
| `fk_country_key` | INT | FK → dim_country |
| `fk_time_key` | INT | FK → dim_time |
| `fk_cpv_key` | INT | FK → dim_cpv |
| `fk_procedure_type_key` | INT | FK → dim_procedure_type |
| `award_value_euro` | DECIMAL(15,2) | Zuschlagswert |
| `estimated_value_euro` | DECIMAL(15,2) | Geschätzter Wert |
| `number_offers` | INT | Anzahl Angebote |
| `flag_1_single_bidder` | BOOLEAN | Flag 1 |
| `flag_2_non_open` | BOOLEAN | Flag 2 |
| `flag_3_no_prior_call` | BOOLEAN | Flag 3 |
| `flag_4_accelerated` | BOOLEAN | Flag 4 |
| `flag_5_award_group` | BOOLEAN | Flag 5 |
| `flag_6_high_value_low_bidders` | BOOLEAN | Flag 6 |
| `flag_7_tax_haven` | BOOLEAN | Flag 7 |
| `comb_1_sb_non_open` | BOOLEAN | Kombination 1 |
| `comb_2_npc_hvlb` | BOOLEAN | Kombination 2 |
| `comb_3_acc_non_open_sb` | BOOLEAN | Kombination 3 |

### 4.2 Dimensionen

#### dim_country
```
id_country_key (INT, PK)
country_code (VARCHAR, Alpha-2)  [DE, DK, HU, RO]
country_name (VARCHAR)
cpi_score (INT)                   [0-100]
wgi_rule_of_law (FLOAT)          [-2.5, +2.5]
wgi_control_corruption (FLOAT)
wgi_regulatory_quality (FLOAT)
wgi_voice_accountability (FLOAT)
wgi_govt_effectiveness (FLOAT)
wgi_political_stability (FLOAT)
valid_from_year (INT)
valid_to_year (INT)
```

#### dim_time
```
id_time_key (INT, PK)
year (INT)
month (INT)
quarter (INT)
crisis_type (VARCHAR)    [COVID-19, Ukraine-Krieg, keine Krise]
is_covid (BOOLEAN)       [2020-2021]
is_ukraine (BOOLEAN)     [2022+]
```

#### dim_cpv
```
id_cpv_key (INT, PK)
cpv_code (VARCHAR)       [z. B. "30000000"]
cpv_division (VARCHAR)   [z. B. "Verwaltung & Support"]
cpv_level (INT)          [2, 3, 5 Ziffern]
```

#### dim_procedure_type
```
id_procedure_key (INT, PK)
procedure_code (VARCHAR) [OPE, NIC, AWP, REQ, etc.]
procedure_name (VARCHAR) [Open, Negotiated w/o Call, ...]
is_open (BOOLEAN)
transparency_level (INT) [1=niedrig, 5=hoch]
```

### 4.3 Joins & Denormalisierung

**Kern-Join-Logik:**
```sql
SELECT 
  ft.id_notice_can,
  dc.country_code,
  dt.year,
  dt.crisis_type,
  dc.cpi_score,
  dc.wgi_control_corruption,
  ft.award_value_euro,
  ft.number_offers,
  ft.flag_1_single_bidder,
  ft.flag_2_non_open,
  -- ...
  CASE 
    WHEN ft.flag_1_single_bidder = 1 AND ft.flag_2_non_open = 1 
    THEN 1 ELSE 0 
  END AS comb_1_sb_non_open
FROM fact_tender ft
JOIN dim_country dc ON ft.fk_country_key = dc.id_country_key
JOIN dim_time dt ON ft.fk_time_key = dt.id_time_key
JOIN dim_cpv dcpv ON ft.fk_cpv_key = dcpv.id_cpv_key
JOIN dim_procedure_type dpt ON ft.fk_procedure_type_key = dpt.id_procedure_key
WHERE dt.year BETWEEN 2014 AND 2023
  AND dc.country_code IN ('DE', 'DK', 'HU', 'RO');
```

---

## 5. ETL-Pipeline – Implementierung

### 5.1 Extract-Phase

**Automatisierte Datenquellen-URLs:**

```python
# TED (jährliche Downloads)
ted_urls = {
    2022: "https://data.europa.eu/api/hub/search?..."  # Beispiel
    2023: "https://data.europa.eu/api/hub/search?..."
}

# CPI (einmalig oder jährlich aktualisiert)
cpi_url = "https://data.humdata.org/dataset/.../download/global-cpi-all.csv"

# WGI (API-basiert)
wgi_base_url = "https://databank.worldbank.org/data/..." 
```

**Python-Implementierung (geplant: src/data_aquisition/):**

```python
# src/data_aquisition/ted/fetch_ted.py
import requests
import pandas as pd

def fetch_ted_year(year):
    """Fetch TED data für ein Jahr (gefiltert auf 4 Länder)"""
    url = f"https://data.europa.eu/..."  # Anpassung erforderlich
    response = requests.get(url)
    df = pd.read_csv(url, encoding='utf-8', low_memory=False)
    
    # Filter auf 4 Länder
    df = df[df['WIN_COUNTRY_CODE'].isin(['DE', 'DK', 'HU', 'RO'])]
    
    df.to_csv(f"data/raw/ted/{year}.csv", index=False)
    print(f"TED {year}: {len(df)} Zeilen gespeichert")
    return df

# src/data_aquisition/cpi/fetch_cpi.py
def fetch_cpi():
    """Fetch globalen CPI, filter auf 4 Länder"""
    url = "https://data.humdata.org/..."
    df = pd.read_csv(url)
    
    # Mapping Alpha-3 → Alpha-2
    iso3_to_iso2 = {'DEU': 'DE', 'DNK': 'DK', 'HUN': 'HU', 'ROU': 'RO'}
    df['country_code'] = df['ISO3'].map(iso3_to_iso2)
    df = df.dropna(subset=['country_code'])
    
    df.to_csv("data/raw/cpi/all_years.csv", index=False)
    print(f"CPI: {len(df)} Zeilen gespeichert")
    return df
```

### 5.2 Transform-Phase

**Zentrale Transformations-Logik (src/data_processing/transform.py):**

```python
import pandas as pd
from src.log.logger import get_logger

logger = get_logger(__name__)

def clean_ted_data(df):
    """Bereinigung der TED-Rohdaten"""
    logger.info(f"Input: {len(df)} Zeilen")
    
    # Duplikate entfernen
    df = df.drop_duplicates(subset=['ID_NOTICE_CAN', 'ID_LOT'])
    logger.info(f"Nach Duplikat-Entfernung: {len(df)} Zeilen")
    
    # Numerische Spalten konvertieren
    df['AWARD_VALUE_EURO'] = pd.to_numeric(df['AWARD_VALUE_EURO'], errors='coerce')
    df['VALUE_EURO'] = pd.to_numeric(df['VALUE_EURO'], errors='coerce')
    df['NUMBER_OFFERS'] = pd.to_numeric(df['NUMBER_OFFERS'], errors='coerce')
    
    # Nulls ersetzen oder flaggen
    df['NUMBER_OFFERS'].fillna(0, inplace=True)
    
    return df

def calculate_red_flags(df):
    """Berechnung aller 8 Red Flags"""
    # Flags 1-7 (zeilenbasiert)
    df['flag_1_single_bidder'] = (df['NUMBER_OFFERS'] == 1).astype(int)
    df['flag_2_non_open'] = (df['TOP_TYPE'] != "OPE").astype(int)
    df['flag_3_no_prior_call'] = (df['TOP_TYPE'].isin(['NIC', 'AWP'])).astype(int)
    df['flag_4_accelerated'] = (df['B_ACCELERATED'] == "Y").astype(int)
    df['flag_5_award_group'] = (df['B_AWARDED_TO_A_GROUP'] == "Y").astype(int)
    
    # Flag 6: High Value / Low Bidders
    high_value_threshold = df['AWARD_VALUE_EURO'].quantile(0.75)
    df['flag_6_high_value_low_bidders'] = (
        (df['AWARD_VALUE_EURO'] >= high_value_threshold) & 
        (df['NUMBER_OFFERS'] <= 2)
    ).astype(int)
    
    # Flag 7: Tax Haven Winner
    tax_havens = ['KY', 'BM', 'VG', 'BS', 'BB', 'SC', 'MU', 'CH']
    df['flag_7_tax_haven'] = (df['WIN_COUNTRY_CODE'].isin(tax_havens)).astype(int)
    
    # Flag 8 (Notice-basiert, separat berechnet)
    # wird später via Groupby hinzugefügt
    
    return df

def calculate_combinations(df):
    """Berechnung der 4 Kern-Kombinationen"""
    df['comb_1_single_bidder_non_open'] = (
        (df['flag_1_single_bidder'] == 1) & (df['flag_2_non_open'] == 1)
    ).astype(int)
    
    df['comb_2_no_prior_call_hvlb'] = (
        (df['flag_3_no_prior_call'] == 1) & (df['flag_6_high_value_low_bidders'] == 1)
    ).astype(int)
    
    df['comb_3_accelerated_non_open_sb'] = (
        (df['flag_4_accelerated'] == 1) & 
        (df['flag_2_non_open'] == 1) & 
        (df['flag_1_single_bidder'] == 1)
    ).astype(int)
    
    return df

def add_crisis_dimension(df):
    """Erweitere Zeitleiste mit Krisen-Dimension"""
    def get_crisis_type(year):
        if 2020 <= year <= 2021:
            return "COVID-19"
        elif year >= 2022:
            return "Ukraine-Krieg"
        else:
            return "keine Krise"
    
    df['crisis_type'] = df['AWARD_DATE_YEAR'].apply(get_crisis_type)
    return df
```

### 5.3 Load-Phase (aktuell CSV, später Exasol)

**Datenbankschema-Erstellung (SQL):**

```sql
-- Dimensionen (DDL)
CREATE TABLE dim_country (
    id_country_key INT PRIMARY KEY AUTO_INCREMENT,
    country_code VARCHAR(2) UNIQUE NOT NULL,
    country_name VARCHAR(100),
    cpi_score INT,
    wgi_rule_of_law FLOAT,
    -- ... weitere WGI-Dimensionen
    valid_from_year INT,
    valid_to_year INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dim_time (
    id_time_key INT PRIMARY KEY AUTO_INCREMENT,
    year INT NOT NULL,
    month INT,
    quarter INT,
    crisis_type VARCHAR(50),
    is_covid BOOLEAN,
    is_ukraine BOOLEAN,
    UNIQUE(year, month)
);

CREATE TABLE dim_cpv (
    id_cpv_key INT PRIMARY KEY AUTO_INCREMENT,
    cpv_code VARCHAR(20) UNIQUE,
    cpv_division VARCHAR(255),
    cpv_level INT
);

CREATE TABLE dim_procedure_type (
    id_procedure_key INT PRIMARY KEY AUTO_INCREMENT,
    procedure_code VARCHAR(20) UNIQUE,
    procedure_name VARCHAR(100),
    is_open BOOLEAN,
    transparency_level INT
);

-- Faktentabelle
CREATE TABLE fact_tender (
    id_tender_key INT PRIMARY KEY AUTO_INCREMENT,
    id_notice_can VARCHAR(50) NOT NULL,
    fk_country_key INT NOT NULL,
    fk_time_key INT NOT NULL,
    fk_cpv_key INT,
    fk_procedure_type_key INT,
    award_value_euro DECIMAL(15, 2),
    estimated_value_euro DECIMAL(15, 2),
    number_offers INT,
    flag_1_single_bidder BOOLEAN,
    flag_2_non_open BOOLEAN,
    flag_3_no_prior_call BOOLEAN,
    flag_4_accelerated BOOLEAN,
    flag_5_award_group BOOLEAN,
    flag_6_high_value_low_bidders BOOLEAN,
    flag_7_tax_haven BOOLEAN,
    comb_1_sb_non_open BOOLEAN,
    comb_2_npc_hvlb BOOLEAN,
    comb_3_acc_non_open_sb BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (fk_country_key) REFERENCES dim_country(id_country_key),
    FOREIGN KEY (fk_time_key) REFERENCES dim_time(id_time_key),
    FOREIGN KEY (fk_cpv_key) REFERENCES dim_cpv(id_cpv_key),
    FOREIGN KEY (fk_procedure_type_key) REFERENCES dim_procedure_type(id_procedure_key),
    
    INDEX idx_country_year (fk_country_key, fk_time_key),
    INDEX idx_flags (flag_1_single_bidder, flag_2_non_open, flag_3_no_prior_call)
);
```

**Python Loader (geplant: src/dw/load.py):**

```python
def load_to_database(df_fact, df_country, df_time, df_cpv, df_procedure):
    """Ladet Daten in Exasol (oder andere DB)"""
    # Verwendung: pyodbc, sqlalchemy o. ä.
    # Vorerst: CSV-Export
    
    df_fact.to_csv("data/processed/fact_tender.csv", index=False)
    df_country.to_csv("data/processed/dim_country.csv", index=False)
    # ...
```

---

## 6. Analyse-Queries (mehrdimensional)

### 6.1 Kern-Queries

**Query 1: Single-Bidder-Rate pro Land & Jahr**

```sql
SELECT 
  dc.country_code,
  dt.year,
  COUNT(*) AS total_tenders,
  SUM(ft.flag_1_single_bidder) AS single_bidder_count,
  ROUND(100 * SUM(ft.flag_1_single_bidder) / COUNT(*), 2) AS single_bidder_pct
FROM fact_tender ft
JOIN dim_country dc ON ft.fk_country_key = dc.id_country_key
JOIN dim_time dt ON ft.fk_time_key = dt.id_time_key
WHERE dt.year BETWEEN 2014 AND 2023
GROUP BY dc.country_code, dt.year
ORDER BY dc.country_code, dt.year;
```

**Query 2: Red-Flag-Kombinationen pro Land**

```sql
SELECT 
  dc.country_code,
  COUNT(*) AS total,
  SUM(ft.comb_1_sb_non_open) AS comb_1_count,
  SUM(ft.comb_2_npc_hvlb) AS comb_2_count,
  SUM(ft.comb_3_acc_non_open_sb) AS comb_3_count
FROM fact_tender ft
JOIN dim_country dc ON ft.fk_country_key = dc.id_country_key
GROUP BY dc.country_code
ORDER BY total DESC;
```

**Query 3: Korrelation CPI-Score mit Single-Bidder-Rate**

```sql
SELECT 
  dc.country_code,
  dc.cpi_score,
  dt.year,
  ROUND(100 * SUM(ft.flag_1_single_bidder) / COUNT(*), 2) AS single_bidder_pct,
  ROUND(100 * SUM(ft.flag_2_non_open) / COUNT(*), 2) AS non_open_pct
FROM fact_tender ft
JOIN dim_country dc ON ft.fk_country_key = dc.id_country_key
JOIN dim_time dt ON ft.fk_time_key = dt.id_time_key
GROUP BY dc.country_code, dt.year
ORDER BY dc.country_code, dt.year;
```

### 6.2 Analyse-Ausgaben (Python)

```python
# Vergleich vor/während/nach COVID
covid_before = df[(df['year'] >= 2018) & (df['year'] <= 2019)]
covid_during = df[(df['year'] >= 2020) & (df['year'] <= 2021)]
covid_after = df[(df['year'] >= 2022) & (df['year'] <= 2023)]

for country in ['DE', 'DK', 'RO', 'HU']:
    before_sb = (covid_before[covid_before['country'] == country]['flag_1'].sum() / 
                 len(covid_before[covid_before['country'] == country])) * 100
    
    during_sb = (covid_during[covid_during['country'] == country]['flag_1'].sum() / 
                 len(covid_during[covid_during['country'] == country])) * 100
    
    after_sb = (covid_after[covid_after['country'] == country]['flag_1'].sum() / 
                len(covid_after[covid_after['country'] == country])) * 100
    
    print(f"{country}: Vorkrise={before_sb:.1f}%, Pandemie={during_sb:.1f}%, Nachkrise={after_sb:.1f}%")
```

---

## 7. Präsentationsgenerator (create_presentation.py)

### 7.1 Struktur

**12 Slides:**
1. **Title Slide**: Titel, Untertitel, Autor
2. **Beschreibung**: Ziel, Datenquellen, Methode (mit Prozessdiagramm)
3. **Warum ist das wichtig?**: Motivation, Business Case
4. **Data Sources**: Tabelle mit TED, CPI, WGI Details
5. **Länder & Zeitraum**: 4-Länder-Kategorisierung, Krisen-Dimension
6. **Red Flags**: Überblick über 8 Indikatoren (Tabelle/Grafik)
7. **DWH-Modell**: Sternschema (Entity-Relationship-Diagramm)
8. **ETL-Pipeline**: Prozessfluss (Extract → Transform → Load)
9. **Query-Beispiele**: 3–4 zentrale SQL-Queries
10. **Preliminary Results**: Analyseergebnisse (Chart/Tabelle)
11. **Next Steps**: Roadmap, Limitationen
12. **Q&A**: Schlussfolie

### 7.2 Technologie

**Library:** `python-pptx`

**Features:**
- Automatisierte Folienerzeugung
- Tabellen mit Styling
- Prozessdiagramme (Shapes, Pfeile)
- Farbschema (Dark Blue, Light Blue, Grau, Rot, Gelb)

**Ausführung:**

```bash
python create_presentation.py
# → presentation.pptx
```

---

## 8. Logging & Fehlerbehandlung

### 8.1 Logging-Setup (src/log/logger.py)

```python
import logging
import sys

def get_logger(name):
    """Zentrale Logging-Funktion"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Handler: Console + File
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    file_handler = logging.FileHandler('logs/application.log')
    file_handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger
```

### 8.2 Fehlerbehandlung

**Beispiel: Daten-Aquisition mit Retry-Logik**

```python
import time
from requests.exceptions import RequestException

def fetch_data_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            logger.info(f"Erfolgreich heruntergeladen: {url}")
            return response.text
        except RequestException as e:
            logger.warning(f"Versuch {attempt+1}/{max_retries} fehlgeschlagen: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error(f"Konnte nicht herunterladen nach {max_retries} Versuchen: {url}")
                raise
```

---

## 9. Performance & Optimierungen

### 9.1 Datenbank-Indizes

```sql
-- Faktentabelle Indizes
CREATE INDEX idx_fact_country_time 
ON fact_tender(fk_country_key, fk_time_key);

CREATE INDEX idx_fact_flags 
ON fact_tender(flag_1_single_bidder, flag_2_non_open, flag_3_no_prior_call);

CREATE INDEX idx_fact_notice 
ON fact_tender(id_notice_can);

-- Dimensionen
CREATE INDEX idx_country_code ON dim_country(country_code);
CREATE INDEX idx_time_year ON dim_time(year);
CREATE INDEX idx_cpv_code ON dim_cpv(cpv_code);
```

### 9.2 Pandas-Optimierungen

```python
# Low-memory Flag bei großen CSV-Dateien
df = pd.read_csv(
    file_path, 
    encoding='utf-8', 
    low_memory=False,
    dtype={
        'NUMBER_OFFERS': 'int32',
        'AWARD_VALUE_EURO': 'float64',
        'TOP_TYPE': 'category',  # Kategorische Variablen sparen Speicher
        'WIN_COUNTRY_CODE': 'category'
    }
)

# Chunked Processing für sehr große Dateien
chunk_size = 100000
for chunk in pd.read_csv(file_path, chunksize=chunk_size):
    process_chunk(chunk)
```

---

## 10. TestStrategie

### 10.1 Unit Tests

**test_redflags.py:** Validierung der Red-Flag-Berechnung

```python
def test_single_bidder_flag():
    """Test Flag 1: Single-Bidder"""
    df = pd.DataFrame({
        'NUMBER_OFFERS': [1, 2, 1, 3, 1],
        'TOP_TYPE': ['OPE', 'OPE', 'NIC', 'OPE', 'AWP']
    })
    
    result = (df['NUMBER_OFFERS'] == 1).sum()
    assert result == 3, "Single-Bidder Flag sollte 3 Treffer haben"
    
def test_non_open_flag():
    """Test Flag 2: Non-Open Procedure"""
    df = pd.DataFrame({
        'TOP_TYPE': ['OPE', 'NIC', 'AWP', 'OPE', 'NIC']
    })
    
    result = (df['TOP_TYPE'] != 'OPE').sum()
    assert result == 3, "Non-Open Flag sollte 3 Treffer haben"
```

### 10.2 Integration Tests

- Datenquellen-Download & Validierung
- ISO-Mapping Konsistenz
- Red-Flag-Kombinationen Korrektheit
- DWH-Load & Join-Validität

---

## 11. Deployment & Betrieb

### 11.1 Environment-Setup

```bash
# Virtuelle Umgebung
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Abhängigkeiten
pip install -r requirements.txt
```

### 11.2 Pipeline-Ausführung

```bash
# Manuelle Ausführung (aktuell)
python src/data_aquisition/ted/fetch_ted.py
python src/data_aquisition/cpi/fetch_cpi.py
python src/data_aquisition/wgi/fetch_wgi.py
python src/data_processing/transform.py
python src/dw/load.py

# Zukünftig: Airflow DAG
airflow dags list
airflow dags trigger red_flags_pipeline
```

### 11.3 Logging & Monitoring

**Log-Pfade:**
- `logs/application.log` – Alle Events
- `logs/errors.log` – Nur Fehler
- `data/processed/` – Zwischenergebnisse

**Monitoring-Metriken:**
- Row counts vor/nach Transform
- Fehlerquoten pro Datenquelle
- Query-Performance

---

## 12. Erweiterungspunkte (Roadmap)

1. **Exasol-Migration**: CSV → echte Datenbankverbindung
2. **Airflow-Automatisierung**: Tägliche/wöchentliche Läufe
3. **ML-Basierte Anomalieerkennung**: Clustering von Red-Flag-Mustern
4. **Dashboard**: Tableau/PowerBI für Live-Analysen
5. **API-Layer**: REST-API für externe Systeme
6. **Datenqualität**: Automatisierte Checks, Data Profiling
7. **Skalierung**: Spark/Hadoop für Multi-Jahrzehnte-Daten

---

## Anhang: Nützliche Referenzen

- **TED-Datensatz-Dokumentation**: https://data.europa.eu/data/datasets/ted-csv?locale=en
- **CPI-Quelle**: https://www.transparency.org/en/cpi/2023
- **WGI-Dokumentation**: https://www.worldbank.org/en/publication/worldwide-governance-indicators
- **python-pptx Docs**: https://python-pptx.readthedocs.io/
- **Pandas Performance**: https://pandas.pydata.org/docs/user_guide/enhancingperf.html

