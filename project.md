# Data-Warehouse-Projekt: Status & gesicherte Basis

## 1. Fixierte Datenquellen

| Quelle | Inhalt | Lizenz | Zugang | Länderkennung (Original) | Format |
|--------|--------|--------|--------|--------------------------|--------|
| **TED-CSV** | EU-Vergabedaten 2006–2023 | CC BY 4.0 | Bulk-Download (CSV) | `WIN_COUNTRY_CODE` (ISO Alpha‑2, z. B. `DE`) | ISO 3166-1 Alpha‑2 |
| **Corruption Perceptions Index (CPI)** | Korruptionswahrnehmung weltweit | CC BY 4.0 / CC BY-ND 4.0 (prüfen) | CSV-Download | `ISO3` (Alpha‑3, z. B. `DEU`) | ISO 3166-1 Alpha‑3 |
| **Worldwide Governance Indicators (WGI)** | Sechs Governance-Dimensionen | CC BY 4.0 | API (öffentlich) oder CSV | `code` (numerisch, z. B. `276`) | ISO 3166-1 numerisch |

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

## 4. Potentielle Vergleichsland-Kandidaten

Ziel: Ein kontrastierendes Land (oder zwei) mit **systematisch niedrigeren Governance-Scores**, um den Einfluss auf Red Flags messen zu können.  

**Erste Kandidaten (EU-Mitglieder, in TED vertreten):**
- **Ungarn** (HU) – CPI und WGI in den letzten Jahren rückläufig  
- **Polen** (PL) – besonders vor dem Regierungswechsel niedrigere Werte  
- **Rumänien** (RO) – dauerhaft niedrigere Werte im EU-Vergleich  

Die endgültige Auswahl erfolgt nach Prüfung von:
- ausreichender Anzahl an Vergabevorgängen in TED (2014–2023)  
- konsistenter Datenverfügbarkeit über den Zeitraum  
- möglichst großer Varianz in den Governance-Indikatoren gegenüber Deutschland

---

## 5. Fixierter Analysezeitraum: 2014–2023 (10 Jahre)

- **Zeitspanne:** 2014-01-01 bis 2023-12-31  
- **Enthaltene Krisenphasen:**  
  - **Corona-Pandemie (2020–2021):** ermöglicht die Analyse von extremen Kurzfristvergaben, Direktaufträgen und Wertanomalien unter außergewöhnlichem Handlungsdruck.  
  - **Beginn des Ukraine-Kriegs (2022–2023):** deckt erste sicherheitspolitisch bedingte Beschaffungsverschiebungen (z. B. Verteidigungs- und Bauaufträge) und mögliche Governance-Effekte ab.  
- **Governance-Referenzdaten:** CPI und WGI liegen für diesen Gesamtzeitraum lückenlos vor.  
- **Datenvolumen (geschätzt):** für DE + zwei Vergleichsländer ca. 1–1,5 Mio. Zeilen in TED, etwa 120–200 MB; zuzüglich der Indizes < 1 MB – **insgesamt weit unter 1 GB**.

---

## 6. Nächster Schritt: Recherche & Auswahl

- Download der TED-CSV-Daten für die Kandidatenländer (DE, HU, PL, RO) **nur zur Fallzahlen-Prüfung**  
- Quantitativer Vergleich: Anzahl Zeilen pro Land und Jahr, um sicherzustellen, dass genügend Volumen für alle Red-Flag-Analysen vorhanden ist  
- Festlegung auf einen oder zwei Vergleichsstaaten auf Basis dieser Daten  
- Nach der Auswahl: endgültiges Datenmodell fixieren, ETL-Pipeline aufsetzen