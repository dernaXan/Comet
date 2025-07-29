import discord
from discord.ext import commands, tasks
import os
import firebaseData as fd
import json
from flask import Flask, jsonify, request
import threading
import bs
import random
import aiohttp
import re
import asyncio
import feedparser

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

#events
@bot.event
async def on_ready():
    print(f"{bot.user} ist online!", flush=True)
    bot.add_view(CloseTicketView())
    bot.add_view(SupportView())
    bot.add_view(DeliveryClaimView(None, None, None))
    for guild in bot.guilds:
        print(f"Checking Members of {guild.name}")
        users = fd.get_users(guild.id)
        async for member in guild.fetch_members(limit=None):
            if member.bot:
                continue
            user_id = member.id
            if user_id not in users:
                fd.addUser(user_id, guild.id)
                print(f"Added User {member.display_name} from server {guild.name}")
                
    print("Synchronizing completed")
    notification_list = []
    for guild in bot.guilds:
        print(f"Checking Youtube Handle of {guild.name}")
        data = get_server_data(guild.id)
        if not data.get("upload-notifications", {}).get("yt", ""):
            continue
        channel_id = data.get("upload-notifications", {}).get("yt", "")
        dc_channel = data.get("upload-notifications", {}).get("channel", "")
        last_video = data.get("upload-notifications", {}).get("last-vid", "")
        notification_list.append({"yt": channel_id, "channel": dc_channel, "last": last_video})
    print("Starting Youtube Channel Check Loop")
    check_youtube_feeds.start(notification_list)

@tasks.loop(seconds=60)
async def check_youtube_feeds(notification_list):
    print("Checking Channels", flush=True)
    for ch in notification_list:
        channel_id = ch.get("yt")  # YouTube Channel-ID (UCxxxx...)
        dc_channel_id = ch.get("channel")  # Discord Channel-ID (int)
        last_vid = ch.get("last")  # Letzte bekannte Video-ID ("" möglich)

        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        feed = feedparser.parse(rss_url)

        print(f"Feed Title: {feed.feed.title if 'title' in feed.feed else 'Kein Titel'}", flush=True)
        print(f"Anzahl der Videos im Feed: {len(feed.entries)}", flush=True)


        if not feed.entries:
            print(f"❌ Kein Video im Feed gefunden für {channel_id}")
            continue

        latest_entry = feed.entries[0]
        video_id = latest_entry.yt_videoid
        video_title = latest_entry.title
        video_url = latest_entry.link

        # Wenn kein Video bekannt ist ODER neues Video gefunden wurde
        if last_vid == "" or video_id != last_vid:
            dc_channel = bot.get_channel(dc_channel_id)
            if dc_channel:
                embed = discord.Embed(
                    title="NEUES VIDEO!",
                    description=f"# 📢 **{feed.feed.title.upper() if feed.feed else 'UNKNOWN'}** hat ein neues **Video** hochgeladen!\nSchaue [das Video]({video_url}) **jetzt** auf **YouTube** an!",
                    color=discord.Color.random()
                )
                await channel.send(embed=embed)
            else:
                print(f"⚠️ Discord-Kanal {dc_channel_id} nicht gefunden.")

            # Aktualisiere die gespeicherte Video-ID
            ch["last"] = video_id

@bot.slash_command(name="set_upload_notification_channel")
async def set_upload_notification_channel(ctx):
    if not is_mod(ctx, ctx.author.id):
        return await ctx.respond("Du benötigst eine Moderatorenrolle um diesen Befehl zu nutzen!")
    data = fd.get_server_value(ctx.guild.id)
    data["upload-notifications"]["channel"] = ctx.channel.id
    fd.update_server_value(ctx.server.id, data)
    return await ctx.respond("Upload Notification Channel erfolgreich gesetzt!")
        

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
    channelid = fd.get_server_value(member.guild.id).get("welcomechannel", "")
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
        await channel.send(embed=embed)

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

def get_shop_data(guild_id):
    raw_data = get_server_data(guild_id)["shop_data"]
    return json.loads(raw_data)

def save_shop_data(guild_id, data):
    r = json.dumps(data)
    sdata = get_server_data(guild_id)
    sdata["shop_data"] = r
    fd.update_server_value(guild_id, sdata)

def create_shop_embed(shop_items, page):
    embed = discord.Embed(title="🛒 Shop", color=discord.Color.blue())
    if page < 0 or page >= len(shop_items):
        embed.description = "❌ Keine Items auf dieser Seite."
        return embed

    item = shop_items[page]
    stock = "∞ verfügbar" if item["stock"] == -1 else f"{item['stock']} verfügbar"
    embed.add_field(
        name=f"{item['name']} – {item['price']} Punkte",
        value=f"📦 {stock}",
        inline=False
    )
    embed.set_footer(text=f"Seite {page+1}/{len(shop_items)}")
    return embed

class DeliveryClaimView(discord.ui.View):
    def __init__(self, member, item, modrole):
        super().__init__(timeout=None)  # persistent view
        self.member = member
        self.item = item
        self.modrole = modrole

    @discord.ui.button(label="Zustellung claimen", style=discord.ButtonStyle.primary, custom_id="delivery_claim_button")
    async def claim_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        # Sicherstellen, dass nur Mods den Button klicken können (optional)
        if self.modrole not in interaction.user.roles:
            await interaction.response.send_message("Du hast keine Berechtigung, das zu claimen.", ephemeral=True)
            return

        # Nachricht updaten: Button entfernen und Text ändern
        self.clear_items()  # entfernt alle Buttons

        new_content = (f"✅ Zustellung von **{self.item['name']}** an {self.member.mention} wurde von "
                       f"{interaction.user.mention} als zugestellt markiert.")
        
        await interaction.message.edit(content=new_content, view=None)
        await interaction.response.send_message("Zustellung wurde erfolgreich als zugestellt markiert.", ephemeral=True)


