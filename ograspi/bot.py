import discord
from discord.ext import commands
import json
import os, sys
import requests
from datetime import timedelta
import asyncio
import logging
import redis

print(discord.__version__)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logging.info("Lets go!")

r = redis.Redis(host='localhost', port=6379, db=0)
def sub(callback):
    pubsub = r.pubsub()
    pubsub.supscribe('intern_ans')
    for message in pubsub.listen():
        if message['type'] == 'message':
            callback(message['data'].decode())
            
def subcallback(txt):
    msg = decode_redis(txt)
    botlog(f"REDIS: {m}")

def send_redis(msg):
    r.publish('intern_req', msg)
    
def decode_redis(txt):
    user, action = txt.split(':')
    action, data = action.split('||', maxsplit=1) if len(action.split('||', maxsplit=1)) == 2 else [str(action), ""]
    return {"user":user, "action": action, "data": data}

def encode_redis(**kwargs):
    return f"{kwargs.get('user', None)}:{kwargs.get('action', None)}||{kwargs.get('data', None)}"

with open("apikey.txt", "r") as apifile:
    API_TOKEN = apifile.read()
    apifile.close()
    
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
jsonFile = "userData.json"
MODS = [1273639740951760937, 1313121277107638353]



def is_mod(user_id):
    return user_id in MODS

def load_data(server_id):
    msg = encode_redis(user="bot", action="load_data", data=str(server_id))
    send_redis(msg)

def save_data(data, server_id):
    msg = encode_redis(user="bot", action="save_data", data=[data, str(server_id)])

@bot.event
async def on_ready():
    logging.info(f"Bot ist online als {bot.user}")
    bot.add_view(SupportView())
    bot.add_view(CloseTicketView())
    await botlog(0, f"Bot ist online als {bot.user}")

    
@bot.slash_command(name="addpoints", description="Mods können Usern punkte geben")
async def addpoints(ctx, member: discord.Member, points:str):
    msg = encode_redis(user=str(ctx.author_id), action="addpoints", data=[str(points), str(member.id)])
    send_redis(msg)
        
@bot.slash_command(name="subtractpoints", description="Mods können Usern punkte abziehen")
async def subtractpoints(ctx, member: discord.Member, points:str):
    msg = encode_redis(user=str(ctx.author_id), action="subtractpoints", data=[str(points), str(member.id)])
    send_redis(msg)
        
