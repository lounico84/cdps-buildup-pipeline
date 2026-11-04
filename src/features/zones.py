import pandas as pd

from src.config import PITCH_X_MIN, PRESSURE_THRESHOLD, ZONES


def add_zone_features(events: pd.DataFrame) -> pd.DataFrame:
    """Zone, Ballbesitz und Druck für jedes Event ergänzen."""
    events = events.copy()

    # Zone 1/2/3 am Start und Ende der Aktion
    events["startZone"] = events.startPitchPosition.map(ZONES).astype("Int64")
    events["endZone"] = events.endPitchPosition.map(ZONES).astype("Int64")

    # Aktion vom Team, das laut Impect den Ball hat
    events["inPossession"] = events.squadId == events.attackingSquadId

    # Distanz zum eigenen Tor in Metern (jedes Team spielt von links nach rechts)
    events["metresFromOwnGoal"] = events.startAdjCoordinatesX - PITCH_X_MIN

    # Unter Druck: eigene Aktion mit Druck ab der Schwelle
    events["underPressure"] = events.inPossession & (events.pressure >= PRESSURE_THRESHOLD)

    return events
