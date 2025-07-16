import discord
from discord.ext import commands
import os
import firebaseData as fd
import json
from flask import Flask, jsonify, request
import threading
import bs
import random

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

#events
@bot.event
async def on_ready():
    print(f"{bot.user} ist online!", flush=True)
    bot.add_view(CloseTicketView())
    bot.add_view(SupportView())
    for guild in bot.guilds:
        print(f"Checking Members of {guild.name}")
        users = fd.get_users(guild.id)
        async for member in guild.fetch_members(limit=None):
            if member.bot:
                continue
            user_id = member.id
            if user_id not in users:
                fd.addUser(user_id, guild.id)
                print(f"Added User {member.user_name} from server {guild.name}")
                
    print("Synchronizing completed")

@bot.event
async def on_connect():
    await bot.sync_commands()

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
    channelid = fd.get_server_value(member.guild.id)["welcomechannel"]
    channel = member.guild.get_channel(channelid)
    
    if channel is not None:
        messages = [
    "👋 Willkommen {member} auf dem Server! Schön, dass du da bist!",
    "Hey {member}, willkommen in der Community! 🎉",
    "{member} ist neu hier – sagt hallo! 👋",
    "🎮 {member} ist jetzt offiziell Teil des Servers!",
    "Ein epischer Moment: {member} ist da! 🚀",
    "Willkommen an Bord, {member}! ⚓",
    "{member}, du bist jetzt Teil der Crew! 🤝",
    "Yay! {member} ist dem Server beigetreten! 🥳",
    "Hey {member}, fühl dich wie zu Hause! 🏡",
    "Achtung, Legende im Anflug: {member} ist gelandet! 💥"
]
        msg = random.choice(messages).format(member=member.mention)
        embed = discord.Embed(title=f"Willkommen, {member.display_name}!", description=msg, color=discord.Color.random())
        channel.send(embed=embed)

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
async def addpoints(ctx, member:discord.Member, points):
    points = int(points)
    if not await is_mod(ctx, ctx.author.id):
        return await ctx.respond(f"Du benötigst eine Moderatorrolle, um auf diese Funktion zugreifen zu können!", ephemeral=True)
    data = get_data(ctx.guild.id, member.id)
    data["points"] += points
    save_data(ctx.guild.id, member.id, data)
    return await ctx.respond(f"Der Moderator {ctx.author.mention} hat dem {member.mention} {points} Punkte zugefügt!")

@bot.slash_command(name="subtractpoints")
async def subtractpoints(ctx, member:discord.Member, points):
    points = int(points)
    if not await is_mod(ctx, ctx.author.id):
        return await ctx.respond(f"Du benötigst eine Moderatorrolle, um auf diese Funktion zugreifen zu können!", ephemeral=True)
    data = get_data(ctx.guild.id, member.id)
    data["points"] -= points
    save_data(ctx.guild.id, member.id, data)
    return await ctx.respond(f"Der Moderator {ctx.author.mention} hat dem {member.mention} {points} Punkte abgezogen!")

@bot.slash_command(name="points")
async def points(ctx, member:discord.Member=None):
    if not member:
        member = ctx.author
    data = get_data(ctx.guild.id, member.id)
    points = data["points"]
    embed = discord.Embed(
        title=f"Punkte von {member.display_name}:",
        description=f"{member.mention} hat **{points}** Punkte!",
        color=discord.Color.random()
    )
    embed.set_footer(text=f"Angefordert von {ctx.author.display_name}", icon_url=ctx.author.avatar.url)

    await ctx.respond(embed=embed)

