"""
Music Player Cog - Core playback logic for Nextus Sounds.

Commands:
    !play <query>      - Play or queue a song
    !pause             - Pause current track
    !resume            - Resume playback
    !skip              - Skip current track
    !stop              - Stop and clear queue
    !queue / !q        - Show queue
    !nowplaying / !np  - Show current track
    !volume <0-150>    - Set volume
    !loop <off|track|queue>
    !shuffle           - Shuffle queue
    !seek <seconds>    - Jump position
    !remove <pos>      - Remove item from queue
    !clearqueue        - Clear queue
"""

from __future__ import annotations

import asyncio
import datetime as dt
import re
import random
from typing import Optional

import discord
import wavelink
from discord.ext import commands
from wavelink import QueueEmpty

from utils import storage, i18n

URL_REGEX = r"(?i)\b((?:https?://|www[.])[^\s()<>]+(?:\([\w\d]+\)|/[^\s()<>]*))"
SPOTIFY_REGEX = r"https?://open\.spotify\.com/(track|album|playlist)/[a-zA-Z0-9]+"
YT_PLAYLIST_REGEX = r"^https?://(www\.)?youtube\.com/playlist\?list="
YT_VIDEO_REGEX = r"(?:youtube\.com/watch\?v=|youtu\.be/)[^\s&]+"

# --------------------------------------------------------------------------------------
# Player per guild
# --------------------------------------------------------------------------------------


class GuildPlayer:
    """In-memory state for one guild. Resets on bot restart."""

    def __init__(self, bot: commands.Bot, guild_id: int) -> None:
        self.bot = bot
        self.guild_id = guild_id
        self.queue: list[wavelink.Playable] = []
        self.loop_mode: str = "off"  # off | track | queue
        self.volume: int = 75
        self.shuffle: bool = False
        self.history: list[wavelink.Playable] = []
        self.last_track: Optional[wavelink.Playable] = None
        self.text_channel: Optional[discord.TextChannel] = None
        self.dj_votes: set[int] = set()

    def __repr__(self) -> str:
        return f"<GuildPlayer guild={self.guild_id} queue={len(self.queue)}>"


