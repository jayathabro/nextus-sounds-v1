"""
Nextus Sounds v1.0
🎵 High-Quality Discord Music Bot
📺 YouTube | 🎧 Spotify | 🎤 SoundCloud | 📁 Direct Files

Features:
- High quality audio playback (up to 384kbps)
- Multi-platform source support
- Advanced queue system with looping/shuffling
- Audio filters (bass boost, nightcore, 8D, etc.)
- Soundboard system
- Welcome sound effect
- DJ roles & vote skip
- Now playing embeds with progress bar
- Lyrics, stats, favorites

Made with 💚 by Nextus Sounds
"""

import asyncio
import logging
import os
import platform
import random
import sys
from pathlib import Path

import discord
import wavelink
from discord.ext import commands, tasks
from dotenv import load_dotenv

# --------------------------------------------------------------------------------------
# Boot logging setup
# --------------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("bot.log", encoding="utf-8")],
)
log = logging.getLogger("NextusSounds")

# --------------------------------------------------------------------------------------
# Load environment variables (.env file)
# --------------------------------------------------------------------------------------
load_dotenv()


class NextusSounds(commands.Bot):
    """Custom Bot class with extra helpers."""

    def __init__(self) -> None:
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=self._get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True,
        )
        self.config_color = {
            "primary": 0x2F3136,
            "success": 0x43B581,
            "error": 0xF04747,
            "warning": 0xFAA61A,
            "music": 0x1DB954,
        }
        self.welcome_sound_enabled = os.getenv("ENABLE_WELCOME_SOUND", "true").lower() == "true"
        self.start_time = discord.utils.utcnow()

    # ------------------------------------------------------------------
    async def _get_prefix(self, bot: "NextusSounds", message: discord.Message) -> list[str]:
        prefixes = ["!", "ns.", "n.", "<@", "@Nextus"]
        return commands.when_mentioned(*prefixes)(bot, message)

    # ------------------------------------------------------------------
    async def setup_hook(self) -> None:
        """Load cogs and connect to Lavalink."""
        log.info("Setting up Nextus Sounds...")
        await self.load_cogs()
        await self.connect_lavalink()
        # Optional: sync tree if you use slash commands
        # await self.tree.sync()
        self.change_status.start()

    async def load_cogs(self) -> None:
        cog_files = [
            "cogs.music",
            "cogs.filters",
            "cogs.soundboard",
            "cogs.welcome",
            "cogs.utilities",
            "cogs.events",
            "cogs.extras",
            "cogs.moderation",
            "cogs.controls",
            "cogs.slash",
            "cogs.owner",
        ]
        for cog in cog_files:
            try:
                await self.load_extension(cog)
                log.info(f"Loaded cog: {cog}")
            except Exception as e:
                log.exception(f"Failed to load cog {cog}: {e}")

    async def connect_lavalink(self) -> None:
        try:
            # 🔧 FIX: secure= → https= (wavelink v3 uses 'https' not 'secure')
            secure = os.getenv("LAVALINK_SECURE", "true").lower() == "true"
            protocol = "https" if secure else "http"
            host = os.getenv("LAVALINK_HOST", "lavalink.jockie.dev")
            port = os.getenv("LAVALINK_PORT", "443")

            node = wavelink.Node(
                uri=f"{protocol}://{host}:{port}",
                password=os.getenv("LAVALINK_PASSWORD", "password"),
                https=secure,  # ← FIXED: was 'secure='
                identifier="MAIN",
            )
            await wavelink.Pool.connect(client=self, nodes=[node])
            log.info("✅ Lavalink connection established!")
        except Exception as e:
            log.error(f"⚠️ Lavalink connection failed: {e}")
            log.warning("Bot will use fallback FFmpeg mode (no filters/effects).")

    @tasks.loop(minutes=5)
    async def change_status(self) -> None:
        statuses = [
            discord.Activity(type=discord.ActivityType.listening, name="music 🎵 | !help"),
            discord.Activity(type=discord.ActivityType.playing, name="!play <song>"),
            discord.Activity(type=discord.ActivityType.watching, name="over your server 👀"),
        ]
        await self.change_presence(activity=random.choice(statuses), status=discord.Status.online)

    @change_status.before_loop
    async def before_status(self) -> None:
        await self.wait_until_ready()


# --------------------------------------------------------------------------------------
# Run
# --------------------------------------------------------------------------------------
async def main() -> None:
    bot = NextusSounds()
    token = os.getenv("DISCORD_TOKEN")
    if not token or token == "YOUR_BOT_TOKEN_HERE" or token == "your_discord_bot_token_here":
        log.critical("❌ DISCORD_TOKEN is missing!")
        log.critical("   1. Open .env file")
        log.critical("   2. Replace 'YOUR_BOT_TOKEN_HERE' with your real token")
        log.critical("   3. Get token: https://discord.com/developers/applications → Bot → Reset Token")
        return

    owner_id = os.getenv("OWNER_ID")
    if owner_id:
        log.info(f"👑 Bot owner ID: {owner_id}")
    else:
        log.warning("⚠️  OWNER_ID not set — owner-only commands disabled")

    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("👋 Shutdown requested by user.")
    except discord.LoginFailure:
        log.critical("❌ Invalid Discord token! Check your .env file.")
    except Exception as e:
        log.exception(f"Fatal error: {e}")