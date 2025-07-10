import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

def init():
  cred = credentials.Certificate("/etc/secrets/FirebaseAccess.json")
  firebase_admin.initialize_app(cred, {
      'databaseURL': 'https://dcbotcomet-default-rtdb.europe-west1.firebasedatabase.app/'
  })
  ref = db.reference("server")
  if not ref.get():  # Falls "server" nicht existiert
    ref.set({}) 
  print("Database initialized")

def get_server_value(server_id: str):
    ref = db.reference(f"servers/{server_id}/data")
    return ref.get() or {}
    
def update_server_value(server_id: str, data):
    ref = db.reference(f"servers/{server_id}/data")
    ref.update(value)

def update_user_data(server_id: str, user, value):
    ref = db.reference(f"servers/{server_id}/user/{user}")
    ref.update(value)

def get_user_data(server_id: str, user):
    ref = db.reference(f"servers/{server_id}/user/{user}")
    return ref.get() or {}

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
