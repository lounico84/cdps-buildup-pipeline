import matplotlib.pyplot as plt
import pandas as pd
from mplsoccer import Pitch

from src.config import PITCH_X_MIN
from src.metrics.buildup import PHASE_LABELS

# Grenzen der Zonen auf der x-Achse (Feld in Drittel à 35 m)
ZONE_EDGES = [-52.5, -17.5, 17.5, 52.5]
ZONE_COLORS = ["#dbe9f6", "#9ecae1", "#4292c6"]


def draw_pitch(ax: plt.Axes) -> Pitch:
    """Impect-Spielfeld zeichnen (passt ohne Umrechnung zu den adjCoordinates)."""
    # line_zorder=2: Feldlinien über Heatmap und Zonenfarben
    pitch = Pitch(pitch_type="impect", line_color="#555555", pitch_color="white", line_zorder=2)
    pitch.draw(ax=ax)
    return pitch


def plot_buildup(sequences: pd.DataFrame, squad: str) -> plt.Figure:
    """Spielaufbau ab Zone 1: Anteil, der Zone 2 und Zone 3 erreicht, für Offensiv und Transition."""
    # Ballbesitze des Teams, die in Zone 1 beginnen
    zone1 = sequences[(sequences.squadName == squad) & (sequences.startZone == 1)]

    # Zwei Felder nebeneinander: Offensiv und Transition
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, phase in zip(axes, ["IN_POSSESSION", "ATTACKING_TRANSITION"]):
        draw_pitch(ax)
        part = zone1[zone1.phase == phase]

        # Zonen farbig hinterlegen (nur innerhalb des Spielfelds)
        for zone, color in enumerate(ZONE_COLORS):
            ax.fill_between([ZONE_EDGES[zone], ZONE_EDGES[zone + 1]], -34, 34, color=color, alpha=0.5, zorder=1)
            ax.text((ZONE_EDGES[zone] + ZONE_EDGES[zone + 1]) / 2, 28, f"Zone {zone + 1}", ha="center", fontsize=11, zorder=3)

        # Titel mit Anzahl Ballbesitze
        ax.set_title(f"{PHASE_LABELS[phase]}: {len(part)} Ballbesitze ab Zone 1", fontsize=13)
        if part.empty:
            continue

        # Pfeile Zone 1 -> Zone 2 und Zone 1 -> Zone 3 mit Prozent
        for y, target, share in [(8, 2, part.reachedZone2.mean()), (-8, 3, part.reachedZone3.mean())]:
            ax.annotate("", xy=(ZONE_EDGES[target] - 15, y), xytext=(-40, y), zorder=3,
                        arrowprops={"arrowstyle": "-|>", "lw": 3, "color": "#08306b"})
            ax.text(ZONE_EDGES[target] - 13, y, f"{share:.0%}", va="center", fontsize=14, fontweight="bold", zorder=3,
                    bbox={"facecolor": "white", "edgecolor": "none", "pad": 2})

    fig.suptitle(f"{squad}: Wie oft kommen wir von Zone 1 nach vorne?", fontsize=15)
    return fig


def plot_pressure_map(events: pd.DataFrame, squad: str) -> plt.Figure:
    """Heatmap: Wo kommt das Team mit Ball unter Druck? Linie = Median der Druckhöhe."""
    # Eigene Aktionen unter Druck
    pressured = events[(events.squadName == squad) & events.underPressure]

    fig, ax = plt.subplots(figsize=(10, 7))
    pitch = draw_pitch(ax)

    # Anteil der Druck-Aktionen pro Feld (6 x 4 Felder)
    stats = pitch.bin_statistic(pressured.startAdjCoordinatesX, pressured.startAdjCoordinatesY,
                                bins=(6, 4), normalize=True)
    pitch.heatmap(stats, ax=ax, cmap="Reds", edgecolor="white", alpha=0.85)
    pitch.label_heatmap(stats, ax=ax, str_format="{:.0%}", exclude_zeros=True, fontsize=12, ha="center", va="center")

    # Median-Druckhöhe als Linie (nur auf dem Spielfeld), Beschriftung unter dem Feld
    median_x = pressured.metresFromOwnGoal.median() + PITCH_X_MIN
    ax.plot([median_x, median_x], [-34, 34], color="black", lw=2, ls="--", zorder=3)
    ax.text(median_x, -37, f"Median: {median_x - PITCH_X_MIN:.0f} m vom eigenen Tor", ha="center", va="top", fontsize=11)

    ax.set_title(f"{squad}: Wo kommen wir unter Druck? ({len(pressured)} Aktionen, eigenes Tor links)", fontsize=13)
    return fig
