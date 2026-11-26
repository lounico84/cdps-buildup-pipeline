"""Testet das interaktive Plotly-Spielfeld: grüne Heatmap mit Tooltips.

Start aus dem Projektordner: python -m notebooks.test_interaktiv
Die Grafik wird als HTML-Datei gespeichert und im Browser geöffnet.
"""

import webbrowser

from src.config import DATA_PROCESSED
from src.features.actions import add_action_features
from src.features.zones import add_zone_features
from src.ingestion.impect_api import read_local_events
from src.menu import choose, choose_local_match
from src.preprocessing.clean import clean_events
from src.visualization.interactive import plot_activity_heatmap

# Spiel aus data/raw wählen (kein Login nötig)
match_id = choose_local_match()
events = add_action_features(add_zone_features(clean_events(read_local_events(match_id))))

# Team wählen
squads = sorted(events.squadName.dropna().unique())
squad = squads[choose("Team wählen:", squads)]

# Heatmap erstellen und als HTML speichern
folder = DATA_PROCESSED / "grafiken"
folder.mkdir(parents=True, exist_ok=True)
path = folder / f"{match_id}_{squad.replace(' ', '_')}_heatmap.html"
plot_activity_heatmap(events, squad).write_html(path, include_plotlyjs="cdn")

# Im Browser öffnen
print(f"\nGespeichert: {path}")
webbrowser.open(path.as_uri())
