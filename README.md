# Red Flags in EU Procurement & Governance Quality

> **1.78M public tenders · 4 countries · 10 years · 6 red flags · Star Schema · Power BI (PDF)**
>
> A data warehouse project correlating procurement anomalies with governance quality indicators (CPI, WGI).

---

## Key Findings

| # | Finding |
|---|---------|
| **1** | CPI ↔ Red Flags: **r ≈ −0.69** — better governance = measurably lower risk |
| **2** | **49.4%** of all tenders have ≥1 red flag — a structural problem, not isolated cases |
| **3** | **Construction (CPV 45)** is the only sector flagged across all 4 countries |
| **4** | **Hungary: 10 years of stagnation at ~60%** — no improvement without reform |
| **5** | Crises act as accelerants — baseline risk in HU/RO is high even without crises |

[Power BI Report (PDF)](src/powerbi/report.pdf)

---

## Architecture

```
Data Sources (TED/CPI/WGI)
        │
        ▼
┌─────────────────────────────┐
│  ETL Pipeline (Python)      │
│  download → clean → flag    │
│  Output: Parquet            │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Data Warehouse (Exasol)    │
│  Star Schema                │
│  fact_tender + 3 dimensions │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Power BI (Import Mode)     │
│  3-page report              │
└─────────────────────────────┘
```

**Tech Stack:** Python 3.9+ · Exasol · Power BI · ODBC · pyexasol

---

## Quick Start

### Prerequisites
- Python 3.9+
- Exasol instance (local or remote)
- ODBC driver for Exasol (for Power BI)
- DBeaver (optional, for SQL scripts)

### Setup

```bash
git clone https://github.com/YOUR_USERNAME/eu-procurement-red-flags.git
cd eu-procurement-red-flags

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install -r requirements.txt
```

### Exasol Setup (via Docker)

If you don't have an Exasol instance, run one locally:
```bash
docker run -d --name exasol-db -p 8563:8563 --privileged exasol/docker-db:latest
```
Wait ~90 seconds for startup, then use these credentials:
```ini
EXASOL_HOST=localhost
EXASOL_PORT=8563
EXASOL_USER=sys
EXASOL_PASSWORD=exasol
```

**DBeaver connection:** Create new Exasol connection → Host: `localhost`, Port: `8563`, User: `sys`, Password: `exasol`. Disable SSL certificate validation in Driver Properties (set `sslcertificate=0`).

### Configuration

```bash
copy .env.template .env
```

Edit `.env` with your Exasol credentials:
```ini
EXASOL_HOST=your-host.example.com
EXASOL_PORT=8563
EXASOL_USER=your_username
EXASOL_PASSWORD=your_password
EXASOL_SCHEMA=procurement_governance
```

### Data Pipeline

**One-command pipeline** (runs all steps: download → cleanup → Exasol load → tests):
```bash
python run_all.py
```

Options:
```bash
python run_all.py --years 2022 2023   # test with fewer years
python run_all.py --skip-download     # skip download, use existing data
python run_all.py --skip-tests        # skip pytest
```

**Individual steps:**
```bash
python src/download_data.py              # downloads TED/CPI/WGI raw data
python -m src.processing.run_cleanup     # cleans data + computes red flags → Parquet
python -m src.dw.setup_and_load          # creates star schema + loads into Exasol
```

After loading, run analytical queries against Exasol:
```bash
python src/powerbi/exploratory_analysis.py   # runs 10 analytical queries against Exasol
```

### Run Tests

```bash
pip install pytest
python -m pytest tests/ -v               # runs 51 unit tests
```

---

## Red Flags

| # | Name | Definition | Type |
|---|------|-----------|------|
| **F1** | Single Bidder | Only 1 bid received — no competition | Core |
| **F2** | Value Discrepancy | `value_eur / award_value_eur > 10` — budget blown | Core |
| **F3** | Direct Award | `TOP_TYPE IN ('NIC','AWP')` — no competitive tender | Core |
| F5 | Award to Group | Contract awarded to a bidding consortium | Exploratory |
| F6 | Elevated Price | Award > 150% of category median — possible collusion | Core |
| F7 | Tax Haven Winner | Winner registered in a tax haven jurisdiction | Exploratory |

**Composite Flags:**
- Single Bidder + Non-Open Procedure
- No Prior Call + High Value / Low Bidders
- High Lot Fragmentation + Single Bidder

`Overall Flag Rate` = share of tenders with ≥1 flag

---

## Project Structure

