"""Owner Cog - Owner-only commands (shutdown, reload, blacklist, etc.)

Only the bot owner (ID in env/config) can use these.
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import subprocess

import discord
from discord.ext import commands

log = logging.getLogger("Owner")


def is_owner() -> bool:
    """Check if the caller is the bot owner."""
    async def predicate(ctx: commands.Context) -> bool:
        owner_id = os.getenv("OWNER_ID")
        try:
            return ctx.author.id == int(owner_id) if owner_id else False
        except (ValueError, TypeError):
            return False
    return commands.check(predicate)


class Owner(commands.Cog, name="Owner"):
    """🔒 Owner-only commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="shutdown", aliases=["stopbot", "off"])
    @is_owner()
    async def shutdown(self, ctx: commands.Context) -> None:
        """Shutdown the bot completely."""
        await ctx.send("👋 Shutting down bot...")
        log.warning(f"Bot shutdown by owner {ctx.author}")
        await self.bot.close()

    @commands.command(name="restart")
    @is_owner()
    async def restart(self, ctx: commands.Context) -> None:
        """Restart the bot by exiting the process."""
        await ctx.send("🔁 Restarting...")
        log.warning(f"Bot restart requested by {ctx.author}")
        # Best-effort: exit and let process manager (pm2/systemd) restart
        await self.bot.close()
        # If not managed, exit Python so external wrapper can restart
        os._exit(0)

    @commands.command(name="reload")
    @is_owner()
    async def reload(self, ctx: commands.Context, *, cog: str) -> None:
        """Reload a cog: !reload music  or  !reload cogs.music"""
        cog = cog.strip()
        if not cog.startswith("cogs."):
            cog = f"cogs.{cog}"
        try:
            await self.bot.reload_extension(cog)
            await ctx.send(f"🔄 Reloaded: {cog}")
        except Exception as e:
            await ctx.send(f"❌ Reload failed: `{e}`")

    @commands.command(name="load")
    @is_owner()
    async def load(self, ctx: commands.Context, *, cog: str) -> None:
        """Load a cog."""
        cog = cog.strip()
        if not cog.startswith("cogs."):
            cog = f"cogs.{cog}"
        try:
            await self.bot.load_extension(cog)
            await ctx.send(f"✅ Loaded: {cog}")
        except Exception as e:
            await ctx.send(f"❌ Load failed: `{e}`")

    @commands.command(name="unload")
    @is_owner()
    async def unload(self, ctx: commands.Context, *, cog: str) -> None:
        """Unload a cog."""
        cog = cog.strip()
        if not cog.startswith("cogs."):
            cog = f"cogs.{cog}"
        try:
            await self.bot.unload_extension(cog)
            await ctx.send(f"✅ Unloaded: {cog}")
        except Exception as e:
            await ctx.send(f"❌ Unload failed: `{e}`")

    @commands.command(name="cogs")
    @is_owner()
    async def list_cogs(self, ctx: commands.Context) -> None:
        """List all loaded cogs."""
        cogs = sorted(self.bot.cogs.keys())
        embed = discord.Embed(title="📦 Loaded Cogs", color=0x1DB954)
        for name in cogs:
            embed.add_field(name=name, value="✅", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="guilds", aliases=["servers"])
    @is_owner()
    async def guilds(self, ctx: commands.Context) -> None:
        """List all guilds the bot is in."""
        embed = discord.Embed(title=f"🌐 Guilds ({len(self.bot.guilds)})", color=0x1DB954)
        for g in self.bot.guilds[:25]:
            embed.add_field(name=g.name, value=f"ID: {g.id} | {len(g.members)} members", inline=False)
        if len(self.bot.guilds) > 25:
            embed.set_footer(text=f"...and {len(self.bot.guilds) - 25} more")
        await ctx.send(embed=embed)

    @commands.command(name="broadcast", aliases=["announce"])
    @is_owner()
    async def broadcast(self, ctx: commands.Context, *, message: str) -> None:
        """DM all bot users (in shared servers) with a message."""
        await ctx.send(f"📤 Broadcasting to users...")
        users = set()
        for g in self.bot.guilds:
            for m in g.members:
                if not m.bot and m != self.bot.user:
                    users.add(m)
        sent, failed = 0, 0
        embed = discord.Embed(title="📢 Bot Announcement", color=0x1DB954, description=message)
        embed.set_footer(text="From Nextus Sounds Bot Team")
        for user in users:
            try:
                await user.send(embed=embed)
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.5)  # rate limit protection
        await ctx.send(f"✅ Sent: **{sent}** | ❌ Failed: **{failed}**")

    @commands.command(name="blacklist", aliases=["ban"])
    @is_owner()
    async def blacklist(self, ctx: commands.Context, target: str, *, reason: str = "No reason") -> None:
        """Blacklist a user by ID or @mention."""
        if target.startswith("<@") and target.endswith(">"):
            target = target.strip("<@!>")
        try:
            uid = int(target)
        except ValueError:
            return await ctx.send("❌ Invalid user ID/mention")
        from utils.storage import update_settings
        # Per-user blacklist stored in a separate file
        import json
        from pathlib import Path
        BL = Path("data") / "blacklist.json"
        BL.parent.mkdir(exist_ok=True)
        data = {}
        if BL.exists():
            try:
                data = json.loads(BL.read_text())
            except Exception:
                data = {}
        data[str(uid)] = {"reason": reason, "by": ctx.author.id, "time": str(ctx.message.created_at)}
        BL.write_text(json.dumps(data, indent=2))
        await ctx.send(f"🚫 Blacklisted user `{uid}`: {reason}")

    @commands.command(name="sync")
    @is_owner()
    async def sync_tree(self, ctx: commands.Context) -> None:
        """Sync slash commands globally."""
        try:
            synced = await self.bot.tree.sync()
            await ctx.send(f"✅ Synced {len(synced)} slash commands")
        except Exception as e:
            await ctx.send(f"❌ Sync failed: `{e}`")

    @commands.command(name="update")
    @is_owner()
    async def update(self, ctx: commands.Context) -> None:
        """Pull latest code via git & reload (requires git)."""
        try:
            result = subprocess.run(
                ["git", "pull"], capture_output=True, text=True, timeout=30
            )
            output = result.stdout + result.stderr
            if result.returncode == 0:
                await ctx.send(f"✅ Updated!\n```\n{output[:1500]}\n```")
            else:
                await ctx.send(f"❌ Update failed:\n```\n{output[:1500]}\n```")
        except FileNotFoundError:
            await ctx.send("❌ git not installed")
        except Exception as e:
            await ctx.send(f"❌ Error: `{e}`")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error) -> None:
        """Silently handle owner check failures for owner-only commands."""
        if isinstance(error, commands.CheckFailure):
            owner_id = os.getenv("OWNER_ID", "")
            if ctx.author.id != int(owner_id) if owner_id else True:
                if ctx.command and hasattr(ctx.command, "callback") and ctx.command.callback.__name__ in [
                    "shutdown", "restart", "reload", "load", "unload",
                    "list_cogs", "guilds", "broadcast", "blacklist", "sync_tree", "update"
                ]:
                    await ctx.send("🔒 Owner-only command. ❌", delete_after=5)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Owner(bot))