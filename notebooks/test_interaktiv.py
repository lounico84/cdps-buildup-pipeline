"""Testet die interaktiven Plotly-Grafiken: grüne Heatmap, Passpfeile, Passströme und Ampel.

Start aus dem Projektordner: python -m notebooks.test_interaktiv
Die Grafiken werden als HTML-Dateien gespeichert, die Passpfeile werden im Browser geöffnet.
"""

import webbrowser

from src.config import DATA_PROCESSED
from src.features.actions import add_action_features
from src.features.passes import add_pass_features
from src.features.zones import add_zone_features
from src.ingestion.impect_api import read_local_events
from src.menu import choose, choose_local_match
from src.metrics.passes import pass_light
from src.preprocessing.clean import clean_events
from src.visualization.pitch import opponent_name
from src.visualization.interactive import (
    own_passes, plot_activity_heatmap, plot_pass_arrows, plot_pass_flows, plot_pass_light,
)

# Spiel aus data/raw wählen (kein Login nötig)
match_id = choose_local_match()
events = add_pass_features(add_action_features(add_zone_features(clean_events(read_local_events(match_id)))))

# Team wählen
squads = sorted(events.squadName.dropna().unique())
squad = squads[choose("Team wählen:", squads)]

# Pässe des Teams (hier ohne Filter, im Dashboard mit Zone, Phase und Ergebnis)
passes = own_passes(events, squad)

# Alle Grafiken erstellen und als HTML speichern
folder = DATA_PROCESSED / "grafiken"
folder.mkdir(parents=True, exist_ok=True)
name = f"{match_id}_{squad.replace(' ', '_')}"
figures = {
    "heatmap": plot_activity_heatmap(events, squad),
    "passpfeile": plot_pass_arrows(passes, squad, opponent_name(events, squad)),
    "passstroeme": plot_pass_flows(passes, squad, opponent_name(events, squad)),
    "ampel": plot_pass_light(pass_light(events, squad), squad),
}
print("\nGespeichert:")
for key, figure in figures.items():
    path = folder / f"{name}_{key}.html"
    figure.write_html(path, include_plotlyjs="cdn")
    print(f"  {path}")

# Passpfeile im Browser öffnen
webbrowser.open((folder / f"{name}_passpfeile.html").as_uri())
