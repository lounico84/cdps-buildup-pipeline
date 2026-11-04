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


def get_iterations(api: Impect) -> pd.DataFrame:
    """Alle Saisons, auf die wir Zugriff haben."""
    # Alle Saisons laden
    iterations = api.getIterations()

    # Nach Wettbewerb und Saison sortieren
    iterations = iterations.sort_values(["competitionName", "season"])

    # Nur die wichtigsten Spalten zurückgeben
    return iterations[["id", "competitionName", "season", "dataVersion"]].reset_index(drop=True)


def get_matches(api: Impect, iteration: int) -> pd.DataFrame:
    """Alle Spiele einer Saison, für die Impect schon Daten hat."""
    # Spielplan der ganzen Saison
    matches = api.getMatches(iteration=iteration)

    # Nur Spiele mit Daten, nach Datum sortiert
    matches = matches[matches.available.eq(True)].sort_values("scheduledDate")
    return matches[["id", "scheduledDate", "homeSquadName", "awaySquadName"]].reset_index(drop=True)


def get_squads(matches: pd.DataFrame) -> list[str]:
    """Alle Mannschaften, die in den Spielen vorkommen (alphabetisch)."""
    return sorted(set(matches.homeSquadName) | set(matches.awaySquadName))


def matches_of_squad(matches: pd.DataFrame, squad: str) -> pd.DataFrame:
    """Spiele einer Mannschaft (heim oder auswärts)."""
    is_squad = (matches.homeSquadName == squad) | (matches.awaySquadName == squad)
    return matches[is_squad].reset_index(drop=True)


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


def get_local_matches() -> pd.DataFrame:
    """Alle Spiele, die schon in data/raw liegen (ohne Login nutzbar)."""
    # Pro Datei nur die erste Zeile mit den Spielinfos lesen
    columns = ["matchId", "dateTime", "homeSquadName", "awaySquadName"]
    rows = [pd.read_parquet(path, columns=columns).iloc[0] for path in DATA_RAW.glob("events_*.parquet")]

    # Nach Datum sortieren
    return pd.DataFrame(rows, columns=columns).sort_values("dateTime").reset_index(drop=True)


def read_local_events(match_id: int) -> pd.DataFrame:
    """Events eines bereits geladenen Spiels aus data/raw lesen."""
    return pd.read_parquet(DATA_RAW / f"events_{match_id}.parquet")
