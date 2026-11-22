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
from src.visualization.pitch import plot_buildup, plot_sides

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

# Ballbesitze und Spielliste laden
sequences = pd.read_parquet(folder / "sequences.parquet")
matches = pd.read_csv(folder / "spiele.csv", encoding="utf-8-sig")

# Alte Daten ohne die neuen Spalten erkennen
if "inZone2" not in sequences.columns:
    st.warning("Die Daten sind veraltet. Bitte die Pipeline für diese Mannschaft nochmals ausführen.")
    st.stop()

# Auswahl in der Seitenleiste: alle Spiele oder ein einzelnes
labels = ["Alle Spiele"] + [f"{row.Datum} gegen {row.Gegner} ({row.Ort})" for row in matches.itertuples()]
choice = st.sidebar.selectbox("Spiel", labels)
if choice != "Alle Spiele":
    match_id = matches.Spiel[labels.index(choice) - 1]
    sequences = sequences[sequences.matchId == match_id]

# Kennzahlen der eigenen Mannschaft: Ballbesitze ab Zone 1
zone1 = sequences[(sequences.squadName == squad) & (sequences.startZone == 1)]
col1, col2, col3 = st.columns(3)
col1.metric("Ballbesitze ab Zone 1", len(zone1))
col2.metric("Zone 2 erreicht", f"{zone1.reachedZone2.mean():.0%}")
col3.metric("Zone 3 erreicht", f"{zone1.reachedZone3.mean():.0%}")

# Grafiken (Titel stehen in der Grafik): Offensiv gegen Transition, dann links / Mitte / rechts
st.pyplot(plot_buildup(sequences, squad))
st.pyplot(plot_sides(sequences, squad))
