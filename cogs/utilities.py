"""
Utilities Cog - General commands: help, ping, lyrics, 24/7, stats, search, invite.
"""

from __future__ import annotations

import os
import platform
import asyncio
import logging
from datetime import datetime
from pathlib import Path

import discord
import psutil
import wavelink
from discord.ext import commands

log = logging.getLogger("Utilities")


class Utilities(commands.Cog, name="Utilities"):
    """🛠️ General-purpose commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.twenty_four_seven: dict[int, bool] = {}

    # ------------------------------------------------------------------
    @commands.command(name="help", aliases=["h", "උදව්", "halp"])
    async def help_cmd(self, ctx: commands.Context, category: str = None) -> None:
        """Show all commands."""
        prefix = ctx.prefix
        embed = discord.Embed(
            title="🎵 Nextus Sounds — Help",
            description=f"ඔයාගේ Discord music bot | Prefix: `{prefix}`",
            color=0x2F3136,
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else discord.Embed.Empty)
        categories = {
            "Music 🎵": [
                f"`{prefix}play <query>` — Play a song / add to queue",
                f"`{prefix}pause` / `{prefix}resume`",
                f"`{prefix}skip` / `{prefix}stop`",
                f"`{prefix}queue` — Show queue",
                f"`{prefix}nowplaying` — Show current",
                f"`{prefix}volume <0-150>` — Set volume",
                f"`{prefix}loop <off|track|queue>`",
                f"`{prefix}shuffle`",
                f"`{prefix}seek <seconds>`",
                f"`{prefix}remove <pos>` / `{prefix}clearqueue`",
            ],
            "Soundboard 🎺": [
                f"`{prefix}sb <name>` — Play a custom sound",
                f"`{prefix}sounds` — List all sounds",
                f"`{prefix}sb add/remove` (Admin)",
            ],
            "Filters 🎚️": [
                f"`{prefix}filter <name>` — Apply filter",
                f"`{prefix}filters` — List all",
                f"`{prefix}speed <val>` / `{prefix}pitch <val>`",
            ],
            "Utilities 🛠️": [
                f"`{prefix}ping` — Latency",
                f"`{prefix}stats` — Bot stats",
                f"`{prefix}lyrics <song>` — Get lyrics",
                f"`{prefix}search <query>` — Search YouTube",
                f"`{prefix}24/7` — Toggle stay-in-VC mode",
                f"`{prefix}invite` — Bot invite link",
            ],
        }
        for name, cmds in categories.items():
            embed.add_field(name=name, value="\n".join(cmds), inline=False)
        embed.set_footer(text="🎵 Made with 💚 | Nextus Sounds v1.0")
        await ctx.send(embed=embed)

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context) -> None:
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"**{latency}ms**",
            color=0x43B581 if latency < 200 else 0xFAA61A,
        )
        await ctx.send(embed=embed)

    @commands.command(name="stats", aliases=["info", "about"])
    async def stats(self, ctx: commands.Context) -> None:
        """Show bot statistics."""
        proc = psutil.Process(os.getpid())
        cpu = psutil.cpu_percent()
        mem = proc.memory_info().rss / 1024 / 1024
        embed = discord.Embed(title="📊 Nextus Sounds Stats", color=0x2F3136)
        embed.add_field(name="Servers", value=f"{len(self.bot.guilds)} 🏠", inline=True)
        embed.add_field(name="Users", value=f"{sum(g.member_count for g in self.bot.guilds)} 👥", inline=True)
        embed.add_field(name="Voice", value=f"{len(self.bot.voice_clients)} 🎙️", inline=True)
        embed.add_field(
            name="Latency",
            value=f"{round(self.bot.latency * 1000)}ms",
            inline=True,
        )
        embed.add_field(name="CPU", value=f"{cpu}%", inline=True)
        embed.add_field(name="RAM", value=f"{mem:.1f} MB", inline=True)
        embed.add_field(name="Python", value=f"{platform.python_version()} 🐍", inline=True)
        embed.add_field(name="Discord.py", value=discord.__version__, inline=True)
        embed.add_field(name="OS", value=f"{platform.system()} 💻", inline=True)
        embed.set_footer(text=f"Uptime since {self.bot.start_time.strftime('%Y-%m-%d %H:%M UTC')}")
        await ctx.send(embed=embed)

    @commands.command(name="lyrics", aliases=["ly"])
    async def lyrics(self, ctx: commands.Context, *, song: str = None) -> None:
        """Fetch lyrics for a song (uses free API)."""
        api_key = os.getenv("GENIUS_API_KEY")
        if not api_key:
            await ctx.send("❌ Genius API key නෑ (.env file බලන්න).")
            return
        if not song:
            if ctx.voice_client and ctx.voice_client.current:
                song = ctx.voice_client.current.title
            else:
                await ctx.send("❌ Song එකක නමක් දෙන්න!")
                return
        try:
            import lyricsgenius
            genius = lyricsgenius.Genius(api_key, verbose=False, remove_section_headers=True)
            data = genius.search_song(song)
            if not data:
                await ctx.send(f"❌ Lyrics හොයාගන්න බෑ: **{song}**")
                return
            text = data.lyrics[:2000] + ("..." if len(data.lyrics) > 2000 else "")
            embed = discord.Embed(title=f"📜 {song}", description=text, color=0xFFFF64)
            embed.set_footer(text="Powered by Genius")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Lyrics fetch බෑ: {e}")

    @commands.command(name="search")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def search(self, ctx: commands.Context, *, query: str) -> None:
        """Search YouTube and show top 5 results."""
        try:
            # wavelink v3: Use YouTubeTrack.search instead of Playable.search
            from wavelink import YouTubeTrack
            tracks = await YouTubeTrack.search(f"ytsearch5:{query}")
            # v3 Search result has .tracks attribute
            if hasattr(tracks, "tracks"):
                tracks = list(tracks.tracks)
            else:
                tracks = list(tracks)
            if not tracks:
                await ctx.send("❌ ඒක හොයාගන්න බෑ!")
                return
            embed = discord.Embed(title=f"🔎 Search: {query}", color=0xFF0000)
            for i, tr in enumerate(tracks[:5], start=1):
                embed.add_field(
                    name=f"{i}. {tr.title}",
                    value=f"`{tr.author}` — {tr.duration // 1000}s\n[Link]({tr.uri})",
                    inline=False,
                )
            embed.set_footer(text=f"!play <url or number> to add")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Search බෑ: {e}")

    @commands.command(name="24/7", aliases=["247", "stay"])
    @commands.has_permissions(manage_guild=True)
    async def twenty_four_seven(self, ctx: commands.Context) -> None:
        """Toggle 24/7 mode (bot stays in VC)."""
        gid = ctx.guild.id
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ Voice channel එකක join වෙන්න ඕනේ!")
            return
        current = self.twenty_four_seven.get(gid, False)
        self.twenty_four_seven[gid] = not current
        new_state = not current
        vc = ctx.voice_client
        if not new_state and vc:
            await vc.disconnect()
        elif new_state and not vc:
            await ctx.author.voice.channel.connect()
        status = "ON 🌙" if new_state else "OFF ☀️"
        await ctx.send(f"🎚️ 24/7 Mode: **{status}**")

    # ------------------------------------------------------------------
    @commands.command(name="invite")
    async def invite(self, ctx: commands.Context) -> None:
        """Bot invite link with required permissions."""
        perms = (
            discord.Permissions(
                send_messages=True,
                embed_links=True,
                connect=True,
                speak=True,
                use_voice_activity=True,
                manage_messages=True,
                read_messages=True,
            ).value
            & ~discord.Permissions(administrator=True).value
        )
        url = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=discord.Permissions(perms),
            scopes=("bot", "applications.commands"),
        )
        embed = discord.Embed(
            title="📩 Invite Nextus Sounds",
            description=f"[Click here to invite]({url})",
            color=0x2F3136,
        )
        await ctx.send(embed=embed)

    @commands.command(name="vote-skip", aliases=["voteskip", "vs"])
    async def vote_skip(self, ctx: commands.Context) -> None:
        """Vote to skip the current track. Threshold: 50% of listeners."""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ Voice channel එකක join වෙන්න ඕනේ!")
            return
        if not ctx.voice_client or not ctx.voice_client.current:
            await ctx.send("❌ Skip කරන්න song එකක් නෑ!")
            return
        channel = ctx.author.voice.channel
        listeners = [m for m in channel.members if not m.bot]
        needed = max(1, int(len(listeners) * 0.5))
        await ctx.send(
            f"🗳️ Vote skip cast! Need **{needed}** votes total "
            f"(your vote already counted). Use `{ctx.prefix}vote-skip` to vote."
        )
        # Simplified: for production, persist votes in GuildPlayer.dj_votes
        # Here we just skip when threshold reached — basic implementation
        threshold = max(1, len(listeners) // 2)
        # Increment votes via a simple counter
        if not hasattr(self, "_votes"):
            self._votes = {}
        self._votes.setdefault(ctx.guild.id, 0)
        self._votes[ctx.guild.id] += 1
        if self._votes[ctx.guild.id] >= threshold:
            await ctx.voice_client.stop()
            self._votes[ctx.guild.id] = 0
            await ctx.send("🗳️ Vote skip **PASSED** — skipped!")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utilities(bot))