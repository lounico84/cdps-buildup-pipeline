"""Testet Login, Auswahl von Saison, Mannschaft und Spiel, Events laden und bereinigen.

Start aus dem Projektordner: python -m notebooks.test_verbindung
"""

from src.ingestion.impect_api import connect, get_iterations, get_matches, get_squads, load_events, matches_of_squad
from src.menu import choose
from src.preprocessing.clean import clean_events

# 1. Anmelden
api = connect()

# 2. Saison auswählen
iterations = get_iterations(api)
labels = [f"{row.competitionName} {row.season} (dataVersion {row.dataVersion})" for row in iterations.itertuples()]
iteration = int(iterations.id[choose("Saison wählen:", labels)])

# 3. Mannschaft auswählen
matches = get_matches(api, iteration)
if matches.empty:
    raise SystemExit("Für diese Saison hat Impect noch keine Spiele mit Daten.")
squads = get_squads(matches)
squad = squads[choose("Mannschaft wählen:", squads)]

# 4. Spiel auswählen
squad_matches = matches_of_squad(matches, squad)
labels = [f"{str(row.scheduledDate)[:10]} | {row.homeSquadName} - {row.awaySquadName}" for row in squad_matches.itertuples()]
match_id = int(squad_matches.id[choose("Spiel wählen:", labels)])

# 5. Events laden
raw = load_events(api, match_id)
print(f"\nRohdaten: {raw.shape[0]} Events, {raw.shape[1]} Spalten")

# 6. Bereinigen und ansehen
events = clean_events(raw)
print(f"Bereinigt: {events.shape[0]} Events, {events.shape[1]} Spalten\n")
print(events.head(10).to_string(index=False))

# Welche Werte gibt es? Wichtig für Zonen, Phasen und Druck
print("\nphase:\n", events.phase.value_counts(dropna=False))
print("\nstartPitchPosition:\n", events.startPitchPosition.value_counts(dropna=False))
print("\npressure:\n", events.pressure.describe())
print("\nx-Koordinaten:", events.startAdjCoordinatesX.min(), "bis", events.startAdjCoordinatesX.max())
