# cdps-buildup-pipeline

Projekt im Modul **Datapipelines im Sport** (Data Science & AI, 2. Semester).

## Idee

Impect liefert sehr viele Daten, aber daraus wird nicht ohne Weiteres klar, was im Spiel passiert.
Wir bauen eine Pipeline und ein Dashboard, die sich auf wenige, aussagekräftige Kennzahlen beschränken.

**Leitfrage:** Wie kommen wir mit dem Ball von Zone 1 in Zone 3, und wann entsteht dabei Druck durch den Gegner?

### Fokus

- **Spielaufbau:** Ballbesitz, Progression von Zone 1 → Zone 2 → Zone 3
- **Gegnerdruck:** Auf welcher Höhe presst der Gegner (hoch stehen = früh pressen)?
- **Phasen:** Offensive und Transition (evtl. Umschaltphasen)

## Testen ohne Impect-Zugang

Die Impect-Daten sind lizenziert und deshalb nicht im Repo. Zum Testen gibt es ein
künstliches Spiel im gleichen Format (zufällig erzeugt, Teams „Team Blau“ und „Team Rot“).
Benötigt wird Python 3.11 oder neuer.

```bash
# 1. Repo herunterladen
git clone https://github.com/lounico84/cdps-buildup-pipeline.git
cd cdps-buildup-pipeline

# 2. Umgebung einrichten
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Künstliches Testspiel erzeugen (landet in data/raw)
python -m notebooks.testdaten_erstellen

# 4. Pipeline-Schritte testen (im Menü das Spiel „Team Blau - Team Rot“ wählen)
python -m notebooks.test_zonen        # Zonen und Druck pro Aktion
python -m notebooks.test_sequenzen    # Ballbesitze: von Zone 1 in Zone 2/3?
```

Mit Impect-Zugang: Zugangsdaten in `.env` eintragen (Vorlage `.env.example`) und
`python -m notebooks.test_verbindung` ausführen. Das Skript lädt echte Spiele nach `data/raw`.

## Struktur

```
data/
  raw/            Rohdaten von Impect (nicht im Repo)
  processed/      Aufbereitete Daten (nicht im Repo)
src/
  ingestion/      Laden der Impect-Daten
  preprocessing/  Bereinigung und Aufbereitung
  events/         Event-Verarbeitung (Pässe, Ballbesitzphasen, ...)
  features/       Abgeleitete Merkmale (Zonen, Druckhöhe, ...)
  metrics/        Kennzahlen für Spielaufbau und Druck
notebooks/        Explorative Analysen
dashboard/        Dashboard
tests/            Tests
docs/             Dokumentation
```
