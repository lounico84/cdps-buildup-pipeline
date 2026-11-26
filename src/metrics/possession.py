import pandas as pd

from src.events.possession import add_control, control_stats

# Reihenfolge der Ergebnisse ab Zone 1 (von schlecht nach gut)
OUTCOMES = ["Bleibt in Zone 1", "Raumgewinn ohne Kontrolle", "Kontrollierter Aufbau"]


def compare_definitions(
    events: pd.DataFrame,
    sequences: pd.DataFrame,
    squad: str,
    passes: tuple[int, ...] = (0, 1, 2, 3),
    seconds: tuple[float | None, ...] = (None, 5, 10),
) -> pd.DataFrame:
    """Wie stark hängt das Ergebnis von der Definition ab? Ballbesitze ab Zone 1 für jede Variante."""
    # Pass-Serien und Zeiten nur einmal berechnen, dann jede Variante schnell vergleichen
    stats = control_stats(events)

    rows = []
    for min_seconds in seconds:
        for min_passes in passes:
            # Kontrolle mit dieser Definition berechnen, nur Ballbesitze des Teams ab Zone 1
            result = add_control(events, sequences, min_passes, min_seconds, stats)
            zone1 = result[(result.squadName == squad) & (result.startZone == 1)]
            rows.append({
                "Pässe": min_passes,
                "Sekunden": "-" if min_seconds is None else min_seconds,
                "Ballbesitze ab Zone 1": len(zone1),
                "Zone 2 kontrolliert (%)": round(zone1.zone2Controlled.mean() * 100, 1),
                "Zone 3 kontrolliert (%)": round(zone1.zone3Controlled.mean() * 100, 1),
            })
    return pd.DataFrame(rows)


def zone1_outcomes(sequences: pd.DataFrame, squad: str, by: str = "exitCategory") -> pd.DataFrame:
    """Ergebnis ab Zone 1 (bleibt / Raumgewinn ohne Kontrolle / kontrolliert) pro Gruppe, z. B. erster Versuch.

    Erwartet Ballbesitze mit add_control().
    """
    zone1 = sequences[(sequences.squadName == squad) & (sequences.startZone == 1)].copy()

    # Ballbesitze ohne Wert in der Gruppe (z. B. kein Versuch nach vorne) bekommen eine eigene Zeile
    zone1[by] = zone1[by].astype("object").where(zone1[by].notna(), "Kein Versuch nach vorne")

    # Anteile in Prozent pro Gruppe, Anzahl dazu
    table = pd.crosstab(zone1[by], zone1.zone1Outcome, normalize="index").reindex(columns=OUTCOMES, fill_value=0)
    table = (table * 100).round(1).add_suffix(" (%)")
    table.insert(0, "Ballbesitze", zone1.groupby(by).size())

    # Zeile für alle Ballbesitze zusammen
    total = (zone1.zone1Outcome.value_counts(normalize=True).reindex(OUTCOMES, fill_value=0) * 100).round(1)
    table.loc["Alle"] = [len(zone1)] + total.tolist()
    return table.reset_index().rename(columns={by: "Gruppe"})
