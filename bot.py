import discord
from discord.ext import commands
import os

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f"{bot.user} ist online!")

TOKEN = os.getenv("DISCORD_TOKEN")
print(f"RUNNING BOT...\nRunning with Token: {TOKEN}", flush=True)
bot.run(TOKEN)
