import discord
from discord.ext import commands
import os
import aiohttp
import json

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} ist online!", flush=True)

#intern functions
async def get_data(server_id, user):
    url = f"{os.getenv('DB_API_URL')}/data/get/{server_id}/user/{user}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
    return data
    
async def save_data(server_id, user, data):
    url = f"{os.getenv('DB_API_URL')}/data/save/{server_id}/user/{user}"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as resp:
            ans = await resp.text()
    return ans
    
#slash commands
@bot.slash_command(name="addpoints")
@commands.has_permissions(administrator=True)
async def addpoints(ctx, member:discord.Member, points:int):
    data = await get_data(ctx.guild.id, member.id)
    data["points"] += points
    await save_data(ctx.guild.id, member.id, data)

@bot.slash_command(name="subtractpoints")
@commands.has_permissions(administrator=True)
async def subtractpoints(ctx, member:discord.Member, points:int):
    data = await get_data(ctx.guild.id, member.id)
    data["points"] -= points
    await save_data(ctx.guild.id, member.id, data)

def start():
    TOKEN = os.getenv("DISCORD_TOKEN")
    print(f"RUNNING BOT...\nRunning with Token: {TOKEN}", flush=True)
    bot.run(TOKEN)
