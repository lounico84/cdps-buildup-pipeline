"""Testet Schritt 4b: Wie und über welche Seite kommt ein Team aus Zone 1 raus und von Zone 2 in Zone 3?

Start aus dem Projektordner: python -m notebooks.test_routen
"""

import pandas as pd

from src.events.sequences import build_sequences
from src.features.actions import add_action_features
from src.features.zones import add_zone_features
from src.ingestion.impect_api import read_local_events
from src.menu import choose_local_match
from src.metrics.routes import exit_by_action, exit_by_patience, exit_by_side, zone3_by_action, zone3_by_side
from src.preprocessing.clean import clean_events

pd.set_option("display.width", 200)

# Spiel aus data/raw wählen (kein Login nötig)
match_id = choose_local_match()

# Ganze Pipeline bis zu den Sequenzen
events = add_action_features(add_zone_features(clean_events(read_local_events(match_id))))
sequences = build_sequences(events)

# Raus aus Zone 1
print("\nRaus aus Zone 1: mit welcher Aktion?")
print(exit_by_action(sequences).to_string(index=False))

print("\nRaus aus Zone 1: über welche Seite?")
print(exit_by_side(sequences).to_string(index=False))

print("\nRaus aus Zone 1: gepflegtes Passspiel oder direkt?")
print(exit_by_patience(sequences).to_string(index=False))

# Von Zone 2 in Zone 3
print("\nVon Zone 2 in Zone 3: über welche Seite?")
print(zone3_by_side(sequences).to_string(index=False))

print("\nVon Zone 2 in Zone 3: mit welcher Aktion?")
print(zone3_by_action(sequences).to_string(index=False))

# Beispiel nach Phase (Offensiv / Transition)
print("\nRaus aus Zone 1 nach Phase und Seite:")
print(exit_by_side(sequences, by_phase=True).to_string(index=False))
