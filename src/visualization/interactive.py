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
        margin=dict(l=10, r=10, t=90, b=10),
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


# Farben für die Passrichtung (drei gut unterscheidbare Farben, auch bei Farbsehschwäche)
DIRECTION_COLORS = {"vorwärts": "#2a78d6", "seitlich": "#eb6834", "rückwärts": "#1baf7a"}

# Blau von hell nach dunkel für die Häufigkeit der Passströme
BLUES = [[0, "#cde2fb"], [0.5, "#5598e7"], [1, "#0d366b"]]

# Ampelfarben mit Zeichen, damit die Bedeutung nicht nur an der Farbe hängt.
# Gelb (kein klarer Unterschied) bewusst hell, damit Grün und Rot hervorstechen
LIGHT_COLORS = {"grün": "#0ca30c", "gelb": "#fbe3a6", "rot": "#d03b3b", "grau": "#f0efec"}
LIGHT_SYMBOLS = {"grün": "▲", "gelb": "●", "rot": "▼", "grau": "○"}


def minute(seconds: float) -> int:
    """Spielminute aus gameTimeInSec (Impect: 2. Halbzeit startet bei 10'000 s, Verlängerung bei 20'000 / 30'000 s)."""
    start = {0: 0, 1: 45, 2: 90, 3: 105}.get(int(seconds // 10_000), 0)
    return start + int(seconds % 10_000 // 60) + 1


def own_passes(events: pd.DataFrame, squad: str, zones: list[int] | None = None, phases: list[str] | None = None,
               result: str = "Alle") -> pd.DataFrame:
    """Pässe des Teams mit Ball, gefiltert nach Startzone, Phase und Ergebnis."""
    passes = events[(events.squadName == squad) & events.inPossession & events.passDirection.notna()
                    & events.endAdjCoordinatesX.notna()]
    if zones:
        passes = passes[passes.startZone.isin(zones)]
    if phases:
        passes = passes[passes.phase.isin(phases)]
    if result == "Erfolgreich":
        passes = passes[passes.passSuccess.astype(bool)]
    elif result == "Misslungen":
        passes = passes[~passes.passSuccess.astype(bool)]
    return passes


def plot_pass_arrows(passes: pd.DataFrame, squad: str, opponent: str = "Gegner", opacity: float = 0.6) -> go.Figure:
    """Jeder Pass als Linie vom Start zum Ziel, Farbe = Richtung, Punkt am Ziel (Tooltip mit Details)."""
    fig = pitch_figure()

    for direction, color in DIRECTION_COLORS.items():
        part = passes[passes.passDirection == direction]
        if part.empty:
            continue

        # Alle Linien einer Richtung in einer Spur: Start, Ziel, Lücke (None), nächster Pass ...
        x = np.column_stack([part.startAdjCoordinatesX, part.endAdjCoordinatesX, np.full(len(part), np.nan)]).ravel()
        y = np.column_stack([part.startAdjCoordinatesY, part.endAdjCoordinatesY, np.full(len(part), np.nan)]).ravel()
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=color, width=1.5), opacity=opacity,
                                 hoverinfo="skip", legendgroup=direction, showlegend=False))

        # Punkt am Ziel: offen = misslungen, gefüllt = angekommen
        success = part.passSuccess.astype(bool)
        hover = [f"{p}<br>{d} | {'angekommen' if ok else 'misslungen'}<br>Minute {minute(t)}"
                 for p, d, ok, t in zip(part.playerName, part.passDirection, success, part.gameTimeInSec)]
        fig.add_trace(go.Scatter(
            x=part.endAdjCoordinatesX, y=part.endAdjCoordinatesY, mode="markers", name=f"{direction} ({len(part)})",
            marker=dict(color=np.where(success, color, SURFACE), size=7, line=dict(color=color, width=1.5)),
            opacity=min(1.0, opacity + 0.3), text=hover, hovertemplate="%{text}<extra></extra>", legendgroup=direction,
        ))

    add_teams(fig, squad, opponent)
    fig.update_layout(
        title=dict(text=f"<b>Wohin spielen wir die Pässe?</b><br><span style='font-size:13px;color:{INK_SECONDARY}'>"
                        f"{squad} | {len(passes)} Pässe | Farbe = Richtung | Spielrichtung →<br>"
                        f"Punkt am Ziel: gefüllt = angekommen, offen = misslungen</span>", x=0.01, xanchor="left", font=dict(size=18)),
        legend=dict(orientation="h", y=-0.02, x=0.5, xanchor="center", title_text="Richtung (anklicken zum Ein-/Ausblenden): "),
    )
    return fig


