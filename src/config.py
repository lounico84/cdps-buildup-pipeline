from pathlib import Path

# Ordner
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"

# Zonen
ZONES = {
    "OWN_BOX": 1,
    "FIRST_THIRD": 1,
    "MIDDLE_THIRD": 2,
    "FINAL_THIRD": 3,
    "OPPONENT_BOX": 3,
}

# Spielfeld 105 x 68 m
PITCH_X_MIN = -52.5

# pressure geht von 0 (kein Druck) bis 100 (keine Ballkontrolle).
PRESSURE_THRESHOLD = 30
