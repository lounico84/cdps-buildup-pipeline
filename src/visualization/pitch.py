import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyArrow, FancyBboxPatch
from mplsoccer import Pitch

from src.config import PITCH_X_MIN
from src.metrics.buildup import PHASE_LABELS

# Farben: ruhige Fläche, dunkle Schrift, ein Blau für die Daten
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
MUTED = "#898781"
PITCH_LINES = "#c3c2b7"
BLUE = "#2a78d6"

# Blau von hell nach dunkel für die Heatmap (wenig Druck -> viel Druck)
BLUES = LinearSegmentedColormap.from_list("blues", [SURFACE, "#cde2fb", "#6da7ec", "#2a78d6", "#104281"])

# Schrift: Systemschrift statt Standard von matplotlib
plt.rcParams.update({"font.family": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]})

# Grenzen der Zonen auf der x-Achse (Feld in Drittel à 35 m)
ZONE_EDGES = [-52.5, -17.5, 17.5, 52.5]

# Seiten auf der y-Achse (links = oben, aus Sicht des Teams mit Ball): Grenzen und Mitte
SIDE_BANDS = {"links": (9.15, 34), "Mitte": (-9.15, 9.15), "rechts": (-34, -9.15)}
SIDE_CENTERS = {"links": 21.6, "Mitte": 0, "rechts": -21.6}


def draw_pitch(ax: plt.Axes) -> Pitch:
    """Impect-Spielfeld zeichnen (passt ohne Umrechnung zu den adjCoordinates)."""
    pitch = Pitch(pitch_type="impect", pitch_color=SURFACE, line_color=PITCH_LINES, linewidth=1, line_zorder=2)
    pitch.draw(ax=ax)
    return pitch


def new_figure(ncols: int, title: str, subtitle: str, height: float = 6.4, top: float = 0.78) -> tuple[plt.Figure, list[plt.Axes]]:
    """Leere Grafik mit Titel und Untertitel oben links."""
    fig, axes = plt.subplots(1, ncols, figsize=(8 * ncols, height), facecolor=SURFACE)
    axes = list(axes) if ncols > 1 else [axes]
    fig.text(0.02, 0.97, title, fontsize=17, fontweight="bold", color=INK, va="top")
    fig.text(0.02, 0.97 - 0.38 / height, subtitle, fontsize=11, color=INK_SECONDARY, va="top")
    fig.subplots_adjust(top=top, bottom=0.06, left=0.04, right=0.96, wspace=0.14)
    return fig, axes


def panel_title(ax: plt.Axes, title: str, subtitle: str) -> None:
    """Titel über einem Spielfeld, darunter eine Zeile mit Zusatzinfo."""
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold", color=INK, pad=24)
    ax.text(-52.5, 36, subtitle, fontsize=10, color=INK_SECONDARY, va="bottom")


def draw_zone_lines(ax: plt.Axes) -> None:
    """Zonengrenzen als feine Linien, Zonen unter dem Feld beschriftet."""
    for x in ZONE_EDGES[1:3]:
        ax.plot([x, x], [-34, 34], color=BLUE, alpha=0.35, lw=1, zorder=2)
    for zone in range(3):
        center = (ZONE_EDGES[zone] + ZONE_EDGES[zone + 1]) / 2
        ax.text(center, -36.5, f"Zone {zone + 1}", ha="center", va="top", fontsize=10, color=MUTED)


def opponent_name(data: pd.DataFrame, squad: str) -> str:
    """Name des Gegners, wenn es genau einen gibt (Einzelspiel), sonst "Gegner"."""
    others = set(data.squadName.dropna()) - {squad}
    return others.pop() if len(others) == 1 else "Gegner"


def draw_teams(ax: plt.Axes, squad: str, opponent: str) -> None:
    """Neben den Toren beschriften, wessen Tor es ist: eigenes Tor links, Tor des Gegners rechts."""
    style = dict(ha="center", va="center", fontsize=9.5, color=INK_SECONDARY, linespacing=1.3, clip_on=False)
    ax.text(-58.5, 0, f"{squad}\neigenes Tor", rotation=90, **style)
    ax.text(58.5, 0, f"{opponent}\nTor des Gegners", rotation=270, **style)


