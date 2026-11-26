"""Dashboard für Coaches: Spielaufbau von Zone 1 nach vorne.

Start aus dem Projektordner: streamlit run dashboard/app.py
Vorher die Pipeline ausführen (python -m src.pipeline), sie erzeugt die Daten in data/processed.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Projektordner zum Suchpfad hinzufügen, damit "from src..." funktioniert
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import DATA_PROCESSED, POSSESSION_MIN_PASSES, POSSESSION_MIN_SECONDS
from src.events.possession import add_control, control_stats
from src.metrics.buildup import PHASE_LABELS
from src.metrics.passes import MIN_PASSES, mean_direction, pass_light
from src.metrics.possession import compare_definitions, zone1_outcomes
from src.visualization.interactive import (
    own_passes, plot_activity_heatmap, plot_pass_arrows, plot_pass_flows, plot_pass_light,
)
from src.visualization.pitch import opponent_name, plot_buildup, plot_sides

st.set_page_config(page_title="Spielaufbau", layout="wide")
st.title("Spielaufbau: Wie kommen wir von Zone 1 nach vorne?")


@st.cache_data
def load(folder_name: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Ballbesitze, Events und Spielliste einer Mannschaft laden (zwischengespeichert)."""
    folder = DATA_PROCESSED / folder_name
    return (
        pd.read_parquet(folder / "sequences.parquet"),
        pd.read_parquet(folder / "events.parquet"),
        pd.read_csv(folder / "spiele.csv", encoding="utf-8-sig"),
    )


@st.cache_data
def stats_for(folder_name: str, match_id: int | None) -> pd.DataFrame:
    """Pass-Serien und Zeiten pro Ballbesitz einmal berechnen (für die Schieberegler der Definition)."""
    _, events, _ = load(folder_name)
    if match_id is not None:
        events = events[events.matchId == match_id]
    return control_stats(events)


# Mannschaften = Ordner in data/processed, für die die Pipeline gelaufen ist
teams = sorted(folder.name for folder in DATA_PROCESSED.iterdir() if (folder / "sequences.parquet").exists())
if not teams:
    st.error("Keine Daten gefunden. Zuerst die Pipeline ausführen: python -m src.pipeline")
    st.stop()

# Auswahl in der Seitenleiste: Mannschaft (Ordnername mit Leerzeichen statt _ anzeigen)
folder_name = st.sidebar.selectbox("Mannschaft", teams, format_func=lambda name: name.replace("_", " "))
squad = folder_name.replace("_", " ")
sequences, events, matches = load(folder_name)

# Alte Daten ohne die neuen Spalten erkennen
if "inZone2" not in sequences.columns or "passDirection" not in events.columns:
    st.warning("Die Daten sind veraltet. Bitte die Pipeline für diese Mannschaft nochmals ausführen.")
    st.stop()

# Auswahl in der Seitenleiste: alle Spiele oder ein einzelnes (mit Resultat, falls vorhanden)
result = matches.Resultat if "Resultat" in matches.columns else pd.Series("", index=matches.index)
labels = ["Alle Spiele"] + [f"{row.Datum} gegen {row.Gegner} ({row.Ort}) {res}" for row, res in zip(matches.itertuples(), result)]
choice = st.sidebar.selectbox("Spiel", labels)
match_id = None
if choice != "Alle Spiele":
    match_id = int(matches.Spiel[labels.index(choice) - 1])
    sequences = sequences[sequences.matchId == match_id]
    events = events[events.matchId == match_id]
opponent = opponent_name(events, squad)

# Vier Bereiche, damit nicht alles auf einer Seite steht
overview, possession, passes_tab, light_tab = st.tabs(["Überblick", "Ballbesitz-Definition", "Pässe", "Ampel"])

# ---------- Überblick ----------
with overview:
    # Kennzahlen der eigenen Mannschaft: Ballbesitze ab Zone 1
    zone1 = sequences[(sequences.squadName == squad) & (sequences.startZone == 1)]
    col1, col2, col3 = st.columns(3)
    col1.metric("Ballbesitze ab Zone 1", len(zone1))
    col2.metric("Zone 2 erreicht", f"{zone1.reachedZone2.mean():.0%}")
    col3.metric("Zone 3 erreicht", f"{zone1.reachedZone3.mean():.0%}")

    # Grüne Heatmap mit Regler für Deckkraft und Art der Aktionen
    left, right = st.columns(2)
    opacity = left.slider("Deckkraft der Heatmap", min_value=0.2, max_value=1.0, value=0.85, step=0.05)
    what = right.radio("Was zählt?", ["Alle Ballaktionen", "Nur Pässe"], horizontal=True)
    heatmap = plot_activity_heatmap(events, squad, opacity=opacity, passes_only=what == "Nur Pässe")
    st.plotly_chart(heatmap, width="stretch", theme=None)

    # Spielaufbau (Offensiv / Transition) und Seiten
    st.pyplot(plot_buildup(sequences, squad))
    st.pyplot(plot_sides(sequences, squad))

