import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

def init():
    cred = credentials.Certificate("/etc/secrets/FirebaseAccess.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://dcbotcomet-default-rtdb.europe-west1.firebasedatabase.app/'
    })
    ref = db.reference("servers")
    if not ref.get():  # Falls "servers" nicht existiert
        ref.set({}) 
    ref = db.reference("universal_data")
    if not ref.get():  # Falls "universal_data" nicht existiert
        ref.set({}) 
    print("Database initialized")

# -------------------------
# Server Data
# -------------------------

def get_server_value(server_id: str):
    ref = db.reference(f"servers/{server_id}/data")
    return ref.get() or {}
    
def update_server_value(server_id: str, data):
    try:
        ref = db.reference(f"servers/{server_id}/data")
        ref.update(data)
        return True
    except:
        return False

def update_user_data(server_id: str, user, value):
    ref = db.reference(f"servers/{server_id}/user/{user}")
    ref.update(value)

def get_user_data(server_id: str, user):
    ref = db.reference(f"servers/{server_id}/user/{user}")
    return ref.get() or {}
    
def get_users(server_id:int):
    ref = db.reference(f"servers/{server_id}/user")
    return ref.get().keys()

def addServer(guild_id:int):
    guild_ref = db.reference(f"servers/{guild_id}")
    if not guild_ref.get():
        guild_ref.set({"data": {}, "user": {}})
    ref = guild_ref.child("data")
    data = ref.get()
    if not data:
        ref.set({
            'upload-notifications': {
                'yt': "",
                'twitch': "",
                'tiktok': "",
            },
            'modrole': '',
        })

def addUser(user, guild_id):
    ref = db.reference(f"servers/{guild_id}/user/{user}")
    try:
        data = ref.get()
    except firebase_admin.exceptions.NotFoundError:
        data = None
    if not data:
        ref.set({
            "tag": "",
            "points": 0,
            "items": []
        })

# -------------------------
# Universal Data
# -------------------------

def get_universal_value(path: str):
    """ Holt Werte aus universal_data/<path> """
    ref = db.reference(f"universal_data/{path}")
    return ref.get() or {}

def update_universal_value(path: str, data: dict):
    """ Updated/erstellt Werte in universal_data/<path> """
    try:
        ref = db.reference(f"universal_data/{path}")
        ref.update(data)
        return True
    except:
        return False

def set_universal_value(path: str, data: dict):
    """ Überschreibt universal_data/<path> """
    ref = db.reference(f"universal_data/{path}")
    ref.set(data)

def delete_universal_value(path: str):
    """ Löscht einen Pfad in universal_data """
    ref = db.reference(f"universal_data/{path}")
    ref.delete()
