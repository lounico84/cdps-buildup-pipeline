import matplotlib.pyplot as plt
import pandas as pd
from mplsoccer import Pitch

from src.config import PITCH_X_MIN
from src.metrics.buildup import PHASE_LABELS

# Grenzen der Zonen auf der x-Achse (Feld in Drittel à 35 m)
ZONE_EDGES = [-52.5, -17.5, 17.5, 52.5]
ZONE_COLORS = ["#dbe9f6", "#9ecae1", "#4292c6"]

# Seiten auf der y-Achse (links = oben, aus Sicht des Teams mit Ball): Grenzen und Mitte
SIDE_BANDS = {"links": (9.15, 34), "Mitte": (-9.15, 9.15), "rechts": (-34, -9.15)}
SIDE_CENTERS = {"links": 21.6, "Mitte": 0, "rechts": -21.6}


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


def draw_side_arrows(
    ax: plt.Axes, data: pd.DataFrame, side_col: str, success_col: str, x_start: float, x_end: float,
    direct_col: str | None = None,
) -> None:
    """Ein Pfeil pro Seite (Seite = wo der Versuch startet): Dicke = Anteil der Versuche, Text = Anzahl, Erfolg, Zone 3."""
    # Seiten leicht hinterlegen und beschriften
    for side, (low, high) in SIDE_BANDS.items():
        ax.fill_between([-52.5, 52.5], low, high, color="#f0f0f0" if side == "Mitte" else "#fafafa", zorder=1)
        ax.text(-51, high - 2, side, va="top", fontsize=10, color="#555555", zorder=3)

    # Zonengrenzen gestrichelt, Zonen unten beschriftet
    for x in ZONE_EDGES[1:3]:
        ax.plot([x, x], [-34, 34], color="#4292c6", lw=1.5, ls="--", zorder=2)
    for zone in range(3):
        ax.text((ZONE_EDGES[zone] + ZONE_EDGES[zone + 1]) / 2, -37, f"Zone {zone + 1}", ha="center", va="top", fontsize=10)

    # Nur Ballbesitze mit Versuch
    attempts = data[data[side_col].notna()]
    for side, y in SIDE_CENTERS.items():
        part = attempts[attempts[side_col] == side]
        if part.empty:
            continue

        # Pfeil: je mehr Versuche über diese Seite, desto dicker
        share = len(part) / len(attempts)
        ax.annotate("", xy=(x_end, y), xytext=(x_start, y), zorder=3,
                    arrowprops={"arrowstyle": "-|>", "lw": 2 + 18 * share, "color": "#08306b", "mutation_scale": 25})

        # Text: Anzahl, (direkt in Zone 3), Erfolg des Versuchs, danach Zone 3
        success = part[success_col].astype("boolean").mean()
        lines = [f"{len(part)} Versuche ({share:.0%})"]
        if direct_col:
            lines.append(f"{int(part[direct_col].astype('boolean').sum())} davon direkt in Zone 3")
        lines += [f"{success:.0%} klappen", f"{part.reachedZone3.mean():.0%} danach Zone 3"]
        text = "\n".join(lines)
        ax.text(x_end + 2, y, text, va="center", fontsize=10, zorder=3,
                bbox={"facecolor": "white", "edgecolor": "#cccccc", "pad": 3})


def plot_sides(sequences: pd.DataFrame, squad: str) -> plt.Figure:
    """Links / Mitte / rechts: Über welche Seite raus aus Zone 1 und rein in Zone 3, und wie erfolgreich?"""
    own = sequences[sequences.squadName == squad]

    # Zone 1 -> weiter: Ballbesitze, die in Zone 1 beginnen
    zone1 = own[own.startZone == 1]

    # Zone 2 -> 3: Ballbesitze, in denen das Team den Ball in Zone 2 hatte
    in_zone2 = own[own.inZone2]

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    panels = [
        (axes[0], zone1, "exitSide", "exitSuccess", "exitDirectToZone3", -45, -15, "Raus aus Zone 1", "Kein Versuch nach vorne"),
        (axes[1], in_zone2, "zone3EntrySide", "zone3EntrySuccess", None, -5, 22, "Von Zone 2 in Zone 3", "Kein Versuch in Zone 3"),
    ]
    for ax, data, side_col, success_col, direct_col, x_start, x_end, title, missing in panels:
        draw_pitch(ax)
        draw_side_arrows(ax, data, side_col, success_col, x_start, x_end, direct_col)

        # Titel mit Anzahl Ballbesitze ohne Versuch
        no_attempt = data[side_col].isna().sum()
        ax.set_title(f"{title} ({len(data)} Ballbesitze, {no_attempt} davon: {missing})", fontsize=12)

    fig.suptitle(f"{squad}: Über welche Seite kommen wir nach vorne? (eigenes Tor links)", fontsize=15)
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
