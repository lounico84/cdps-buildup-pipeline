import pandas as pd

# Gegner-Abschluss nach Ballverlust zählt, wenn er innerhalb dieser Zeit kommt (Sekunden)
DANGER_SECONDS = 15


def first_action(own: pd.DataFrame, mask: pd.Series) -> pd.Series | None:
    """Erste Aktion, auf die die Bedingung zutrifft (oder None)."""
    hits = own[mask]
    return hits.iloc[0] if not hits.empty else None


def summarise_sequence(own: pd.DataFrame) -> dict:
    """Einen Ballbesitz (alle eigenen Aktionen einer Sequenz) in einer Zeile zusammenfassen.

    Erwartet Events mit add_zone_features() und add_action_features().
    """
    own = own.reset_index(drop=True)
    first, last = own.iloc[0], own.iloc[-1]
    success = own.result == "SUCCESS"

    # Erreichte Zone: Start jeder Aktion, bei erfolgreichen Aktionen auch das Ziel
    reached = own.startZone.where(~success, own[["startZone", "endZone"]].max(axis=1))
    max_zone = reached.max()

    # Erste Aktion unter Druck (falls es eine gibt)
    pressure = first_action(own, own.underPressure)

    # Häufigste Phase der Aktionen (bei Gleichstand die, die zuerst vorkommt)
    phase_counts = own.phase.value_counts(sort=False)
    main_phase = phase_counts.idxmax() if not phase_counts.empty else pd.NA

    # Ausgang aus Zone 1: erste erfolgreiche Aktion von Zone 1 nach Zone 2 oder 3
    is_move = own.actionCategory.notna() & success
    exit_ = first_action(own, is_move & (own.startZone == 1) & (own.endZone >= 2))
    passes_before = int((own.loc[: exit_.name - 1, "actionType"] == "PASS").sum()) if exit_ is not None else pd.NA

    # Eintritt in Zone 3: erste erfolgreiche Aktion von Zone 1/2 nach Zone 3
    entry3 = first_action(own, is_move & (own.startZone < 3) & (own.endZone == 3))

    # Ballverlust in Zone 1: nie rausgekommen und letzte Aktion misslungen
    lost_in_zone1 = bool(max_zone == 1 and last.result == "FAIL")

    return {
        "squadName": first.attackingSquadName,
        "phase": main_phase,
        "startTime": first.gameTimeInSec,
        "endTime": last.gameTimeInSec,
        "durationSec": last.gameTimeInSec - first.gameTimeInSec,
        "actions": len(own),
        "passes": int((own.actionType == "PASS").sum()),
        "shot": bool((own.actionType == "SHOT").any()),
        # Wo beginnt der Ballbesitz und wie weit kommt er?
        "startZone": first.startZone,
        "maxZone": max_zone,
        "reachedZone2": max_zone >= 2,
        "reachedZone3": max_zone >= 3,
        # Wo entsteht der erste Druck?
        "pressured": pressure is not None,
        "firstPressureZone": pressure.startZone if pressure is not None else pd.NA,
        "firstPressureMetres": pressure.metresFromOwnGoal if pressure is not None else float("nan"),
        # Wie kommt der Ball aus Zone 1 raus?
        "exitCategory": exit_.actionCategory if exit_ is not None else pd.NA,
        "exitSide": exit_.startSide if exit_ is not None else pd.NA,
        "exitTargetSide": exit_.endSide if exit_ is not None else pd.NA,
        "exitPosition": exit_.playerPosition if exit_ is not None else pd.NA,
        "exitPlayer": exit_.playerName if exit_ is not None else pd.NA,
        "exitUnderPressure": bool(exit_.underPressure) if exit_ is not None else pd.NA,
        "exitDirectToZone3": bool(exit_.endZone == 3) if exit_ is not None else pd.NA,
        "passesBeforeExit": passes_before,
        # Wie kommt der Ball in Zone 3?
        "zone3EntryCategory": entry3.actionCategory if entry3 is not None else pd.NA,
        "zone3EntrySide": entry3.endSide if entry3 is not None else pd.NA,
        # Ballverlust in Zone 1
        "lostInZone1": lost_in_zone1,
        "lostSide": last.startSide if lost_in_zone1 else pd.NA,
    }


def add_danger_after_loss(sequences: pd.DataFrame) -> pd.DataFrame:
    """Markiert Ballverluste in Zone 1, nach denen der Gegner schnell zum Abschluss kommt."""
    sequences = sequences.sort_values(["matchId", "startTime"]).reset_index(drop=True)

    # Nächster Ballbesitz im selben Spiel
    following = sequences.groupby("matchId").shift(-1)

    # Gefährlich: nächster Ballbesitz gehört dem Gegner, endet mit Schuss und beginnt kurz nach dem Verlust
    sequences["opponentShotAfterLoss"] = (
        sequences.lostInZone1
        & (following.squadName != sequences.squadName)
        & following.shot.eq(True)
        & (following.startTime - sequences.endTime < DANGER_SECONDS)
    )
    return sequences


def build_sequences(events: pd.DataFrame) -> pd.DataFrame:
    """Eine Zeile pro Ballbesitz. Erwartet Events mit add_zone_features() und add_action_features()."""
    # Nur Aktionen des Teams mit Ball, die eine Position haben
    own = events[events.inPossession & events.startZone.notna()]

    # Impect nummeriert die Ballbesitze mit sequenceIndex
    rows = []
    for (match_id, sequence), group in own.groupby(["matchId", "sequenceIndex"]):
        rows.append({"matchId": match_id, "sequenceIndex": int(sequence), **summarise_sequence(group)})

    # Zonen als ganze Zahlen
    sequences = pd.DataFrame(rows)
    for col in ["startZone", "maxZone", "firstPressureZone", "passesBeforeExit"]:
        sequences[col] = sequences[col].astype("Int64")

    # Gefährliche Ballverluste ergänzen
    return add_danger_after_loss(sequences)
