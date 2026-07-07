# Power BI Model Setup Guide

**Projekt:** Red Flags in EU Procurement Governance  
**Verbindung:** DirectQuery zu Exasol (konfigurierbar via `.env`)

---

## Schritt 0: Exasol-Connector installieren (einmalig)

### Status: ✅ Bereits erledigt (30.06.2026)

Power BI benötigt den Exasol-Custom-Connector, damit "Exasol" in **Daten abrufen → Datenbank** erscheint.

| Komponente | Status |
|------------|:---:|
| `Exasol.mez` (v1.1.0) in `C:\Users\Johannes\Documents\Microsoft Power BI Desktop\Custom Connectors\` | ✅ |
| VC++ Redistributable (2022 x64 + x86) | ✅ |
| Exasol ODBC-Treiber | ⬜ Nicht nötig — der .mez-Connector nutzt das native Exasol-Protokoll (WebSocket), kein ODBC |

### Power BI Einstellung (MANUELL — von dir auszuführen!)

Damit Power BI den Connector lädt, muss die Sicherheitseinstellung angepasst werden:

1. Power BI Desktop öffnen
2. **Datei → Optionen und Einstellungen → Optionen**
3. Links: **Sicherheit**
4. Unter **Daten-Erweiterungen:** Wähle **„(Nicht empfohlen) Beliebige Erweiterung ohne Überprüfung oder Warnung laden"**
5. **OK**
6. Power BI Desktop **komplett schließen** und **neu starten**
7. Prüfen: **Daten abrufen → Datenbank → Exasol** sollte jetzt sichtbar sein

> **Hinweis:** Diese Einstellung lässt ALLE benutzerdefinierten Connectors zu. After the setup you can reset it.

---

## Schritt 1: Power BI mit Exasol verbinden

1. Power BI Desktop öffnen
2. **Daten abrufen** → Mehr… → **Datenbank** → **Exasol**

   (Falls Exasol nicht erscheint → Schritt 0 wiederholen, Einstellung prüfen, Power BI neu starten)

3. Im Exasol-Verbindungsdialog:
   - **Server:** `your-exasol-host:8563/nocertcheck` (wie in `.env` konfiguriert)
   - **Modus:** DirectQuery (nicht Import!)
   - OK

4. **Authentifizierung:**
   - Authentifizierungsart: **Standard**
   - Benutzername: Dein Exasol-Benutzername (wie in `.env` konfiguriert)
   - Passwort: (dein OTH-Exasol-Passwort)
   - **Verbinden**

---

## Schritt 2: Tabellen auswählen

Im Navigator diese **4 Tabellen** anhaken (KEINE Staging-Tabellen):

| Tabelle | Zweck |
|---------|-------|
| `FACT_TENDER` | Fakten-Tabelle (~1,78 Mio. Zeilen) |
| `DIM_COUNTRY` | Länder-Dimension (SCD2, ~40 Zeilen) |
| `DIM_CPV` | CPV-Produkt-Dimension |
| `DIM_PROCEDURE_TYPE` | Verfahrensart-Dimension |

**Laden** klicken.

---

## Schritt 3: Modellansicht — Beziehungen setzen

In **Modellansicht** wechseln (linke Seitenleiste, 3. Symbol).

Power BI erkennt Beziehungen manchmal automatisch. Falls nicht, manuell anlegen:

### Beziehung 1: Land (Auftraggeber)
- Von: `fact_tender[country_key]`
- Nach: `dim_country[country_key]`
- Kardinalität: **Viele zu Eins (*:1)**
- Filterrichtung: **Einfach**
- **Diese Beziehung aktiv machen:** ✅ anhaken

### Beziehung 2: CPV
- Von: `fact_tender[cpv_key]`
- Nach: `dim_cpv[cpv_key]`
- Kardinalität: Viele zu Eins (*:1)
- **Aktiv machen:** ✅

### Beziehung 3: Verfahrensart
- Von: `fact_tender[procedure_key]`
- Nach: `dim_procedure_type[procedure_key]`
- Kardinalität: Viele zu Eins (*:1)
- **Aktiv machen:** ✅

---

## Schritt 4: dim_country duplizieren für Role-Playing (Gewinner-Land)

Power BI erlaubt nur eine aktive Beziehung pro Tabellenpaar. `winner_country_key` braucht aber auch `dim_country` → wir duplizieren sie.

### Im Power Query-Editor:

1. Auf **Daten transformieren** klicken (Registerkarte Start)
2. Rechtsklick auf `dim_country` im Bereich „Abfragen" → **Duplizieren**
3. Rechtsklick auf das Duplikat → **Umbenennen** → `dim_country_winner`
4. Optional: Rechtsklick `dim_country_winner` → **Laden aktivieren** anhaken lassen (wir brauchen die Tabelle für Gewinner-Land-Visuals)
5. **Schließen und übernehmen**

### Gewinner-Land-Beziehung hinzufügen:

1. Zurück in der **Modellansicht**:
   - Von: `fact_tender[winner_country_key]`
   - Nach: `dim_country_winner[country_key]`
   - Kardinalität: Viele zu Eins (*:1)
   - **Aktiv machen:** ✅

**Ergebnis:** 5 Tabellen im Modell, 4 aktive Beziehungen.

```
dim_country ──────────< fact_tender >──────── dim_procedure_type
     (country_key)      │    (procedure_key)
                        │
