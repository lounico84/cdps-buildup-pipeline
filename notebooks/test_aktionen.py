"""Testet Schritt 2: Aktionstyp und Seite pro Event.

Start aus dem Projektordner: python -m notebooks.test_aktionen
"""

import pandas as pd

from src.features.actions import add_action_features
from src.features.zones import add_zone_features
from src.ingestion.impect_api import read_local_events
from src.menu import choose_local_match
from src.preprocessing.clean import clean_events

pd.set_option("display.width", 200)

# Spiel aus data/raw wählen (kein Login nötig)
match_id = choose_local_match()

# Bereinigen, Zonen und Aktionstyp ergänzen
events = add_action_features(add_zone_features(clean_events(read_local_events(match_id))))

# Nur Pässe und Dribblings des Teams mit Ball
own = events[events.inPossession & events.actionCategory.notna()]

# Beispiele
columns = ["squadName", "actionType", "action", "passDistance", "actionCategory", "startLane", "startSide", "endSide"]
print("\nBeispiel-Aktionen:")
print(own[columns].head(12).to_string(index=False))

# Wie oft welcher Aktionstyp?
print("\nAktionstyp pro Team (Anzahl):")
print(own.groupby(["squadName", "actionCategory"]).size().unstack(fill_value=0))

# Über welche Seite spielt ein Team?
print("\nStartseite der Aktionen pro Team (%):")
print((pd.crosstab(own.squadName, own.startSide, normalize="index") * 100).round(1))

# Nur Aktionen in Zone 1: wie wird dort aufgebaut?
print("\nAktionstyp in Zone 1 pro Team (%):")
zone1 = own[own.startZone == 1]
print((pd.crosstab(zone1.squadName, zone1.actionCategory, normalize="index") * 100).round(1))
