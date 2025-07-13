import requests
import os

API_TOKEN = os.environ.get("BS_API_KEY")
BASE_URL = "https://api.brawlstars.com/v1"

headers = {
  "Authorization": f"Bearer {API_TOKEN}"
}

def get_player(player_tag):
  url = f"{BASE_URL}/players{player_tag.replace('#', '%23')}"
  r = requests.get(url, headers=headers)
  print(r.text, flush=True)

  if r.status_code == 200:
    data = r.json()
    return data
  else:
    return {}