@bot.slash_command(name="points", description="Schau dir deinen Punktestand oder den von anderen an!")
async def points(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author
    data = load_data()
    if str(member.id) not in data:
        await ctx.respond(f"Der User {member.display_name} ist nicht in diesem Bot und somit auch nicht beim Punktesystem registriert.")
        register_without_tag(member.id)
        await member.send(f"Du wurdest automatisch beim BRAWLSTARS BOT registriert, jedoch nur beim Punktesystem. Um auch aktionen die mit Brawlstars in Verbindung stehen ausführen zu können, wie Zb trophäen abzurufen, nutze !registrate #12345ABCDE um dich mit deinem Brawlstars Spielertag zu registrieren(Schreibe statt #12345ABCDE deinen eigenen Spielertag).")

    points = data[str(member.id)]["points"]
    embed_color = discord.Color.red() if int(points) < 0 else discord.Color.green()
    embed = discord.Embed(
        title=f"Punktzahl – {member.display_name}",
        description=f"{member.display_name} hat insgesamt {points} Punkte.",
        color=embed_color
    )
    await ctx.respond(embed=embed)
    
@bot.command()
async def setkey(ctx, key):
    global API_TOKEN
    await ctx.message.delete()
    if ctx.channel.id == 1375160037164453969:
        with open("apikey.txt", "w")as f:
            f.write(key)
            f.close()
        API_TOKEN = key
        await ctx.send(f"APIKEY wurde zu {key} geändert", delete_after=3.5)
    
@bot.slash_command(name="shopinfo", description="Erfahre die neusten Angebote im Punkteshop!")
async def shopinfo(ctx):
    data = load_data()
    if str(ctx.author.id) not in data:
        await ctx.respond(f"Der User {member.display_name} ist nicht in diesem Bot und somit auch nicht beim Punktesystem registriert.")
        register_without_tag(member.id)
        await member.send(f"Du wurdest automatisch beim BRAWLSTARS BOT registriert, jedoch nur beim Punktesystem. Um auch aktionen die mit Brawlstars in Verbindung stehen ausführen zu können, wie Zb trophäen abzurufen, nutze !registrate #12345ABCDE um dich mit deinem Brawlstars Spielertag zu registrieren(Schreibe statt #12345ABCDE deinen eigenen Spielertag).")
    
    file = discord.File("Shoptable.png", filename="Shoptable.png")
    embed = discord.Embed(title="Shopinfo – Angebote",
                          description="(Diese Angaben werden noch geändert und dienen nur als Platzhalter)",
                          color=discord.Color.blue()
    )
    embed.set_image(url="attachment://Shoptable.png")
    await ctx.respond(embed=embed, file=file)

class Item:
    def __init__(self, name, price, callback, ):
        self.name = name
        self.price = price
        self.callback = callback
        self.user = None
        self.ctx = "None"

    async def cancel(self, ctx):
        await self.ctx.edit(content=f"@{ctx.author.name} Dein Kauf wurde abgebrochen!")

    async def _buy(self, ctx):
        logging.info(self.ctx)
        await botlog(0, "Kauf von", self.user.id, ":", self.name)
        data = load_data()
        points = int(data[str(self.user.id)]["points"]) - self.price
        data[str(self.user.id)]["points"] = points
        save_data(data)
        if "Pin" in self.name:
            await self.callback(ctx=self.ctx, pin=self.name.split(" ")[1])
            return
        await self.callback(ctx=self.ctx)

    async def buy(self, ctx):
        self.user = ctx.author
        logging.info(ctx)
        self.ctx = ctx

        if self.name == "Pin":
            view = PinSelectView(self)
            await ctx.respond("Wähle einen Pin aus dem Dropdown-Menü:", view=view, ephemeral=True)
            return

        data = load_data()[str(self.user.id)]
        if int(data["points"]) < self.price:
            await ctx.respond(
                f"Du hast zu wenige Punkte und kannst dir das Angebot **{self.name}** nicht leisten, @{self.user.display_name}!",
                ephemeral=True
            )
            return

        view = YesNoView(self, ctx)
        await ctx.respond(
            f"Willst du das Angebot **{self.name}** für **{self.price} Punkte** wirklich kaufen?",
            view=view,
            ephemeral=True
        )

# ----- PIN SYSTEM -----

class PinSelect(discord.ui.Select):
    def __init__(self, item: Item):
        self.item = item
        options = []
        for rarity, pins_list in pins.items():
            for pin in pins_list:
                price = {
                    "rare": 300,
                    "epic": 500,
                    "legendary": 1000,
                    "ultralegendary": 3000
                }[rarity]
                name = pin_names[int(pin)-1]
                options.append(discord.SelectOption(label=f"{name} ({rarity})", value=f"{pin}:{rarity}", description=f"{price} Punkte"))

        super().__init__(placeholder="Wähle einen Pin...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        pin_data = self.values[0]
        pin_id, rarity = pin_data.split(":")
        price = {
            "rare": 300,
            "epic": 500,
            "legendary": 1000,
            "ultralegendary": 3000
        }[rarity]

        file = discord.File(f"pins/{pin_id}.webp")
        embed = discord.Embed(
            title=f"Pin {pin_id}",
            description=f"**Seltenheit:** {rarity}\n**Preis:** {price} Punkte",
            color=discord.Color.random()
        )
        embed.set_image(url=f"attachment://{pin_id}.webp")

        self.item.name = f"Pin {pin_id}"
        self.item.price = price
        self.item.user = interaction.user

        view = YesNoView(self.item, interaction)
        await interaction.response.send_message(
            f"Willst du den Pin **{pin_id}** für **{price} Punkte** kaufen?",
            embed=embed,
            view=view,
            file=file,
            ephemeral=True
        )

class PinSelectView(discord.ui.View):
    def __init__(self, item: Item):
        super().__init__(timeout=60)
        self.add_item(PinSelect(item))

# ----- YES / NO VIEW -----

class YesNoView(discord.ui.View):
    def __init__(self, item: Item, ctx=None):
        super().__init__(timeout=60)
        self.item = item

    @discord.ui.button(label="Ja", style=discord.ButtonStyle.success)
    async def confirm(self, interaction:discord.Interaction, button: discord.ui.Button):
        await self.item._buy(interaction)
        await interaction.response.send_message(content="...", ephemeral=True, delete_after=1)
        self.stop()
        

    @discord.ui.button(label="Nein", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction:discord.Interaction, button: discord.ui.Button):
        await self.item.cancel(interaction)
        await interaction.response.send_message(content="...", ephemeral=True, delete_after=1)
        self.stop()

# ----- CALLBACK -----

async def PassCallback(ctx):
    await ctx.followup.send("Callback ausgeführt! ✅")
    await bot.close()
    os.execv(sys.executable, [sys.executable] + sys.argv)
    
async def PinCallback(ctx, pin):
    logging.info(ctx)
    await ctx.followup.send(f"Pin **{pin}** erfolgreich gekauft! ✅")
    data = load_data()
    data[str(ctx.author.id)].setdefault("items", [])
    data[str(ctx.author.id)]["items"].append(f"PIN{pin}")
    save_data(data)
    logging.info("Pin gekauft und Kauf gespeichert!")
    await bot.close()
    os.execv(sys.executable, [sys.executable] + sys.argv)

# ----- SHOP ITEMS -----

shopitems = [
    Item("ColorRole", 750, PassCallback),
    Item("FL", 15000, PassCallback),
    Item("Brawlpass", 5000000, PassCallback),
    Item("Club", 9000, PassCallback),
    Item("Video", 11000, PassCallback),
    Item("Account bewerten", 12000, PassCallback),
    Item("Pin", 0, PinCallback)
]

# ----- PIN DATEN -----

rare_pins = ["01", "02", "06", "07", "09", "10", "12", "13", "15", "16", "17"]
epic_pins = ["18", "20", "11", "14", "19"]
legendary_pins = ["04", "08"]
ultralegendary_pins = ["03", "05"]

pins = {
    "rare": rare_pins,
    "epic": epic_pins,
    "legendary": legendary_pins,
    "ultralegendary": ultralegendary_pins
}

# ----- SLASH COMMAND -----

@bot.slash_command(name="buy", description="Kaufe ein Angebot im Shop!")
async def buy(ctx, item: discord.Option(str, "Welches Item möchstest du kaufen?", choices=[i.name for i in shopitems])):
    ctx.response.defer()
    selected = next((i for i in shopitems if i.name == item), None)
    logging.info(selected)
    logging.info(ctx.author.id)
    if selected:
        await selected.buy(ctx)
    else:
        await ctx.respond("Item nicht gefunden!", ephemeral=True)

def sort_pins(data, id_):
    user_items = set(data[id_].get("items", []))  # z. B. ["PIN01", "PIN03"]
    unlocked = []
    locked = []

    for rarity, pin_list in pins.items():  # z. B. {"rare": ["01", "02"], ...}
        for pin_num in pin_list:
            pin_id = f"PIN{pin_num}"
            if pin_id in user_items:
                unlocked.append(pin_num)
            else:
                locked.append(pin_num)

    return {
        "unlocked": unlocked,
        "locked": locked
    }


pin_names = ["Buzz Yes", "Colette Clap", "True Gold Buzz", "True Silver Buzz", "True Gold Colette", "Colette Smile",
             "Colette Love", "True Silver Colette", "Buzz Clap", "Buzz Yes", "Buzz Hyper", "Buzz Love", "Colette Yes",
             "Colette Hyper", "Crazy Colette", "Colette Love 2", "Sushiiii!", "Kit!", "Kenji Hyper", "Buzz"]

class PinDropdown(discord.ui.Select):
    def __init__(self, id_):
        _pins = sort_pins(load_data(), id_)
        options = []
        for pin in _pins["unlocked"]:
            name = pin_names[int(pin)-1]
            opt = discord.SelectOption(label=f"Pin: {name}", value=str(pin))
            options.append(opt)
        super().__init__(
            placeholder="Wähle einen Pin",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction:discord.Interaction):
        embed = discord.Embed(
            color=discord.Color.random(),
        )
        file = discord.File(f"pins/{self.values[0]}.webp")
        embed.set_image(url=f"attachment://{self.values[0]}.webp")
        await fake(interaction, interaction.user, embed=embed, file=file)
        await botlog(0, "Pin von", ctx.author.id, ":", self.values[0])
        await interaction.response.send_message(f"Pin Gesendet!", delete_after=0.01, ephemeral=True)

class PinSendSelectView(discord.ui.View):
    def __init__(self, id_):
        super().__init__(timeout=None)
        self.add_item(PinDropdown(id_))
       
@bot.slash_command(name="pin", description="Poste Pins!")
async def pin(ctx):
    logging.info(ctx.author.id)
    view = PinSendSelectView(str(ctx.author.id))
    await ctx.respond(view=view, ephemeral=True)

def botmention(message):
    return (bot.user in message.mentions)

def botresponse(message):
    response = message.reference and message.reference.resolved
    tobot = (message.reference.author.id == bot.user.id) if response else False
    return tobot

@bot.slash_command(name="gift", description="Schenke einem Freund Punkte!")
async def gift(ctx, member:discord.Member, points:str):
    points=int(points)
    if points < 0:
        points = 1
    data = load_data()
    if str(ctx.author.id) not in list(data.keys()):
        data[str(ctx.author.id)] = {"points":0, "items":[]}
    if int(data[str(ctx.author.id)]["points"]) < points:
        return await ctx.respond(f"Du kannst nicht mehr Punkte verschenken, als du hast!", ephemeral=True)
    if str(member.id) not in list(data.keys()):
        data[str(member.id)] = {"points":0, "items":[]}
    data[str(member.id)]["points"] = str(int(data[str(member.id)]["points"])+points)
    data[str(ctx.author.id)]["points"] = str(int(data[str(ctx.author.id)]["points"])-points)
    save_data(data)
    return await ctx.respond(f"Es wurden erfolgreich {points} Punkte an **{member.display_name}** verschenkt!")
    
    
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if botmention(message) or botresponse(message):
        pass
    
    await bot.process_commands(message)
    
@bot.command()
async def ip(ctx):
    ip = requests.get("https://api.ipify.org").text
    await ctx.send(ip)
    
@bot.command()
async def restart(ctx=None):
    await botlog(0, "Der Bot wird neu gestartet...↓")
    await bot.close()
     
#botlog
class ModViewButton(discord.ui.Button):
    def __init__(self, message, level):
        super().__init__(label=f"LEVEL {level} LOG", style=discord.ButtonStyle.primary)
        self.message = message
        self.level = level
    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.id in MODS:
            await interaction.response.send_message(f"Diesen Log können nur **Mods** anschauen!", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"Log Level {self.level}",
            description=self.message
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
class ModView(discord.ui.View):
    def __init__(self, message, level:int):
        super().__init__(timeout=None)
        self.add_item(ModViewButton(message, level))

log_channel_id = 1384505304951029771
async def botlog(level:int, *msgs):
    level_map = {
        0: "INFO",
        1: "ONLYMODS",
        2: "WARNING",
        3: "ERROR"
    }
    message = " ".join(str(x) for x in msgs)
    channel = bot.get_channel(log_channel_id)
    msg = f"{level_map.get(level, 'ONLYMODS')}: {message}"
    if level==0:
        await channel.send(msg)
    else:
        view = ModView(msg, level)
        await channel.send(view=view)
     
async def fake(ctx, member: discord.Member, message:str=None, embed:discord.Embed=None, file:str=None):
    webhook = await ctx.channel.create_webhook(name=f"{member.display_name}_fake")
    if file:
        await webhook.send(
            content=message,
            username=member.display_name,
            avatar_url=member.avatar.url if member.avatar else None,
            embed=embed,
            file=file
        )
    else:
        await webhook.send(
        content=message,
        username=member.display_name,
        avatar_url=member.avatar.url if member.avatar else None,
        embed=embed,
    )
    
    await webhook.delete()

@bot.command()
async def announcement(ctx, title:str, message:str, url:str=None):
    await ctx.message.delete()
    if not ctx.author.id in MODS:
        return await ctx.send("Du hast keinen Zugriff auf diese Funktion!", ephemeral=True)
    allowed = [".png", ".jpg", ".jpeg", ".webp", ".gif", ]
    embed = discord.Embed(title=title, description=message)
    if url:
        if not any(url.lower().endswith(ext) for ext in allowed):
            return await ctx.send(f"Das angehängte Dateiformat wird nicht unterstützt! Unterstützte Formate: **{ext+', ' for ext in allowed}**", ephemeral=True)
        embed.set_image(url=url)
    
    return await fake(ctx, ctx.author, embed=embed)
    

#support
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
    if not is_mod(ctx.author.id):
        ctx.respond("Nur Mods können das!", ephemeral=True)
    view = SupportView()
    embed = discord.Embed(
        title="Support",
        description="Klicke unten, um ein privates Support-Ticket zu öffnen.",
        color=0x00aaff
    )
    await ctx.channel.send(embed=embed, view=view)
    await ctx.respond("Support-System wurde eingerichtet.", ephemeral=True)


if __name__ == "__main__":
    subthread = threading.Thread(target=lambda:sub(ans_callback))
    thread.start()
    bot.run("TOKEN")