```
eu-procurement-red-flags/
├── README.md
├── run_all.py                      # single-entry pipeline script
├── requirements.txt
├── .env.template                  # connection config (copy to .env, NEVER commit .env)
├── .gitignore
├── LICENSE
│
├── doc/                           # documentation
│   ├── project.md                 # project concept & design decisions
│   ├── doc.md                     # technical reference
│   ├── analysis_results.md        # key analytical findings
│   └── data-model/                # star schema design documents
│       ├── mer_model.md           # ME/R entity-relationship model
│       ├── mer_model.png          # model diagram
│       ├── measure_table.md       # measure classification
│       └── snowflake_variant.md   # alternative schema design
│
├── src/                           # source code
│   ├── download_data.py           # automated data download (TED, CPI, WGI)
│   ├── acquisitions/               # data source connectors
│   │   ├── ted/download.py
│   │   ├── cpi/download.py
│   │   └── wgi/download.py
│   ├── processing/                # ETL pipeline
│   │   ├── config.py              # constants, thresholds, paths
│   │   ├── utils.py               # shared utilities
│   │   ├── run_cleanup.py         # CLI orchestrator
│   │   ├── ted/clean.py           # TED cleaning + red flag computation
│   │   ├── cpi/clean.py
│   │   ├── wgi/clean.py
│   │   └── profiling/             # data quality profiling
│   ├── dw/                        # data warehouse layer
│   │   ├── setup_and_load.py      # schema creation + data load (pyexasol)
│   │   ├── reset_staging.py       # staging table reset
│   │   └── ddl/                   # SQL scripts (run in DBeaver)
│   │       ├── create_staging_tables.sql
│   │       ├── create_star_schema.sql
│   │       ├── import_staging.sql
│   │       ├── merge_dimensions.sql
│   │       ├── data_quality_checks.sql
│   │       └── analytical_queries.sql
│   ├── powerbi/                   # Exasol analysis + Power BI PDF report
│   │   ├── report.pdf             # final report (3 pages)
│   │   ├── exploratory_analysis.py # analytical queries against Exasol
│   │   ├── test_connections.py    # ODBC + native Exasol connection tests
│   │   └── setup-guide.md         # Exasol connection setup guide
│   └── log/                       # logging utilities
│
├── tests/                          # test suite (pytest)
│   ├── conftest.py                 # shared fixtures
│   ├── test_red_flags.py           # red flag logic tests (30 tests)
│   ├── test_config.py              # config validation (13 tests)
│   └── test_utils.py               # utility function tests (8 tests)
│
├── data/                          # data directory (gitignored, pipeline-generated)
│   ├── lookup/
│   │   └── lookup_countries.csv   # ISO country code reference
│   ├── raw/                       # raw downloads (TED CSV, CPI, WGI)
│   └── processed/                 # clean Parquet exports
│
└── logs/                          # application logs (gitignored)
```

---

## Disclaimer

Red flags in this project are **rule-based anomaly indicators** derived from public procurement data. They are **not** evidence of corruption, fraud, or misconduct. A flagged tender may reflect data quality issues, different national reporting practices, legitimate emergency procurement, or structural market characteristics (e.g., few bidders in a specialized sector). The correlation with CPI/WGI governance scores reveals statistical patterns, not causal relationships. All data is sourced from publicly available EU and World Bank datasets under CC BY 4.0 license.

---

## Key Insights

**Governance explains ~48% of variance.** CPI (Corruption Perceptions Index) has a strong negative correlation with red flag rates. Higher CPI → lower procurement risk.

**Construction is the universal risk sector.** Across all 4 countries, CPV division 45 (construction) shows the highest red flag rates. This suggests sector-level structural issues independent of national governance.

**Hungary and Romania show systemic patterns.** Unlike DE/DK where red flags are relatively stable, HU shows 10 years of consistent ~60% overall rate with no improvement trend, and RO shows volatile patterns likely driven by reporting changes rather than real reform.

**Crisis composition effect:** Red flag rates appear to drop during crisis years — this is a composition effect (different goods procured, temporary EU threshold adjustments), not genuine governance improvement. Rates return to baseline after crises.

---

## Data Sources

| Source | Description | License |
|--------|-------------|---------|
| [TED (Tenders Electronic Daily)](https://data.europa.eu/data/datasets/ted-csv) | EU public procurement notices | CC BY 4.0 |
| [CPI (Corruption Perceptions Index)](https://www.transparency.org/en/cpi/) | Perceived corruption scores (0–100) | CC BY 4.0 |
| [WGI (Worldwide Governance Indicators)](https://www.worldbank.org/en/publication/worldwide-governance-indicators) | 6 governance dimensions | CC BY 4.0 |

**Time Range:** 2014–2023 (10 years)
**Countries:** Denmark (DK), Germany (DE), Romania (RO), Hungary (HU)

---

## License

MIT — See [LICENSE](LICENSE) file.
