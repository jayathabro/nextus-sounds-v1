"""
Filters Cog - Audio filters and effects using Lavalink.

Available filters:
- bassboost    - Heavy bass boost
- nightcore    - Faster + pitched up
- vaporwave    - Slowed + pitched down
- 8d           - Rotating audio (headphones recommended)
- karaoke      - Removes vocals (basic)
- pop / soft   - EQ presets
- tremolo      - Volume oscillation
- vibrato      - Pitch oscillation

Usage:
    !filter bassboost
    !filter off
    !filters         - list all available
"""

from __future__ import annotations

import logging
from typing import Optional

import discord
import wavelink
from discord.ext import commands

log = logging.getLogger("Filters")


# Preset definitions using Lavalink Equalizer (15 bands, -0.25 to 1.0)
PRESETS = {
    "none": [0.0] * 15,
    "bassboost": [0.20, 0.20, 0.20, 0.18, 0.15, 0.10, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "soft": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.05, 0.08, 0.10, 0.08, 0.05, 0.0],
    "pop": [0.0, 0.05, 0.10, 0.08, 0.0, -0.05, -0.05, 0.0, 0.0, 0.05, 0.10, 0.12, 0.10, 0.05, 0.0],
    "treblebass": [0.15, 0.15, 0.10, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.05, 0.10, 0.15, 0.15],
    "electronic": [0.15, 0.12, 0.05, 0.0, -0.05, -0.05, 0.0, 0.05, 0.08, 0.10, 0.10, 0.08, 0.05, 0.0, 0.0],
    "rock": [0.10, 0.10, 0.08, 0.05, 0.0, -0.05, -0.10, -0.05, 0.05, 0.10, 0.12, 0.12, 0.10, 0.08, 0.05],
}

# Lavalink FilterPayload presets (wavelink v3 uses Filters plural)
SPECIAL_FILTERS = {
    "nightcore": wavelink.Filters(timescale=wavelink.Timescale(speed=1.20, pitch=1.20, rate=1.0)),
    "vaporwave": wavelink.Filters(timescale=wavelink.Timescale(speed=0.85, pitch=0.85, rate=1.0)),
    "8d": wavelink.Filters(rotation=wavelink.Rotation(rotation_hz=0.30)),
    "karaoke": wavelink.Filters(
        karaoke=wavelink.Karaoke(level=1.0, mono_level=1.0, filter_band=220.0, filter_width=110.0)
    ),
    "tremolo": wavelink.Filters(tremolo=wavelink.Tremolo(frequency=4.0, depth=0.5)),
    "vibrato": wavelink.Filters(vibrato=wavelink.Vibrato(frequency=4.0, depth=0.5, frequency_in_hz=False)),
}


class Filters(commands.Cog, name="Filters"):
    """🎚️ Audio filters and effects."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.current_filter: dict[int, str] = {}  # guild_id -> filter name

    # ------------------------------------------------------------------
    @commands.command(name="filter", aliases=["fx", "effect"])
    async def filter_cmd(self, ctx: commands.Context, *, name: str = None) -> None:
        """Apply an audio filter."""
        if not ctx.voice_client or not ctx.voice_client.current:
            await ctx.send("❌ Filter දාන්න play වෙන song එකක් ඕනේ!")
            return
        if name is None:
            return await self.list_filters(ctx)
        name = name.lower()
        player: wavelink.Player = ctx.voice_client

        try:
            if name == "off" or name == "none" or name == "reset":
                await player.set_filter(wavelink.Filters())
                self.current_filter[ctx.guild.id] = "none"
                await ctx.message.add_reaction("🔄")
                return

            # Special filters (timescale, rotation, etc.)
            if name in SPECIAL_FILTERS:
                await player.set_filter(SPECIAL_FILTERS[name])
                self.current_filter[ctx.guild.id] = name
            elif name in PRESETS:
                eq = wavelink.Equalizer(bands=[(i, g) for i, g in enumerate(PRESETS[name])])
                await player.set_filter(wavelink.Filters(equalizer=eq))
                self.current_filter[ctx.guild.id] = name
            else:
                await ctx.send(f"❌ Unknown filter. `!filters` බලන්න.")
                return
            embed = discord.Embed(
                title="🎚️ Filter Applied",
                description=f"**{name.title()}** 🎧",
                color=0x9B59B6,
            )
            if name in ("nightcore", "8d", "vaporwave"):
                embed.set_footer(text="⚠️ Headphones recommended")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Filter apply කරන්න බෑ: {e}")

    @commands.command(name="filters", aliases=["fxs"])
    async def list_filters(self, ctx: commands.Context) -> None:
        """List all available filters."""
        embed = discord.Embed(
            title="🎚️ Available Filters",
            description="`!filter <name>` use කරන්න",
            color=0x9B59B6,
        )
        embed.add_field(
            name="🎛️ EQ Presets",
            value="```\n" + ", ".join(PRESETS.keys()) + "```",
            inline=False,
        )
        embed.add_field(
            name="🌈 Special Effects",
            value="```\n" + ", ".join(SPECIAL_FILTERS.keys()) + "```",
            inline=False,
        )
        embed.set_footer(text="!filter off to reset | !filter <name> to apply")
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------
    @commands.command(name="speed")
    async def speed(self, ctx: commands.Context, value: float = 1.0) -> None:
        """Change playback speed (0.5 = half, 2.0 = double)."""
        if not ctx.voice_client or not ctx.voice_client.current:
            await ctx.send("❌ Song play වෙන් නෑ!")
            return
        if not (0.25 <= value <= 3.0):
            await ctx.send("❌ Speed range: 0.25 - 3.0")
            return
        player: wavelink.Player = ctx.voice_client
        await player.set_filter(wavelink.Filters(timescale=wavelink.Timescale(speed=value, pitch=1.0, rate=1.0)))
        await ctx.send(f"⚡ Speed: **{value}x**")

    @commands.command(name="pitch")
    async def pitch(self, ctx: commands.Context, value: float = 1.0) -> None:
        """Change pitch (0.5 = lower, 2.0 = higher)."""
        if not ctx.voice_client or not ctx.voice_client.current:
            await ctx.send("❌ Song play වෙන් නෑ!")
            return
        if not (0.25 <= value <= 3.0):
            await ctx.send("❌ Pitch range: 0.25 - 3.0")
            return
        player: wavelink.Player = ctx.voice_client
        await player.set_filter(wavelink.Filters(timescale=wavelink.Timescale(speed=1.0, pitch=value, rate=1.0)))
        await ctx.send(f"🎤 Pitch: **{value}x**")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Filters(bot))