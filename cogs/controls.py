"""Controls Cog - Interactive buttons on Now Playing message.

The Now Playing message gets live controls:
    ⏮ Prev    ⏯ Pause/Resume    ⏭ Skip
    ⏹ Stop    🔀 Shuffle         🔁 Loop
    🔊 Volume slider view (uses select)
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Optional

import discord
import wavelink
from discord.ext import commands

log = logging.getLogger("Controls")


class MusicControlView(discord.ui.View):
    """Persistent view with play/pause/skip/stop/loop/shuffle buttons."""

    def __init__(self, cog: "Controls") -> None:
        # 🔧 FIX: timeout=None makes view persistent across restarts
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(emoji="⏯", style=discord.ButtonStyle.primary, custom_id="ctrl:pause")
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("❌ Not in VC", ephemeral=True)
        if vc.is_paused():
            await vc.pause(False)
            button.style = discord.ButtonStyle.primary
        elif vc.is_playing():
            await vc.pause(True)
            button.style = discord.ButtonStyle.success
        await interaction.response.defer()

    @discord.ui.button(emoji="⏭", style=discord.ButtonStyle.primary, custom_id="ctrl:skip")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            await vc.stop()
        await interaction.response.defer()

    @discord.ui.button(emoji="⏹", style=discord.ButtonStyle.danger, custom_id="ctrl:stop")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.edit_message(content="⏹️ Stopped & disconnected", embed=None, view=None)
            return
        await interaction.response.defer()

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, custom_id="ctrl:shuffle")
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        music = interaction.client.get_cog("Music")
        if music:
            player = music.get_player(interaction.guild.id)
            if not player.queue:
                return await interaction.response.send_message("📭 Queue empty!", ephemeral=True)
            random.shuffle(player.queue)
        await interaction.response.defer()

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary, custom_id="ctrl:loop")
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        music = interaction.client.get_cog("Music")
        if music:
            player = music.get_player(interaction.guild.id)
            cycle = {"off": "track", "track": "queue", "queue": "off"}
            player.loop_mode = cycle.get(player.loop_mode, "off")
            await interaction.response.send_message(f"🔁 Loop: **{player.loop_mode}**", ephemeral=True)
            return
        await interaction.response.defer()

    @discord.ui.button(emoji="📃", style=discord.ButtonStyle.secondary, custom_id="ctrl:queue")
    async def queue(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        music = interaction.client.get_cog("Music")
        if not music:
            return await interaction.response.defer()
        player = music.get_player(interaction.guild.id)
        vc = interaction.guild.voice_client
        if not (player.queue or (vc and vc.current)):
            return await interaction.response.send_message("📭 Queue empty!", ephemeral=True)
        embed = discord.Embed(title="📃 Queue", color=0x1DB954)
        if vc and vc.current:
            embed.add_field(name="Now Playing", value=f"🎶 **{vc.current.title}**", inline=False)
        for i, t in enumerate(player.queue[:10], start=1):
            embed.add_field(name=f"{i}.", value=t.title, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class Controls(commands.Cog, name="Controls"):
    """🎛️ Now Playing with interactive buttons."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Add persistent view when bot is ready."""
        # 🔧 FIX: View is now persistent (timeout=None + custom_id on all buttons)
        view = MusicControlView(self)
        # Store view in bot's persistent view registry
        self.bot.add_view(view)
        log.info("✅ Controls persistent view registered")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload) -> None:
        """Send a Now Playing embed with control buttons."""
        guild = payload.player.guild
        music = self.bot.get_cog("Music")
        if not music:
            return
        player = music.get_player(guild.id)
        channel = player.text_channel
        if channel is None:
            return
        embed = music._now_playing_embed(payload.player, payload.track)
        view = MusicControlView(self)
        try:
            await channel.send(embed=embed, view=view)
        except Exception as e:
            log.warning(f"Could not send now-playing with controls: {e}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Controls(bot))