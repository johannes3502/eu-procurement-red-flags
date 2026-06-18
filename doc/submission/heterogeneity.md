# Forms of Heterogeneity — TED ↔ CPI/WGI

**Project:** Red Flags Procurement Governance  
**Exercise:** Challenge 3 — Sheet 3, Exercise 1.4

---

## 1. Technical Heterogeneity

TED und CPI werden als CSV-Dateien per HTTP-Download bezogen. WGI hingegen wird über eine REST API (`wbgapi`) abgefragt und liefert eine JSON-Antwort.

> **Bewertung:** Es besteht technische Heterogenität — die Zugriffsprotokolle (HTTP-Download vs. REST API) und die Übertragungsformate (CSV vs. JSON) unterscheiden sich.
>
> **Lösung:** Die Unterschiede werden im Akquisitionsschritt gekapselt. Jede Datenquelle hat ein eigenes Download-Modul, das die rohen Daten in ein einheitliches CSV-Format überführt. Die ETL-Pipeline verarbeitet nur diese vereinheitlichten CSV-Dateien — die ursprüngliche technische Heterogenität ist für sie transparent.

---

## 2. Data-Model Heterogeneity

TED und CPI liegen in einem tabellarischen Datenmodell vor: Jede Zeile entspricht einem Datensatz, jede Spalte einem Attribut. WGI liefert nach dem API-Aufruf eine hierarchische JSON-Struktur mit verschachtelten Objekten.

> **Bewertung:** Es besteht Data-Model-Heterogenität — das flache, relationale Modell von TED/CPI steht dem hierarchischen JSON-Modell von WGI gegenüber.
>
> **Lösung:** Der Akquisitionsschritt für WGI extrahiert die relevanten Felder aus der JSON-Hierarchie und flacht sie in eine tabellarische Struktur ab (eine Zeile pro Land-Jahr-Indikator). Nach diesem Schritt liegen alle drei Quellen als flache Tabellen vor und können einheitlich weiterverarbeitet werden.

---

## 3. Syntactic Heterogeneity

TED enthält große Dezimalzahlen (`DECIMAL(18,2)` für Euro-Beträge) und Booleans (Red Flags). CPI verwendet Ganzzahlen (`SMALLINT`, 0–100 für den Korruptionsscore). WGI liefert sechs normalisierte Dezimalwerte (`DECIMAL(5,2)`, Wertebereich ca. −2,5 bis +2,5).

> **Bewertung:** Es besteht syntaktische Heterogenität — die Datentypen der Attribute sind grundverschieden. Ohne Harmonisierung würde `AVG(AWARD_VALUE_EURO)` und `AVG(cpi_score)` im gleichen Query unterschiedliche numerische Präzision liefern.
>
> **Lösung:** Die Typkonvertierung erfolgt zentral in der ETL-Pipeline — jedem Quellattribut ist ein Exasol-Zieldatentyp zugeordnet. Die einheitlichen Typen im Staging- und Star-Schema stellen sicher, dass abfrageübergreifende Operationen mit konsistenter Präzision arbeiten.

---

## 4. Semantic Heterogeneity

TED verwendet ISO Alpha-2 zur Länderkodierung: `ISO_COUNTRY_CODE = 'DE'`, `'DK'`, `'RO'`, `'HU'`. CPI und WGI verwenden dagegen ISO Alpha-3: `country_iso3 = 'DEU'`, `'DNK'`, `'ROU'`, `'HUN'`. Ohne Mapping würde `WHERE country = 'DE'` nur TED-Zeilen finden.

> **Bewertung:** Es besteht semantische Heterogenität — derselbe reale Sachverhalt (ein Land) wird mit unterschiedlichen Kodierungssystemen repräsentiert.
>
> **Lösung:** Eine Lookup-Tabelle (`lookup_countries.csv`) enthält das bidirektionale Mapping Alpha-2 ↔ Alpha-3 für alle vier untersuchten Länder (DE, DK, RO, HU). Sie wird im ETL-Prozess für Filter und Joins genutzt. Im Star-Schema wird der einheitliche Alpha-2-Code in `dim_country.country_code` gespeichert.

---

## 5. Structural Heterogeneity

