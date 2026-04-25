# Data-Warehouse-Projekt: Status & gesicherte Basis

## 1. Fixierte Datenquellen

| Quelle | Inhalt | Lizenz | Zugang | Länderkennung (Original) | Format |
|--------|--------|--------|--------|--------------------------|--------|
| **TED-CSV** | EU-Vergabedaten 2006–2023 | CC BY 4.0 | Bulk-Download (CSV) – [https://data.europa.eu/data/datasets/ted-csv?locale=en](https://data.europa.eu/data/datasets/ted-csv?locale=en) | `WIN_COUNTRY_CODE` (ISO Alpha‑2, z. B. `DE`) | ISO 3166-1 Alpha‑2 |
| **Corruption Perceptions Index (CPI)** | Korruptionswahrnehmung weltweit | CC BY 4.0 / CC BY-ND 4.0 (prüfen) | CSV-Download – [https://data.humdata.org/dataset/fb4adde0-93d5-4ff9-befc-4a6916c1181b/resource/a6a4e225-50bb-4abf-958c-c37e3c3b380b/download/global-cpi-all.csv](https://data.humdata.org/dataset/fb4adde0-93d5-4ff9-befc-4a6916c1181b/resource/a6a4e225-50bb-4abf-958c-c37e3c3b380b/download/global-cpi-all.csv) | `ISO3` (Alpha‑3, z. B. `DEU`) | ISO 3166-1 Alpha‑3 |
| **Worldwide Governance Indicators (WGI)** | Sechs Governance-Dimensionen | CC BY 4.0 | API (öffentlich) oder CSV – [https://databank.worldbank.org/source/worldwide-governance-indicators](https://databank.worldbank.org/source/worldwide-governance-indicators) | `code` (numerisch, z. B. `276`) | ISO 3166-1 numerisch |

- TED umfasst EU/EWR und assoziierte Staaten.  
- CPI und WGI sind global (ca. 180 bzw. >200 Länder).

---

## 2. Mapping-Strategie (deterministisch)

- **Ziel-Join-Key:** `Land (ISO Alpha‑2) + Jahr`  
- **Umwandlung:**  
  - CPI: Alpha‑3 → Alpha‑2 mittels statischer Lookup-Tabelle (`lookup_iso_alpha3_to_alpha2.csv`)  
  - WGI: numerisch → Alpha‑2 mittels statischer Lookup-Tabelle (`lookup_iso_numeric_to_alpha2.csv`)  
- Beide Lookups sind einmalig aus öffentlichen ISO-Listen erstellbar (Aufwand < 1 h).

---

## 3. Benchmark-Land: Deutschland

Deutschland dient als Referenzland mit:
- stabilen, hohen CPI‑/WGI‑Werten  
- hoher Datenqualität und Fallzahl in TED  
- Ziel: Vergleich mit Ländern, die niedrigere Governance-Werte aufweisen

---

## 4. Endgültige Auswahl der Vergleichsländer

Nach Analyse der Datenverfügbarkeit, der Governance-Varianz und der projektinternen Anforderungen wurden **drei Vergleichsländer** festgelegt. Zusammen mit Deutschland ergibt sich ein **4-Länder-Set**, das eine systematische Analyse entlang der gesamten Governance-Skala ermöglicht.

| Land (ISO Alpha‑2) | Kategorie | Reasoning |
|--------------------|-----------|-----------|
| **Deutschland (DE)** | Benchmark (stabile Mitte) | Hohe Governance-Werte (CPI ~75), sehr große Fallzahl in TED, Referenz für „normales“ Vergabeverhalten. |
| **Dänemark (DK)** | Positivkontrolle (Best‑in‑Class) | Höchste Governance-Werte in der EU (CPI ~90). Dient als „Placebo“: Sind auch in einem Top‑System Red Flags erkennbar? |
| **Ungarn (HU)** | Negativtrend (Governance‑Erosion) | Stärkster CPI‑Rückgang innerhalb der EU (von ~55 auf ~40) im Analysezeitraum. Testet, ob sinkende Governance zu mehr Red Flags führt. |
| **Rumänien (RO)** | High Risk (dauerhaft niedrig) | Chronisch niedrige Governance (CPI ~45), aber keine drastische Trendumkehr. Steht für ein System mit konstant hohem Risiko. |

**Begründung der Auswahl:**
- Alle vier Länder sind EU‑Mitglieder → gleiche rechtliche Grundlage (Vergaberichtlinien).  
- Ausreichende Anzahl an TED‑Vergabevorgängen (2014–2023) für jedes Land (Vorabprüfung bestätigt >50.000 Zeilen pro Land).  
- Maximale Varianz in den Governance-Indikatoren: DK (Spitze) → DE (Mitte) → RO (unten, stabil) → HU (unten, fallend).  
- Ermöglicht sowohl Querschnitts- (Ländervergleich) als auch Längsschnittanalysen (Zeitreihen pro Land).

---

## 5. Fixierter Analysezeitraum: 2014–2023 (10 Jahre)

- **Zeitspanne:** 2014-01-01 bis 2023-12-31  
- **Enthaltene Krisenphasen:**  
  - **Corona-Pandemie (2020–2021):** ermöglicht die Analyse von extremen Kurzfristvergaben, Direktaufträgen und Wertanomalien unter außergewöhnlichem Handlungsdruck.  
  - **Beginn des Ukraine-Kriegs (2022–2023):** deckt erste sicherheitspolitisch bedingte Beschaffungsverschiebungen (z. B. Verteidigungs- und Bauaufträge) und mögliche Governance-Effekte ab.  
- **Governance-Referenzdaten:** CPI und WGI liegen für diesen Gesamtzeitraum für alle vier Länder lückenlos vor.  
- **Datenvolumen (geschätzt):** für DE + DK + HU + RO ca. **1,6–2,2 Mio. Zeilen** in TED, etwa **200–300 MB**; zuzüglich der Indizes < 1 MB – **insgesamt weit unter 1 GB**.

---

## 6. Nächster Schritt: ETL-Pipeline & Datenmodell

Die Vorauswahl der Länder ist abgeschlossen. Es folgt:

- **Download der TED-CSV-Daten** für DE, DK, HU, RO (nur Zeitraum 2014–2023, Felder gemäß Red‑Flag‑Anforderungen).  
- **Aufbau der Lookup-Tabellen** für CPI (Alpha‑3 → Alpha‑2) und WGI (numerisch → Alpha‑2).  
- **Entwicklung der ETL-Pipeline** (z. B. mit Python/Pandas oder dbt):  
  - Lesen und Filtern der TED-CSVs  
  - Bereinigung (fehlende Werte, konsistente Datentypen)  
  - Mapping der Länderkennungen  
  - Join mit CPI/WGI-Daten (Land + Jahr)  
  - Ableitung der Red‑Flag‑Indikatoren (z. B. Direktvergabe, nur ein Bieter, übermäßig kurze Frist etc.)  
- **Finales Datenmodell** als Star‑Schema (Faktentabelle: Vergabevorgänge; Dimensionen: Zeit, Land, Käufertyp, Verfahrensart etc.)  
- **Erste explorative Analyse** (Deskriptive Statistiken, Zeitreihen der Red‑Flag‑Raten pro Land)

