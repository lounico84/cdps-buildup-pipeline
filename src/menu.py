from src.ingestion.impect_api import get_local_matches


def choose(title: str, options: list[str]) -> int:
    """Nummerierte Auswahl anzeigen und Index der gewählten Option zurückgeben."""
    # Optionen mit Nummer ab 1 anzeigen
    print(f"\n{title}")
    for number, option in enumerate(options, start=1):
        print(f"  {number:>3}) {option}")

    # So lange fragen, bis eine gültige Nummer kommt
    while True:
        answer = input("Nummer wählen: ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return int(answer) - 1
        print(f"Bitte eine Zahl von 1 bis {len(options)} eingeben.")


def choose_local_match() -> int:
    """Ein bereits geladenes Spiel aus data/raw auswählen und matchId zurückgeben."""
    # Lokale Spiele suchen
    matches = get_local_matches()
    if matches.empty:
        raise SystemExit("Noch keine Spiele in data/raw. Zuerst notebooks.test_verbindung ausführen.")

    # Auswahl anzeigen: Datum | Heim - Auswärts
    labels = [f"{row.dateTime[:10]} | {row.homeSquadName} - {row.awaySquadName}" for row in matches.itertuples()]
    return int(matches.matchId[choose("Spiel wählen:", labels)])
