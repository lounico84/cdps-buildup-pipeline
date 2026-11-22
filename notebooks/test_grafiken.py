"""Testet Schritt 7b: Grafiken auf dem Spielfeld mit mplsoccer.

Start aus dem Projektordner: python -m notebooks.test_grafiken
Die Bilder werden in data/processed/grafiken gespeichert.
"""

from src.config import DATA_PROCESSED
from src.events.sequences import build_sequences
from src.features.actions import add_action_features
from src.features.zones import add_zone_features
from src.ingestion.impect_api import read_local_events
from src.menu import choose, choose_local_match
from src.preprocessing.clean import clean_events
from src.visualization.pitch import plot_buildup, plot_pressure_map

# Spiel aus data/raw wählen (kein Login nötig)
match_id = choose_local_match()

# Ganze Pipeline bis zu den Sequenzen
events = add_action_features(add_zone_features(clean_events(read_local_events(match_id))))
sequences = build_sequences(events)

# Team wählen
squads = sorted(sequences.squadName.unique())
squad = squads[choose("Team wählen:", squads)]

# Ordner für die Bilder
folder = DATA_PROCESSED / "grafiken"
folder.mkdir(parents=True, exist_ok=True)
name = f"{match_id}_{squad.replace(' ', '_')}"

# Grafiken erstellen und speichern
plot_buildup(sequences, squad).savefig(folder / f"{name}_spielaufbau.png", dpi=120, bbox_inches="tight")
plot_pressure_map(events, squad).savefig(folder / f"{name}_druck.png", dpi=120, bbox_inches="tight")

print(f"\nGrafiken gespeichert in {folder}:")
print(f"  {name}_spielaufbau.png")
print(f"  {name}_druck.png")
