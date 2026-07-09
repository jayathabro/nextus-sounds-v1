"""Moderation Cog - DJ role checks, manage/stop permissions."""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

import discord
from discord.ext import commands

from utils import storage

log = logging.getLogger("Moderation")


# Music commands that require DJ (or Administrator) privileges
DJ_REQUIRED_COMMANDS = {
    "skip", "stop", "volume", "loop", "shuffle", "seek", "remove",
    "clearqueue", "play", "queue", "nowplaying", "filter", "speed",
    "pitch", "24/7", "dedupe", "filters",
}


class Moderation(commands.Cog, name="Moderation"):
    """🛡️ Permission system & DJ roles."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_before_invoke(self, ctx: commands.Context) -> None:
        """Pre-check DJ permissions before any DJ-required command runs."""
        cmd_name = ctx.command.qualified_name.split()[0] if ctx.command else ""
        if cmd_name.lower() not in DJ_REQUIRED_COMMANDS:
            return
        # Skip check when bot admin invokes
        if ctx.author.guild_permissions.administrator:
            return
        settings = await storage.get_settings(ctx.guild.id)
        dj_role_id = settings.get("dj_role")
        if dj_role_id is None:
            return  # no DJ required
        role = ctx.guild.get_role(dj_role_id)
        if role is None:
            return
        if role not in ctx.author.roles:
            await ctx.send(f"❌ DJ Role '{role.name}' ඕනේ මේ command එක use කරන්න!")
            raise commands.CheckFailure("DJ role required")

    @commands.has_permissions(administrator=True)
    @commands.command(name="djrole")
    async def dj_role(self, ctx: commands.Context, *, role: discord.Role = None) -> None:
        """Set or clear the DJ role (admin only). Use @role, name, or ID."""
        if role is None:
            # clear
            await storage.update_settings(ctx.guild.id, dj_role=None)
            return await ctx.send("🛡️ DJ role requirement removed.")
        await storage.update_settings(ctx.guild.id, dj_role=role.id)
        await ctx.send(f"🛡️ DJ role set: {role.mention}")

    @commands.has_permissions(administrator=True)
    @commands.command(name="djinfo")
    async def dj_info(self, ctx: commands.Context) -> None:
        settings = await storage.get_settings(ctx.guild.id)
        dj_role_id = settings.get("dj_role")
        if not dj_role_id:
            return await ctx.send("🛡️ No DJ role set (all can use music commands).")
        role = ctx.guild.get_role(dj_role_id)
        if role:
            await ctx.send(f"🛡️ DJ role: {role.mention}")
        else:
            await ctx.send(f"🛡️ DJ role: <deleted role>, ID: {dj_role_id}")

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context) -> None:
        """Log command usage for moderation/monitoring."""
        # Intentionally lightweight: skip noisy logs; production can hook into DB.
        pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))