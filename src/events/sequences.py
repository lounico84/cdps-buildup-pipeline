import pandas as pd


def summarise_sequence(own: pd.DataFrame) -> dict:
    """Einen Ballbesitz (alle eigenen Aktionen einer Sequenz) in einer Zeile zusammenfassen."""
    first = own.iloc[0]

    # Höchste Zone, in der das Team eine Aktion mit Ball hatte
    max_zone = own.startZone.max()

    # Erste Aktion unter Druck (falls es eine gibt)
    pressured = own[own.underPressure]
    first_pressure = pressured.iloc[0] if not pressured.empty else None

    return {
        "squadName": first.attackingSquadName,
        # Phase, mit der der Ballbesitz beginnt
        "phase": first.phase,
        "startTime": first.gameTimeInSec,
        "durationSec": own.gameTimeInSec.iloc[-1] - first.gameTimeInSec,
        "actions": len(own),
        "passes": int((own.actionType == "PASS").sum()),
        # Wo beginnt der Ballbesitz und wie weit kommt er?
        "startZone": first.startZone,
        "maxZone": max_zone,
        "reachedZone2": max_zone >= 2,
        "reachedZone3": max_zone >= 3,
        # Wo entsteht der erste Druck?
        "pressured": first_pressure is not None,
        "firstPressureZone": first_pressure.startZone if first_pressure is not None else pd.NA,
        "firstPressureMetres": first_pressure.metresFromOwnGoal if first_pressure is not None else float("nan"),
    }


def build_sequences(events: pd.DataFrame) -> pd.DataFrame:
    """Eine Zeile pro Ballbesitz. Erwartet Events mit add_zone_features()."""
    # Nur Aktionen des Teams mit Ball, die eine Position haben
    own = events[events.inPossession & events.startZone.notna()]

    # Impect nummeriert die Ballbesitze mit sequenceIndex
    rows = []
    for (match_id, sequence), group in own.groupby(["matchId", "sequenceIndex"]):
        rows.append({"matchId": match_id, "sequenceIndex": int(sequence), **summarise_sequence(group)})

    # Zonen als ganze Zahlen
    sequences = pd.DataFrame(rows)
    for col in ["startZone", "maxZone", "firstPressureZone"]:
        sequences[col] = sequences[col].astype("Int64")
    return sequences