# ---------- Ballbesitz-Definition ----------
with possession:
    st.markdown(
        "**Wann gilt eine Zone als kontrolliert?** Nach der Ankunft in der Zone braucht es mindestens so viele "
        "aufeinanderfolgende erfolgreiche Pässe ab dieser Zone (0 = Zone nur erreicht), optional zusätzlich eine "
        "Mindestzeit mit Ball. Die Definition ist mit dem FC St. Gallen abzustimmen."
    )

    # Schieberegler für die Definition (Standard aus config.py)
    left, right = st.columns(2)
    min_passes = left.slider("Aufeinanderfolgende erfolgreiche Pässe", min_value=0, max_value=5, value=POSSESSION_MIN_PASSES)
    seconds_options = ["keine", 3, 5, 10, 15]
    seconds_choice = right.select_slider(
        "Mindestzeit mit Ball nach Ankunft (Sekunden)", options=seconds_options,
        value="keine" if POSSESSION_MIN_SECONDS is None else POSSESSION_MIN_SECONDS,
    )
    min_seconds = None if seconds_choice == "keine" else seconds_choice

    # Kontrolle mit dieser Definition (Pass-Serien sind zwischengespeichert)
    stats = stats_for(folder_name, match_id)
    controlled = add_control(events, sequences, min_passes, min_seconds, stats)
    own_zone1 = controlled[(controlled.squadName == squad) & (controlled.startZone == 1)]

    # Erreicht gegenüber kontrolliert, für Zone 2 und Zone 3
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Zone 2 erreicht", f"{own_zone1.reachedZone2.mean():.0%}")
    col2.metric("Zone 2 kontrolliert", f"{own_zone1.zone2Controlled.mean():.0%}")
    col3.metric("Zone 3 erreicht", f"{own_zone1.reachedZone3.mean():.0%}")
    col4.metric("Zone 3 kontrolliert", f"{own_zone1.zone3Controlled.mean():.0%}")

    # Ergebnis ab Zone 1 nach erstem Versuch: bleibt / Raumgewinn ohne Kontrolle / kontrolliert
    st.subheader("Ergebnis ab Zone 1 nach erstem Versuch nach vorne")
    st.dataframe(zone1_outcomes(controlled, squad), hide_index=True, width="stretch")

    # Alle Varianten nebeneinander
    with st.expander("Alle Definitionen im Vergleich"):
        st.dataframe(compare_definitions(events, sequences, squad, stats=stats), hide_index=True, width="stretch")

# ---------- Pässe ----------
with passes_tab:
    # Filter in einer Reihe: Zone, Phase, Ergebnis, Richtung
    col1, col2, col3, col4 = st.columns(4)
    zones = col1.multiselect("Startzone", [1, 2, 3], default=[1, 2, 3], format_func=lambda z: f"Zone {z}")
    phase_names = col2.multiselect("Phase", list(PHASE_LABELS.values()), default=list(PHASE_LABELS.values()))
    pass_result = col3.radio("Ergebnis", ["Alle", "Erfolgreich", "Misslungen"], horizontal=True)
    directions = col4.multiselect("Passrichtung", ["vorwärts", "seitlich", "rückwärts"], default=["vorwärts", "seitlich", "rückwärts"])

    # Phasen-Namen zurück in Impect-Werte übersetzen
    phases = [key for key, label in PHASE_LABELS.items() if label in phase_names]
    passes = own_passes(events, squad, zones=zones, phases=phases, result=pass_result, directions=directions)

    # Einzelne Passpfeile mit Regler für die Deckkraft
    pass_opacity = st.slider("Deckkraft der Passpfeile", min_value=0.1, max_value=1.0, value=0.5, step=0.05)
    st.plotly_chart(plot_pass_arrows(passes, squad, opponent, opacity=pass_opacity), width="stretch", theme=None)

    # Zusammengefasst: durchschnittliche Richtung pro Feld, Farbe = Anzahl Pässe
    st.plotly_chart(plot_pass_flows(passes, squad, opponent), width="stretch", theme=None)

# ---------- Ampel ----------
with light_tab:
    st.markdown(
        "**Welche Pässe kommen besser an?** Verglichen wird nur mit Pässen aus derselben Zone in dieselbe Richtung. "
        "Grün/Rot: Die Erfolgsquote ist signifikant besser/schlechter (95 %-Konfidenzintervall). "
        f"Grau: weniger als {MIN_PASSES} Pässe. Erfolg heisst nur, dass der Pass ankommt, nicht, wie wertvoll er ist."
    )
    if match_id is not None:
        st.info("In einem einzelnen Spiel sind es meist zu wenige Pässe pro Feld. Für die Ampel besser 'Alle Spiele' wählen.")
    st.plotly_chart(plot_pass_light(pass_light(events, squad), squad), width="stretch", theme=None)

    # Durchschnittliche Passrichtung pro Zone
    st.subheader("Durchschnittliche Passrichtung")
    st.caption("0 Grad = vorwärts, 90 = links, 270 = rechts. Konzentration R: 1 = alle Pässe in dieselbe Richtung, "
               "0 = gleichmässig verteilt. Bei kleinem R sagt die durchschnittliche Richtung wenig aus.")
    st.dataframe(mean_direction(events, squad), hide_index=True)