async def handle_purchase(interaction: discord.Interaction, item_id: str):
    guild_id = interaction.guild.id
    user_id = interaction.user.id
    member = interaction.user

    # Daten abrufen
    shop_data = get_shop_data(guild_id)
    item = next((i for i in shop_data if i["id"] == item_id), None)

    if not item:
        await interaction.response.send_message("❌ Dieses Item existiert nicht mehr.", ephemeral=True)
        return

    # Verfügbarkeit prüfen
    if item["stock"] == 0:
        await interaction.response.send_message("❌ Dieses Item ist ausverkauft.", ephemeral=True)
        return

    # Punkte prüfen
    user_data = get_data(guild_id, user_id)
    user_points = user_data.get("points", 0)
    if user_points < item["price"]:
        await interaction.response.send_message("❌ Du hast nicht genug Punkte.", ephemeral=True)
        return

    # Punkte abziehen & Stock verringern
    user_data["points"] -= item["price"]
    save_data(guild_id, user_id, user_data)

    if item["stock"] != -1:
        item["stock"] -= 1
        save_shop_data(guild_id, shop_data)

    # Modchat informieren
    modchat_id = int(get_server_data(guild_id).get("modchat", 0))
    modrole_id = int(get_server_data(guild_id).get("modrole", 0))

    if modchat_id and modrole_id:
        modchat = interaction.guild.get_channel(modchat_id)
        modrole = interaction.guild.get_role(modrole_id)
        if modchat and modrole:
            view = DeliveryClaimView(member, item, modrole)
            msg = await modchat.send(
                f"📦 {member.mention} hat **{item['name']}** gekauft. Bitte stellt es ihm zu. {modrole.mention}",
                view=view
            )
        else:
            view = DeliveryClaimView(member, item, modrole)
            msg = await interaction.channel.send(
                f"📦 {member.mention} hat **{item['name']}** gekauft. Bitte stellt es ihm zu. {modrole.mention}",
                view=view
            )
    else:
        view = DeliveryClaimView(member, item, modrole)
        msg = await interaction.channel.send(
            f"📦 {member.mention} hat **{item['name']}** gekauft. Bitte stellt es ihm zu. {modrole.mention}",
            view=view
        )

    await msg.pin()
    await interaction.response.send_message(f"✅ Du hast **{item['name']}** gekauft! Ein Moderator wird dir deinen Kauf in kürze zustellen!", ephemeral=True)

class ShopView(discord.ui.View):
    def __init__(self, shop_items, page=0, timeout=60):
        super().__init__(timeout=timeout)
        self.shop_items = shop_items
        self.page = page
        self.message = None
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        self.add_item(self.PreviousButton())
        self.add_item(self.NextButton())

        # Kaufbutton nur hinzufügen, wenn Item existiert & verfügbar
        if 0 <= self.page < len(self.shop_items):
            item = self.shop_items[self.page]
            if item["stock"] != 0:
                self.add_item(self.BuyButton(item_id=item["id"], label=f"Kaufen ({item['price']} Punkte)"))

    async def update(self, interaction: discord.Interaction):
        self.update_buttons()
        embed = create_shop_embed(self.shop_items, self.page)
        await interaction.response.edit_message(embed=embed, view=self)

    class PreviousButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="◀️ Zurück", style=discord.ButtonStyle.secondary)

        async def callback(self, interaction: discord.Interaction):
            view: ShopView = self.view
            if view.page > 0:
                view.page -= 1
                await view.update(interaction)

    class NextButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="▶️ Weiter", style=discord.ButtonStyle.secondary)

        async def callback(self, interaction: discord.Interaction):
            view: ShopView = self.view
            if view.page + 1 < len(view.shop_items):
                view.page += 1
                await view.update(interaction)

    class BuyButton(discord.ui.Button):
        def __init__(self, item_id: str, label: str):
            super().__init__(label=label, style=discord.ButtonStyle.success)
            self.item_id = item_id

        async def callback(self, interaction: discord.Interaction):
            await handle_purchase(interaction, self.item_id)

@bot.slash_command(name="shop", description="Zeigt den Shop an")
async def shop(ctx: discord.ApplicationContext):
    shop_items = get_shop_data(ctx.guild.id)

    if not shop_items:
        await ctx.respond("❌ Der Shop ist leer.", ephemeral=True)
        return

    embed = create_shop_embed(shop_items, page=0)
    view = ShopView(shop_items)
    await ctx.respond(embed=embed, view=view, ephemeral=True)

# CometAI
async def build_conversation_history(message):
    history = []
    current_msg = message
    while True:
        role = "assistant" if current_msg.author == bot.user else "user"
        history.insert(0, {"role": role, "content": current_msg.content})
        if not current_msg.reference or not current_msg.reference.message_id:
            break
        try:
            current_msg = await current_msg.channel.fetch_message(current_msg.reference.message_id)
        except discord.NotFound:
            break
    return history

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.reference:
        try:
            referenced_msg = await message.channel.fetch_message(message.reference.message_id)
        except discord.NotFound:
            referenced_msg = None
        if referenced_msg and referenced_msg.author == bot.user and bot.user in message.mentions:
            conv_history = await build_conversation_history(message)
            print(conv_history, flush=True)


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
