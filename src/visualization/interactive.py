"""Interaktive Spielfeld-Grafiken mit Plotly (Tooltips, Zoom) für das Streamlit-Dashboard.

Die Spielfeld-Masse kommen aus mplsoccer (pitch_type="impect"), damit das Feld genau gleich ist
wie in den matplotlib-Grafiken.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from mplsoccer import Pitch

from src.visualization.pitch import opponent_name

# Masse des Impect-Spielfelds (Ursprung in der Mitte, 105 x 68 m)
DIM = Pitch(pitch_type="impect").dim

# Farben wie in den matplotlib-Grafiken
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
PITCH_LINES = "#c3c2b7"
FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"

# Grün von hell nach dunkel: je häufiger bespielt, desto intensiver
GREENS = [[0, SURFACE], [0.25, "#c7e9c0"], [0.5, "#74c476"], [0.75, "#238b45"], [1, "#00441b"]]

# Felder für die Heatmap: 6 in der Länge (2 pro Zone), 4 in der Breite
X_EDGES = np.linspace(DIM.left, DIM.right, 7)
Y_EDGES = np.linspace(DIM.bottom, DIM.top, 5)

# Namen der 4 Streifen in der Breite (oben = links aus Sicht des Teams mit Ball)
Y_NAMES = ["rechts aussen", "rechts innen", "links innen", "links aussen"]


def line(x0: float, y0: float, x1: float, y1: float) -> dict:
    """Eine gerade Spielfeldlinie als Plotly-Form."""
    return dict(type="line", x0=x0, y0=y0, x1=x1, y1=y1, line=dict(color=PITCH_LINES, width=1.5), layer="above")


def rect(x0: float, y0: float, x1: float, y1: float) -> dict:
    """Ein Rechteck (Strafraum, Torraum, Tor) als Plotly-Form."""
    return dict(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, line=dict(color=PITCH_LINES, width=1.5), layer="above")


def penalty_arc(side: int) -> dict:
    """Teilkreis vor dem Strafraum (9.15 m um den Elfmeterpunkt), side = -1 links, 1 rechts."""
    spot = side * DIM.penalty_right
    angles = np.linspace(-np.pi / 2, np.pi / 2, 60)
    x = spot - side * 9.15 * np.cos(angles)
    y = 9.15 * np.sin(angles)

    # Nur der Teil ausserhalb des Strafraums
    outside = np.abs(x) < DIM.penalty_area_right
    path = "M " + " L ".join(f"{a:.2f},{b:.2f}" for a, b in zip(x[outside], y[outside]))
    return dict(type="path", path=path, line=dict(color=PITCH_LINES, width=1.5), layer="above")


def pitch_figure(height: int = 560) -> go.Figure:
    """Leeres Impect-Spielfeld als Plotly-Grafik."""
    r = DIM.circle_diameter / 2
    shapes = [
        # Aussenlinien und Mittellinie
        rect(DIM.left, DIM.bottom, DIM.right, DIM.top),
        line(0, DIM.bottom, 0, DIM.top),
        # Mittelkreis
        dict(type="circle", x0=-r, y0=-r, x1=r, y1=r, line=dict(color=PITCH_LINES, width=1.5), layer="above"),
    ]

    # Strafräume, Torräume, Tore und Teilkreise auf beiden Seiten
    for side in (-1, 1):
        edge = side * DIM.right
        shapes += [
            rect(edge, DIM.penalty_area_bottom, side * DIM.penalty_area_right, DIM.penalty_area_top),
            rect(edge, DIM.six_yard_bottom, side * DIM.six_yard_right, DIM.six_yard_top),
            rect(edge, DIM.goal_bottom, edge + side * DIM.goal_length, DIM.goal_top),
            penalty_arc(side),
        ]

    fig = go.Figure()
    fig.update_layout(
        shapes=shapes,
        height=height,
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        font=dict(family=FONT, color=INK),
        margin=dict(l=10, r=10, t=70, b=10),
        # Gleicher Massstab in x und y, Achsen ausblenden. constrain="domain": bei anderer Fenstergrösse
        # wird die Zeichenfläche angepasst, nicht der Ausschnitt (sonst wird das Feld winzig)
        # Links und rechts etwas mehr Platz für die Beschriftung der Tore
        xaxis=dict(range=[DIM.left - 8, DIM.right + 8], visible=False, constrain="domain"),
        yaxis=dict(range=[DIM.bottom - 3, DIM.top + 3], visible=False, scaleanchor="x", scaleratio=1, constrain="domain"),
    )
    return fig


def add_teams(fig: go.Figure, squad: str, opponent: str) -> None:
    """Neben den Toren beschriften, wessen Tor es ist: eigenes Tor links, Tor des Gegners rechts."""
    style = dict(xref="x", yref="y", y=0, showarrow=False, font=dict(size=12, color=INK_SECONDARY))
    fig.add_annotation(x=DIM.left - 4.5, text=f"{squad}<br>eigenes Tor", textangle=-90, **style)
    fig.add_annotation(x=DIM.right + 4.5, text=f"{opponent}<br>Tor des Gegners", textangle=90, **style)


def zone_of(x: float) -> int:
    """Zone 1/2/3 aus der x-Koordinate (Feld in Drittel)."""
    return int(np.digitize(x, [-17.5, 17.5])) + 1


def plot_activity_heatmap(events: pd.DataFrame, squad: str, opacity: float = 0.85, passes_only: bool = False) -> go.Figure:
    """Grüne Heatmap: Wo spielt das Team mit Ball? Je häufiger ein Feld bespielt wird, desto dunkler grün."""
    # Aktionen des Teams mit Ball (optional nur Pässe), Startpunkt der Aktion
    own = events[(events.squadName == squad) & events.inPossession & events.startAdjCoordinatesX.notna()]
    if passes_only:
        own = own[own.actionType == "PASS"]

    # Anzahl Aktionen pro Feld (Zeilen = Breite, Spalten = Länge)
    counts, _, _ = np.histogram2d(own.startAdjCoordinatesY, own.startAdjCoordinatesX, bins=[Y_EDGES, X_EDGES])
    shares = counts / counts.sum() if counts.sum() else counts

    # Text für den Tooltip pro Feld
    x_centers = (X_EDGES[:-1] + X_EDGES[1:]) / 2
    y_centers = (Y_EDGES[:-1] + Y_EDGES[1:]) / 2
    hover = [[f"Zone {zone_of(x)} | {Y_NAMES[row]}<br>{int(counts[row, col])} Aktionen | {shares[row, col]:.0%}"
              for col, x in enumerate(x_centers)] for row in range(len(y_centers))]

    fig = pitch_figure()
    fig.add_trace(go.Heatmap(
        x=x_centers, y=y_centers, z=shares,
        colorscale=GREENS, zmin=0, opacity=opacity,
        xgap=3, ygap=3, showscale=False,
        text=hover, hovertemplate="%{text}<extra></extra>",
        texttemplate="%{z:.0%}", textfont=dict(size=13),
    ))
    add_teams(fig, squad, opponent_name(events, squad))

    what = "Pässe" if passes_only else "Ballaktionen"
    fig.update_layout(title=dict(
        text=f"<b>Wo spielen wir?</b><br><span style='font-size:13px;color:{INK_SECONDARY}'>"
             f"{squad} | {len(own)} {what} | Anteil pro Feld | Spielrichtung →</span>",
        x=0.01, xanchor="left", font=dict(size=18),
    ))
    return fig
