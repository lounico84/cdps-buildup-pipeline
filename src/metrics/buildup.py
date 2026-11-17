import pandas as pd

# Impect-Phasen in Begriffen, die Coaches verstehen
PHASE_LABELS = {
    "IN_POSSESSION": "Offensiv",
    "ATTACKING_TRANSITION": "Transition",
    "SECOND_BALL": "Zweiter Ball",
    "SET_PIECE": "Standard",
}


def buildup_from_zone1(sequences: pd.DataFrame, by_phase: bool = True) -> pd.DataFrame:
    """Spielaufbau: Wie oft kommen Ballbesitze ab Zone 1 in Zone 2 und Zone 3?"""
    # Nur Ballbesitze, die in Zone 1 beginnen
    zone1 = sequences[sequences.startZone == 1].copy()

    # Phase mit verständlichem Namen
    zone1["Phase"] = zone1.phase.map(PHASE_LABELS)

    # Erster Druck schon in Zone 1? (Ballbesitze ohne Druck zählen als nein)
    zone1["pressureInZone1"] = (zone1.firstPressureZone == 1).fillna(False)

    # Gruppieren pro Spiel und Team (optional zusätzlich pro Phase)
    groups = ["matchId", "squadName"] + (["Phase"] if by_phase else [])
    table = zone1.groupby(groups).agg(
        Ballbesitze=("sequenceIndex", "size"),
        zone2=("reachedZone2", "mean"),
        zone3=("reachedZone3", "mean"),
        druck=("pressureInZone1", "mean"),
    )

    # Anteile in Prozent
    table[["zone2", "zone3", "druck"]] = (table[["zone2", "zone3", "druck"]].astype(float) * 100).round(1)

    # Spaltennamen für das Dashboard
    table = table.rename(columns={
        "zone2": "Zone 2 erreicht (%)",
        "zone3": "Zone 3 erreicht (%)",
        "druck": "Erster Druck in Zone 1 (%)",
    })
    return table.reset_index().rename(columns={"matchId": "Spiel", "squadName": "Team"})


def pressing_height(events: pd.DataFrame) -> pd.DataFrame:
    """Gegnerdruck: In welcher Zone und wie weit vom eigenen Tor kommt ein Team unter Druck?"""
    # Eigene Aktionen unter Druck = Stellen, an denen der Gegner presst
    pressured = events[events.underPressure]

    # Anteil der Druck-Aktionen pro Zone (%)
    zones = pd.crosstab([pressured.matchId, pressured.squadName], pressured.startZone, normalize="index")
    zones = (zones * 100).round(1)
    zones.columns = [f"Druck in Zone {zone} (%)" for zone in zones.columns]

    # Anzahl und Median-Distanz zum eigenen Tor
    stats = pressured.groupby(["matchId", "squadName"]).agg(
        **{
            "Aktionen unter Druck": ("eventNumber", "size"),
            "Druck im Median bei (m vom eigenen Tor)": ("metresFromOwnGoal", "median"),
        }
    ).round(1)

    # Zusammenführen
    table = stats.join(zones).reset_index()
    return table.rename(columns={"matchId": "Spiel", "squadName": "Team"})
