import os
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix="!")

@bot.event
async def on_ready():
  print(f"Bot ist eingeloggt als {bot.user}")

TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN is None:
  print("ERROR: Kein Token!")
  exit()
bot.run(TOKEN)