class Music(commands.Cog, name="Music"):
    """🎵 Music playback commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.players: dict[int, GuildPlayer] = {}
        log = __import__("logging").getLogger("Music")
        self.log = log

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def get_player(self, guild_id: int) -> GuildPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = GuildPlayer(self.bot, guild_id)
        return self.players[guild_id]

    @staticmethod
    def make_progress_bar(current: int, total: int, length: int = 20) -> str:
        if total == 0:
            return "▬" * length
        filled = int((current / total) * length)
        bar = "▬" * filled + "🔘" + "─" * (length - filled - 1)
        return bar

    @staticmethod
    def format_time(seconds: int) -> str:
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"

    async def _search(self, query: str) -> list[wavelink.Playable]:
        """
        Search for tracks using wavelink v3 API.

        Tries multiple known v3 search patterns in order:
        1. YouTubeTrack.search() / SpotifyTrack.search() by platform
        2. SearchableTrack.search() (v3.1+ unified search)
        3. node.get_tracks() fallback
        """
        import re as _re
        # Determine source from query prefix
        source = None
        clean_query = query
        if query.startswith("ytsearch:") or query.startswith("ytmsearch:"):
            source = "youtube"
            clean_query = _re.sub(r"^(ytm?search:)\s*", "", query)
        elif query.startswith("scsearch:"):
            source = "soundcloud"
        elif query.startswith("spsearch:"):
            source = "spotify"

        # Try v3 track class search methods
        try:
            if source == "youtube" or not source:
                from wavelink import YouTubeTrack
                return await YouTubeTrack.search(clean_query if not source else query)
        except (ImportError, AttributeError):
            pass

        try:
            if source == "spotify":
                from wavelink import SpotifyTrack
                return await SpotifyTrack.search(query)
        except (ImportError, AttributeError):
            pass

        try:
            # v3.1+ unified SearchableTrack.search() — returns SearchResult with .tracks
            from wavelink import SearchableTrack
            result = await SearchableTrack.search(query)
            if hasattr(result, "tracks"):
                return list(result.tracks)
            return list(result)
        except (ImportError, AttributeError):
            pass

        # Final fallback: try node.get_tracks (v3 standard)
        try:
            pool = wavelink.Pool
            nodes = list(pool.nodes)
            if nodes:
                return await nodes[0].get_tracks(query)
        except Exception:
            pass

        # If all above fail, return empty list
        return []

    async def ensure_voice(self, ctx: commands.Context) -> Optional[wavelink.Player]:
        # 🔧 Check if Lavalink pool has connected nodes
        try:
            pool = wavelink.Pool
            nodes = list(pool.nodes) if hasattr(pool, 'nodes') else []
            if not nodes:
                await ctx.send("❌ Voice එකට connect වෙන්න බෑ: No nodes are currently assigned to the wavelink.Pool in a CONNECTED state.\n💡 Check bot logs - Lavalink may be unreachable!")
                return None
        except Exception:
            pass  # If check fails, proceed and let the actual error happen

        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ Voice channel එකක join වෙන්න ඕනේ!")
            return None
        if ctx.voice_client:
            return ctx.voice_client
        try:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player, self_deaf=True)
            return player
        except Exception as e:
            await ctx.send(f"❌ Voice එකට connect වෙන්න බෑ: {e}")
            return None

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload) -> None:
        """Handle track start event."""
        try:
            player = self.players.get(payload.player.guild.id)
            if player and player.text_channel:
                embed = self._now_playing_embed(payload.player, payload.track)
                await player.text_channel.send(embed=embed)
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload) -> None:
        """Handle track end event."""
        player = self.players.get(payload.player.guild.id)
        if not player:
            return
        # If was stopped (skip, manual), don't auto-play next
        if payload.reason == wavelink.TrackEndReason.STOPPED:
            return
        next_track: Optional[wavelink.Playable] = None
        if player.loop_mode == "track":
            next_track = payload.track
        elif player.queue:
            if player.shuffle and player.loop_mode != "queue":
                next_track = random.choice(player.queue)
                player.queue.remove(next_track)
                player.queue.append(next_track)
            else:
                next_track = player.queue.pop(0)
            if player.loop_mode == "queue":
                player.queue.append(next_track)
        if next_track:
            await payload.player.play(next_track)
            player.last_track = next_track
        else:
            await self._auto_disconnect_check(payload.player, player)

    async def _auto_disconnect_check(self, voice: wavelink.Player, player: GuildPlayer) -> None:
        """Schedule an auto-disconnect if nobody is listening anymore."""
        settings = await storage.get_settings(player.guild_id)
        if not settings.get("auto_leave", True):
            return
        # 24/7 mode — never disconnect
        utilities = self.bot.get_cog("Utilities")
        if utilities and utilities.twenty_four_seven.get(player.guild_id):
            return
        timeout = settings.get("auto_leave_timeout", 180)
        # Wait, then check if VC is empty
        await asyncio.sleep(min(timeout, 5))  # short first check
        if voice.is_connected():
            channel = voice.channel
            if channel:
                listeners = [m for m in channel.members if not m.bot]
                if not listeners:
                    await voice.disconnect()
                    if player.text_channel:
                        try:
                            await player.text_channel.send("👋 Auto-disconnected (VC empty).")
                        except Exception:
                            pass
                    return
        # If still has listeners or connected, schedule final check after full timeout
        if timeout > 5:
            await asyncio.sleep(timeout - 5)
            if voice.is_connected():
                channel = voice.channel
                if channel:
                    listeners = [m for m in channel.members if not m.bot]
                    if not listeners and not (voice.current or player.queue):
                        await voice.disconnect()
                        if player.text_channel:
                            try:
                                await player.text_channel.send("👋 Auto-disconnected.")
                            except Exception:
                                pass

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    @commands.command(name="play", aliases=["p", "නාද", "ප්ලේ"])
    @commands.cooldown(1, 2, commands.BucketType.guild)
    async def play(self, ctx: commands.Context, *, query: str = None) -> None:
        """Play a song by URL or search query."""
        if not query:
            await ctx.send("❌ Song එකක නමක් දෙන්න! (e.g., `!play faded` or `!play <url>`)")
            return

        voice = await self.ensure_voice(ctx)
        if not voice:
            return

        player = self.get_player(ctx.guild.id)
        player.text_channel = ctx.channel

        if not voice.is_playing():
            # wavelink v3: is_paused is a property, not directly settable
            # The proper way to resume is voice.resume(); check first
            try:
                if getattr(voice, "is_paused", False):
                    await voice.resume()
            except Exception:
                pass

        # Confirm loading
        embed_loading = discord.Embed(
            description=f"🔎 Searching: **{query}**",
            color=0x1DB954,
        )
        msg = await ctx.send(embed=embed_loading)

        try:
            # wavelink v3: search moved to YouTubeTrack / Track classes, NOT Playable
            # Try multiple known v3 search entry points
            if re.match(URL_REGEX, query):
                result = await self._search(query)
            else:
                # Default: YouTube search with 'ytsearch:'
                result = await self._search(f"ytsearch:{query}")
            # Normalize result to list
            if hasattr(result, "tracks"):
                tracks: list[wavelink.Playable] = list(result.tracks)
            elif isinstance(result, wavelink.Playlist):
                tracks = list(result.tracks) if hasattr(result, "tracks") else list(result)
            else:
                tracks = list(result)
        except Exception as e:
            await msg.edit(content=f"❌ Search failed: {e}")
            return

        if not tracks:
            await msg.edit(content=f"❌ ඒක හොයාගන්න බෑ: **{query}**")
            return

        if not voice.is_playing() and len(voice.queue) > 0 and not (await self._has_current_track(voice)):
            voice.queue.clear()  # wavelink v3: voice.queue is a list-like object, .clear() works via del

        if voice.is_playing() or voice.is_paused():
            for tr in (tracks if isinstance(tracks, list) else [tracks]):
                player.queue.append(tr)
            if not isinstance(tracks, list):
                tracks = [tracks]
            embed = discord.Embed(
                title="➕ Added to Queue",
                description=(
                    f"**{tracks[0].title}**" if len(tracks) == 1 else f"📃 {len(tracks)} songs added!"
                ),
                color=0x1DB954,
            )
            if hasattr(tracks[0], "artwork") and tracks[0].artwork:
                embed.set_thumbnail(url=tracks[0].artwork)
            embed.add_field(name="Pos", value=f"#{len(player.queue)}")
            embed.set_footer(text=f"Requested by {ctx.author.display_name} 🎵")
            await msg.edit(embed=embed)
        else:
            # If playlist → add rest to queue
            if isinstance(tracks, list) and len(tracks) > 1:
                first = tracks[0]
                player.queue.extend(tracks[1:])
                track = first
                embed_added = f"📃 Added **{len(tracks) - 1}** songs to queue"
            else:
                track = tracks[0] if isinstance(tracks, list) else tracks
                embed_added = None

            await voice.play(track)
            player.last_track = track
            if embed_added:
                await msg.edit(content=embed_added)

    async def _has_current_track(self, voice: wavelink.Player) -> bool:
        return voice.current is not None

    @commands.command(name="pause")
    async def pause(self, ctx: commands.Context) -> None:
        if ctx.voice_client and ctx.voice_client.is_playing():
            await ctx.voice_client.pause(True)
            await ctx.message.add_reaction("⏸")
        else:
            await ctx.send("❌ Play වෙන song එකක් නෑ!")

    @commands.command(name="resume", aliases=["unpause"])
    async def resume(self, ctx: commands.Context) -> None:
        if ctx.voice_client and ctx.voice_client.is_paused():
            await ctx.voice_client.pause(False)
            await ctx.message.add_reaction("▶️")
        else:
            await ctx.send("❌ Pause වෙලා නෑ!")

    @commands.command(name="skip", aliases=["s", "next"])
    async def skip(self, ctx: commands.Context) -> None:
        if ctx.voice_client and ctx.voice_client.is_playing():
            await ctx.voice_client.stop()
            await ctx.message.add_reaction("⏭")
        else:
            await ctx.send("❌ Skip කරන්න song එකක් නෑ!")

    @commands.command(name="stop", aliases=["leave", "disconnect", "dc"])
    async def stop(self, ctx: commands.Context) -> None:
        if ctx.voice_client:
            player = self.get_player(ctx.guild.id)
            player.queue.clear()
            player.loop_mode = "off"
            await ctx.voice_client.disconnect()
            await ctx.message.add_reaction("⏹")
        else:
            await ctx.send("❌ Voice channel එකේ නෑ!")

    @commands.command(name="queue", aliases=["q", "පෝලිම"])
    async def queue_cmd(self, ctx: commands.Context, page: int = 1) -> None:
        """Show the current queue."""
        player = self.get_player(ctx.guild.id)
        if not player.queue and not (ctx.voice_client and ctx.voice_client.current):
            await ctx.send("📭 Queue හිස්!")
            return
        per_page = 10
        start = (page - 1) * per_page
        end = start + per_page
        items = player.queue[start:end]
        embed = discord.Embed(title=f"📃 Queue ({len(player.queue)})", color=0x1DB954)
        if ctx.voice_client and ctx.voice_client.current:
            embed.add_field(
                name="Now Playing",
                value=f"🎶 **{ctx.voice_client.current.title}** — {self.format_time(int(ctx.voice_client.current.duration))}",
                inline=False,
            )
        if items:
            description = "\n".join(
                f"**{start + i + 1}.** {t.title} `{self.format_time(int(t.duration))}`"
                for i, t in enumerate(items)
            )
            embed.add_field(name="Up Next", value=description, inline=False)
        pages = max((len(player.queue) + per_page - 1) // per_page, 1)
        embed.set_footer(text=f"Page {page}/{pages} | Loop: {player.loop_mode}")
        await ctx.send(embed=embed)

    @commands.command(name="nowplaying", aliases=["np", "current", "now"])
    async def nowplaying(self, ctx: commands.Context) -> None:
        if not (ctx.voice_client and ctx.voice_client.current):
            await ctx.send("❌ දැන් play වෙන song එකක් නෑ!")
            return
        embed = self._now_playing_embed(ctx.voice_client, ctx.voice_client.current)
        await ctx.send(embed=embed)

    def _now_playing_embed(self, voice: wavelink.Player, track: wavelink.Playable) -> discord.Embed:
        pos_ms = voice.position if voice.position else 0
        duration = int(track.duration) if track.duration else 0
        bar = self.make_progress_bar(pos_ms // 1000, duration)
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**[{track.title}]({track.uri})**",
            color=0x1DB954,
        )
        if hasattr(track, "artwork") and track.artwork:
            embed.set_thumbnail(url=track.artwork)
        embed.add_field(
            name="Progress",
            value=f"{bar}\n`{self.format_time(pos_ms // 1000)} / {self.format_time(duration)}`",
            inline=False,
        )
        embed.add_field(name="Author", value=getattr(track, "author", "Unknown"), inline=True)
        embed.add_field(name="Volume", value=f"{self.get_player(voice.guild.id).volume}%", inline=True)
        if getattr(track, "source", ""):
            embed.add_field(name="Source", value=track.source.title(), inline=True)
        embed.set_footer(text="🎵 Nextus Sounds v1.0")
        return embed

    @commands.command(name="volume", aliases=["vol", "v"])
    async def volume(self, ctx: commands.Context, vol: int = None) -> None:
        if vol is None:
            await ctx.send(f"🔊 Volume: **{self.get_player(ctx.guild.id).volume}%**")
            return
        if not (0 <= vol <= 150):
            await ctx.send("❌ 0-150 අතර number එකක් දෙන්න!")
            return
        self.get_player(ctx.guild.id).volume = vol
        if ctx.voice_client:
            await ctx.voice_client.set_volume(vol)
        await ctx.message.add_reaction("🔊")

    @commands.command(name="loop", aliases=["repeat"])
    async def loop_cmd(self, ctx: commands.Context, mode: str = None) -> None:
        if mode is None or mode.lower() not in ("off", "track", "queue", "song"):
            await ctx.send("❌ Mode එකක් දෙන්න: `off`, `track`, `queue`")
            return
        player = self.get_player(ctx.guild.id)
        if mode.lower() == "song":
            mode = "track"
        player.loop_mode = mode.lower()
        emojis = {"off": "➡️ Off", "track": "🔂 Track", "queue": "🔁 Queue"}
        await ctx.send(f"🔁 Loop: **{emojis[mode.lower()]}**")

    @commands.command(name="shuffle")
    async def shuffle(self, ctx: commands.Context) -> None:
        import random
        player = self.get_player(ctx.guild.id)
        if not player.queue:
            await ctx.send("❌ Queue හිස්!")
            return
        random.shuffle(player.queue)
        await ctx.message.add_reaction("🔀")

    @commands.command(name="seek")
    async def seek(self, ctx: commands.Context, seconds: int) -> None:
        if not (ctx.voice_client and ctx.voice_client.current):
            await ctx.send("❌ දැන් song play වෙන් නෑ!")
            return
        if seconds < 0 or (ctx.voice_client.current.duration and seconds > ctx.voice_client.current.duration // 1000):
            await ctx.send("❌ වලංගු timestamp එකක් නෑ!")
            return
        await ctx.voice_client.seek(seconds * 1000)
        await ctx.message.add_reaction("⏩")

    @commands.command(name="remove", aliases=["rm"])
    async def remove(self, ctx: commands.Context, position: int) -> None:
        player = self.get_player(ctx.guild.id)
        if not player.queue:
            await ctx.send("❌ Queue හිස්!")
            return
        if position < 1 or position > len(player.queue):
            await ctx.send(f"❌ 1-{len(player.queue)} අතර position එකක් දෙන්න!")
            return
        removed = player.queue.pop(position - 1)
        await ctx.send(f"🗑️ Removed: **{removed.title}**")

    @commands.command(name="clearqueue", aliases=["cq", "clear"])
    async def clear_queue(self, ctx: commands.Context) -> None:
        player = self.get_player(ctx.guild.id)
        player.queue.clear()
        await ctx.message.add_reaction("🧹")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music(bot))
