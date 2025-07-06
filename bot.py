import discord
from discord.ext import commands
import os
import firebaseData as fd
import json

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

#events
@bot.event
async def on_ready():
    print(f"{bot.user} ist online!", flush=True)

@bot.event
async def on_guild_join(guild):
    print(f"Bot wurde zu Server zugefügt: {guild.name}", flush=True)
    fd.addServer(guild.id)
    members = await guild.fetch_members().flatten()
    for member in members:
        fd.addUser(member.id, guild.id)

@bot.event
async def on_member_join(member):
    print(f"{member} ist dem Server beigetreten!")
    fd.addUser(member.id, member.guild.id)

#intern functions
def get_data(server_id, user):
    return fd.get_user_data(server_id, user)
    
def save_data(server_id, user, data):
    fd.update_user_data(server_id, user, data)

def get_server_data(server_id):
    return fd.get_server_value(server_id)

async def is_mod(ctx, user_id):
    modroleid = (await get_server_data(ctx.guild.id))["modrole"]
    modrole = ctx.guild.get_role(int(modroleid))
    user = await ctx.guild.fetch_member(int(user_id))
    return modrole in user.roles
    
#slash commands
@bot.slash_command(name="addpoints")
async def addpoints(ctx, member:discord.Member, points:int):
    if not await is_mod(ctx, ctx.author.id):
        return await ctx.respond(f"Du benötigst eine Moderatorrolle, um auf diese Funktion zugreifen zu können!", ephemeral=True)
    data = get_data(ctx.guild.id, member.id)
    data["points"] += points
    save_data(ctx.guild.id, member.id, data)
    return await ctx.respond(f"Der Moderator {ctx.author.mention} hat dem {member.mention} {points} Punkte zugefügt!")

@bot.slash_command(name="subtractpoints")
async def subtractpoints(ctx, member:discord.Member, points:int):
    if not await is_mod(ctx, ctx.author.id):
        return await ctx.respond(f"Du benötigst eine Moderatorrolle, um auf diese Funktion zugreifen zu können!", ephemeral=True)
    data = get_data(ctx.guild.id, member.id)
    data["points"] -= points
    save_data(ctx.guild.id, member.id, data)
    return await ctx.respond(f"Der Moderator {ctx.author.mention} hat dem {member.mention} {points} Punkte abgezogen!")

def start():
    TOKEN = os.getenv("DISCORD_TOKEN")
    print(f"RUNNING BOT...\nRunning with Token: {TOKEN}", flush=True)
    fd.init()
    bot.run(TOKEN)
