# ME/R Model — Star Schema (Diagram)

**Project:** Red Flags Procurement Governance  
**Format:** [Mermaid.js](https://mermaid.live) — mit der Mermaid-Erweiterung in VS Code (`Strg+Shift+V`) renderbar

---

```mermaid
erDiagram
    dim_country ||--o{ fact_tender : "1:N"
    dim_cpv ||--o{ fact_tender : "1:N"
    dim_procedure_type ||--o{ fact_tender : "1:N"

    dim_country {
        int country_key PK "SURROGATE KEY"
        char2 country_code "ISO Alpha-2"
        varchar country_name
        smallint cpi_score "0-100"
        decimal control_of_corruption "WGI"
        decimal government_effectiveness "WGI"
        decimal political_stability "WGI"
        decimal rule_of_law "WGI"
        decimal regulatory_quality "WGI"
        decimal voice_accountability "WGI"
        smallint valid_from_year "SCD2"
        smallint valid_to_year "SCD2"
    }

    dim_cpv {
        int cpv_key PK "SURROGATE KEY"
        char8 cpv_code "e.g. 03110000"
        varchar cpv_division "first 2 digits"
        varchar cpv_group "first 3 digits"
        varchar cpv_class "first 4 digits"
    }

    dim_procedure_type {
        int procedure_key PK "SURROGATE KEY"
        varchar procedure_code "OPE, NIC, AWP,…"
        varchar procedure_name
        smallint transparency_level "1-5"
        boolean is_open
    }

    fact_tender {
        varchar award_id PK "NATURAL KEY"
        varchar id_notice_can "(degenerierte Dimension)"
        varchar id_lot "(degenerierte Dimension)"
        smallint year "2014-2023"
        varchar crisis_type "aus year abgeleitet"
        int country_key FK "AUFTRAGGEBER"
        int winner_country_key FK "GEWINNER (Role-Playing)"
        int cpv_key FK
        int procedure_key FK
        decimal award_value_eur "FLOW"
        decimal value_eur "FLOW"
        smallint number_offers "FLOW"
        int lots_number "FLOW"
        int number_awards "FLOW"
        boolean F1 "Single-Bidder"
        boolean F2 "Award Discrepancy"
        boolean F3 "No Prior Call"
        boolean F5 "Award to Group"
        boolean F6 "Single-Bidder High Value"
        boolean F7 "Lot Fragmentation"
        boolean comb_single_discrepancy "F1 AND F2"
        boolean comb_single_non_open "F1 AND non-OPE"
        boolean comb_no_call_high_value "F3 AND F6"
        boolean comb_frag_single "F7 AND F1"
    }
```

---

## Legende

| Symbol | Bedeutung |
|--------|-----------|
| `PK` | Primary Key |
| `FK` | Foreign Key (Name identisch mit referenziertem PK) |
| `||--o{` | 1-zu-N-Beziehung (eine Dimension → viele Fakt-Zeilen) |
| `SURROGATE KEY` | Technischer Schlüssel (`INTEGER IDENTITY`, automatisch generiert) |
| `NATURAL KEY` | Fachlicher Schlüssel aus den Quelldaten |
| `degenerierte Dimension` | Referenzattribut ohne eigene Dimensionstabelle |

---

## Design-Merkmale

1. **Kein `dim_time`:** `year` und `crisis_type` sind in `fact_tender` eingebettet (design specification)
2. **Kein `F4`:** Beschleunigtes Verfahren wurde gestrichen (99,16 % NULL)
3. **SCD Type 2:** `dim_country` nutzt `valid_from_year`/`valid_to_year` zur Versionierung von Governance-Scores
4. **FK-Namen = PK-Namen:** `country_key` in `fact_tender` referenziert `country_key` in `dim_country`

---

*Diagramm erstellt 2026-05-17 mit Mermaid.js — rendert in VS Code, mermaid.live, GitHub, GitLab.*
