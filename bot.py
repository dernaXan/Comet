import discord
from discord.ext import commands
import os
import firebaseData as fd
import json
from flask import Flask, jsonify, request
import threading

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
    modroleid = get_server_data(ctx.guild.id)["modrole"]
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

#api
app = Flask(__name__)

API_TOKEN = os.environ.get("API_TOKEN")

@app.route("/user/<int:user_id>/admin_guilds")
def get_user_admin_guilds(user_id):
    result = []
    for guild in bot.guilds:
        member = guild.get_member(user_id)
        if member and member.guild_permissions.administrator:
            result.append({"id": str(guild.id), "name": guild.name})
    return jsonify(result)


@app.route("/guild/<int:guild_id>/roles")
def get_guild_roles(guild_id):
    guild = bot.get_guild(guild_id)
    if not guild:
        return jsonify([])
    roles = [{"id": str(role.id), "name": role.name} for role in guild.roles if not role.is_default()]
    return jsonify(roles)

@app.route("/guild/<int:guild_id>/channels")
def get_guild_channels(guild_id):
    guild = bot.get_guild(guild_id)
    if not guild:
        return jsonify([])
    text_channels = [
        {"id": str(ch.id), "name": ch.name}
        for ch in guild.channels
        if ch.type == discord.ChannelType.text
    ]
    return jsonify(text_channels)
    
@app.route('/guild/<int:guild_id>/data/update', methods=['POST'])
def update_guild_data(guild_id):
    # Token aus Header auslesen und validieren
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f"Bearer {API_TOKEN}":
        return jsonify({"error": "Unauthorized"}), 401

    # JSON Daten aus Request Body lesen
    if not request.is_json:
        return jsonify({"error": "Invalid or missing JSON"}), 400

    data = request.get_json()
    success = fd.update_server_value(guild_id, data)

    if success:
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"status": "failed"}), 500

@app.route('/guild/<int:guild_id>/data/load', methods=['GET'])
def load_guild_data(guild_id):
    # Token aus Header auslesen und validieren
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f"Bearer {API_TOKEN}":
        return jsonify({"error": "Unauthorized"}), 401

    # Daten abrufen
    data = fd.get_server_value(guild_id)
    if data is None:
        return jsonify({"error": "Data not found"}), 404

    return jsonify({"data": data}), 200

def run_flask():
    app.run(host="0.0.0.0", port=os.environ.get("PORT", 10000))

def start():
    TOKEN = os.getenv("DISCORD_TOKEN")
    print("RUNNING API")
    threading.Thread(target=run_flask).start()
    print(f"RUNNING BOT...\nRunning with Token: {TOKEN}", flush=True)
    fd.init()
    bot.run(TOKEN)
