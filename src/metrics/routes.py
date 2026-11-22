import pandas as pd

from src.metrics.buildup import PHASE_LABELS


def route_table(
    data: pd.DataFrame,
    route: str,
    label: str,
    missing: str,
    success: str | None = None,
    by_phase: bool = False,
    direct: str | None = None,
) -> pd.DataFrame:
    """Pro Spiel, Team und Route: Anzahl, Anteil, Erfolg des Versuchs und wie oft danach Zone 3.

    data: die Ballbesitze, die gezählt werden
    route: Spalte mit der Route (z. B. Aktionstyp oder Seite)
    label: Spaltenname für die Route im Ergebnis
    missing: Name für Ballbesitze ohne Route (damit alles zusammen 100 % ergibt)
    success: Spalte, ob der Versuch geklappt hat (optional)
    direct: Spalte, ob der Versuch direkt in Zone 3 ging (optional)
    """
    data = data.copy()

    # Ballbesitze ohne Route bekommen eine eigene Kategorie
    data[label] = data[route].astype("object").where(data[route].notna(), missing)
    data["Phase"] = data.phase.map(PHASE_LABELS)

    # Gruppieren pro Spiel und Team (optional pro Phase) und Route
    groups = ["matchId", "squadName"] + (["Phase"] if by_phase else []) + [label]
    agg = {"Ballbesitze": ("sequenceIndex", "size"), "zone3": ("reachedZone3", "mean")}
    if success:
        # "boolean" erlaubt leere Werte (Ballbesitze ohne Versuch)
        agg["erfolg"] = (success, lambda s: s.astype("boolean").mean())
    if direct:
        agg["direkt"] = (direct, lambda s: s.astype("boolean").mean())
    table = data.groupby(groups).agg(**agg)

    # Anteil der Route an allen Ballbesitzen des Teams (pro Spiel bzw. Phase)
    table["Anteil (%)"] = (table.Ballbesitze / table.groupby(level=groups[:-1]).Ballbesitze.transform("sum") * 100).round(1)

    # Prozentwerte und Spaltennamen fürs Dashboard
    table["zone3"] = (table.zone3.astype(float) * 100).round(1)
    table = table.rename(columns={"zone3": "Danach Zone 3 erreicht (%)"})
    if success:
        table["erfolg"] = (pd.to_numeric(table.erfolg) * 100).round(1)
        table = table.rename(columns={"erfolg": "Versuch erfolgreich (%)"})
    if direct:
        table["direkt"] = (pd.to_numeric(table.direkt) * 100).round(1)
        table = table.rename(columns={"direkt": "Direkt in Zone 3 (%)"})

    # Lesereihenfolge: Anzahl, Anteil, direkt, Erfolg, Zone 3
    order = ["Ballbesitze", "Anteil (%)", "Direkt in Zone 3 (%)", "Versuch erfolgreich (%)", "Danach Zone 3 erreicht (%)"]
    table = table[[col for col in order if col in table.columns]]
    return table.reset_index().rename(columns={"matchId": "Spiel", "squadName": "Team"})


def exit_by_action(sequences: pd.DataFrame, by_phase: bool = False) -> pd.DataFrame:
    """Wie versucht ein Team aus Zone 1 rauszukommen? (kurzer / mittlerer Pass, langer Ball, Dribbling)"""
    zone1 = sequences[sequences.startZone == 1]
    return route_table(zone1, "exitCategory", "Aktion", "Kein Versuch nach vorne", "exitSuccess", by_phase, "exitDirectToZone3")


def exit_by_side(sequences: pd.DataFrame, by_phase: bool = False) -> pd.DataFrame:
    """Über welche Seite versucht ein Team aus Zone 1 rauszukommen? (links / Mitte / rechts)"""
    zone1 = sequences[sequences.startZone == 1]
    return route_table(zone1, "exitSide", "Seite", "Kein Versuch nach vorne", "exitSuccess", by_phase, "exitDirectToZone3")


def exit_by_patience(sequences: pd.DataFrame, by_phase: bool = False) -> pd.DataFrame:
    """Gepflegtes Passspiel oder direkt? Pässe in Zone 1 vor dem ersten Versuch nach vorne."""
    zone1 = sequences[sequences.startZone == 1].copy()

    # Anzahl Pässe in drei Gruppen einteilen
    zone1["aufbau"] = pd.cut(
        zone1.passesBeforeExit.astype(float),
        bins=[-1, 0, 2, 1000],
        labels=["Direkt (0 Pässe)", "Kurz (1-2 Pässe)", "Gepflegt (3+ Pässe)"],
    )
    return route_table(zone1, "aufbau", "Aufbau", "Kein Versuch nach vorne", "exitSuccess", by_phase, "exitDirectToZone3")


def zone3_by_side(sequences: pd.DataFrame, by_phase: bool = False) -> pd.DataFrame:
    """Über welche Seite versucht ein Team von Zone 2 in Zone 3 zu kommen? Nur Ballbesitze mit Ball in Zone 2."""
    in_zone2 = sequences[sequences.inZone2]
    return route_table(in_zone2, "zone3EntrySide", "Seite", "Kein Versuch in Zone 3", "zone3EntrySuccess", by_phase)


def zone3_by_action(sequences: pd.DataFrame, by_phase: bool = False) -> pd.DataFrame:
    """Mit welcher Aktion versucht ein Team von Zone 2 in Zone 3 zu kommen? Nur Ballbesitze mit Ball in Zone 2."""
    in_zone2 = sequences[sequences.inZone2]
    return route_table(in_zone2, "zone3EntryCategory", "Aktion", "Kein Versuch in Zone 3", "zone3EntrySuccess", by_phase)
