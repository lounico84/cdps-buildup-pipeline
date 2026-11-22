"""Testet Schritt 6: Ballbesitz-Sequenzen.

Start aus dem Projektordner: python -m notebooks.test_sequenzen
"""

from src.events.sequences import build_sequences
from src.features.actions import add_action_features
from src.features.zones import add_zone_features
from src.ingestion.impect_api import read_local_events
from src.menu import choose_local_match
from src.preprocessing.clean import clean_events

# Spiel aus data/raw wählen (kein Login nötig)
match_id = choose_local_match()

# Bereinigen, Zonen und Aktionstyp ergänzen, Sequenzen bilden
events = add_action_features(add_zone_features(clean_events(read_local_events(match_id))))
sequences = build_sequences(events)

# Beispiel-Sequenzen (nur die wichtigsten Spalten, sonst wird es zu breit)
columns = ["squadName", "phase", "startZone", "maxZone", "passes", "exitCategory", "exitSide", "passesBeforeExit", "zone3EntryCategory", "zone3EntrySide"]
print(f"\n{len(sequences)} Ballbesitze. Die ersten 10:")
print(sequences[columns].head(10).to_string(index=False))

# Wie viele Ballbesitze pro Team und Startzone?
print("\nBallbesitze pro Startzone:")
print(sequences.groupby(["squadName", "startZone"]).size().unstack())

# Nur Ballbesitze, die in Zone 1 beginnen
zone1 = sequences[sequences.startZone == 1]

# Wie oft kommen sie in Zone 2 und Zone 3?
print("\nBallbesitze ab Zone 1: Anteil, der Zone 2 / Zone 3 erreicht (%):")
print((zone1.groupby("squadName")[["reachedZone2", "reachedZone3"]].mean() * 100).round(1))

# Dasselbe nach Phase (Offensiv = IN_POSSESSION, Transition = ATTACKING_TRANSITION)
print("\nDasselbe nach Phase, mit Anzahl Ballbesitze:")
by_phase = zone1.groupby(["squadName", "phase"]).agg(
    ballbesitze=("sequenceIndex", "size"),
    zone2=("reachedZone2", "mean"),
    zone3=("reachedZone3", "mean"),
)
by_phase[["zone2", "zone3"]] = (by_phase[["zone2", "zone3"]] * 100).round(1)
print(by_phase)

# In welcher Zone kommt der erste Druck?
print("\nBallbesitze ab Zone 1: Zone des ersten Drucks (Anzahl):")
print(zone1[zone1.pressured].groupby(["squadName", "firstPressureZone"]).size().unstack(fill_value=0))

# Erster Versuch raus aus Zone 1: wie oft welcher Aktionstyp, wie oft erfolgreich?
exits = zone1[zone1.exitCategory.notna()]
print("\nVersuch raus aus Zone 1 nach Aktionstyp (Anzahl und Erfolg in %):")
print(exits.groupby(["squadName", "exitCategory"]).agg(
    versuche=("exitSuccess", "size"),
    erfolg=("exitSuccess", lambda s: round(s.astype(float).mean() * 100, 1)),
))
print("\nVersuch raus aus Zone 1 nach Seite (Anzahl und Erfolg in %):")
print(exits.groupby(["squadName", "exitSide"]).agg(
    versuche=("exitSuccess", "size"),
    erfolg=("exitSuccess", lambda s: round(s.astype(float).mean() * 100, 1)),
))
print("\nBallbesitze ab Zone 1 ganz ohne Versuch nach vorne:")
print(zone1[zone1.exitCategory.isna()].groupby("squadName").size())

# Gepflegtes Passspiel oder direkt? Pässe in Zone 1 vor dem Versuch
print("\nVersuch raus aus Zone 1: Pässe davor (Anzahl Ballbesitze):")
print(exits.groupby(["squadName", "passesBeforeExit"]).size().unstack(fill_value=0))

# Versuch in Zone 3: Aktionstyp und Seite, mit Erfolg
entries = sequences[sequences.zone3EntryCategory.notna()]
print("\nVersuch in Zone 3 nach Seite (Anzahl und Erfolg in %):")
print(entries.groupby(["squadName", "zone3EntrySide"]).agg(
    versuche=("zone3EntrySuccess", "size"),
    erfolg=("zone3EntrySuccess", lambda s: round(s.astype(float).mean() * 100, 1)),
))
