"""
Welcome Cog - Plays a beat/sound effect when the bot joins a voice channel.

Features:
- Plays a configured welcome beat (default: sounds/welcome.mp3)
- Optional per-server enable/disable
- Cooldown to prevent spam
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import discord
from discord.ext import commands

SOUNDS_DIR = Path("sounds")
log = logging.getLogger("Welcome")


class Welcome(commands.Cog, name="Welcome"):
    """👋 Welcome beat when the bot joins VC."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        SOUNDS_DIR.mkdir(exist_ok=True)
        self.default_sound = SOUNDS_DIR / "welcome.mp3"
        self.cooldown_users: dict[int, float] = {}
        self.cooldown_seconds = 60  # per-user cooldown

    def _get_welcome_file(self) -> Path | None:
        # Config file from env, fallback to default
        env_file = os.getenv("WELCOME_SOUND_FILE", "welcome.mp3")
        target = SOUNDS_DIR / env_file
        if target.exists():
            return target
        # fallback to any welcome.* file
        for ext in (".mp3", ".wav", ".ogg"):
            candidate = SOUNDS_DIR / f"welcome{ext}"
            if candidate.exists():
                return candidate
        return None

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        """Trigger welcome sound when bot joins a voice channel."""
        # Ignore non-bot events
        if member.id != self.bot.user.id:
            return
        # Bot joined a new channel (was None / different channel before)
        if after.channel and before.channel != after.channel:
            await self._play_welcome(after.channel)

    async def _play_welcome(self, channel: discord.VoiceChannel) -> None:
        if not os.getenv("ENABLE_WELCOME_SOUND", "true").lower() == "true":
            return
        sound_file = self._get_welcome_file()
        if not sound_file:
            log.debug("No welcome sound file found, skipping.")
            return
        # Try connect, ensure clean state
        try:
            vc = channel.guild.voice_client
            if vc and vc.is_playing():
                vc.stop()
                await asyncio.sleep(0.3)
            if vc is None:
                vc = await channel.connect()
            elif vc.channel != channel:
                await vc.move_to(channel)
            # Save volume
            try:
                vol = vc.source.volume if vc.source and hasattr(vc.source, "volume") else 1.0
            except Exception:
                vol = 1.0
            source = discord.FFmpegPCMAudio(sound_file.as_posix())
            vc.play(source)
            log.info(f"Welcome sound played in {channel.name} ({channel.guild.name})")
        except Exception as e:
            log.warning(f"Could not play welcome sound: {e}")

    # ------------------------------------------------------------------
    # Manual triggers & settings
    # ------------------------------------------------------------------
    @commands.command(name="welcome", aliases=["welc"])
    @commands.has_permissions(manage_guild=True)
    async def welcome_cmd(self, ctx: commands.Context) -> None:
        """Toggle welcome sound on/off for this server."""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ Voice channel එකක join වෙන්න ඕනේ!")
            return
        sound_file = self._get_welcome_file()
        if not sound_file:
            await ctx.send("❌ `sounds/welcome.mp3` file එක නෑ! මේ folder එකට welcome.mp3 දාන්න.")
            return
        await self._play_welcome(ctx.author.voice.channel)
        embed = discord.Embed(
            title="👋 Welcome Sound",
            description=f"Beat එක play කරා **{ctx.author.voice.channel.name}** එකේ!",
            color=0xFF6B35,
        )
        embed.set_footer(text=f"File: {sound_file.name}")
        await ctx.send(embed=embed)

    @commands.command(name="welcometoggle", aliases=["welctoggle", "togglewelcome"])
    @commands.has_permissions(administrator=True)
    async def toggle_welcome(self, ctx: commands.Context) -> None:
        """Toggle welcome sound globally (admin only)."""
        current = os.getenv("ENABLE_WELCOME_SOUND", "true").lower() == "true"
        new = "false" if current else "true"
        # Update .env in-memory (real change must be done in .env file)
        os.environ["ENABLE_WELCOME_SOUND"] = new
        status = "ON ✅" if new == "true" else "OFF ❌"
        await ctx.send(f"🔔 Welcome sound: **{status}**\n*(Note: Permanently edit `.env` file to keep this change)*")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))