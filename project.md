# **Mehrdimensionale Analyse von Auffälligkeiten in EU-Vergabedaten (TED) mit externen Governance‑Scores (CPI/WGI) – Ein Data‑Warehouse‑Ansatz**  
*Data-Warehouse-Projekt – gesicherte Basis & finale Konzeption*

---

## 0. Definitionen der zentralen Datenquellen

| Kürzel | Langname | Kurzbeschreibung |
|--------|----------|------------------|
| **TED** | *Tenders Electronic Daily* | Elektronisches Amtsblatt der EU für öffentliche Aufträge oberhalb der Schwellenwerte. Enthält strukturierte Bekanntmachungen zu Ausschreibungen, Verfahren und Zuschlägen. |
| **CPI** | *Corruption Perceptions Index* | Jährlicher Index von Transparency International, der das wahrgenommene Ausmaß von Korruption im öffentlichen Sektor misst. Skala 0 (hoch korrupt) bis 100 (sehr sauber). |
| **WGI** | *Worldwide Governance Indicators* | Weltbank‑Datensatz mit sechs Dimensionen der Governance (z. B. „Korruptionsbekämpfung“, „Regulatory Quality“). Werte von ca. -2,5 (schwach) bis +2,5 (stark). |

Diese drei Quellen bilden die Grundlage für die mehrdimensionale Analyse.

---

## 1. Fixierte Datenquellen

