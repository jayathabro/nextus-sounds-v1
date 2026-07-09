"""Extras Cog - Favorites, Playlists, History, Stats.

Commands:
    !fav / !favorites [list]   - list favorites
    !fav add                  - favorite the current song
    !fav remove <uri or idx>   - remove from favorites
    !fav play <idx>           - play saved favorite

    !playlist make <name>     - save current queue as playlist
    !playlist load <name>     - load and play playlist
    !playlist list            - list your playlists
    !playlist delete <name>   - delete playlist

    !history                  - show last 10 played songs in this server
    !recent                   - globally recent

    !stat / !stats <user>     - show stats
    !top                      - top 10 most-played songs in this server
    !topuser                  - top 10 listeners

    !dedupe                   - remove duplicate songs from queue
    !repeat <off|track|queue> - alias for loop

    !language <si|en>         - change server language
    !djrole @role             - set DJ role (admin)
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Optional

import discord
import wavelink
from discord.ext import commands

from utils import storage, i18n

log = logging.getLogger("Extras")


class Extras(commands.Cog, name="Extras"):
    """⭐ Favorites, 📜 Playlists, 📈 Stats, 🌍 Language."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # Per-guild history (limited in-memory; persistent via stats)
        self.history: dict[int, deque] = {}
        self.history_max = 20

    # =====================================================================
    # Favorites
    # =====================================================================
    @commands.group(name="favorites", aliases=["fav", "f"], invoke_without_command=True)
    async def favorites_group(self, ctx: commands.Context, *, query: str = None) -> None:
        if query and query.lower() == "list":
            return await self.fav_list(ctx)
        if query:
            # Treat as: !fav play <query>
            args = query.split(maxsplit=1)
            if args[0].lower() == "play" and len(args) == 2:
                return await self.fav_play(ctx, args[1])
        await self.fav_list(ctx)

    @favorites_group.command(name="list", aliases=["all"])
    async def fav_list(self, ctx: commands.Context) -> None:
        favs = await storage.get_favorites(ctx.author.id)
        if not favs:
            await ctx.send("📭 Favorites හිස්! `!fav add` කරන්න current song add කරන්න.")
            return
        embed = discord.Embed(
            title=f"⭐ {ctx.author.display_name}'s Favorites",
            color=0xFFD700,
        )
        description = []
        for i, f in enumerate(favs[:15], start=1):
            description.append(f"**{i}.** [{f['title']}]({f['uri']})")
        embed.description = "\n".join(description)
        embed.set_footer(text=f"{len(favs)} total • !fav play <#> to play")
        await ctx.send(embed=embed)

    @favorites_group.command(name="add")
    async def fav_add(self, ctx: commands.Context) -> None:
        if not (ctx.voice_client and ctx.voice_client.current):
            return await ctx.send("❌ Favorite එකට add කරන්න song play වෙන් නෑ!")
        track = ctx.voice_client.current
        info = {
            "title": track.title,
            "uri": track.uri,
            "author": getattr(track, "author", "Unknown"),
            "duration": int(track.duration) if track.duration else 0,
            "artwork": getattr(track, "artwork", None),
        }
        await storage.add_favorite(ctx.author.id, info)
        await ctx.message.add_reaction("⭐")

    @favorites_group.command(name="remove", aliases=["rm"])
    async def fav_remove(self, ctx: commands.Context, *, query: str) -> None:
        favs = await storage.get_favorites(ctx.author.id)
        target = None
        if query.isdigit():
            idx = int(query) - 1
            if 0 <= idx < len(favs):
                target = favs[idx]["uri"]
        else:
            # treat as uri
            target = query
        if not target:
            return await ctx.send("❌ Favorite not found!")
        ok = await storage.remove_favorite(ctx.author.id, target)
        if ok:
            await ctx.message.add_reaction("💔")
        else:
            await ctx.send("❌ Couldn't find that favorite")

    @favorites_group.command(name="play", aliases=["p"])
    async def fav_play(self, ctx: commands.Context, index: int) -> None:
        favs = await storage.get_favorites(ctx.author.id)
        if not favs:
            return await ctx.send("📭 Favorites හිස්!")
        if index < 1 or index > len(favs):
            return await ctx.send(f"❌ 1-{len(favs)} range එකක් දෙන්න")
        target = favs[index - 1]
        await ctx.invoke(self.bot.get_command("play"), query=target["uri"])

    # =====================================================================
    # Playlists
    # =====================================================================
    @commands.group(name="playlist", aliases=["pl"], invoke_without_command=True)
    async def playlist_group(self, ctx: commands.Context) -> None:
        await self.pl_list(ctx)

    @playlist_group.command(name="make", aliases=["save", "create"])
    async def pl_make(self, ctx: commands.Context, name: str = None) -> None:
        if not name:
            return await ctx.send("❌ Playlist name එකක් දෙන්න!")
        # Read currently playing + queue
        tracks = []
        if ctx.voice_client and ctx.voice_client.current:
            cur = ctx.voice_client.current
            tracks.append({
                "title": cur.title,
                "uri": cur.uri,
                "author": getattr(cur, "author", "Unknown"),
                "duration": int(cur.duration) if cur.duration else 0,
            })
        # Queue from music cog
        music_cog = self.bot.get_cog("Music")
        if music_cog:
            player = music_cog.get_player(ctx.guild.id)
            for t in player.queue:
                tracks.append({
                    "title": t.title,
                    "uri": t.uri,
                    "author": getattr(t, "author", "Unknown"),
                    "duration": int(t.duration) if t.duration else 0,
                })
        if not tracks:
            return await ctx.send("❌ Playlist save කරන්න song එකක් නෑ!")
        await storage.save_playlist(ctx.author.id, name, tracks)
        await ctx.send(f"💾 Playlist save කරා: **{name}** ({len(tracks)} tracks)")

    @playlist_group.command(name="load", aliases=["play", "start"])
    async def pl_load(self, ctx: commands.Context, *, name: str) -> None:
        pl = await storage.get_playlist(ctx.author.id, name)
        if not pl:
            return await ctx.send(f"❌ Playlist '{name}' නෑ!")
        await ctx.send(f"📃 Loading **{pl['name']}** ({len(pl['tracks'])} tracks)...")
        for track in pl["tracks"]:
            await ctx.invoke(self.bot.get_command("play"), query=track["uri"])
            await asyncio.sleep(0.5)

    @playlist_group.command(name="list", aliases=["all"])
    async def pl_list(self, ctx: commands.Context) -> None:
        pls = await storage.list_playlists(ctx.author.id)
        if not pls:
            return await ctx.send("📭 Playlist එකක් නෑ!")
        embed = discord.Embed(title=f"📜 {ctx.author.display_name}'s Playlists", color=0x9B59B6)
        for pl in pls:
            embed.add_field(name=f"🎵 {pl['name']}", value=f"{len(pl['tracks'])} tracks", inline=True)
        embed.set_footer(text="!playlist load <name>")
        await ctx.send(embed=embed)

    @playlist_group.command(name="delete", aliases=["rm", "remove"])
    async def pl_delete(self, ctx: commands.Context, *, name: str) -> None:
        if await storage.delete_playlist(ctx.author.id, name):
            await ctx.send(f"🗑️ Deleted playlist: **{name}**")
        else:
            await ctx.send(f"❌ '{name}' not found")

    # =====================================================================
    # History
    # =====================================================================
    @commands.command(name="history")
    async def history(self, ctx: commands.Context) -> None:
        guild_id = ctx.guild.id
        if guild_id not in self.history or not self.history[guild_id]:
            return await ctx.send("📭 History empty!")
        items = list(self.history[guild_id])[-15:][::-1]
        embed = discord.Embed(title="📜 Recently Played", color=0xFFA500)
        for i, t in enumerate(items, start=1):
            embed.add_field(name=f"{i}.", value=f"[{t.title}]({t.uri})", inline=False)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload) -> None:
        gid = payload.player.guild.id
        if gid not in self.history:
            self.history[gid] = deque(maxlen=self.history_max)
        self.history[gid].append(payload.track)
        # Record stats
        await storage.record_play(
            gid,
            0,  # user_id unknown at this layer
            {
                "title": payload.track.title,
                "author": getattr(payload.track, "author", "Unknown"),
                "uri": payload.track.uri,
            },
        )

    # =====================================================================
    # Stats
    # =====================================================================
    @commands.command(name="top")
    async def top_songs(self, ctx: commands.Context) -> None:
        stats = await storage.get_stats(ctx.guild.id)
        songs = stats.get("songs", {})
        if not songs:
            return await ctx.send("📊 තව plays නෑ!")
        sorted_songs = sorted(songs.items(), key=lambda x: x[1]["count"], reverse=True)[:10]
        embed = discord.Embed(title="🏆 Top Songs", color=0xFFD700)
        for i, (title, info) in enumerate(sorted_songs, start=1):
            embed.add_field(
                name=f"{i}. {title}",
                value=f"`{info['count']} plays` • {info['author']}",
                inline=False,
            )
        embed.set_footer(text=f"Total plays: {stats.get('plays', 0)}")
        await ctx.send(embed=embed)

    @commands.command(name="topuser", aliases=["toplisteners"])
    async def top_users(self, ctx: commands.Context) -> None:
        stats = await storage.get_stats(ctx.guild.id)
        users = stats.get("users", {})
        if not users:
            return await ctx.send("📊 No data yet!")
        sorted_users = sorted(users.items(), key=lambda x: x[1], reverse=True)[:10]
        embed = discord.Embed(title="👥 Top Listeners", color=0xFF69B4)
        for i, (uid, count) in enumerate(sorted_users, start=1):
            member = ctx.guild.get_member(int(uid))
            name = member.display_name if member else f"User#{uid}"
            embed.add_field(name=f"{i}. {name}", value=f"{count} requests", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="dedupe")
    async def dedupe(self, ctx: commands.Context) -> None:
        """Remove duplicate songs from the queue."""
        music_cog = self.bot.get_cog("Music")
        if not music_cog:
            return await ctx.send("❌ Music cog not loaded")
        player = music_cog.get_player(ctx.guild.id)
        if not player.queue:
            return await ctx.send("📭 Queue empty!")
        seen = set()
        unique = []
        current_uri = ctx.voice_client.current.uri if ctx.voice_client and ctx.voice_client.current else None
        for t in player.queue:
            if t.uri in seen or t.uri == current_uri:
                continue
            seen.add(t.uri)
            unique.append(t)
        removed = len(player.queue) - len(unique)
        player.queue = unique
        await ctx.send(f"🧹 Removed **{removed}** duplicate(s)!")

    # =====================================================================
    # Language
    # =====================================================================
    @commands.has_permissions(manage_guild=True)
    @commands.command(name="language", aliases=["lang"])
    async def language(self, ctx: commands.Context, lang: str = None) -> None:
        """Change server language. si|sinhala, en|english."""
        if not lang:
            current = await storage.get_settings(ctx.guild.id)
            await ctx.send(f"🌍 Language: **{current['language']}** (si/en)")
            return
        lang = lang.lower()[:2]
        if lang not in i18n.languages():
            return await ctx.send(f"❌ Available: {', '.join(i18n.languages())}")
        await storage.update_settings(ctx.guild.id, language=lang)
        await ctx.send(i18n.t("language_set", lang, name=lang))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Extras(bot))