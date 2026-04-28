"""
All-in-One Discord Bot — Single File Edition
Features: Music, Moderation, AI Chat, Fun Commands, Ticket System, Help
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import json
import random
import datetime
import aiohttp
import yt_dlp
from collections import deque
from typing import Optional

# ─── CONFIG ────────────────────────────────────────────────────────────────────
TOKEN = os.getenv("DISCORD_TOKEN", "YOUR_DISCORD_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_API_KEY")
PREFIX = "!"

WARNINGS_FILE = "data/warnings.json"
TICKETS_FILE = "data/tickets.json"
MAX_HISTORY = 20

# ─── BOT SETUP ─────────────────────────────────────────────────────────────────
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ─── SHARED UTILITIES ──────────────────────────────────────────────────────────
def error_embed(msg: str) -> discord.Embed:
    return discord.Embed(description=msg, color=0xE74C3C)

def success_embed(msg: str) -> discord.Embed:
    return discord.Embed(description=msg, color=0x2ECC71)

bot.error_embed = error_embed
bot.success_embed = success_embed
bot.ANTHROPIC_API_KEY = ANTHROPIC_API_KEY


# ═══════════════════════════════════════════════════════════════════════════════
# MODERATION COG
# ═══════════════════════════════════════════════════════════════════════════════

def load_warnings():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(WARNINGS_FILE):
        return {}
    with open(WARNINGS_FILE, "r") as f:
        return json.load(f)

def save_warnings(data):
    os.makedirs("data", exist_ok=True)
    with open(WARNINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def mod_embed(title, desc, color=0x3498DB):
    return discord.Embed(title=title, description=desc, color=color, timestamp=datetime.datetime.utcnow())

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        if member.top_role >= ctx.author.top_role:
            return await ctx.send(embed=self.bot.error_embed("❌ You cannot ban someone with an equal or higher role."))
        await member.ban(reason=reason)
        await ctx.send(embed=mod_embed("🔨 User Banned", f"**{member}** has been banned.\n**Reason:** {reason}", 0xE74C3C))

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, user_input):
        bans = [entry async for entry in ctx.guild.bans()]
        for ban_entry in bans:
            if str(ban_entry.user) == user_input or str(ban_entry.user.id) == user_input:
                await ctx.guild.unban(ban_entry.user)
                return await ctx.send(embed=mod_embed("✅ User Unbanned", f"**{ban_entry.user}** has been unbanned.", 0x2ECC71))
        await ctx.send(embed=self.bot.error_embed("❌ User not found in ban list."))

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        if member.top_role >= ctx.author.top_role:
            return await ctx.send(embed=self.bot.error_embed("❌ You cannot kick someone with an equal or higher role."))
        await member.kick(reason=reason)
        await ctx.send(embed=mod_embed("👢 User Kicked", f"**{member}** has been kicked.\n**Reason:** {reason}", 0xE67E22))

    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, duration: int = 10, *, reason="No reason provided"):
        """Mute a user for [duration] minutes (default 10)."""
        until = datetime.datetime.utcnow() + datetime.timedelta(minutes=duration)
        await member.timeout(until, reason=reason)
        await ctx.send(embed=mod_embed("🔇 User Muted", f"**{member}** muted for **{duration}m**.\n**Reason:** {reason}", 0xF39C12))

    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        await member.timeout(None)
        await ctx.send(embed=mod_embed("🔊 User Unmuted", f"**{member}** has been unmuted.", 0x2ECC71))

    @commands.command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason="No reason provided"):
        warnings = load_warnings()
        key = str(member.id)
        if key not in warnings:
            warnings[key] = []
        warnings[key].append({"reason": reason, "mod": str(ctx.author), "time": str(datetime.datetime.utcnow())})
        save_warnings(warnings)
        count = len(warnings[key])
        await ctx.send(embed=mod_embed("⚠️ User Warned", f"**{member}** warned. Total warnings: **{count}**\n**Reason:** {reason}", 0xF39C12))

    @commands.command(name="warnings")
    @commands.has_permissions(manage_messages=True)
    async def warnings(self, ctx, member: discord.Member):
        warnings = load_warnings()
        key = str(member.id)
        user_warns = warnings.get(key, [])
        if not user_warns:
            return await ctx.send(embed=mod_embed("📋 Warnings", f"**{member}** has no warnings.", 0x2ECC71))
        desc = "\n".join([f"**{i+1}.** {w['reason']} — by {w['mod']}" for i, w in enumerate(user_warns)])
        await ctx.send(embed=mod_embed(f"⚠️ Warnings for {member}", desc, 0xF39C12))

    @commands.command(name="clearwarns")
    @commands.has_permissions(manage_guild=True)
    async def clearwarns(self, ctx, member: discord.Member):
        warnings = load_warnings()
        warnings[str(member.id)] = []
        save_warnings(warnings)
        await ctx.send(embed=mod_embed("✅ Warnings Cleared", f"All warnings cleared for **{member}**.", 0x2ECC71))

    @commands.command(name="purge", aliases=["clear"])
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int = 10):
        if amount < 1 or amount > 500:
            return await ctx.send(embed=self.bot.error_embed("❌ Amount must be between 1 and 500."))
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(embed=mod_embed("🧹 Messages Purged", f"Deleted **{len(deleted)-1}** messages.", 0x2ECC71))
        await msg.delete(delay=4)

    @commands.command(name="slowmode")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int = 0):
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.send(embed=mod_embed("✅ Slowmode Disabled", "Slowmode has been turned off.", 0x2ECC71))
        else:
            await ctx.send(embed=mod_embed("🐢 Slowmode Set", f"Slowmode set to **{seconds}s**.", 0x3498DB))

    @commands.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(embed=mod_embed("🔒 Channel Locked", f"{ctx.channel.mention} has been locked.", 0xE74C3C))

    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = True
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(embed=mod_embed("🔓 Channel Unlocked", f"{ctx.channel.mention} has been unlocked.", 0x2ECC71))

    @commands.command(name="nick")
    @commands.has_permissions(manage_nicknames=True)
    async def nick(self, ctx, member: discord.Member, *, nickname: Optional[str] = None):
        await member.edit(nick=nickname)
        if nickname:
            await ctx.send(embed=mod_embed("✏️ Nickname Changed", f"**{member}**'s nickname set to **{nickname}**.", 0x3498DB))
        else:
            await ctx.send(embed=mod_embed("✏️ Nickname Reset", f"**{member}**'s nickname was reset.", 0x3498DB))

    @commands.command(name="role")
    @commands.has_permissions(manage_roles=True)
    async def role(self, ctx, member: discord.Member, role: discord.Role):
        if role in member.roles:
            await member.remove_roles(role)
            await ctx.send(embed=mod_embed("➖ Role Removed", f"Removed **{role.name}** from **{member}**.", 0xE74C3C))
        else:
            await member.add_roles(role)
            await ctx.send(embed=mod_embed("➕ Role Added", f"Added **{role.name}** to **{member}**.", 0x2ECC71))

    @commands.command(name="serverinfo", aliases=["si"])
    async def serverinfo(self, ctx):
        g = ctx.guild
        e = discord.Embed(title=f"📊 {g.name}", color=0x3498DB, timestamp=datetime.datetime.utcnow())
        if g.icon:
            e.set_thumbnail(url=g.icon.url)
        e.add_field(name="Owner", value=g.owner.mention)
        e.add_field(name="Members", value=f"{g.member_count}")
        e.add_field(name="Channels", value=f"💬 {len(g.text_channels)} | 🔊 {len(g.voice_channels)}")
        e.add_field(name="Roles", value=len(g.roles))
        e.add_field(name="Boosts", value=f"{g.premium_subscription_count} (Tier {g.premium_tier})")
        e.add_field(name="Created", value=g.created_at.strftime("%b %d, %Y"))
        e.set_footer(text=f"ID: {g.id}")
        await ctx.send(embed=e)

    @commands.command(name="userinfo", aliases=["ui", "whois"])
    async def userinfo(self, ctx, member: Optional[discord.Member] = None):
        member = member or ctx.author
        roles = [r.mention for r in member.roles[1:]]
        e = discord.Embed(title=f"👤 {member}", color=member.color, timestamp=datetime.datetime.utcnow())
        e.set_thumbnail(url=member.display_avatar.url)
        e.add_field(name="ID", value=member.id)
        e.add_field(name="Nickname", value=member.nick or "None")
        e.add_field(name="Account Created", value=member.created_at.strftime("%b %d, %Y"), inline=False)
        e.add_field(name="Joined Server", value=member.joined_at.strftime("%b %d, %Y") if member.joined_at else "Unknown")
        e.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles) if roles else "None", inline=False)
        e.add_field(name="Bot", value="✅" if member.bot else "❌")
        await ctx.send(embed=e)


# ═══════════════════════════════════════════════════════════════════════════════
# MUSIC COG
# ═══════════════════════════════════════════════════════════════════════════════

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }],
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn"
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)


class Song:
    def __init__(self, source_url, title, webpage_url, thumbnail, duration, requester):
        self.source_url = source_url
        self.title = title
        self.webpage_url = webpage_url
        self.thumbnail = thumbnail
        self.duration = duration
        self.requester = requester

    @classmethod
    async def from_query(cls, query: str, requester):
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        if "entries" in data:
            data = data["entries"][0]
        return cls(
            source_url=data.get("url"),
            title=data.get("title", "Unknown"),
            webpage_url=data.get("webpage_url", ""),
            thumbnail=data.get("thumbnail", ""),
            duration=data.get("duration", 0),
            requester=requester,
        )

    def fmt_duration(self):
        mins, secs = divmod(self.duration or 0, 60)
        hrs, mins = divmod(mins, 60)
        return f"{hrs:02}:{mins:02}:{secs:02}" if hrs else f"{mins:02}:{secs:02}"


class GuildPlayer:
    def __init__(self):
        self.queue: deque[Song] = deque()
        self.current: Optional[Song] = None
        self.voice_client: Optional[discord.VoiceClient] = None
        self.loop = False
        self.volume = 0.5


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players: dict[int, GuildPlayer] = {}

    def get_player(self, guild_id: int) -> GuildPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = GuildPlayer()
        return self.players[guild_id]

    def music_embed(self, title, desc="", color=0x1DB954):
        return discord.Embed(title=title, description=desc, color=color, timestamp=datetime.datetime.utcnow())

    async def play_next(self, ctx):
        player = self.get_player(ctx.guild.id)
        if not player.queue and not player.loop:
            player.current = None
            return
        if not player.loop or player.current is None:
            if not player.queue:
                player.current = None
                return
            player.current = player.queue.popleft()
        song = player.current
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(song.source_url, **FFMPEG_OPTIONS),
            volume=player.volume
        )
        def after(error):
            if error:
                print(f"[Music] Player error: {error}")
            asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)
        player.voice_client.play(source, after=after)
        e = self.music_embed("🎵 Now Playing")
        e.set_thumbnail(url=song.thumbnail)
        e.add_field(name="Track", value=f"[{song.title}]({song.webpage_url})", inline=False)
        e.add_field(name="Duration", value=song.fmt_duration())
        e.add_field(name="Requested by", value=song.requester.mention)
        e.add_field(name="Loop", value="✅" if player.loop else "❌")
        await ctx.send(embed=e)

    @commands.command(name="join", aliases=["connect"])
    async def join(self, ctx):
        if not ctx.author.voice:
            return await ctx.send(embed=self.bot.error_embed("❌ You must be in a voice channel."))
        channel = ctx.author.voice.channel
        player = self.get_player(ctx.guild.id)
        if player.voice_client and player.voice_client.is_connected():
            await player.voice_client.move_to(channel)
        else:
            player.voice_client = await channel.connect()
        await ctx.send(embed=self.music_embed("✅ Joined", f"Connected to **{channel.name}**"))

    @commands.command(name="leave", aliases=["disconnect", "dc"])
    async def leave(self, ctx):
        player = self.get_player(ctx.guild.id)
        if player.voice_client and player.voice_client.is_connected():
            player.queue.clear()
            player.current = None
            await player.voice_client.disconnect()
            await ctx.send(embed=self.music_embed("👋 Disconnected", "Left the voice channel and cleared the queue."))
        else:
            await ctx.send(embed=self.bot.error_embed("❌ I'm not in a voice channel."))

    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx, *, query: str):
        if not ctx.author.voice:
            return await ctx.send(embed=self.bot.error_embed("❌ You must be in a voice channel."))
        player = self.get_player(ctx.guild.id)
        if not player.voice_client or not player.voice_client.is_connected():
            player.voice_client = await ctx.author.voice.channel.connect()
        async with ctx.typing():
            try:
                song = await Song.from_query(query, ctx.author)
            except Exception as e:
                return await ctx.send(embed=self.bot.error_embed(f"❌ Error fetching track: `{e}`"))
        player.queue.append(song)
        if not player.voice_client.is_playing():
            await self.play_next(ctx)
        else:
            e = self.music_embed("➕ Added to Queue")
            e.add_field(name="Track", value=f"[{song.title}]({song.webpage_url})", inline=False)
            e.add_field(name="Duration", value=song.fmt_duration())
            e.add_field(name="Position", value=len(player.queue))
            await ctx.send(embed=e)

    @commands.command(name="pause")
    async def pause(self, ctx):
        player = self.get_player(ctx.guild.id)
        if player.voice_client and player.voice_client.is_playing():
            player.voice_client.pause()
            await ctx.send(embed=self.music_embed("⏸️ Paused", "Playback paused."))
        else:
            await ctx.send(embed=self.bot.error_embed("❌ Nothing is playing."))

    @commands.command(name="resume")
    async def resume(self, ctx):
        player = self.get_player(ctx.guild.id)
        if player.voice_client and player.voice_client.is_paused():
            player.voice_client.resume()
            await ctx.send(embed=self.music_embed("▶️ Resumed", "Playback resumed."))
        else:
            await ctx.send(embed=self.bot.error_embed("❌ Playback is not paused."))

    @commands.command(name="stop")
    async def stop(self, ctx):
        player = self.get_player(ctx.guild.id)
        player.queue.clear()
        player.current = None
        player.loop = False
        if player.voice_client:
            player.voice_client.stop()
        await ctx.send(embed=self.music_embed("⏹️ Stopped", "Playback stopped and queue cleared."))

    @commands.command(name="skip", aliases=["s"])
    async def skip(self, ctx):
        player = self.get_player(ctx.guild.id)
        if player.voice_client and (player.voice_client.is_playing() or player.voice_client.is_paused()):
            player.voice_client.stop()
            await ctx.send(embed=self.music_embed("⏭️ Skipped", "Skipped to the next track."))
        else:
            await ctx.send(embed=self.bot.error_embed("❌ Nothing is playing."))

    @commands.command(name="queue", aliases=["q"])
    async def queue(self, ctx):
        player = self.get_player(ctx.guild.id)
        if not player.current and not player.queue:
            return await ctx.send(embed=self.music_embed("📭 Queue Empty", "Nothing is queued. Use `!play` to add songs."))
        e = self.music_embed("🎶 Music Queue")
        if player.current:
            e.add_field(
                name="▶️ Now Playing",
                value=f"[{player.current.title}]({player.current.webpage_url}) `{player.current.fmt_duration()}`",
                inline=False
            )
        if player.queue:
            lines = []
            for i, song in enumerate(list(player.queue)[:10], 1):
                lines.append(f"`{i}.` [{song.title}]({song.webpage_url}) `{song.fmt_duration()}`")
            e.add_field(name=f"Up Next ({len(player.queue)})", value="\n".join(lines), inline=False)
        e.set_footer(text=f"Loop: {'✅' if player.loop else '❌'} | Volume: {int(player.volume*100)}%")
        await ctx.send(embed=e)

    @commands.command(name="nowplaying", aliases=["np"])
    async def nowplaying(self, ctx):
        player = self.get_player(ctx.guild.id)
        if not player.current:
            return await ctx.send(embed=self.bot.error_embed("❌ Nothing is currently playing."))
        song = player.current
        e = self.music_embed("🎵 Now Playing")
        e.set_thumbnail(url=song.thumbnail)
        e.add_field(name="Track", value=f"[{song.title}]({song.webpage_url})", inline=False)
        e.add_field(name="Duration", value=song.fmt_duration())
        e.add_field(name="Requested by", value=song.requester.mention)
        await ctx.send(embed=e)

    @commands.command(name="volume", aliases=["vol"])
    async def volume(self, ctx, vol: int):
        if not 0 <= vol <= 100:
            return await ctx.send(embed=self.bot.error_embed("❌ Volume must be between 0 and 100."))
        player = self.get_player(ctx.guild.id)
        player.volume = vol / 100
        if player.voice_client and player.voice_client.source:
            player.voice_client.source.volume = player.volume
        await ctx.send(embed=self.music_embed("🔊 Volume Set", f"Volume set to **{vol}%**"))

    @commands.command(name="loop")
    async def loop(self, ctx):
        player = self.get_player(ctx.guild.id)
        player.loop = not player.loop
        state = "✅ enabled" if player.loop else "❌ disabled"
        await ctx.send(embed=self.music_embed("🔁 Loop", f"Loop is now **{state}**."))


# ═══════════════════════════════════════════════════════════════════════════════
# FUN COG
# ═══════════════════════════════════════════════════════════════════════════════

EIGHT_BALL_RESPONSES = [
    "🟢 It is certain.", "🟢 It is decidedly so.", "🟢 Without a doubt.",
    "🟢 Yes, definitely.", "🟢 You may rely on it.", "🟢 As I see it, yes.",
    "🟢 Most likely.", "🟢 Outlook good.", "🟢 Yes.", "🟢 Signs point to yes.",
    "🟡 Reply hazy, try again.", "🟡 Ask again later.", "🟡 Better not tell you now.",
    "🟡 Cannot predict now.", "🟡 Concentrate and ask again.",
    "🔴 Don't count on it.", "🔴 My reply is no.", "🔴 My sources say no.",
    "🔴 Outlook not so good.", "🔴 Very doubtful.",
]

JOKES = [
    ("Why don't scientists trust atoms?", "Because they make up everything!"),
    ("Why did the scarecrow win an award?", "He was outstanding in his field!"),
    ("Why don't eggs tell jokes?", "They'd crack each other up!"),
    ("What do you call a fish without eyes?", "A fsh!"),
    ("Did you hear about the mathematician who's afraid of negative numbers?", "He'll stop at nothing to avoid them!"),
    ("Why did the bicycle fall over?", "Because it was two-tired!"),
    ("What's the best way to watch a fly fishing tournament?", "Live stream!"),
    ("I'm reading a book about anti-gravity.", "It's impossible to put down!"),
    ("Did you hear about the claustrophobic astronaut?", "He just needed a little space."),
    ("Why don't scientists trust stairs?", "They're always up to something."),
]

FACTS = [
    "A group of flamingos is called a 'flamboyance'.",
    "Honey never spoils — archaeologists have found 3,000-year-old honey in Egyptian tombs that was still good.",
    "The shortest war in history lasted only 38–45 minutes.",
    "Bananas are berries, but strawberries are not.",
    "Octopuses have three hearts and blue blood.",
    "There are more possible iterations of a chess game than atoms in the observable universe.",
    "The average person walks the equivalent of five times around the Earth in their lifetime.",
    "Crows can recognise human faces and hold grudges.",
    "A single cloud can weigh more than a million pounds.",
    "Wombat poop is cube-shaped.",
]

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def fun_embed(self, title="", desc="", color=0x9B59B6):
        return discord.Embed(title=title, description=desc, color=color, timestamp=datetime.datetime.utcnow())

    @commands.command(name="8ball", aliases=["magic8"])
    async def eight_ball(self, ctx, *, question: str):
        response = random.choice(EIGHT_BALL_RESPONSES)
        e = self.fun_embed("🎱 Magic 8-Ball")
        e.add_field(name="Question", value=question, inline=False)
        e.add_field(name="Answer", value=response, inline=False)
        await ctx.send(embed=e)

    @commands.command(name="coinflip", aliases=["flip", "coin"])
    async def coinflip(self, ctx):
        result = random.choice(["🪙 **Heads!**", "🪙 **Tails!**"])
        await ctx.send(embed=self.fun_embed("Coin Flip", result, 0xF1C40F))

    @commands.command(name="dice", aliases=["roll"])
    async def dice(self, ctx, sides: int = 6):
        if sides < 2:
            return await ctx.send(embed=self.bot.error_embed("❌ Dice must have at least 2 sides."))
        result = random.randint(1, sides)
        await ctx.send(embed=self.fun_embed("🎲 Dice Roll", f"Rolling a **d{sides}**... You rolled **{result}**!", 0xE74C3C))

    @commands.command(name="rps")
    async def rps(self, ctx, choice: str):
        choices = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        choice = choice.lower()
        if choice not in choices:
            return await ctx.send(embed=self.bot.error_embed("❌ Choose: `rock`, `paper`, or `scissors`"))
        bot_choice = random.choice(list(choices.keys()))
        wins = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
        if choice == bot_choice:
            result, color = "🤝 **It's a tie!**", 0xF1C40F
        elif wins[choice] == bot_choice:
            result, color = "🎉 **You win!**", 0x2ECC71
        else:
            result, color = "💀 **You lose!**", 0xE74C3C
        e = self.fun_embed("Rock Paper Scissors", "", color)
        e.add_field(name="Your choice", value=f"{choices[choice]} {choice.capitalize()}")
        e.add_field(name="My choice", value=f"{choices[bot_choice]} {bot_choice.capitalize()}")
        e.add_field(name="Result", value=result, inline=False)
        await ctx.send(embed=e)

    @commands.command(name="joke")
    async def joke(self, ctx):
        setup, punchline = random.choice(JOKES)
        e = self.fun_embed("😂 Random Joke", color=0xF39C12)
        e.add_field(name="Setup", value=setup, inline=False)
        e.add_field(name="Punchline", value=f"||{punchline}||", inline=False)
        e.set_footer(text="Click the spoiler to reveal the punchline!")
        await ctx.send(embed=e)

    @commands.command(name="fact")
    async def fact(self, ctx):
        f = random.choice(FACTS)
        await ctx.send(embed=self.fun_embed("🌍 Random Fact", f, 0x1ABC9C))

    @commands.command(name="poll")
    async def poll(self, ctx, question: str, *options):
        if len(options) < 2:
            return await ctx.send(embed=self.bot.error_embed('❌ Usage: `!poll "Question" "Option1" "Option2" ...`'))
        if len(options) > 10:
            return await ctx.send(embed=self.bot.error_embed("❌ Maximum 10 options allowed."))
        emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        desc = "\n".join([f"{emojis[i]} {opt}" for i, opt in enumerate(options)])
        e = self.fun_embed(f"📊 {question}", desc, 0x3498DB)
        e.set_footer(text=f"Poll by {ctx.author.display_name}")
        msg = await ctx.send(embed=e)
        for i in range(len(options)):
            await msg.add_reaction(emojis[i])

    @commands.command(name="avatar", aliases=["av", "pfp"])
    async def avatar(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        e = discord.Embed(title=f"🖼️ {member.display_name}'s Avatar", color=0x3498DB)
        e.set_image(url=member.display_avatar.url)
        e.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=e)

    @commands.command(name="ping")
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        color = 0x2ECC71 if latency < 100 else (0xF39C12 if latency < 200 else 0xE74C3C)
        await ctx.send(embed=self.fun_embed("🏓 Pong!", f"Latency: **{latency}ms**", color))

    @commands.command(name="choose")
    async def choose(self, ctx, *options):
        if len(options) < 2:
            return await ctx.send(embed=self.bot.error_embed("❌ Give me at least 2 options to choose from!"))
        chosen = random.choice(options)
        await ctx.send(embed=self.fun_embed("🤔 I Choose...", f"**{chosen}**", 0x9B59B6))

    @commands.command(name="reverse")
    async def reverse(self, ctx, *, text: str):
        await ctx.send(embed=self.fun_embed("🔄 Reversed", text[::-1], 0x3498DB))


# ═══════════════════════════════════════════════════════════════════════════════
# AI CHAT COG
# ═══════════════════════════════════════════════════════════════════════════════

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.histories: dict[int, list] = {}

    def get_history(self, user_id: int) -> list:
        return self.histories.setdefault(user_id, [])

    def trim_history(self, user_id: int):
        h = self.histories.get(user_id, [])
        if len(h) > MAX_HISTORY:
            self.histories[user_id] = h[-MAX_HISTORY:]

    async def call_claude(self, user_id: int, user_message: str) -> str:
        history = self.get_history(user_id)
        history.append({"role": "user", "content": user_message})
        self.trim_history(user_id)
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "system": (
                "You are a helpful, friendly, and witty Discord bot assistant. "
                "Keep responses concise (under 1800 characters) and conversational. "
                "Use Discord markdown formatting where appropriate. "
                "If someone asks about your capabilities, mention your features: "
                "music, moderation, AI chat, fun commands, and a ticket system."
            ),
            "messages": self.histories[user_id],
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.bot.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        }
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"API error {resp.status}: {error_text}")
                data = await resp.json()
        reply = data["content"][0]["text"]
        history.append({"role": "assistant", "content": reply})
        return reply

    def ai_embed(self, title, desc, color=0x7289DA):
        return discord.Embed(title=title, description=desc, color=color, timestamp=datetime.datetime.utcnow())

    @commands.command(name="ask", aliases=["ai", "claude"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ask(self, ctx, *, question: str):
        """Ask the AI a question. Maintains conversation history per user."""
        async with ctx.typing():
            try:
                reply = await self.call_claude(ctx.author.id, question)
            except Exception as e:
                return await ctx.send(embed=self.bot.error_embed(f"❌ AI error: `{e}`"))
        if len(reply) > 1900:
            reply = reply[:1900] + "..."
        e = self.ai_embed("🤖 AI Response", reply)
        e.set_footer(text=f"Asked by {ctx.author.display_name} | !resetchat to clear history")
        await ctx.send(embed=e)

    @commands.command(name="resetchat", aliases=["clearchat", "newchat"])
    async def resetchat(self, ctx):
        """Clear your AI conversation history."""
        self.histories[ctx.author.id] = []
        await ctx.send(embed=self.bot.success_embed("🔄 Chat history cleared! Starting fresh."))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if self.bot.user not in message.mentions:
            return
        content = message.content.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "").strip()
        if not content:
            await message.channel.send(embed=self.ai_embed("👋 Hi there!", f"Hey {message.author.mention}! Mention me with a question, or use `!ask <question>` to chat with me."))
            return
        async with message.channel.typing():
            try:
                reply = await self.call_claude(message.author.id, content)
            except Exception as e:
                return await message.channel.send(embed=self.bot.error_embed(f"❌ AI error: `{e}`"))
        if len(reply) > 1900:
            reply = reply[:1900] + "..."
        e = self.ai_embed("🤖 AI Response", reply)
        e.set_footer(text=f"Replying to {message.author.display_name}")
        await message.channel.send(embed=e)


# ═══════════════════════════════════════════════════════════════════════════════
# TICKET SYSTEM COG
# ═══════════════════════════════════════════════════════════════════════════════

def load_tickets():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(TICKETS_FILE):
        return {}
    with open(TICKETS_FILE) as f:
        return json.load(f)

def save_tickets(data):
    os.makedirs("data", exist_ok=True)
    with open(TICKETS_FILE, "w") as f:
        json.dump(data, f, indent=2)


class TicketView(discord.ui.View):
    """Persistent view for the ticket creation panel."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Open Ticket", style=discord.ButtonStyle.green, custom_id="ticket_open")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        tickets = load_tickets()
        guild_tickets = tickets.get(str(guild.id), {})
        for ch_id, info in guild_tickets.items():
            if str(info.get("user_id")) == str(member.id) and info.get("open"):
                ch = guild.get_channel(int(ch_id))
                if ch:
                    return await interaction.response.send_message(
                        f"❌ You already have an open ticket: {ch.mention}", ephemeral=True
                    )
        category = discord.utils.get(guild.categories, name="Support Tickets")
        if not category:
            category = await guild.create_category("Support Tickets")
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
        }
        for role in guild.roles:
            if role.permissions.manage_guild:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        ticket_num = len(guild_tickets) + 1
        channel = await guild.create_text_channel(
            name=f"ticket-{ticket_num:04d}",
            category=category,
            overwrites=overwrites,
            topic=f"Support ticket for {member} | ID: {member.id}"
        )
        if str(guild.id) not in tickets:
            tickets[str(guild.id)] = {}
        tickets[str(guild.id)][str(channel.id)] = {
            "user_id": member.id,
            "username": str(member),
            "channel_id": channel.id,
            "open": True,
            "created_at": str(datetime.datetime.utcnow()),
            "number": ticket_num,
        }
        save_tickets(tickets)
        e = discord.Embed(
            title=f"🎫 Ticket #{ticket_num:04d}",
            description=(
                f"Welcome {member.mention}! A staff member will be with you shortly.\n\n"
                "**Please describe your issue in detail.**\n\n"
                "Use the button below to close this ticket when resolved."
            ),
            color=0x3498DB,
            timestamp=datetime.datetime.utcnow()
        )
        e.set_footer(text=f"Ticket by {member.display_name}")
        close_view = CloseTicketView()
        await channel.send(f"{member.mention}", embed=e, view=close_view)
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)


