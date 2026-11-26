"""Testet die Passrichtung: vorwärts / seitlich / rückwärts und zur Mitte / nach aussen.

Start aus dem Projektordner: python -m notebooks.test_paesse
"""

import pandas as pd

from src.features.actions import add_action_features
from src.features.passes import add_pass_features
from src.features.zones import add_zone_features
from src.ingestion.impect_api import read_local_events
from src.menu import choose, choose_local_match
from src.preprocessing.clean import clean_events

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)

# Spiel aus data/raw wählen (kein Login nötig)
match_id = choose_local_match()
events = add_pass_features(add_action_features(add_zone_features(clean_events(read_local_events(match_id)))))

# Team wählen, nur seine Pässe mit Ball
squads = sorted(events.squadName.dropna().unique())
squad = squads[choose("Team wählen:", squads)]
passes = events[(events.squadName == squad) & events.inPossession & events.passDirection.notna()]

# Beispiele
columns = ["actionType", "passAngle", "passDirection", "startAdjCoordinatesY", "endAdjCoordinatesY", "passTowardCenter", "result"]
print(f"\n{len(passes)} Pässe. Beispiele:")
print(passes[columns].head(10).to_string(index=False))

# Anzahl und Erfolg pro Richtung und Zone
for col in ["passDirection", "passTowardCenter"]:
    table = passes.groupby(["startZone", col]).passSuccess.agg(pässe="size", erfolgreich="mean")
    table["erfolgreich"] = (table.erfolgreich.astype(float) * 100).round(1)
    print(f"\n{col} pro Zone (Anzahl und Erfolg in %):")
    print(table.unstack(col))
