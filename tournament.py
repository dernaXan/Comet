import firebaseData as fd
import random
import time

def get_server_tournaments(guild_id):
    """
    Holt alle Turniere für einen bestimmten Server (Guild).
    """
    all_tournaments = fd.get_universal_value('tournaments')  # Dict
    server_tournaments = []
    for tournament_id, tournament in all_tournaments.items():
        if tournament.get('guild_id') == str(guild_id):
            server_tournaments.append(tournament)
    return server_tournaments


def create_tournament(guild_id, name="", max_team_size=None):
    """
    Erstellt ein neues Turnier mit eindeutiger ID und speichert es in Firebase.
    """
    guild_id = str(guild_id)
    all_tournaments = fd.get_universal_value('tournaments')

    if not isinstance(all_tournaments, dict):
        all_tournaments = {}

    # Einzigartige ID generieren
    while True:
        tournament_id = f"{guild_id}-{random.randint(10000000, 99999999)}"
        if tournament_id not in all_tournaments:
            break

    # Beispiel: Start-Team erstellen
    start_team_id = "team1"
    start_team = {
        "name": "Start Team",
        "captain": "",
        "members": [],
        "score": 0
    }

    tournament = {
        "id": tournament_id,
        "guild_id": guild_id,
        "name": name,
        "status": "pending",  # pending | running | finished | cancelled
        "teams": {start_team_id: start_team},   # Dict mit erstem Team
        "bracket": {"1":"11"},                          # noch leer
        "max_team_size": max_team_size,
        "created_at": time.time(),
        "last_updated": time.time()
    }

    # In Firebase speichern
    success = fd.update_universal_value('tournaments', {tournament_id: tournament})
    return tournament if success else False

def get_tournament(tournament_id):
    """
    Holt ein Turnier anhand der ID.
    """
    all_tournaments = fd.get_universal_value('tournaments')
    return all_tournaments.get(tournament_id, False)


def update_tournament(tournament_id, updates: dict):
    """
    Aktualisiert ein bestehendes Turnier.
    `updates` ist ein Dict mit den Feldern, die geändert werden sollen.
    """
    all_tournaments = fd.get_universal_value('tournaments')
    print("DEBUG tournaments:", all_tournaments.keys())
    print("DEBUG looking for:", tournament_id)

    if tournament_id not in all_tournaments:
        return False  # Turnier existiert nicht

    # Vorhandenes Turnier updaten
    all_tournaments[tournament_id].update(updates)
    # Last updated timestamp setzen
    all_tournaments[tournament_id]['last_updated'] = time.time()

    # In Firebase speichern
    success = fd.update_universal_value('tournaments', {tournament_id: all_tournaments[tournament_id]})
    return success


def delete_tournament(tournament_id):
    """
    Löscht ein Turnier anhand der ID.
    """
    all_tournaments = fd.get_universal_value('tournaments')

    if tournament_id not in all_tournaments:
        return False  # Turnier existiert nicht

    # Turnier löschen
    del all_tournaments[tournament_id]

    # In Firebase speichern
    success = fd.set_universal_value('tournaments', all_tournaments)
    return success