@bot.slash_command(name="savetag")
async def savetag(ctx, tag:str):
    data = bs.get_player(tag)
    print("data:", data, flush=True)
    if data:
        save_data(ctx.guild.id, ctx.author.id, {"tag": tag})
        name = data.get("name", "UNKNOWN")
        embed = discord.Embed(
            title="Spielertag gespeichert!",
            description=f"Du hast deinen Brawlstars account({name}) mit dem Tag {tag} erfolgreich verbunden!\n{ctx.author.mention}",
            color=discord.Color.random()
        )
    else:
        embed = discord.Embed(
            title="Spieler nicht gefunden!",
            description=f"Das Spielertag {tag} existiert nicht!\n{ctx.author.mention}",
            color=discord.Color.red()
        )
    embed.set_footer(text=f"Angefordert von {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
    await ctx.respond(embed=embed)

@bot.slash_command(name="trophies")
async def trophies(ctx, brawler:str=None):
    tag = get_data(ctx.guild.id, ctx.author.id).get('tag', '')
    if not tag:
        embed = discord.Embed(
            title="Kein Spielertag",
            description=f"Du hast noch kein Spielertag hinterlegt! Nutze dazu `/savetag SPIELERTAG` und ersetze **SPIELERTAG** mit deinem Ingame Spielertag!\n{ctx.author.mention}",
            color=discord.Color.red()
        )
    else:
        data = bs.get_player(tag)
        trophies = data.get('trophies', 0) if not brawler else 0
        if brawler:
            brawlers = data.get("brawlers", [{}])
            for b in brawlers:
                if b.get("name", "UNKNOWN") == brawler.upper():
                    trophies = b.get("trophies", 0)
                    
            
        plustext = f" auf dem Brawler **{brawler}**." if brawler else "."
        embed = discord.Embed(
            title=f"Trophäen von {ctx.author.display_name}",
            description=f"Der Spieler **{data.get('name', 'Unknown')}** a.k.a {ctx.author.mention} hat insgesamt {trophies}"+plustext,
            color=discord.Color.random()
        )
    embed.set_footer(text=f"Angefordert von {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
    await ctx.respond(embed=embed)
    
# support
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Ticket schließen", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, button, interaction):
        await interaction.channel.send("Ticket wird geschlossen...")
        await interaction.channel.edit(archived=True, locked=True)

class SupportView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Ticket erstellen", style=discord.ButtonStyle.blurple, custom_id="create_ticket")
    async def create_ticket(self, button, interaction):
        guild = interaction.guild
        user = interaction.user
        
        existing_thread = discord.utils.get(guild.threads, name=f"ticket-{user.name}")
        if existing_thread:
            await interaction.response.send_message(f"Du hast bereits ein Ticket geöffnet. [Hier öffnen](https://discord.com/channels/{existing_thread.guild.id}/{existing_thread.id})", ephemeral=True)
            return
        thread = await interaction.channel.create_thread(
            name=f"ticket-{user.name}",
            type=discord.ChannelType.private_thread,
            invitable=False
        )
        await thread.add_user(user)
    
        role = discord.utils.get(guild.roles, name="Supporter")
        for member in role.members:
            await thread.add_user(member)
        
        await thread.send(f"{user.mention} hat ein neues Support-Ticket eröffnet. {role.mention}")
        await thread.send("Wenn dein Problem gelöst ist, klicke hier:", view=CloseTicketView())
        await interaction.response.send_message(f"Es wurde ein neues Ticket erstellt: [Hier öffnen](https://discord.com/channels/{thread.guild.id}/{thread.id})", ephemeral=True)


@bot.slash_command(name="setup_support", description="Setzt den Support auf(nur 1x nötig)")
async def setup_support(ctx):
    if not (await is_mod(ctx, ctx.author.id)):
        ctx.respond("Nur Mods können das!", ephemeral=True)
    view = SupportView()
    embed = discord.Embed(
        title="Support",
        description="Klicke unten, um ein privates Support-Ticket zu öffnen.",
        color=0x00aaff
    )
    await ctx.channel.send(embed=embed, view=view)
    await ctx.respond("Support-System wurde eingerichtet.", ephemeral=True)



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
    print(auth_header, flush=True)
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
