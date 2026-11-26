"""Testet die Ballbesitz-Definitionen: Zone nur erreicht oder kontrolliert? Und das Ergebnis ab Zone 1.

Start aus dem Projektordner: python -m notebooks.test_ballbesitz
"""

import pandas as pd

from src.events.possession import add_control
from src.events.sequences import build_sequences
from src.features.actions import add_action_features
from src.features.zones import add_zone_features
from src.ingestion.impect_api import read_local_events
from src.menu import choose, choose_local_match
from src.preprocessing.clean import clean_events

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)

# Spiel aus data/raw wählen (kein Login nötig)
match_id = choose_local_match()
events = add_action_features(add_zone_features(clean_events(read_local_events(match_id))))
sequences = build_sequences(events)

# Team wählen
squads = sorted(sequences.squadName.unique())
squad = squads[choose("Team wählen:", squads)]

# Alle Varianten durchrechnen: Anzahl Pässe (0 = nur erreicht) und optional Mindestzeit
rows = []
for min_seconds in [None, 5, 10]:
    for min_passes in [0, 1, 2, 3]:
        result = add_control(events, sequences, min_passes, min_seconds)
        zone1 = result[(result.squadName == squad) & (result.startZone == 1)]
        rows.append({
            "Pässe": min_passes,
            "Sekunden": min_seconds or "-",
            "Zone 2 kontrolliert (%)": round(zone1.zone2Controlled.mean() * 100, 1),
            "Zone 3 kontrolliert (%)": round(zone1.zone3Controlled.mean() * 100, 1),
        })
print(f"\n{squad}: Ballbesitze ab Zone 1, je nach Definition von 'kontrolliert'")
print(pd.DataFrame(rows).to_string(index=False))

# Ergebnis ab Zone 1 mit der Standard-Definition aus config.py, nach erstem Versuch raus aus Zone 1
result = add_control(events, sequences)
zone1 = result[(result.squadName == squad) & (result.startZone == 1)]
print("\nErgebnis ab Zone 1 (Standard-Definition) nach erstem Versuch nach vorne (Anzahl):")
print(pd.crosstab(zone1.exitCategory.fillna("Kein Versuch nach vorne"), zone1.zone1Outcome, margins=True, margins_name="Total"))
