"""
All-in-One Discord Bot — Single File Edition (Gemini Version)
Features: Music, Moderation, Gemini AI Chat, Fun, Tickets
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
TOKEN = os.getenv("DISCORD_TOKEN", "YOUR_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_KEY")
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
bot.GEMINI_API_KEY = GEMINI_API_KEY


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
            return await ctx.send(embed=self.bot.error_embed("❌ Higher role error."))
        await member.ban(reason=reason)
        await ctx.send(embed=mod_embed("🔨 Banned", f"**{member}** banned.\n**Reason:** {reason}", 0xE74C3C))

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        if member.top_role >= ctx.author.top_role:
            return await ctx.send(embed=self.bot.error_embed("❌ Higher role error."))
        await member.kick(reason=reason)
        await ctx.send(embed=mod_embed("👢 Kicked", f"**{member}** kicked.\n**Reason:** {reason}", 0xE67E22))

    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, duration: int = 10, *, reason="No reason provided"):
        until = datetime.datetime.utcnow() + datetime.timedelta(minutes=duration)
        await member.timeout(until, reason=reason)
        await ctx.send(embed=mod_embed("🔇 Muted", f"**{member}** muted for **{duration}m**.", 0xF39C12))

    @commands.command(name="unmute")
    async def unmute(self, ctx, member: discord.Member):
        await member.timeout(None)
        await ctx.send(embed=mod_embed("🔊 Unmuted", f"**{member}** unmuted.", 0x2ECC71))

    @commands.command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason="No reason provided"):
        warnings = load_warnings()
        key = str(member.id)
        if key not in warnings: warnings[key] = []
        warnings[key].append({"reason": reason, "mod": str(ctx.author), "time": str(datetime.datetime.utcnow())})
        save_warnings(warnings)
        await ctx.send(embed=mod_embed("⚠️ Warned", f"**{member}** warned. Count: **{len(warnings[key])}**", 0xF39C12))

    @commands.command(name="purge", aliases=["clear"])
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int = 10):
        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(embed=mod_embed("🧹 Purged", f"Deleted **{len(deleted)-1}** messages.", 0x2ECC71), delete_after=4)

    @commands.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(embed=mod_embed("🔒 Locked", "Channel locked.", 0xE74C3C))

    @commands.command(name="unlock")
    async def unlock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send(embed=mod_embed("🔓 Unlocked", "Channel unlocked.", 0x2ECC71))

    @commands.command(name="serverinfo", aliases=["si"])
    async def serverinfo(self, ctx):
        g = ctx.guild
        e = discord.Embed(title=f"📊 {g.name}", color=0x3498DB)
        e.add_field(name="Owner", value=g.owner.mention)
        e.add_field(name="Members", value=g.member_count)
        await ctx.send(embed=e)


# ═══════════════════════════════════════════════════════════════════════════════
# MUSIC COG
# ═══════════════════════════════════════════════════════════════════════════════

YTDL_OPTIONS = {"format": "bestaudio/best", "noplaylist": True, "quiet": True, "default_search": "ytsearch"}
FFMPEG_OPTIONS = {"before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", "options": "-vn"}
ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

class Song:
    def __init__(self, source_url, title, webpage_url, thumbnail, duration, requester):
        self.source_url, self.title, self.webpage_url = source_url, title, webpage_url
        self.thumbnail, self.duration, self.requester = thumbnail, duration, requester
    @classmethod
    async def from_query(cls, query, requester):
        data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        if "entries" in data: data = data["entries"][0]
        return cls(data["url"], data["title"], data["webpage_url"], data["thumbnail"], data["duration"], requester)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}
    
    async def play_next(self, ctx, player):
        if not player["queue"]: player["current"] = None; return
        song = player["queue"].popleft()
        player["current"] = song
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song.source_url, **FFMPEG_OPTIONS), volume=0.5)
        ctx.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx, player), self.bot.loop))
        await ctx.send(f"🎵 **Playing:** {song.title}")

    @commands.command(name="play")
    async def play(self, ctx, *, query):
        if not ctx.voice_client: await ctx.author.voice.channel.connect()
        player = self.players.setdefault(ctx.guild.id, {"queue": deque(), "current": None})
        song = await Song.from_query(query, ctx.author)
        player["queue"].append(song)
        if not ctx.voice_client.is_playing(): await self.play_next(ctx, player)
        else: await ctx.send(f"➕ **Queued:** {song.title}")

    @commands.command(name="stop")
    async def stop(self, ctx):
        if ctx.voice_client: 
            self.players[ctx.guild.id]["queue"].clear()
            ctx.voice_client.stop()
            await ctx.send("⏹️ Stopped.")
