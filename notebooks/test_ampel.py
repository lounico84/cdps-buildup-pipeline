"""Testet die Kennzahlen zu Ballbesitz-Definitionen, Ergebnis ab Zone 1 und Passrichtungs-Ampel.

Rechnet über alle Spiele in data/raw, an denen das gewählte Team beteiligt ist (für die Ampel braucht es viele Pässe).
Start aus dem Projektordner: python -m notebooks.test_ampel
"""

import pandas as pd

from src.events.possession import add_control
from src.events.sequences import build_sequences
from src.features.actions import add_action_features
from src.features.passes import add_pass_features
from src.features.zones import add_zone_features
from src.ingestion.impect_api import get_local_matches, get_squads, matches_of_squad, read_local_events
from src.menu import choose
from src.metrics.passes import mean_direction, pass_light
from src.metrics.possession import compare_definitions, zone1_outcomes
from src.preprocessing.clean import clean_events

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)

# Team wählen, dann alle seine lokalen Spiele laden
matches = get_local_matches()
squads = get_squads(matches)
squad = squads[choose("Team wählen:", squads)]
match_ids = matches_of_squad(matches, squad).matchId.tolist()
print(f"\n{squad}: {len(match_ids)} Spiele")

# Pipeline bis zu den Ballbesitzen für jedes Spiel
events = pd.concat([
    add_pass_features(add_action_features(add_zone_features(clean_events(read_local_events(m))))) for m in match_ids
], ignore_index=True)
sequences = pd.concat([build_sequences(events[events.matchId == m]) for m in match_ids], ignore_index=True)

# 1. Wie stark hängt das Ergebnis von der Definition ab?
print("\nBallbesitze ab Zone 1 je nach Definition von 'kontrolliert':")
print(compare_definitions(events, sequences, squad).to_string(index=False))

# 2. Ergebnis ab Zone 1 nach erstem Versuch (Standard-Definition aus config.py)
print("\nErgebnis ab Zone 1 nach erstem Versuch nach vorne:")
print(zone1_outcomes(add_control(events, sequences), squad).to_string(index=False))

# 3. Durchschnittliche Passrichtung pro Zone
print("\nDurchschnittliche Passrichtung (0 = vorwärts, 90 = links, 270 = rechts):")
print(mean_direction(events, squad).to_string(index=False))

# 4. Ampel: zur Mitte / nach aussen, verglichen mit Pässen aus gleicher Zone in gleicher Richtung
print("\nAmpel: Erfolg zur Mitte / nach aussen im Vergleich zu Pässen gleicher Zone und Richtung:")
print(pass_light(events, squad).to_string(index=False))
