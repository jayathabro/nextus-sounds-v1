"""Slash Commands Cog - discord.py app commands.

Provides slash equivalents for popular music commands.
"""

from __future__ import annotations

import logging
from typing import Optional

import discord
import wavelink
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("Slash")


class Slash(commands.Cog, name="Slash"):
    """💬 Slash command equivalents."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ------------------------------------------------------------------
    @app_commands.command(name="play", description="Play a song or add it to the queue")
    @app_commands.describe(query="Song name, YouTube URL, or Spotify link")
    async def slash_play(self, interaction: discord.Interaction, query: str) -> None:
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message("❌ Voice channel එකක join වෙන්න ඕනේ", ephemeral=True)
        await interaction.response.defer()
        music = self.bot.get_cog("Music")
        if not music:
            return await interaction.followup.send("❌ Music cog missing")
        # Use ctx with channel scope
        ctx = await self.bot.get_context(interaction)
        await music.play.callback(music, ctx, query=query)

    @app_commands.command(name="skip", description="Skip current song")
    async def slash_skip(self, interaction: discord.Interaction) -> None:
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            return await interaction.response.send_message("❌ Skip කරන්න song එකක් නෑ", ephemeral=True)
        await vc.stop()
        await interaction.response.send_message("⏭️ Skipped!")

    @app_commands.command(name="pause", description="Pause / resume the current song")
    async def slash_pause(self, interaction: discord.Interaction) -> None:
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("❌ Not in VC", ephemeral=True)
        if vc.is_paused():
            await vc.pause(False)
            await interaction.response.send_message("▶️ Resumed")
        elif vc.is_playing():
            await vc.pause(True)
            await interaction.response.send_message("⏸️ Paused")
        else:
            await interaction.response.send_message("❌ දැන් play වෙන song එකක් නෑ", ephemeral=True)

    @app_commands.command(name="queue", description="Show the queue")
    async def slash_queue(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        music = self.bot.get_cog("Music")
        if not music:
            return await interaction.followup.send("❌ Music cog missing")
        player = music.get_player(interaction.guild.id)
        vc = interaction.guild.voice_client
        embed = discord.Embed(title=f"📃 Queue ({len(player.queue)})", color=0x1DB954)
        if vc and vc.current:
            embed.add_field(name="Now Playing", value=f"🎶 **{vc.current.title}**", inline=False)
        if player.queue:
            description = "\n".join(f"**{i+1}.** {t.title}" for i, t in enumerate(player.queue[:10]))
            embed.add_field(name="Up Next", value=description, inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="filter", description="Apply an audio filter")
    @app_commands.describe(name="Filter name (bassboost, nightcore, 8d, etc.)")
    async def slash_filter(self, interaction: discord.Interaction, name: str) -> None:
        filters = self.bot.get_cog("Filters")
        if not filters:
            return await interaction.response.send_message("❌ Filters cog missing", ephemeral=True)
        ctx = await self.bot.get_context(interaction)
        await filters.filter_cmd.callback(filters, ctx, name=name)

    @app_commands.command(name="volume", description="Set playback volume (0-150)")
    @app_commands.describe(percent="Volume percent (0-150)")
    async def slash_volume(self, interaction: discord.Interaction, percent: int) -> None:
        if not (0 <= percent <= 150):
            return await interaction.response.send_message("❌ 0-150 range එකක් දෙන්න", ephemeral=True)
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("❌ Not in VC", ephemeral=True)
        await vc.set_volume(percent)
        await interaction.response.send_message(f"🔊 Volume: **{percent}%**")

    @app_commands.command(name="join", description="Bot join your voice channel")
    async def slash_join(self, interaction: discord.Interaction) -> None:
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message("❌ Voice channel එකක join වෙන්න ඕනේ", ephemeral=True)
        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client
        if vc:
            await vc.move_to(channel)
        else:
            await channel.connect(cls=wavelink.Player, self_deaf=True)
        await interaction.response.send_message(f"✅ Joined {channel.mention}")


async def setup(bot: commands.Bot) -> None:
    cog = Slash(bot)
    await bot.add_cog(cog)
    try:
        synced = await bot.tree.sync()
        log.info(f"Synced {len(synced)} slash commands")
    except Exception as e:
        log.warning(f"Slash sync failed: {e}")