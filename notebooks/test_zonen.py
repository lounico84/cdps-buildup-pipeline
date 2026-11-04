"""Testet Schritt 5: Zonen und Druck pro Event.

Start aus dem Projektordner: python -m notebooks.test_zonen
"""

from src.features.zones import add_zone_features
from src.ingestion.impect_api import read_local_events
from src.menu import choose_local_match
from src.preprocessing.clean import clean_events

# Spiel aus data/raw wählen (kein Login nötig)
match_id = choose_local_match()

# Bereinigen und Zonen ergänzen
events = add_zone_features(clean_events(read_local_events(match_id)))

# Beispiel-Events mit den neuen Spalten
columns = ["squadName", "actionType", "startPitchPosition", "startZone", "metresFromOwnGoal", "pressure", "inPossession", "underPressure"]
print("\nBeispiel-Events:")
print(events[columns].head(15).to_string(index=False))

# Nur Aktionen des Teams mit Ball
own = events[events.inPossession]

# Wie viele Aktionen pro Team und Zone?
print("\nAktionen mit Ball pro Zone:")
print(own.groupby(["squadName", "startZone"]).size().unstack())

# Wie oft unter Druck pro Team und Zone?
print("\nAnteil unter Druck pro Zone (%):")
print((own.groupby(["squadName", "startZone"]).underPressure.mean() * 100).round(1).unstack())

# Wo entsteht der Druck? Median-Distanz zum eigenen Tor
print("\nDruck entsteht im Median so weit vom eigenen Tor weg (m):")
print(own[own.underPressure].groupby("squadName").metresFromOwnGoal.median().round(1))