dim_cpv ───────────────┤
     (cpv_key)          │
                        │
dim_country_winner ─────┘
     (winner_country_key)
```

---

## Schritt 5: CPV-Hierarchie anlegen

1. In der **Modellansicht** auf Tabelle `dim_cpv` klicken
2. Spalten in dieser Reihenfolge markieren: `cpv_division` → `cpv_group` → `cpv_class` → `cpv_code`
3. Rechtsklick → **Hierarchie erstellen**
4. Name: `CPV-Hierarchie`
5. Reihenfolge: division (oberste) → group → class → code (unterste)

**Verwendung:** In Visuals die Hierarchie auf die Achse ziehen. Drilldown-Pfeile erscheinen automatisch.

---

## Schritt 6: Als Datumstabelle markieren (Optional)

`fact_tester[year]` ist eine ganze Zahl. Für Zeitintelligenz-Funktionen (eher nicht nötig, aber gute Praxis):

1. Berechnete Tabelle in DAX anlegen: `DatumsTabelle = DISTINCT(SELECTCOLUMNS(fact_tender, "Jahr", fact_tender[year]))`
2. Oder einfach überspringen — unsere Visuals verwenden `year` direkt, kein `SAMEPERIODLASTYEAR` nötig.

---

## Schritt 7: DAX-Measures importieren

1. Datei `src/powerbi/measures.dax` öffnen
2. Für jedes Measure (insgesamt 17):
   - Rechtsklick auf die passende Tabelle:
     - `fact_tender`: Total Tenders, F1-F7 Count/Rate, Total Flagged, Avg Award Value, Award Value, Comb Rates
     - `dim_country`: Avg CPI, Avg WGI-Dimensionen
     - `dim_country_winner`: Winner CPI, Winner WGI
   - **Neues Measure**
   - DAX-Code einfügen
   - Bei allen "Rate"-Measures das **Format** auf **Prozent** (0,0 %) stellen (Measure-Tools → Format)

---

## Schritt 8: Modell verifizieren

In der Modellansicht prüfen:
- [x] 5 Tabellen geladen (fact_tender + 3 Dims + dim_country_winner)
- [x] 4 aktive Beziehungen (alle *:1, einfache Filterrichtung)
- [x] Keine mehrdeutigen Pfade
- [x] CPV-Hierarchie angelegt
- [x] Alle Measures definiert und liefern Werte (testen mit einem **Kachel**-Visual)

---

## Referenz: Wichtige Spaltennamen für Visuals

### Dimensions-Attribute

| Attribut | Tabelle | Verwendung |
|----------|---------|------------|
| `country_name` | dim_country | Ländernamen (Achse, Legende) |
| `country_code` | dim_country | Kurzbezeichnung (DE, DK, RO, HU) |
| `cpi_score` | dim_country | Governance-Analyse (0–100) |
| `control_of_corruption` bis `voice_accountability` | dim_country | WGI-Dimensionen (-2,5 bis +2,5) |
| `country_name` | dim_country_winner | Gewinner-Länder (Achse, Legende) |
| `cpv_division`, `cpv_group`, `cpv_class`, `cpv_code` | dim_cpv | CPV-Drilldown (Hierarchie) |
| `procedure_name`, `procedure_code` | dim_procedure_type | Verfahrensart-Beschriftung |
| `transparency_level` | dim_procedure_type | Ordinalskala 1–5 |
| `is_open` | dim_procedure_type | Wahr/Falsch-Filter |

### Fakten-Maße & Dimensionen

| Attribut | Tabelle | Verwendung |
|----------|---------|------------|
| `year` | fact_tender | Zeitachse (2014–2023) |
| `crisis_type` | fact_tender | COVID/Ukraine-Gruppierung |
| `award_value_eur` | fact_tender | Wert-Analyse |
| `number_offers` | fact_tender | Wettbewerbs-Analyse |
| `lots_number`, `number_awards` | fact_tender | Fragmentierungs-Analyse |
| `F1` bis `F7` | fact_tender | Boolesche Red Flags (Filter/Slicer) |

---

## Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| **Exasol erscheint NICHT** in Daten abrufen → Datenbank | 1) Prüfen: `Exasol.mez` in `C:\Users\Johannes\Documents\Microsoft Power BI Desktop\Custom Connectors\` vorhanden? 2) Prüfen: Sicherheitseinstellung (Schritt 0) gesetzt? 3) Power BI komplett neu starten (Taskleiste prüfen!) |
| Verbindung wird abgelehnt | VPN/Netzwerk prüfen; Benutzername/Passwort prüfen |
| DirectQuery 1-Million-Zeilen-Fehler | Niemals `award_id` auf eine Achse legen — nur aggregierte Measures oder Dimensions-Attribute verwenden |
| Leere Werte bei Governance-Scores | SCD2-Lücken? Prüfen ob `merge_dimensions.sql` erfolgreich gelaufen ist |
| Gewinner-Land-Measures liefern nichts | Prüfen ob Beziehung `dim_country_winner[country_key]` in der Modellansicht aktiv ist |
