import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

def init():
  cred = credentials.Certificate("/etc/secrets/FirebaseAccess.json")
  firebase_admin.initialize_app(cred, {
      'databaseURL': 'https://dcbotcomet.firebaseio.com/' # Deine Projekt-URL
  })
  print("Database initialized")

def get_server_value(server_id: str):
    ref = db.reference(f"servers/{server_id}/data")
    return ref.get() or {}

def update_user_data(server_id: str, user, value):
    ref = db.reference(f"servers/{server_id}/user/{user}")
    ref.set(value)

def get_user_data(server_id: str, user):
    ref = db.reference(f"servers/{server_id}/user/{user}")
    return ref.get() or {}

def addServer(guild_id:int):
  ref = db.reference(f"servers/{guild_id}/data")
  if not ref.get() or {}:
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
  if not ref.get() or {}:
    ref.set({
      "tag": "",
      "points": 0,
      "items": []
    })
