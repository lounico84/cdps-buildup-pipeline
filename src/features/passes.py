import numpy as np
import pandas as pd

# Passwinkel von Impect: 0 Grad = nach vorne, 90 = nach links, 180 = zurück, 270 = nach rechts.
# Ein Pass gilt als vorwärts bzw. rückwärts, wenn er höchstens so viele Grad von der Richtung abweicht
FORWARD_MAX_DEG = 45

# Ein Pass geht zur Mitte bzw. nach aussen, wenn sich der Abstand zur Mittelachse um mindestens so viele Meter ändert
CENTER_TOLERANCE_M = 2


def add_pass_features(events: pd.DataFrame) -> pd.DataFrame:
    """Passrichtung (vorwärts / seitlich / rückwärts) und ob ein Pass zur Mitte oder nach aussen geht."""
    events = events.copy()
    is_pass = (events.actionType == "PASS") & events.passAngle.notna()
    angle = events.passAngle

    # Richtung aus dem Winkel: vorwärts um 0 Grad, rückwärts um 180 Grad, dazwischen seitlich
    forward = (angle <= FORWARD_MAX_DEG) | (angle >= 360 - FORWARD_MAX_DEG)
    backward = (angle >= 180 - FORWARD_MAX_DEG) & (angle <= 180 + FORWARD_MAX_DEG)
    events["passDirection"] = np.select(
        [is_pass & forward, is_pass & backward, is_pass],
        ["vorwärts", "rückwärts", "seitlich"],
        default=None,
    )

    # Zur Mitte oder nach aussen: Abstand zur Mittelachse (y = 0) vorher und nachher
    change = events.endAdjCoordinatesY.abs() - events.startAdjCoordinatesY.abs()
    has_end = is_pass & events.endAdjCoordinatesY.notna()
    events["passTowardCenter"] = np.select(
        [has_end & (change <= -CENTER_TOLERANCE_M), has_end & (change >= CENTER_TOLERANCE_M), has_end],
        ["zur Mitte", "nach aussen", "gleiche Breite"],
        default=None,
    )

    # Erfolgreich = beim Mitspieler angekommen (Impect: result SUCCESS)
    events["passSuccess"] = (events.result == "SUCCESS").where(is_pass)

    return events