def plot_buildup(sequences: pd.DataFrame, squad: str) -> plt.Figure:
    """Spielaufbau ab Zone 1: Wie viele Ballbesitze erreichen Zone 2 und Zone 3? Offensiv und Transition."""
    # Ballbesitze des Teams, die in Zone 1 beginnen
    zone1 = sequences[(sequences.squadName == squad) & (sequences.startZone == 1)]

    fig, axes = new_figure(2, "Wie weit kommen wir von Zone 1 aus?",
                           f"{squad} | Anteil der Ballbesitze ab Zone 1, die Zone 2 und Zone 3 erreichen | Spielrichtung →")
    opponent = opponent_name(sequences, squad)

    for ax, phase in zip(axes, ["IN_POSSESSION", "ATTACKING_TRANSITION"]):
        draw_pitch(ax)
        draw_zone_lines(ax)
        draw_teams(ax, squad, opponent)
        part = zone1[zone1.phase == phase]
        panel_title(ax, PHASE_LABELS[phase], f"{len(part)} Ballbesitze ab Zone 1")
        if part.empty:
            ax.text(0, 0, "Keine Ballbesitze", ha="center", va="center", fontsize=12, color=MUTED)
            continue

        # Pro Zone ein Balken, der von unten wächst: Höhe = Anteil der Ballbesitze, die diese Zone erreichen
        shares = [1.0, part.reachedZone2.mean(), part.reachedZone3.mean()]
        captions = ["starten hier", "erreichen Zone 2", "erreichen Zone 3"]
        baseline = -31
        for zone, (share, caption) in enumerate(zip(shares, captions)):
            left, right = ZONE_EDGES[zone] + 4, ZONE_EDGES[zone + 1] - 4
            height = max(48 * share, 0.5)
            ax.add_patch(FancyBboxPatch((left, baseline), right - left, height,
                                        boxstyle="round,pad=0,rounding_size=1.2", fc=BLUE, ec="none", zorder=3))

            # Zahl und Beschriftung über dem Balken
            center, top = (left + right) / 2, baseline + height
            ax.text(center, top + 5, f"{share:.0%}", ha="center", va="bottom", fontsize=20,
                    fontweight="bold", color=INK, zorder=4)
            ax.text(center, top + 1.2, caption, ha="center", va="bottom", fontsize=10, color=INK_SECONDARY, zorder=4)

    return fig


def draw_side_arrows(
    ax: plt.Axes, data: pd.DataFrame, side_col: str, success_col: str, x_start: float, x_end: float,
    direct_col: str | None = None,
) -> None:
    """Ein Pfeil pro Seite (Seite = wo der Versuch startet): Dicke = Anteil der Versuche, Text = Anzahl, Erfolg, Zone 3."""
    # Seiten mit feinen Linien trennen und beschriften
    for y in (9.15, -9.15):
        ax.plot([-52.5, 52.5], [y, y], color=BLUE, alpha=0.2, lw=1, zorder=2)
    for side, (low, high) in SIDE_BANDS.items():
        ax.text(-51, high - 1.5, side.capitalize(), va="top", fontsize=10, color=MUTED, zorder=4)

    # Nur Ballbesitze mit Versuch
    attempts = data[data[side_col].notna()]
    for side, y in SIDE_CENTERS.items():
        part = attempts[attempts[side_col] == side]
        if part.empty:
            continue

        # Pfeil: je mehr Versuche über diese Seite, desto dicker
        share = len(part) / len(attempts)
        width = 0.8 + 6 * share
        ax.add_patch(FancyArrow(x_start, y, x_end - x_start, 0, width=width, head_width=width + 3, head_length=3.5,
                                length_includes_head=True, fc=BLUE, ec="none", zorder=3))

        # Text rechts vom Pfeil: Anzahl gross, Details klein
        success = part[success_col].astype("boolean").mean()
        details = []
        if direct_col:
            details.append(f"{int(part[direct_col].astype('boolean').sum())} direkt in Zone 3")
        details += [f"{success:.0%} klappen", f"{part.reachedZone3.mean():.0%} danach in Zone 3"]

        backing = {"facecolor": SURFACE, "edgecolor": "none", "alpha": 0.9, "pad": 1.5}
        ax.text(x_end + 2, y + 2.2, f"{len(part)} Versuche | {share:.0%}", va="bottom", fontsize=11,
                fontweight="bold", color=INK, zorder=4, bbox=backing)
        ax.text(x_end + 2, y + 1.6, "\n".join(details), va="top", fontsize=9.5, color=INK_SECONDARY,
                linespacing=1.4, zorder=4, bbox=backing)