def plot_pass_flows(passes: pd.DataFrame, squad: str, opponent: str = "Gegner") -> go.Figure:
    """Ein Pfeil pro Feld: zeigt in die durchschnittliche Passrichtung, je mehr Pässe, desto dunkler."""
    fig = pitch_figure()

    # Feld (6 x 4) für jeden Pass bestimmen
    passes = passes.assign(
        col=np.clip(np.digitize(passes.startAdjCoordinatesX, X_EDGES[1:-1]), 0, 5),
        row=np.clip(np.digitize(passes.startAdjCoordinatesY, Y_EDGES[1:-1]), 0, 3),
    )
    cells = []
    for (row, col), part in passes.groupby(["row", "col"]):
        # Durchschnittliche Richtung als Vektormittel der Winkel
        radians = np.deg2rad(part.passAngle)
        sin, cos = np.sin(radians).mean(), np.cos(radians).mean()
        cells.append(dict(x=(X_EDGES[col] + X_EDGES[col + 1]) / 2, y=(Y_EDGES[row] + Y_EDGES[row + 1]) / 2,
                          n=len(part), angle=np.arctan2(sin, cos), concentration=np.hypot(sin, cos),
                          success=part.passSuccess.astype(float).mean(), zone=zone_of(X_EDGES[col] + 1), side=Y_NAMES[row]))
    cells = pd.DataFrame(cells)
    if cells.empty:
        return fig

    # Farbe nach Anzahl Pässe (hell = wenige, dunkel = viele), Pfeile immer gleich lang
    most = cells.n.max()
    for cell in cells.itertuples():
        share = cell.n / most
        color = "#cde2fb" if share < 0.25 else "#5598e7" if share < 0.5 else "#256abf" if share < 0.75 else "#0d366b"
        dx, dy = 7 * np.cos(cell.angle), 7 * np.sin(cell.angle)
        fig.add_annotation(x=cell.x + dx, y=cell.y + dy, ax=cell.x - dx, ay=cell.y - dy, xref="x", yref="y",
                           axref="x", ayref="y", showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=3, arrowcolor=color)

    # Unsichtbare Punkte in der Feldmitte für den Tooltip, Farbskala als Legende
    hover = [f"Zone {c.zone} | {c.side}<br>{c.n} Pässe | {c.success:.0%} angekommen<br>"
             f"mittlere Richtung {np.rad2deg(c.angle) % 360:.0f} Grad | Konzentration {c.concentration:.2f}"
             for c in cells.itertuples()]
    fig.add_trace(go.Scatter(x=cells.x, y=cells.y, mode="markers", text=hover, hovertemplate="%{text}<extra></extra>",
                             marker=dict(size=40, color=cells.n, colorscale=BLUES, opacity=0, showscale=True,
                                         colorbar=dict(title="Pässe", thickness=12, len=0.6))))

    add_teams(fig, squad, opponent)
    fig.update_layout(title=dict(
        text=f"<b>Passströme</b><br><span style='font-size:13px;color:{INK_SECONDARY}'>"
             f"{squad} | {len(passes)} Pässe | Spielrichtung →<br>"
             f"Pfeil = durchschnittliche Richtung ab diesem Feld | dunkler = mehr Pässe</span>", x=0.01, xanchor="left", font=dict(size=18)))
    return fig


def plot_pass_light(light: pd.DataFrame, squad: str) -> go.Figure:
    """Ampel als Raster: Zeilen = Richtung und Kategorie, Spalten = Zone, Farbe = Ampel. Erwartet pass_light()."""
    light = light.rename(columns={"Erfolg (%)": "erfolg", "Intervall (%)": "intervall", "Vergleich (%)": "vergleich"})
    light = light.assign(row=light.Richtung + " | " + light.Kategorie)
    # Feste Reihenfolge von oben nach unten: vorwärts, seitlich, rückwärts (Plotly zählt von unten)
    order = [f"{d} | {c}" for d in ["vorwärts", "seitlich", "rückwärts"] for c in ["zur Mitte", "nach aussen", "gleiche Breite"]]
    rows = [r for r in reversed(order) if r in set(light.row)]
    columns = [f"Zone {z}" for z in sorted(light.Zone.unique())]

    # Pro Feld ein farbiges Rechteck mit Erfolg und Anzahl, Tooltip mit Intervall und Vergleich
    fig = go.Figure()
    for item in light.itertuples():
        x, y = columns.index(f"Zone {item.Zone}"), rows.index(item.row)
        fig.add_shape(type="rect", x0=x - 0.46, x1=x + 0.46, y0=y - 0.42, y1=y + 0.42, line=dict(width=0),
                      fillcolor=LIGHT_COLORS[item.Ampel])
        dark = item.Ampel in ("grün", "rot")
        fig.add_annotation(x=x, y=y, showarrow=False, font=dict(size=13, color="white" if dark else INK),
                           text=f"{LIGHT_SYMBOLS[item.Ampel]} {item.erfolg:.0f} % (n={item.Pässe})")
    hover = [f"{r.row}, Zone {r.Zone}<br>{r.erfolg:.0f} % angekommen (Intervall {r.intervall} %)<br>"
             f"Vergleich gleiche Zone und Richtung: {r.vergleich:.0f} %<br>Ampel: {r.Ampel}" for r in light.itertuples()]
    fig.add_trace(go.Scatter(x=[columns.index(f"Zone {z}") for z in light.Zone], y=[rows.index(r) for r in light.row],
                             mode="markers", marker=dict(size=60, opacity=0, symbol="square"), text=hover,
                             hovertemplate="%{text}<extra></extra>", showlegend=False))

    fig.update_layout(
        height=160 + 48 * len(rows), plot_bgcolor=SURFACE, paper_bgcolor=SURFACE, font=dict(family=FONT, color=INK),
        margin=dict(l=10, r=10, t=140, b=10),
        xaxis=dict(tickvals=list(range(len(columns))), ticktext=columns, side="top", showgrid=False, zeroline=False,
                   range=[-0.5, len(columns) - 0.5]),
        yaxis=dict(tickvals=list(range(len(rows))), ticktext=rows, showgrid=False, zeroline=False,
                   range=[-0.5, len(rows) - 0.5]),
        title=dict(text=f"<b>Ampel: Welche Pässe kommen besser an?</b><br><span style='font-size:13px;color:{INK_SECONDARY}'>"
                        f"{squad} | Vergleich mit Pässen aus gleicher Zone in gleiche Richtung<br>"
                        f"▲ signifikant besser | ● kein klarer Unterschied | ▼ signifikant schlechter | ○ zu wenige Pässe</span>",
                   x=0.01, xanchor="left", font=dict(size=18)),
    )
    return fig
