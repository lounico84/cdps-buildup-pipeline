"""Ganze Pipeline für alle Spiele einer Mannschaft.

Start aus dem Projektordner: python -m src.pipeline
Ergebnisse landen in data/processed/<Mannschaft>/
"""

import matplotlib

# Grafiken nur speichern, kein Fenster öffnen
matplotlib.use("Agg")

import pandas as pd

from src.config import DATA_PROCESSED
from src.events.sequences import build_sequences
from src.features.zones import add_zone_features
from src.ingestion.impect_api import (
    connect, get_iterations, get_local_matches, get_matches, get_squads, load_events, matches_of_squad, read_local_events,
)
from src.menu import choose
from src.metrics.buildup import buildup_from_zone1, pressing_height
from src.preprocessing.clean import clean_events
from src.visualization.pitch import plot_buildup, plot_pressure_map


def choose_local() -> tuple[str, list[int]]:
    """Mannschaft aus den bereits geladenen Spielen wählen (kein Login nötig)."""
    matches = get_local_matches()
    if matches.empty:
        raise SystemExit("Noch keine Spiele in data/raw.")

    # Mannschaft wählen, dann alle ihre lokalen Spiele
    squads = get_squads(matches)
    squad = squads[choose("Mannschaft wählen:", squads)]
    return squad, matches_of_squad(matches, squad).matchId.astype(int).tolist()


def choose_impect(api) -> tuple[str, list[int]]:
    """Saison und Mannschaft bei Impect wählen."""
    # Saison wählen
    iterations = get_iterations(api)
    labels = [f"{row.competitionName} {row.season}" for row in iterations.itertuples()]
    iteration = int(iterations.id[choose("Saison wählen:", labels)])

    # Mannschaft wählen, dann alle ihre Spiele mit Daten
    matches = get_matches(api, iteration)
    squads = get_squads(matches)
    squad = squads[choose("Mannschaft wählen:", squads)]
    return squad, matches_of_squad(matches, squad).id.astype(int).tolist()


def match_info(raw: pd.DataFrame, squad: str) -> dict:
    """Datum, Gegner und Heim/Auswärts eines Spiels."""
    first = raw.iloc[0]
    home = first.homeSquadName == squad
    return {
        "Spiel": int(first.matchId),
        "Datum": str(first.dateTime)[:10],
        "Gegner": first.awaySquadName if home else first.homeSquadName,
        "Ort": "Heim" if home else "Auswärts",
    }


def main() -> None:
    # Datenquelle wählen
    source = choose("Woher kommen die Spiele?", [
        "Bereits geladene Spiele (ohne Login)",
        "Alle Spiele einer Mannschaft von Impect laden",
    ])
    api = connect() if source == 1 else None
    squad, match_ids = choose_impect(api) if api else choose_local()
    print(f"\n{squad}: {len(match_ids)} Spiele")

    # Jedes Spiel laden, bereinigen, Zonen ergänzen und Sequenzen bilden
    all_events, all_sequences, infos, failed = [], [], [], []
    for match_id in match_ids:
        # Spiel laden; schlägt es fehl, überspringen statt alles abzubrechen
        try:
            raw = load_events(api, match_id) if api else read_local_events(match_id)
        except Exception as error:
            print(f"  Spiel {match_id} übersprungen: {error}")
            failed.append(match_id)
            continue

        events = add_zone_features(clean_events(raw))
        all_events.append(events)
        all_sequences.append(build_sequences(events))
        infos.append(match_info(raw, squad))
        print(f"  {infos[-1]['Datum']} gegen {infos[-1]['Gegner']}: {len(all_sequences[-1])} Ballbesitze")

    # Ohne ein einziges Spiel gibt es nichts auszuwerten
    if not all_events:
        raise SystemExit("Kein Spiel konnte geladen werden.")

    # Alle Spiele zusammenfügen
    events = pd.concat(all_events, ignore_index=True)
    sequences = pd.concat(all_sequences, ignore_index=True)

    # Kennzahlen pro Spiel und über alle Spiele ("Saison")
    tables = {
        "spiele": pd.DataFrame(infos),
        "aufbau_pro_spiel": buildup_from_zone1(sequences),
        "aufbau_saison": buildup_from_zone1(sequences.assign(matchId="Saison")),
        "druck_pro_spiel": pressing_height(events),
        "druck_saison": pressing_height(events.assign(matchId="Saison")),
    }

    # Ordner pro Mannschaft
    folder = DATA_PROCESSED / squad.replace(" ", "_")
    folder.mkdir(parents=True, exist_ok=True)

    # Tabellen als CSV (fürs Dashboard), Events und Sequenzen als Parquet
    for name, table in tables.items():
        table.to_csv(folder / f"{name}.csv", index=False, encoding="utf-8-sig")
    events.to_parquet(folder / "events.parquet", index=False)
    sequences.to_parquet(folder / "sequences.parquet", index=False)

    # Grafiken über alle Spiele
    plot_buildup(sequences, squad).savefig(folder / "spielaufbau.png", dpi=120, bbox_inches="tight")
    plot_pressure_map(events, squad).savefig(folder / "druck.png", dpi=120, bbox_inches="tight")

    # Kurze Zusammenfassung für die eigene Mannschaft
    own = tables["aufbau_saison"]
    print(f"\nSpielaufbau ab Zone 1, alle Spiele ({squad}):")
    print(own[own.Team == squad].drop(columns=["Spiel", "Team"]).to_string(index=False))
    print(f"\nGespeichert in {folder}")

    # Hinweis auf übersprungene Spiele
    if failed:
        print(f"\nNicht geladen: {failed}. Pipeline später nochmals starten, "
              "bereits geladene Spiele werden nicht erneut angefragt.")


if __name__ == "__main__":
    main()
