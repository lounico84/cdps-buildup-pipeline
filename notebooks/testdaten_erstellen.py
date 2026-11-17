"""Erstellt ein künstliches Testspiel in data/raw, damit man ohne Impect-Zugang testen kann.

Die Daten sind zufällig erzeugt, haben aber dasselbe Format wie die Impect-Events.
Start aus dem Projektordner: python -m notebooks.testdaten_erstellen
"""

import numpy as np
import pandas as pd

from src.config import DATA_RAW

MATCH_ID = 999999
TEAMS = {1: "Team Blau", 2: "Team Rot"}
PRESSURE_VALUES = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]


def pitch_position(x: float) -> str:
    """Impect-pitchPosition aus der x-Koordinate (-52.5 bis 52.5)."""
    if x < -36:
        return "OWN_BOX"
    if x < -17.5:
        return "FIRST_THIRD"
    if x < 17.5:
        return "MIDDLE_THIRD"
    if x < 36:
        return "FINAL_THIRD"
    return "OPPONENT_BOX"


def random_pressure(rng: np.random.Generator, x: float) -> float:
    """Druck: je weiter vorne, desto häufiger."""
    # Wahrscheinlichkeit für Druck steigt von 30 % (eigenes Tor) auf 70 % (gegnerisches Tor)
    chance = 0.3 + 0.4 * (x + 52.5) / 105
    return float(rng.choice(PRESSURE_VALUES)) if rng.random() < chance else 0.0


def make_match(seed: int = 1879) -> pd.DataFrame:
    """Ein Spiel mit 200 Ballbesitzen erzeugen."""
    rng = np.random.default_rng(seed)
    rows = []
    time = 0.0

    for sequence in range(200):
        # Wer hat den Ball, in welcher Phase beginnt der Ballbesitz?
        squad_id = int(rng.choice([1, 2]))
        phase = rng.choice(["ATTACKING_TRANSITION", "SET_PIECE", "SECOND_BALL", "IN_POSSESSION"], p=[0.45, 0.3, 0.15, 0.1])

        # 2. Halbzeit beginnt bei Impect bei 10'000 Sekunden
        period = 1 if sequence < 100 else 2
        if sequence == 100:
            time = 10_000.0

        # Startpunkt und Anzahl Pässe
        x, y = rng.uniform(-50, 20), rng.uniform(-30, 30)
        n_passes = int(rng.integers(1, 9))

        for number in range(n_passes):
            # Transition wird nach zwei Pässen zum geordneten Ballbesitz
            event_phase = "IN_POSSESSION" if phase == "ATTACKING_TRANSITION" and number >= 2 else phase
            pressure = random_pressure(rng, x)

            # Ziel des Passes: meistens nach vorne
            x_next = float(np.clip(x + rng.normal(7, 10), -52, 52))
            y_next = float(np.clip(y + rng.normal(0, 12), -33, 33))

            # Letzter Pass geht verloren, die anderen kommen an
            last = number == n_passes - 1

            base = {
                "matchId": MATCH_ID,
                "dateTime": "2026-01-01T15:00:00Z",
                "homeSquadName": TEAMS[1],
                "awaySquadName": TEAMS[2],
                "periodId": period,
                "sequenceIndex": sequence,
                "squadId": squad_id,
                "squadName": TEAMS[squad_id],
                "attackingSquadId": squad_id,
                "attackingSquadName": TEAMS[squad_id],
                "playerName": f"{TEAMS[squad_id]} Spieler {int(rng.integers(1, 12))}",
                "phase": event_phase,
                "startAdjCoordinatesX": round(x, 1),
                "startAdjCoordinatesY": round(y, 1),
                "startPitchPosition": pitch_position(x),
                "pressure": pressure,
                "pressingPlayerName": "Gegenspieler" if pressure >= 50 else None,
            }

            # Ballannahme, danach Pass
            rows.append(base | {"gameTimeInSec": time, "actionType": "RECEPTION", "action": "RECEPTION",
                                "result": None, "endPitchPosition": None})
            rows.append(base | {"gameTimeInSec": time + 1.5, "actionType": "PASS", "action": "LOW_PASS",
                                "result": "FAIL" if last else "SUCCESS", "endPitchPosition": pitch_position(x_next)})

            x, y = x_next, y_next
            time += 3.0
        time += 5.0

    # Laufende Event-Nummer wie bei Impect
    events = pd.DataFrame(rows)
    events.insert(1, "eventNumber", range(len(events)))
    return events


if __name__ == "__main__":
    # Testspiel erzeugen und wie ein echtes Spiel in data/raw speichern
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    path = DATA_RAW / f"events_{MATCH_ID}.parquet"
    make_match().to_parquet(path, index=False)
    print(f"Testspiel gespeichert: {path}")
    print("Jetzt z. B. testen mit: python -m notebooks.test_sequenzen")
