"""Einfaches Dashboard für Coaches: Spielaufbau von Zone 1 nach vorne.

Start aus dem Projektordner: streamlit run dashboard/app.py
Vorher die Pipeline ausführen (python -m src.pipeline), sie erzeugt die Daten in data/processed.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Projektordner zum Suchpfad hinzufügen, damit "from src..." funktioniert
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import DATA_PROCESSED
from src.visualization.interactive import own_passes, plot_activity_heatmap, plot_pass_arrows
from src.visualization.pitch import opponent_name, plot_buildup, plot_sides

st.set_page_config(page_title="Spielaufbau", layout="wide")
st.title("Spielaufbau: Wie kommen wir von Zone 1 nach vorne?")

# Mannschaften = Ordner in data/processed, für die die Pipeline gelaufen ist
teams = sorted(folder.name for folder in DATA_PROCESSED.iterdir() if (folder / "sequences.parquet").exists())
if not teams:
    st.error("Keine Daten gefunden. Zuerst die Pipeline ausführen: python -m src.pipeline")
    st.stop()

# Auswahl in der Seitenleiste: Mannschaft (Ordnername mit Leerzeichen statt _ anzeigen)
folder_name = st.sidebar.selectbox("Mannschaft", teams, format_func=lambda name: name.replace("_", " "))
folder = DATA_PROCESSED / folder_name

# Mannschaftsname = Ordnername mit Leerzeichen statt _
squad = folder_name.replace("_", " ")

# Ballbesitze, Events und Spielliste laden
sequences = pd.read_parquet(folder / "sequences.parquet")
events = pd.read_parquet(folder / "events.parquet")
matches = pd.read_csv(folder / "spiele.csv", encoding="utf-8-sig")

# Alte Daten ohne die neuen Spalten erkennen
if "inZone2" not in sequences.columns or "passDirection" not in events.columns:
    st.warning("Die Daten sind veraltet. Bitte die Pipeline für diese Mannschaft nochmals ausführen.")
    st.stop()

# Auswahl in der Seitenleiste: alle Spiele oder ein einzelnes
# Resultat anzeigen, falls die Pipeline es schon berechnet hat (ältere Daten haben es nicht)
result = matches.Resultat if "Resultat" in matches.columns else pd.Series("", index=matches.index)
labels = ["Alle Spiele"] + [f"{row.Datum} gegen {row.Gegner} ({row.Ort}) {res}" for row, res in zip(matches.itertuples(), result)]
choice = st.sidebar.selectbox("Spiel", labels)
if choice != "Alle Spiele":
    match_id = matches.Spiel[labels.index(choice) - 1]
    sequences = sequences[sequences.matchId == match_id]
    events = events[events.matchId == match_id]

# Kennzahlen der eigenen Mannschaft: Ballbesitze ab Zone 1
zone1 = sequences[(sequences.squadName == squad) & (sequences.startZone == 1)]
col1, col2, col3 = st.columns(3)
col1.metric("Ballbesitze ab Zone 1", len(zone1))
col2.metric("Zone 2 erreicht", f"{zone1.reachedZone2.mean():.0%}")
col3.metric("Zone 3 erreicht", f"{zone1.reachedZone3.mean():.0%}")

# Interaktive Heatmap (Plotly): Regler für Deckkraft und Art der Aktionen
left, right = st.columns(2)
opacity = left.slider("Deckkraft der Heatmap", min_value=0.2, max_value=1.0, value=0.85, step=0.05)
what = right.radio("Was zählt?", ["Alle Ballaktionen", "Nur Pässe"], horizontal=True)
heatmap = plot_activity_heatmap(events, squad, opacity=opacity, passes_only=what == "Nur Pässe")
st.plotly_chart(heatmap, width="stretch", theme=None)

# Alle Pässe als Pfeile (ohne Filter, damit man die ganze Menge sieht), Regler für die Deckkraft
pass_opacity = st.slider("Deckkraft der Passpfeile", min_value=0.1, max_value=1.0, value=0.5, step=0.05)
arrows = plot_pass_arrows(own_passes(events, squad), squad, opponent_name(events, squad), opacity=pass_opacity)
st.plotly_chart(arrows, width="stretch", theme=None)

# Grafiken (Titel stehen in der Grafik): Offensiv gegen Transition, dann links / Mitte / rechts
st.pyplot(plot_buildup(sequences, squad))
st.pyplot(plot_sides(sequences, squad))
