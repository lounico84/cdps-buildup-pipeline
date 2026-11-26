"""Ballbesitz genauer definieren: eine Zone nur erreichen oder dort kontrolliert Ballbesitz haben?

Definitionen (alle Werte sind Parameter, damit Varianten verglichen werden können):

- Ankunft in Zone Z: erste eigene Aktion, die in Zone Z oder weiter vorne startet,
  oder erste erfolgreiche Aktion, die dort endet.
- Kontrolliert in Zone Z: nach der Ankunft mindestens `min_passes` aufeinanderfolgende
  erfolgreiche Pässe, die in Zone Z oder weiter vorne starten. Ein misslungener Pass oder
  ein misslungenes Dribbling unterbricht die Serie. min_passes = 0 heisst: Zone nur erreicht.
- Optional `min_seconds`: Das Team behält den Ball nach der Ankunft mindestens so lange.
  Sind beide Werte gesetzt, müssen beide Bedingungen erfüllt sein.
- Ballverlust: Der Ballbesitz endet (Impect beginnt eine neue Sequenz, sobald der Gegner
  die Kontrolle übernimmt).
"""

import pandas as pd

from src.config import POSSESSION_MIN_PASSES, POSSESSION_MIN_SECONDS


def control_in_zone(own: pd.DataFrame, zone: int, min_passes: int, min_seconds: float | None) -> tuple[bool, bool]:
    """Für einen Ballbesitz: (Zone erreicht?, Zone kontrolliert?). own = eigene Aktionen in Reihenfolge."""
    own = own.reset_index(drop=True)
    success = own.result == "SUCCESS"

    # Erreichte Zone pro Aktion: Start, bei erfolgreichen Aktionen auch das Ziel
    reached = own.startZone.where(~success, own[["startZone", "endZone"]].max(axis=1))
    hits = own.index[reached >= zone]
    if len(hits) == 0:
        return False, False

    # Ab der Ankunft zählen (kommt der Ball erst mit dieser Aktion an, zählt sie selbst nicht)
    arrival = hits[0]
    after = own.loc[arrival + 1:] if own.startZone[arrival] < zone else own.loc[arrival:]

    # Längste Serie aufeinanderfolgender erfolgreicher Pässe ab dieser Zone
    streak = best = 0
    for row in after.itertuples():
        if row.actionType == "PASS":
            streak = streak + 1 if (row.result == "SUCCESS" and row.startZone >= zone) else 0
            best = max(best, streak)
        elif row.actionType == "DRIBBLE" and row.result == "FAIL":
            streak = 0
    controlled = best >= min_passes

    # Optional: Ball lange genug behalten
    if min_seconds is not None:
        controlled = controlled and (own.gameTimeInSec.iloc[-1] - own.gameTimeInSec[arrival] >= min_seconds)

    return True, controlled


def add_control(
    events: pd.DataFrame,
    sequences: pd.DataFrame,
    min_passes: int = POSSESSION_MIN_PASSES,
    min_seconds: float | None = POSSESSION_MIN_SECONDS,
) -> pd.DataFrame:
    """Ergänzt pro Ballbesitz, ob Zone 2 und Zone 3 kontrolliert erreicht wurden, und das Ergebnis ab Zone 1."""
    # Eigene Aktionen pro Ballbesitz (wie in build_sequences)
    own = events[events.inPossession & events.startZone.notna()]

    rows = []
    for (match_id, sequence), group in own.groupby(["matchId", "sequenceIndex"]):
        _, zone2 = control_in_zone(group, 2, min_passes, min_seconds)
        _, zone3 = control_in_zone(group, 3, min_passes, min_seconds)
        rows.append({"matchId": match_id, "sequenceIndex": int(sequence), "zone2Controlled": zone2, "zone3Controlled": zone3})
    control = pd.DataFrame(rows)

    sequences = sequences.drop(columns=["zone2Controlled", "zone3Controlled", "zone1Outcome"], errors="ignore")
    sequences = sequences.merge(control, on=["matchId", "sequenceIndex"], how="left")
    for col in ["zone2Controlled", "zone3Controlled"]:
        sequences[col] = sequences[col].fillna(False).astype(bool)

    # Ergebnis für Ballbesitze ab Zone 1: bleibt drin, Raumgewinn ohne Kontrolle, kontrollierter Aufbau
    outcome = pd.Series(pd.NA, index=sequences.index, dtype="object")
    zone1 = sequences.startZone == 1
    outcome[zone1 & ~sequences.reachedZone2] = "Bleibt in Zone 1"
    outcome[zone1 & sequences.reachedZone2 & ~sequences.zone2Controlled] = "Raumgewinn ohne Kontrolle"
    outcome[zone1 & sequences.zone2Controlled] = "Kontrollierter Aufbau"
    sequences["zone1Outcome"] = outcome
    return sequences
