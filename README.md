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
