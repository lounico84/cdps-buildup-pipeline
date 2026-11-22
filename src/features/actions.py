import numpy as np
import pandas as pd

# Passlängen in Metern
SHORT_PASS_MAX = 15
LONG_PASS_MIN = 30

# Pässe, die immer als langer/hoher Ball zählen
LONG_PASS_ACTIONS = ["CHIPPED_PASS", "DIAGONAL_PASS", "SHORT_AERIAL_PASS", "HIGH_CROSS"]

# Impect-Bahnen zusammengefasst zu links / Mitte / rechts (aus Sicht des Teams mit Ball)
SIDES = {
    "LEFT_WING": "links",
    "LEFT_HALF_SPACE": "links",
    "CENTER": "Mitte",
    "RIGHT_HALF_SPACE": "rechts",
    "RIGHT_WING": "rechts",
}


def add_action_features(events: pd.DataFrame) -> pd.DataFrame:
    """Aktionstyp (kurz / mittel / lang / Dribbling) und Seite für jedes Event ergänzen."""
    events = events.copy()

    # Welche Art von Pass oder Dribbling?
    is_pass = events.actionType == "PASS"
    is_long = is_pass & (events.action.isin(LONG_PASS_ACTIONS) | (events.passDistance >= LONG_PASS_MIN))
    is_short = is_pass & ~is_long & (events.passDistance < SHORT_PASS_MAX)
    is_medium = is_pass & ~is_long & ~is_short
    is_dribble = events.actionType == "DRIBBLE"

    # Bedingungen der Reihe nach prüfen, alles andere bleibt leer
    events["actionCategory"] = np.select(
        [is_long, is_short, is_medium, is_dribble],
        ["Langer Ball", "Kurzer Pass", "Mittlerer Pass", "Dribbling"],
        default=None,
    )

    # Seite am Start und am Ende der Aktion
    events["startSide"] = events.startLane.map(SIDES)
    events["endSide"] = events.endLane.map(SIDES)

    return events
