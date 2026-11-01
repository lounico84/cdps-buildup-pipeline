import os
from getpass import getpass

import pandas as pd
from dotenv import load_dotenv
from impectPy import Impect

from src.config import DATA_RAW


def connect() -> Impect:
    """Bei Impect anmelden und API-Objekt zurückgeben."""
    # Zugangsdaten aus .env laden, falls vorhanden
    load_dotenv()

    # Fehlt etwas in der .env, wird es abgefragt
    username = os.getenv("IMPECT_USERNAME") or input("IMPECT Benutzername: ")
    password = os.getenv("IMPECT_PASSWORD") or getpass("IMPECT Passwort: ")

    # Anmelden: der Token wird im API-Objekt gespeichert
    api = Impect()
    api.login(username, password)
    print("Erfolgreich angemeldet!")
    return api


def find_iterations(api: Impect, search: str) -> pd.DataFrame:
    """Saisons suchen, deren Wettbewerbsname den Suchbegriff enthält."""
    # Alle Saisons laden
    iterations = api.getIterations()

    # Nach Wettbewerbsname filtern
    found = iterations.competitionName.str.contains(search, case=False, na=False)

    # Nur die wichtigsten Spalten zurückgeben
    return iterations[found][["id", "competitionName", "season", "dataVersion"]]


def find_matches(api: Impect, iteration: int, squad: str) -> pd.DataFrame:
    """Verfügbare Spiele einer Mannschaft in einer Saison."""
    # Spielplan der ganzen Saison
    matches = api.getMatches(iteration=iteration)

    # Spiele, in denen die Mannschaft Heim- oder Auswärtsteam ist
    is_squad = (
        matches.homeSquadName.str.contains(squad, case=False, na=False)
        | matches.awaySquadName.str.contains(squad, case=False, na=False)
    )

    # Nur Spiele, für die Impect schon Daten hat, nach Datum sortiert
    found = matches[is_squad & matches.available].sort_values("scheduledDate")
    return found[["id", "scheduledDate", "homeSquadName", "awaySquadName"]]


def load_events(api: Impect, match_id: int) -> pd.DataFrame:
    """Events eines Spiels laden (beim ersten Mal von Impect, danach aus data/raw)."""
    path = DATA_RAW / f"events_{match_id}.parquet"

    # Schon geladen: aus der Datei lesen, keine API-Anfrage nötig
    if path.exists():
        return pd.read_parquet(path)

    # Sonst von Impect holen
    print(f"Lade Events für Spiel {match_id}...")
    events = api.getEvents(matches=[match_id], include_kpis=False, include_set_pieces=False)

    # Für den nächsten Lauf speichern
    events.to_parquet(path, index=False)
    return events
