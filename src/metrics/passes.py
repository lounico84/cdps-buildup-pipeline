"""Passrichtungen: durchschnittliche Richtung und Ampel nach Erfolgsquote.

Ampel-Regel (statistisch, nachvollziehbar):
- Vergleichsgruppe = Pässe aus derselben Zone in dieselbe Richtung (vorwärts / seitlich / rückwärts).
  So wird ein Vorwärtspass nur mit anderen Vorwärtspässen verglichen, nicht mit sicheren Rückpässen.
- Für jede Kategorie (z. B. "zur Mitte") wird die Erfolgsquote mit 95 %-Konfidenzintervall (Wilson) berechnet.
- Grün: Intervall liegt ganz über der Quote der Vergleichsgruppe (signifikant besser).
  Rot: Intervall liegt ganz darunter (signifikant schlechter). Gelb: kein klarer Unterschied.
  Grau: weniger als MIN_PASSES Pässe, zu wenig für eine Aussage.
"""

import numpy as np
import pandas as pd

# Mindestanzahl Pässe für eine Ampelfarbe
MIN_PASSES = 30

# z-Wert für ein 95 %-Konfidenzintervall
Z = 1.96


def wilson_interval(successes: int, n: int, z: float = Z) -> tuple[float, float]:
    """95 %-Konfidenzintervall für eine Erfolgsquote (Wilson-Methode, auch bei kleinen n stabil)."""
    if n == 0:
        return np.nan, np.nan
    p = successes / n
    center = (p + z**2 / (2 * n)) / (1 + z**2 / n)
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    return center - half, center + half


def traffic_light(low: float, high: float, reference: float, n: int) -> str:
    """Ampelfarbe aus Konfidenzintervall und Vergleichsquote."""
    if n < MIN_PASSES:
        return "grau"
    if low > reference:
        return "grün"
    if high < reference:
        return "rot"
    return "gelb"


def pass_light(events: pd.DataFrame, squad: str, category: str = "passTowardCenter") -> pd.DataFrame:
    """Ampel pro Zone, Richtung und Kategorie (Standard: zur Mitte / nach aussen / gleiche Breite).

    Erwartet Events mit add_pass_features().
    """
    passes = events[(events.squadName == squad) & events.inPossession & events.passDirection.notna()
                    & events[category].notna() & events.startZone.notna()]

    rows = []
    for (zone, direction), group in passes.groupby(["startZone", "passDirection"]):
        # Erfolgsquote der Vergleichsgruppe (gleiche Zone, gleiche Richtung)
        reference = group.passSuccess.astype(float).mean()

        for value, part in group.groupby(category):
            n, successes = len(part), int(part.passSuccess.astype(bool).sum())
            low, high = wilson_interval(successes, n)
            rows.append({
                "Zone": int(zone),
                "Richtung": direction,
                "Kategorie": value,
                "Pässe": n,
                "Erfolg (%)": round(successes / n * 100, 1),
                "Intervall (%)": f"{low * 100:.0f}-{high * 100:.0f}",
                "Vergleich (%)": round(reference * 100, 1),
                "Ampel": traffic_light(low, high, reference, n),
            })
    return pd.DataFrame(rows)


def mean_direction(events: pd.DataFrame, squad: str) -> pd.DataFrame:
    """Durchschnittliche Passrichtung pro Zone (Vektormittel der Winkel) und wie stark die Pässe streuen.

    Konzentration R: 1 = alle Pässe in dieselbe Richtung, 0 = Richtungen gleichmässig verteilt.
    Bei kleinem R sagt die durchschnittliche Richtung wenig aus.
    """
    passes = events[(events.squadName == squad) & events.inPossession & events.passAngle.notna() & events.startZone.notna()]

    rows = []
    for zone, group in passes.groupby("startZone"):
        # Winkel als Vektoren mitteln (sonst wäre der Mittelwert von 350 und 10 Grad falsch 180)
        radians = np.deg2rad(group.passAngle)
        sin, cos = np.sin(radians).mean(), np.cos(radians).mean()
        rows.append({
            "Zone": int(zone),
            "Pässe": len(group),
            "Mittlere Richtung (Grad)": round(float(np.rad2deg(np.arctan2(sin, cos)) % 360)),
            "Konzentration R": round(float(np.hypot(sin, cos)), 2),
        })
    return pd.DataFrame(rows)