def plot_sides(sequences: pd.DataFrame, squad: str) -> plt.Figure:
    """Links / Mitte / rechts: Über welche Seite raus aus Zone 1 und von Zone 2 in Zone 3, und wie erfolgreich?"""
    own = sequences[sequences.squadName == squad]

    # Zone 1 -> weiter: Ballbesitze, die in Zone 1 beginnen
    zone1 = own[own.startZone == 1]

    # Zone 2 -> 3: Ballbesitze, in denen das Team den Ball in Zone 2 hatte
    in_zone2 = own[own.inZone2]

    fig, axes = new_figure(2, "Über welche Seite kommen wir nach vorne?",
                           f"{squad} | Pfeildicke = Anteil der Versuche | Seite = wo der Versuch startet | Spielrichtung →")
    opponent = opponent_name(sequences, squad)
    panels = [
        (axes[0], zone1, "exitSide", "exitSuccess", "exitDirectToZone3", -46, -21, "Raus aus Zone 1", "ohne Versuch nach vorne"),
        (axes[1], in_zone2, "zone3EntrySide", "zone3EntrySuccess", None, -4, 21, "Von Zone 2 in Zone 3", "ohne Versuch in Zone 3"),
    ]
    for ax, data, side_col, success_col, direct_col, x_start, x_end, title, missing in panels:
        draw_pitch(ax)
        draw_zone_lines(ax)
        draw_teams(ax, squad, opponent)
        draw_side_arrows(ax, data, side_col, success_col, x_start, x_end, direct_col)

        # Titel mit Anzahl Ballbesitze und wie viele davon ohne Versuch
        no_attempt = data[side_col].isna().sum()
        panel_title(ax, title, f"{len(data)} Ballbesitze | {no_attempt} {missing}")

    return fig


def plot_pressure_map(events: pd.DataFrame, squad: str) -> plt.Figure:
    """Heatmap: Wo kommt das Team mit Ball unter Druck? Linie = Median der Druckhöhe."""
    # Eigene Aktionen unter Druck
    pressured = events[(events.squadName == squad) & events.underPressure]

    fig, (ax,) = new_figure(1, "Wo kommen wir unter Druck?",
                            f"{squad} | {len(pressured)} Aktionen unter Druck | Anteil pro Feld | Spielrichtung →",
                            height=6.6, top=0.85)
    fig.set_size_inches(9, 6.6)
    pitch = draw_pitch(ax)
    draw_teams(ax, squad, opponent_name(events, squad))

    # Anteil der Druck-Aktionen pro Feld (6 x 4 Felder), Lücke zwischen den Feldern in Flächenfarbe
    stats = pitch.bin_statistic(pressured.startAdjCoordinatesX, pressured.startAdjCoordinatesY, bins=(6, 4), normalize=True)
    pitch.heatmap(stats, ax=ax, cmap=BLUES, edgecolor=SURFACE, linewidth=2, zorder=1)

    # Werte in die Felder schreiben: weiss auf dunklem, schwarz auf hellem Blau
    highest = stats["statistic"].max()
    for value, x, y in zip(stats["statistic"].ravel(), stats["cx"].ravel(), stats["cy"].ravel()):
        if value > 0:
            color = "white" if value > 0.55 * highest else INK
            ax.text(x, y, f"{value:.0%}", ha="center", va="center", fontsize=12, color=color, zorder=4)

    # Median-Druckhöhe als Linie, Beschriftung unter dem Feld
    median_x = pressured.metresFromOwnGoal.median() + PITCH_X_MIN
    ax.plot([median_x, median_x], [-34, 34], color=INK, lw=2, zorder=3)
    ax.text(median_x, -36.5, f"Median: {median_x - PITCH_X_MIN:.0f} m vom eigenen Tor", ha="center", va="top",
            fontsize=11, color=INK)
    return fig