| Quelle | Inhalt | Lizenz | Zugang | Länderkennung (Original) | Format |
|--------|--------|--------|--------|--------------------------|--------|
| **TED-CSV** | EU-Vergabedaten 2006–2023 | CC BY 4.0 | Bulk-Download (CSV) – [Link](https://data.europa.eu/data/datasets/ted-csv?locale=en) | `WIN_COUNTRY_CODE` (ISO Alpha‑2, z. B. `DE`) | ISO 3166-1 Alpha‑2 |
| **Corruption Perceptions Index (CPI)** | Wahrnehmung von Korruption | CC BY 4.0 | CSV-Download – [Link](https://data.humdata.org/dataset/fb4adde0-93d5-4ff9-befc-4a6916c1181b/resource/a6a4e225-50bb-4abf-958c-c37e3c3b380b/download/global-cpi-all.csv) | `ISO3` (Alpha‑3, z. B. `DEU`) | ISO 3166-1 Alpha‑3 |
| **Worldwide Governance Indicators (WGI)** | Sechs Governance‑Dimensionen | CC BY 4.0 | API / CSV – [Link](https://databank.worldbank.org/source/worldwide-governance-indicators) | `code` (numerisch, z. B. `276`) | ISO 3166-1 numerisch |

---

## 2. Mapping-Strategie (deterministisch)

- **Ziel-Join-Key:** `Land (ISO Alpha‑2) + Jahr`  
- **Umwandlung:**  
  - CPI: Alpha‑3 → Alpha‑2 mittels Lookup-Tabelle  
  - WGI: numerisch → Alpha‑2 mittels Lookup-Tabelle  

---

## 3. Ausgewählte Länder (4‑Länder‑Set)

| Land (ISO Alpha‑2) | Kategorie | CPI‑Bereich (ca.) |
|--------------------|-----------|--------------------|
| **Dänemark (DK)** | Positivkontrolle | ~90 (sehr hoch) |
| **Deutschland (DE)** | Benchmark (Mitte) | ~75 |
| **Rumänien (RO)** | Dauerhaft niedrig | ~45 |
| **Ungarn (HU)** | Fallend | 55 → 40 |

---

## 4. Fixierter Analysezeitraum & Krisendimension

**Analysezeitraum: 2014–2023 (10 Jahre)**  
Datenvolumen: ca. 1,6–2,2 Mio. Zeilen, 200–300 MB.

### 4.1 Krisenjahre als explizite Dimension

Im DWH wird eine binäre/mehrstufige Dimension `crisis_type` angelegt:
- `keine Krise` (2014–2019, 2023)
- `COVID-19-Pandemie` (2020–2021)
- `Ukraine-Krieg` (2022)

Ermöglicht Queries wie:  
*„Vergleich der Single‑Bidder‑Rate zwischen Vorkrise, Pandemie und Nachkriegsbeginn – pro Land und Verfahrenstyp.“*

---

## 5. Red Flags – Acht Indikatoren für Auffälligkeiten

| Nr. | Red Flag | Bedeutung | TED‑Feld(er) | Bedingung | Status |
|-----|----------|-----------|--------------|-----------|--------|
| **1** | **Single‑Bidder** | Nur ein Bieter – mangelnder Wettbewerb | `NUMBER_OFFERS` | = 1 | **KERN** |
| **2** | **Non‑Open Procedure** | Nicht offenes Verfahren – weniger transparent | `TOP_TYPE` | ≠ "OPE" | **KERN** |
| **3** | **No Prior Call** | Keine vorherige Bekanntmachung – starke Flag | `TOP_TYPE` | = "NIC" oder "AWP" | **KERN** |
| 4 | Accelerated Procedure | Beschleunigtes Verfahren | `B_ACCELERATED` | = "Y" | explorativ |
| 5 | Award to a Group | Zuschlag an Bietergemeinschaft | `B_AWARDED_TO_A_GROUP` | = "Y" | explorativ |
| 6 | High Value / Low Bidders | Hoher Wert & wenige Bieter | `AWARD_VALUE_EURO`, `NUMBER_OFFERS` | Top‑Quartil & Bieter ≤ 2 | explorativ |
| 7 | Tax Haven Winner | Gewinner aus Steueroase (EU‑Liste) – in TED sehr selten, daher nur explorativ | `WIN_COUNTRY_CODE` | In EU‑Liste | explorativ, geringe Fallzahl |
| **8** | **High Lot Fragmentation** | >5 Lose pro Notice | `ID_LOT` pro Notice | > 5 | explorativ (Notice‑Ebene) |

**Berechnungsebene:** Flags 1–7 zeilenbasiert, Flag 8 notice‑basiert.

---

## 6. Kombinationen der Red Flags – Mehrdimensionale Risikosignaturen

| Kombination | Logik | Beispiel-Query |
|-------------|-------|----------------|
| **Single‑Bidder + Non‑Open Procedure** | Nicht-offenes Verfahren mit nur einem Bieter – Wettbewerb faktisch ausgeschaltet. | *„Anteil dieser Kombination pro Land und Jahr.“* |
| **No Prior Call + High Value / Low Bidders** | Direktvergabe ohne Vorankündigung, hoher Wert, kaum Bieter – starkes Korruptionssignal. | *„Welche CPV‑Gruppen in Ungarn zeigen diese Kombination?“* |
| **Accelerated + Non‑Open + Single‑Bidder** | „Perfekte“ Red‑Flag‑Trias für intransparente Eilvergaben. | *„Hat die Pandemie die Trias-Rate beeinflusst?“* |
| **High Lot Fragmentation + Single‑Bidder** | Viele Lose, aber nur ein Bieter – Lose sind möglicherweise auf einen Anbieter zugeschnitten. | *„In welchen CPV‑Gruppen tritt diese Kombination in Rumänien auf?“* |

*Hinweis:* Die Kombination „High Lot Fragmentation + Tax Haven Winner“ wird entfernt, da Steueroasen als Gewinner in TED‑Daten faktisch nicht vorkommen (nur EU‑Länder).

---

## 7. Natürlich‑sprachige, mehrdimensionale Queries

1. *„Entwicklung der Single‑Bidder‑Rate über die Jahre für jedes der vier Länder – im Vergleich zum CPI‑Trend.“*  
2. *„Welche CPV‑Hauptgruppen haben in Ungarn die höchste Non‑Open‑Rate?“*  
3. *„Gibt es einen Zusammenhang zwischen der Fragmentierungsrate (Flag 8) und dem WGI‑Wert für ‚Regulatory Quality‘?“*  
4. *„Zeige mir die jährliche Anzahl von No‑Prior‑Call‑Verfahren in Deutschland und Rumänien – überlagert mit den Corona‑Jahren 2020/21.“*  
5. *„Vergleiche Single‑Bidder‑Rate in Vorkrise (2018–19), Pandemie (2020–21) und Nachkriegsbeginn (2022–23) – separat nach offenen und nicht‑offenen Verfahren.“*

---

## 8. DWH‑Datenmodell (Sternschema)

**Faktentabelle:** `fact_tender` (pro Vergabevorgang)  
- Fremdschlüssel zu Dimensionen  
- Faktwerte: `AWARD_VALUE_EURO`, `NUMBER_OFFERS`, acht Booleans für Flags, Kombinations‑Flags

**Dimensionen:**

| Dimension | Fragewort | Felder |
|-----------|-----------|--------|
| Zeit | **When?** | `YEAR`, `MONTH`, `CRISIS_TYPE` |
| Land | **Where?** | `WIN_COUNTRY_CODE` (DK, DE, RO, HU) |
| CPV‑Warengruppe | **What?** | `CPV` (erste 2/3/5 Ziffern) |
| Verfahrenstyp | **How?** | `TOP_TYPE` |
| Governance‑Score | **Which Quality?** | `CPI`, `WGI_*` (gejoint über Land+Jahr) |

---

## 9. ETL‑Pipeline – vollautomatisiert

**Keine manuellen Downloads.** Alle Rohdaten werden über die festen Download‑Links automatisiert abgerufen (`requests.get()`), dann skriptgesteuert bereinigt.

| Schritt | Technologie | Beschreibung |
|---------|-------------|--------------|
| Extraktion | Python (Requests) | Automatischer Abruf TED‑CSVs (gefiltert auf 4 Länder, 2014–2023) sowie CPI, WGI |
| Transformation | Python (Pandas) | Bereinigung, ISO‑Mapping, Berechnung Red Flags, Kombinations‑Flags, Aggregation |
| Laden | Exasol | Automatisches Erstellen des Sternschemas und Einfügen |
| Analyse | SQL + Python | Ausführung der mehrdimensionalen Queries |

Die Pipeline ist ein einziges ausführbares Skript (oder Airflow‑DAG). Manuelle Eingriffe entfallen.

---

## 10. Limitationen

- Nur EU‑Schwellenwerte (kleinere Aufträge fehlen).  
- CPI/WGI nur jährlich (keine feineren Muster).  
- Keine Kausalität.  
- „Tax Haven Winner“ praktisch irrelevant für EU‑Daten – bleibt nur aus Vollständigkeit erwähnt, aber nicht weiter analysiert.

---

## 11. Nächste Schritte

1. Präsentationsfolien erstellen.  
2. Proof‑of‑Concept mit einem Jahr (z. B. 2022).  
3. ISO‑Lookup‑Tabellen erstellen.  
4. Sternschema in Exasol anlegen (inkl. Krisen‑Dimension).  
5. Vollautomatisierte Pipeline für 2014–2023 implementieren.  
6. Analyse der Red‑Flag‑Kombinationen (insb. die vier sinnvollen aus Abschnitt 6).

