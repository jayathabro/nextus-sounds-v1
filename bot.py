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
import json
import logging
import os
import random
import sys

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
        # Non-privileged intents only by default
        intents = discord.Intents.default()
        intents.message_content = True   # Required for prefix commands
        intents.guilds = True            # Guild events
        intents.voice_states = True      # Music player
        # Members intent is privileged — only enabled if env flag set
        if os.getenv("ENABLE_MEMBERS_INTENT", "false").lower() == "true":
            intents.members = True

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
        """Connect to Lavalink with fallback to multiple public nodes."""
        host = os.getenv("LAVALINK_HOST", "lavalink.jockie.dev")
        port = os.getenv("LAVALINK_PORT", "443")
        secure = os.getenv("LAVALINK_SECURE", "true").lower() == "true"
        password = os.getenv("LAVALINK_PASSWORD", "password")

        # Nodes to try in order — with explicit https parameter for wavelink v3
        nodes_to_try = [
            {
                "uri": f"{'https' if secure else 'http'}://{host}:{port}",
                "password": password,
                "identifier": "MAIN",
                "https": secure,  # ← Explicit HTTPS flag
            },
            {
                "uri": "http://lavalink.jockie.dev:2333",
                "password": "youshallnotpass",
                "identifier": "JOCKIE_HTTP",
                "https": False,  # ← HTTP, no SSL
            },
            {
                "uri": "https://lavalink.darrenofficial.com:443",
                "password": "darrenoff",
                "identifier": "DARREN",
                "https": True,  # ← HTTPS
            },
        ]

        for node_cfg in nodes_to_try:
            try:
                # 🔧 FIX: Explicit Node() with all parameters (wavelink v3)
                node = wavelink.Node(
                    uri=node_cfg["uri"],
                    password=node_cfg["password"],
                    identifier=node_cfg["identifier"],
                    https=node_cfg["https"],  # ← Critical fix
                )
                await wavelink.Pool.connect(client=self, nodes=[node])
                log.info(f"✅ Lavalink connection established: {node_cfg['identifier']}")
                return
            except Exception as e:
                log.warning(f"⚠️ Failed to connect {node_cfg['identifier']}: {e}")
                continue

        log.error("❌ All Lavalink nodes failed. Bot will use fallback FFmpeg mode.")

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
    if not token or token in ("YOUR_BOT_TOKEN_HERE", "your_discord_bot_token_here"):
        log.critical("❌ DISCORD_TOKEN is missing!")
        log.critical("   Get token: https://discord.com/developers/applications → Bot → Reset Token")
        return

    # Load owner_id from config.json if env var missing
    owner_id = os.getenv("OWNER_ID")
    if not owner_id:
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            owner_id = str(cfg.get("bot", {}).get("owner_id", ""))
            if owner_id and owner_id not in ("YOUR_DISCORD_USER_ID_HERE", "0", ""):
                os.environ["OWNER_ID"] = owner_id
                log.info(f"👑 Bot owner ID (from config.json): {owner_id}")
        except Exception:
            pass

    if owner_id and owner_id not in ("YOUR_DISCORD_USER_ID_HERE", "0", ""):
        log.info(f"👑 Bot owner ID: {owner_id}")
    else:
        log.warning("⚠️ OWNER_ID not set — owner-only commands disabled")

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