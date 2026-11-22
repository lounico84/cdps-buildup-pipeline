import pandas as pd


def first_action(own: pd.DataFrame, mask: pd.Series) -> pd.Series | None:
    """Erste Aktion, auf die die Bedingung zutrifft (oder None)."""
    hits = own[mask]
    return hits.iloc[0] if not hits.empty else None


def summarise_sequence(own: pd.DataFrame) -> dict:
    """Einen Ballbesitz (alle eigenen Aktionen einer Sequenz) in einer Zeile zusammenfassen.

    Erwartet Events mit add_zone_features() und add_action_features().
    """
    own = own.reset_index(drop=True)
    first = own.iloc[0]
    success = own.result == "SUCCESS"

    # Erreichte Zone: Start jeder Aktion, bei erfolgreichen Aktionen auch das Ziel
    reached = own.startZone.where(~success, own[["startZone", "endZone"]].max(axis=1))
    max_zone = reached.max()

    # Erste Aktion unter Druck (falls es eine gibt)
    pressure = first_action(own, own.underPressure)

    # Häufigste Phase der Aktionen (bei Gleichstand die, die zuerst vorkommt)
    phase_counts = own.phase.value_counts(sort=False)
    main_phase = phase_counts.idxmax() if not phase_counts.empty else pd.NA

    # Pässe und Dribblings, egal ob erfolgreich oder nicht (auch misslungene Versuche zählen)
    is_move = own.actionCategory.notna()

    # Erster Versuch, den Ball aus Zone 1 nach Zone 2 oder 3 zu bringen
    exit_ = first_action(own, is_move & (own.startZone == 1) & (own.endZone >= 2))

    # Gepflegtes Passspiel oder direkt? Pässe vor diesem Versuch
    passes_before = int((own.loc[: exit_.name - 1, "actionType"] == "PASS").sum()) if exit_ is not None else pd.NA

    # Erster Versuch, den Ball von Zone 2 in Zone 3 zu bringen (lange Bälle aus Zone 1 zählen beim Ausgang)
    entry3 = first_action(own, is_move & (own.startZone == 2) & (own.endZone == 3))

    return {
        "squadName": first.attackingSquadName,
        "phase": main_phase,
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
        "pressured": pressure is not None,
        "firstPressureZone": pressure.startZone if pressure is not None else pd.NA,
        "firstPressureMetres": pressure.metresFromOwnGoal if pressure is not None else float("nan"),
        # Wie und über welche Seite versucht das Team aus Zone 1 rauszukommen, und klappt es?
        "exitCategory": exit_.actionCategory if exit_ is not None else pd.NA,
        "exitSide": exit_.startSide if exit_ is not None else pd.NA,
        "exitSuccess": exit_.result == "SUCCESS" if exit_ is not None else pd.NA,
        # Geht der Versuch über Zone 2 hinweg direkt in Zone 3?
        "exitDirectToZone3": exit_.endZone == 3 if exit_ is not None else pd.NA,
        "passesBeforeExit": passes_before,
        # Hatte das Team den Ball in Zone 2? (Grundlage für den Weg von Zone 2 in Zone 3)
        "inZone2": bool((own.startZone == 2).any()),
        # Wie und über welche Seite versucht das Team von Zone 2 in Zone 3 zu kommen, und klappt es?
        "zone3EntryCategory": entry3.actionCategory if entry3 is not None else pd.NA,
        "zone3EntrySide": entry3.startSide if entry3 is not None else pd.NA,
        "zone3EntrySuccess": entry3.result == "SUCCESS" if entry3 is not None else pd.NA,
    }


def build_sequences(events: pd.DataFrame) -> pd.DataFrame:
    """Eine Zeile pro Ballbesitz. Erwartet Events mit add_zone_features() und add_action_features()."""
    # Nur Aktionen des Teams mit Ball, die eine Position haben
    own = events[events.inPossession & events.startZone.notna()]

    # Impect nummeriert die Ballbesitze mit sequenceIndex
    rows = []
    for (match_id, sequence), group in own.groupby(["matchId", "sequenceIndex"]):
        rows.append({"matchId": match_id, "sequenceIndex": int(sequence), **summarise_sequence(group)})

    # Zonen und Anzahl als ganze Zahlen
    sequences = pd.DataFrame(rows)
    for col in ["startZone", "maxZone", "firstPressureZone", "passesBeforeExit"]:
        sequences[col] = sequences[col].astype("Int64")
    return sequences
