"""
Events Cog - Bot lifecycle events, error handler, member welcome messages.
"""

from __future__ import annotations

import logging
import platform
import sys

import discord
import wavelink
from discord.ext import commands

log = logging.getLogger("Events")


class Events(commands.Cog, name="Events"):
    """📡 Bot events and error handling."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        log.info(f"✅ Logged in as {self.bot.user} (ID: {self.bot.user.id})")
        log.info(f"📡 Connected to {len(self.bot.guilds)} guilds")
        log.info(f"🐍 Python {platform.python_version()} | discord.py {discord.__version__}")
        log.info("─" * 50)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        log.info(f"➕ Joined guild: {guild.name} (ID: {guild.id}, members: {guild.member_count})")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        log.info(f"➖ Left guild: {guild.name} (ID: {guild.id})")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        """Global error handler."""
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(f"❌ Permission නෑ: {error.missing_permissions[0].replace('_', ' ').title()}")
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument: `{error.param.name}`")
            return
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Bad argument: {error}")
            return
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Cooldown! {error.retry_after:.1f}s බලාගෙන ඉන්න.")
            return
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"❌ Bot ට permission නෑ: {error.missing_permissions}")
            return
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send("❌ මේ command එක server එකේ විතරයි use කරන්න පුළුවන්!")
            return
        if isinstance(error, commands.UserInputError):
            await ctx.send(f"❌ Input error: {error}")
            return
        # Lavalink / wavelink errors
        if isinstance(error, wavelink.exceptions.LavalinkException):
            await ctx.send(f"❌ Audio engine error: {error}")
            log.exception("Wavelink error")
            return
        # Unknown error — log it
        log.exception(f"Unhandled error in {ctx.command}: {error}", exc_info=error)
        try:
            await ctx.send(f"❌ Error: ```{str(error)[:500]}```")
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Send a friendly welcome DM (optional, lightweight)."""
        if member.bot:
            return
        try:
            embed = discord.Embed(
                title=f"👋 Welcome to {member.guild.name}!",
                description=(
                    f"Hi {member.mention}, welcome!\n"
                    f"🎵 Music bot: use `!play <song>` in any voice channel.\n"
                    f"Type `!help` to see all commands."
                ),
                color=0x2F3136,
            )
            if member.guild.icon:
                embed.set_thumbnail(url=member.guild.icon.url)
            await member.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEvent) -> None:
        log.info(f"✅ Lavalink node ready: {payload.node.identifier}")

    @commands.Cog.listener()
    async def on_wavelink_node_closed(self, payload) -> None:
        log.warning(f"⚠️ Lavalink node closed: {payload}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Events(bot))