"""Testet Schritt 7: Kennzahlen zu Spielaufbau und Gegnerdruck.

Start aus dem Projektordner: python -m notebooks.test_kennzahlen
"""

import pandas as pd

from src.events.sequences import build_sequences
from src.features.actions import add_action_features
from src.features.zones import add_zone_features
from src.ingestion.impect_api import read_local_events
from src.menu import choose_local_match
from src.metrics.buildup import buildup_from_zone1, pressing_height
from src.preprocessing.clean import clean_events

pd.set_option("display.width", 200)

# Spiel aus data/raw wählen (kein Login nötig)
match_id = choose_local_match()

# Ganze Pipeline bis zu den Sequenzen
events = add_action_features(add_zone_features(clean_events(read_local_events(match_id))))
sequences = build_sequences(events)

# Spielaufbau gesamt und nach Phase
print("\nSpielaufbau ab Zone 1 (gesamt):")
print(buildup_from_zone1(sequences, by_phase=False).to_string(index=False))

print("\nSpielaufbau ab Zone 1 (nach Phase):")
print(buildup_from_zone1(sequences).to_string(index=False))

# Wo presst der Gegner?
print("\nGegnerdruck (wo kommt das Team mit Ball unter Druck?):")
print(pressing_height(events).to_string(index=False))