class CloseTicketView(discord.ui.View):
    """View inside ticket channel for closing."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.red, custom_id="ticket_close_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await close_ticket_channel(interaction.channel, interaction.user, interaction.guild)
        await interaction.response.send_message("✅ Closing ticket...", ephemeral=True)


async def close_ticket_channel(channel: discord.TextChannel, closer, guild: discord.Guild):
    tickets = load_tickets()
    guild_data = tickets.get(str(guild.id), {})
    ch_id = str(channel.id)
    if ch_id in guild_data:
        guild_data[ch_id]["open"] = False
        guild_data[ch_id]["closed_by"] = str(closer)
        guild_data[ch_id]["closed_at"] = str(datetime.datetime.utcnow())
        tickets[str(guild.id)] = guild_data
        save_tickets(tickets)
    e = discord.Embed(
        title="🔒 Ticket Closed",
        description=f"Ticket closed by **{closer.mention}**.\nThis channel will be deleted in **5 seconds**.",
        color=0xE74C3C,
        timestamp=datetime.datetime.utcnow()
    )
    await channel.send(embed=e)
    await asyncio.sleep(5)
    await channel.delete(reason=f"Ticket closed by {closer}")


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_view(TicketView())
        bot.add_view(CloseTicketView())

    def ticket_embed(self, title, desc="", color=0x3498DB):
        return discord.Embed(title=title, description=desc, color=color, timestamp=datetime.datetime.utcnow())

    @commands.group(name="ticket", invoke_without_command=True)
    async def ticket_group(self, ctx):
        await ctx.send(embed=self.bot.error_embed(
            "❌ Use a subcommand: `setup`, `close`, `add`, `remove`, `rename`, `list`"
        ))

    @ticket_group.command(name="setup")
    @commands.has_permissions(manage_guild=True)
    async def ticket_setup(self, ctx, channel: discord.TextChannel = None):
        """Send the ticket panel to a channel."""
        channel = channel or ctx.channel
        e = discord.Embed(
            title="🎫 Support Tickets",
            description=(
                "Need help? Click the button below to open a private support ticket.\n\n"
                "A staff member will assist you as soon as possible.\n\n"
                "**Please do not open multiple tickets for the same issue.**"
            ),
            color=0x3498DB
        )
        e.set_footer(text=ctx.guild.name)
        if ctx.guild.icon:
            e.set_thumbnail(url=ctx.guild.icon.url)
        await channel.send(embed=e, view=TicketView())
        await ctx.send(embed=self.bot.success_embed(f"✅ Ticket panel sent to {channel.mention}!"))

    @ticket_group.command(name="close")
    async def ticket_close(self, ctx):
        """Close the current ticket channel."""
        tickets = load_tickets()
        guild_data = tickets.get(str(ctx.guild.id), {})
        if str(ctx.channel.id) not in guild_data:
            return await ctx.send(embed=self.bot.error_embed("❌ This is not a ticket channel."))
        await close_ticket_channel(ctx.channel, ctx.author, ctx.guild)

    @ticket_group.command(name="add")
    @commands.has_permissions(manage_channels=True)
    async def ticket_add(self, ctx, member: discord.Member):
        tickets = load_tickets()
        if str(ctx.channel.id) not in tickets.get(str(ctx.guild.id), {}):
            return await ctx.send(embed=self.bot.error_embed("❌ This is not a ticket channel."))
        await ctx.channel.set_permissions(member, read_messages=True, send_messages=True)
        await ctx.send(embed=self.ticket_embed("➕ User Added", f"**{member.mention}** added to ticket.", 0x2ECC71))

    @ticket_group.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    async def ticket_remove(self, ctx, member: discord.Member):
        tickets = load_tickets()
        if str(ctx.channel.id) not in tickets.get(str(ctx.guild.id), {}):
            return await ctx.send(embed=self.bot.error_embed("❌ This is not a ticket channel."))
        await ctx.channel.set_permissions(member, overwrite=None)
        await ctx.send(embed=self.ticket_embed("➖ User Removed", f"**{member.mention}** removed from ticket.", 0xE74C3C))

    @ticket_group.command(name="rename")
    @commands.has_permissions(manage_channels=True)
    async def ticket_rename(self, ctx, *, name: str):
        tickets = load_tickets()
        if str(ctx.channel.id) not in tickets.get(str(ctx.guild.id), {}):
            return await ctx.send(embed=self.bot.error_embed("❌ This is not a ticket channel."))
        safe_name = name.lower().replace(" ", "-")
        await ctx.channel.edit(name=safe_name)
        await ctx.send(embed=self.ticket_embed("✏️ Ticket Renamed", f"Channel renamed to **{safe_name}**."))

    @ticket_group.command(name="list")
    @commands.has_permissions(manage_guild=True)
    async def ticket_list(self, ctx):
        tickets = load_tickets()
        guild_data = tickets.get(str(ctx.guild.id), {})
        open_tickets = {k: v for k, v in guild_data.items() if v.get("open")}
        if not open_tickets:
            return await ctx.send(embed=self.ticket_embed("🎫 Open Tickets", "No open tickets.", 0x2ECC71))
        lines = []
        for ch_id, info in open_tickets.items():
            ch = ctx.guild.get_channel(int(ch_id))
            ch_mention = ch.mention if ch else f"<#{ch_id}>"
            lines.append(f"{ch_mention} — **{info['username']}** (Ticket #{info['number']:04d})")
        await ctx.send(embed=self.ticket_embed(f"🎫 Open Tickets ({len(open_tickets)})", "\n".join(lines)))


# ═══════════════════════════════════════════════════════════════════════════════
# BOT EVENTS & STARTUP
# ═══════════════════════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    print(f"\n{'='*45}")
    print(f"  🤖  {bot.user} is online!")
    print(f"  🌐  Guilds: {len(bot.guilds)}")
    print(f"  👥  Users:  {sum(g.member_count for g in bot.guilds)}")
    print(f"{'='*45}\n")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{PREFIX}help | {len(bot.guilds)} servers"
        )
    )
    try:
        synced = await bot.tree.sync()
        print(f"  🔄  Synced {len(synced)} slash commands\n")
    except Exception as e:
        print(f"  ⚠️  Slash sync error: {e}\n")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=error_embed("❌ You don't have permission to use this command."))
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=error_embed(f"❌ Missing argument: `{error.param.name}`"))
    elif isinstance(error, commands.BadArgument):
        await ctx.send(embed=error_embed("❌ Invalid argument provided."))
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(embed=error_embed(f"⏳ Cooldown! Try again in `{error.retry_after:.1f}s`"))
    else:
        await ctx.send(embed=error_embed(f"❌ An error occurred: `{error}`"))


async def main():
    async with bot:
        await bot.add_cog(Moderation(bot))
        await bot.add_cog(Music(bot))
        await bot.add_cog(Fun(bot))
        await bot.add_cog(AIChat(bot))
        await bot.add_cog(Tickets(bot))
        print("  ✅ All cogs loaded")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
