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

import numpy as np
import pandas as pd

from src.config import POSSESSION_MIN_PASSES, POSSESSION_MIN_SECONDS


def zone_stats(own: pd.DataFrame, zone: int) -> tuple[float, float]:
    """Für einen Ballbesitz und eine Zone: (längste Pass-Serie nach Ankunft, Sekunden nach Ankunft).

    own = eigene Aktionen in Reihenfolge. Wird die Zone nicht erreicht, sind beide Werte leer (NaN).
    """
    own = own.reset_index(drop=True)
    success = own.result == "SUCCESS"

    # Erreichte Zone pro Aktion: Start, bei erfolgreichen Aktionen auch das Ziel
    reached = own.startZone.where(~success, own[["startZone", "endZone"]].max(axis=1))
    hits = own.index[reached >= zone]
    if len(hits) == 0:
        return np.nan, np.nan

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

    # Wie lange hat das Team den Ball nach der Ankunft noch?
    seconds = own.gameTimeInSec.iloc[-1] - own.gameTimeInSec[arrival]
    return best, seconds


def control_stats(events: pd.DataFrame) -> pd.DataFrame:
    """Pro Ballbesitz einmal rechnen: längste Pass-Serie und Sekunden nach Ankunft in Zone 2 und Zone 3.

    Danach ist jede Definition nur noch ein Vergleich mit Schwellenwerten (schnell, auch für Schieberegler).
    """
    # Eigene Aktionen pro Ballbesitz (wie in build_sequences)
    own = events[events.inPossession & events.startZone.notna()]

    rows = []
    for (match_id, sequence), group in own.groupby(["matchId", "sequenceIndex"]):
        streak2, seconds2 = zone_stats(group, 2)
        streak3, seconds3 = zone_stats(group, 3)
        rows.append({"matchId": match_id, "sequenceIndex": int(sequence),
                     "zone2Streak": streak2, "zone2Seconds": seconds2, "zone3Streak": streak3, "zone3Seconds": seconds3})
    return pd.DataFrame(rows)


def add_control(
    events: pd.DataFrame,
    sequences: pd.DataFrame,
    min_passes: int = POSSESSION_MIN_PASSES,
    min_seconds: float | None = POSSESSION_MIN_SECONDS,
    stats: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Ergänzt pro Ballbesitz, ob Zone 2 und Zone 3 kontrolliert erreicht wurden, und das Ergebnis ab Zone 1.

    stats: Ergebnis von control_stats() (optional, spart Zeit, wenn mehrere Definitionen verglichen werden).
    """
    if stats is None:
        stats = control_stats(events)

    sequences = sequences.drop(columns=["zone2Controlled", "zone3Controlled", "zone1Outcome"], errors="ignore")
    merged = sequences.merge(stats, on=["matchId", "sequenceIndex"], how="left")

    # Kontrolliert: Zone erreicht und genug Pässe (und optional genug Zeit); nicht erreicht = leer = False
    for zone in (2, 3):
        controlled = merged[f"zone{zone}Streak"] >= min_passes
        if min_seconds is not None:
            controlled &= merged[f"zone{zone}Seconds"] >= min_seconds
        sequences[f"zone{zone}Controlled"] = controlled.fillna(False).astype(bool).to_numpy()

    # Ergebnis für Ballbesitze ab Zone 1: bleibt drin, Raumgewinn ohne Kontrolle, kontrollierter Aufbau
    outcome = pd.Series(pd.NA, index=sequences.index, dtype="object")
    zone1 = sequences.startZone == 1
    outcome[zone1 & ~sequences.reachedZone2] = "Bleibt in Zone 1"
    outcome[zone1 & sequences.reachedZone2 & ~sequences.zone2Controlled] = "Raumgewinn ohne Kontrolle"
    outcome[zone1 & sequences.zone2Controlled] = "Kontrollierter Aufbau"
    sequences["zone1Outcome"] = outcome
    return sequences
