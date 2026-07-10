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
            command_prefix=commands.when_mentioned_or("!", "ns.", "n."),
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
        # Lavalink state — set by connect_lavalink(). Initialized here so the
        # rest of the bot can safely read them even before setup_hook runs.
        self.lavalink_connected = False
        self.ffmpeg_fallback = False

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
        """Connect to Lavalink, trying multiple public nodes in order.

        In wavelink v3, ``Pool.connect()`` returns as soon as the node objects
        are registered — the websocket handshake completes asynchronously
        afterwards. So we cannot trust it returning to mean "connected". After
        registering each node we poll ``node.status`` until it reaches
        CONNECTED, and only then consider the node usable. If every node fails
        (DNS / TLS / handshake / bad password), we DO NOT crash — we flip on
        FFmpeg fallback mode so direct-URL playback still works.
        """
        # Primary node from env (overridable per-deploy via Railway variables).
        host = os.getenv("LAVALINK_HOST", "lavalink.lavalink.xyz")
        port = os.getenv("LAVALINK_PORT", "443")
        secure = os.getenv("LAVALINK_SECURE", "true").lower() == "true"
        password = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")
        scheme = "https" if secure else "http"

        # Env-configured node first, then known public fallbacks. Duplicates of
        # the env node are filtered out below so we never dial the same URI twice.
        nodes_to_try = [
            {
                "uri": f"{scheme}://{host}:{port}",
                "password": password,
                "identifier": "ENV",
            },
            {
                "uri": "https://lavalink.lavalink.xyz:443",
                "password": "youshallnotpass",
                "identifier": "LAVALINK_XYZ",
            },
            {
                "uri": "https://lavalink.publicnode.com:443",
                "password": "public",
                "identifier": "PUBLIC_NODE",
            },
            {
                "uri": "https://lavalink.weiss.ovh:443",
                "password": "weiss",
                "identifier": "WEISS",
            },
        ]

        # De-duplicate by URI, preserving order (env node keeps priority).
        seen_uris: set[str] = set()
        unique_nodes = []
        for cfg in nodes_to_try:
            if cfg["uri"] in seen_uris:
                continue
            seen_uris.add(cfg["uri"])
            unique_nodes.append(cfg)

        self.lavalink_connected = False
        self.ffmpeg_fallback = False
        last_error = "unknown"

        for node_cfg in unique_nodes:
            identifier = node_cfg["identifier"]
            uri = node_cfg["uri"]
            try:
                log.info(f"🔄 Trying Lavalink node: {identifier} ({uri})")
                node = wavelink.Node(
                    uri=uri,
                    password=node_cfg["password"],
                    identifier=identifier,
                )
                # Registers the node; websocket connects in the background.
                await wavelink.Pool.connect(client=self, nodes=[node])

                # Poll until the node's websocket is actually CONNECTED.
                if await self._await_node_connected(node, timeout=10.0):
                    self.lavalink_connected = True
                    log.info(f"✅ Lavalink connection established: {identifier}")
                    return

                last_error = "handshake did not complete (bad host/password/TLS?)"
                log.warning(f"⚠️ Node {identifier} registered but never became ready.")
                # Drop the dead node so a later working one becomes node[0].
                await self._discard_node(node)
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                log.warning(f"⚠️ Failed to connect {identifier}: {last_error}")
            continue

        # ⚠️ CRITICAL: never crash. Fall back to FFmpeg direct-URL playback.
        log.warning(
            f"❌ All Lavalink nodes failed (last error: {last_error}). "
            f"Enabling FFmpeg fallback mode (direct-URL playback only)."
        )
        self.lavalink_connected = False
        self.ffmpeg_fallback = True

    @staticmethod
    async def _await_node_connected(node: "wavelink.Node", timeout: float = 10.0) -> bool:
        """Poll a node until its status is CONNECTED, or timeout. Returns success."""
        deadline = timeout
        step = 0.25
        while deadline > 0:
            status = getattr(node, "status", None)
            status_name = getattr(status, "name", str(status)).upper() if status is not None else ""
            if "CONNECTED" in status_name and "DISCONNECT" not in status_name:
                return True
            # Some wavelink builds expose a boolean-ish readiness instead.
            if getattr(node, "connected", False) is True:
                return True
            await asyncio.sleep(step)
            deadline -= step
        return False

    @staticmethod
    async def _discard_node(node: "wavelink.Node") -> None:
        """Best-effort removal of a dead node from the pool so it isn't reused."""
        try:
            await node.close()
        except Exception:
            pass
        try:
            # Pool.nodes is a dict keyed by identifier in wavelink v3.
            nodes = getattr(wavelink.Pool, "nodes", {})
            ident = getattr(node, "identifier", None)
            if isinstance(nodes, dict) and ident in nodes:
                del nodes[ident]
        except Exception:
            pass

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