TED ist eine breite, denormalisierte Tabelle (75 Roh-Spalten, nach Bereinigung 25 Spalten: 15 Basisattribute + 10 Red Flags). CPI und WGI sind schmale Tabellen mit 3 bzw. 8 Spalten.

| Aspekt | TED | CPI | WGI |
|--------|-----|-----|-----|
| Spalten (roh → bereinigt) | 75 → 25 | 10 → 3 | 8 (via API) |
| Granularität | Pro Auftrag (`ID_AWARD`) | Pro Land-Jahr | Pro Land-Jahr |
| Zeilenanzahl | ~1,78 Mio. (nach Dedup) | 40 (4 Länder × 10 Jahre) | 40 (4 Länder × 10 Jahre) |

Die strukturellen Unterschiede zeigen sich in drei Dimensionen: Die Spaltenanzahl differiert stark (TED 25, CPI 3, WGI 8). Die Granularität ist inkompatibel — TED arbeitet auf Auftragsebene (~1,78 Mio. Zeilen), CPI und WGI auf der aggregierten Land-Jahr-Ebene (je 40 Zeilen). Die Zeilenanzahlen liegen um den Faktor ~44.000 auseinander.

> **Bewertung:** Es besteht strukturelle Heterogenität auf allen drei Ebenen — Spaltenstruktur, Granularität und Datenvolumen sind grundverschieden.
>
> **Lösung:** Die Integration erfolgt über ein Star-Schema mit `dim_country` als SCD Typ 2. Die Governance-Scores (CPI/WGI) werden in der Länderdimension versioniert (`valid_from_year`/`valid_to_year`). Beim Join mit `fact_tender` werden die Scores über das passende Land-Jahr-Intervall auf jede Auftragszeile repliziert — so entsteht eine einheitliche Granularität auf Auftragsebene.

---

## 6. Schematic Heterogeneity

Die Namenskonventionen unterscheiden sich systematisch: TED verwendet Großbuchstaben mit Unterstrichen (`ISO_COUNTRY_CODE`, `AWARD_VALUE_EURO`), CPI und WGI verwenden Kleinschreibung mit Underscores (`country_iso3`, `cpi_score`). Auch die Schlüsselstrategien differieren: TED besitzt einen expliziten natürlichen Primärschlüssel (`ID_AWARD`), während CPI und WGI einen impliziten, zusammengesetzten Schlüssel aus `country_iso3` und `year` nutzen.

> **Bewertung:** Es besteht schematische Heterogenität — sowohl die Benennung der Attribute als auch die Definition der Primärschlüssel folgen unterschiedlichen Konventionen.
>
> **Lösung:** Das Star-Schema definiert eine eigene, einheitliche Namenskonvention (Kleinschreibung mit Underscores, z. B. `award_value_eur`, `country_code`). Die unterschiedlichen Schlüsselstrategien werden durch Surrogatschlüssel (`INTEGER IDENTITY`) in den Dimensionstabellen vereinheitlicht — `country_key` ersetzt sowohl `ISO_COUNTRY_CODE` als auch `country_iso3`.

---

## Summary

| Heterogenitätstyp | TED | CPI/WGI | Lösung |
|-------------------|-----|---------|--------|
| Technical | CSV (HTTP-Download) | REST API (JSON) | Einheitliche CSV-Schnittstelle nach dem Akquisitionsschritt |
| Data‑Model | Relational (flach) | Hierarchisch (JSON) | Konvertierung nach tabellarisch im Akquisitionsschritt |
| Syntactic | DECIMAL(18,2), BOOLEAN | SMALLINT, DECIMAL(5,2) | Zentrale Typzuordnung in der ETL-Pipeline |
| Semantic | Alpha‑2 (`DE`) | Alpha‑3 (`DEU`) | Bidirektionale Lookup-Tabelle (`lookup_countries.csv`) |
| Structural | 25 Spalten, Auftrag‑Granularität | 3–8 Spalten, Land‑Jahr‑Granularität | SCD Typ 2 auf `dim_country` |
| Schematic | `ID_AWARD` PK, Großbuchstaben | `(country_iso3, year)`, Kleinschreibung | Einheitliches Star-Schema mit Surrogatschlüsseln |
