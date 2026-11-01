import pandas as pd

# Spalten, die wir für Spielaufbau und Druck brauchen
COLUMNS = [
    "matchId",
    "eventNumber",
    "periodId",
    "gameTimeInSec",
    "sequenceIndex",
    "squadId",
    "squadName",
    "attackingSquadId",
    "attackingSquadName",
    "playerName",
    "phase",
    "actionType",
    "action",
    "result",
    "startAdjCoordinatesX",
    "startAdjCoordinatesY",
    "startPitchPosition",
    "endPitchPosition",
    "pressure",
    "pressingPlayerName",
]

# Events ohne Spielinhalt
NON_PLAY = ["NO_VIDEO", "FINAL_WHISTLE"]


def clean_events(raw: pd.DataFrame) -> pd.DataFrame:
    """Rohe Impect-Events auf die nötigen Spalten und echten Spielaktionen reduzieren."""
    # Nur benötigte Spalten
    events = raw[COLUMNS].copy()

    # Events ohne Spielinhalt entfernen
    events = events[~events.actionType.isin(NON_PLAY)]

    # Zahlen sicher als Zahlen
    for col in ["gameTimeInSec", "sequenceIndex", "pressure", "startAdjCoordinatesX"]:
        events[col] = pd.to_numeric(events[col], errors="coerce")

    # Nach Spiel und Reihenfolge sortieren
    return events.sort_values(["matchId", "eventNumber"]).reset_index(drop=True)
