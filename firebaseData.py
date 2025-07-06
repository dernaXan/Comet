import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

def init():
  cred = credentials.Certificate("/etc/secrets/FirebaseAccess.json")
  firebase_admin.initialize_app(cred, {
      'databaseURL': 'https://dcbotcomet.firebaseio.com/' # Deine Projekt-URL
  })
  print("Database initialized")
