"""
Soundboard Cog - Quick-play custom sound effects from /sounds folder.

Files in the /sounds folder are auto-loaded. Users can type:
    !sounds              - list all available sounds
    !play <name>         - normal play (already supported by music cog)
    !sb <name>           - quick play sound (this cog)
    !sb stop             - stop soundboard playback

Server admins can upload new sounds:
    !sb-add <name>       - attach an MP3 to use as <name>.mp3
    !sb-remove <name>    - delete a sound
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands

SOUNDS_DIR = Path("sounds")
ALLOWED_EXT = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}
MAX_SOUND_SECONDS = 30
MAX_SOUND_BYTES = 10 * 1024 * 1024  # 10 MB
log = logging.getLogger("Soundboard")


class Soundboard(commands.Cog, name="Soundboard"):
    """🎺 Custom sound effects from /sounds folder."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        SOUNDS_DIR.mkdir(exist_ok=True)
        self.sounds: dict[str, Path] = {}
        self.refresh_sounds()

    def refresh_sounds(self) -> None:
        """Reload list of sounds from the /sounds directory."""
        self.sounds = {}
        for path in SOUNDS_DIR.iterdir():
            if path.is_file() and path.suffix.lower() in ALLOWED_EXT:
                self.sounds[path.stem.lower()] = path
        log.info(f"Loaded {len(self.sounds)} sounds: {list(self.sounds.keys())}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def ensure_voice(self, ctx: commands.Context) -> Optional[discord.VoiceClient]:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ Voice channel එකක join වෙන්න ඕනේ!")
            return None
        if ctx.voice_client and ctx.voice_client.channel == ctx.author.voice.channel:
            return ctx.voice_client
        if ctx.voice_client:
            await ctx.voice_client.move_to(ctx.author.voice.channel)
            return ctx.voice_client
        try:
            vc = await ctx.author.voice.channel.connect()
            return vc
        except Exception as e:
            await ctx.send(f"❌ Connect වෙන්න බෑ: {e}")
            return None

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    @commands.group(name="soundboard", aliases=["sb", "sounds"], invoke_without_command=True)
    async def soundboard_group(self, ctx: commands.Context, name: str = None) -> None:
        """Quick-play a sound effect. With no args, lists all sounds."""
        if name is None:
            return await self.list_sounds(ctx)
        await self.play_sound(ctx, name)

    @soundboard_group.command(name="list", aliases=["all"])
    async def sb_list(self, ctx: commands.Context) -> None:
        await self.list_sounds(ctx)

    @soundboard_group.command(name="play", aliases=["p"])
    async def sb_play(self, ctx: commands.Context, name: str) -> None:
        await self.play_sound(ctx, name)

    @soundboard_group.command(name="stop")
    async def sb_stop(self, ctx: commands.Context) -> None:
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.message.add_reaction("🛑")
        else:
            await ctx.send("❌ Soundboard play වෙන් නෑ!")

    @commands.has_permissions(administrator=True)
    @soundboard_group.command(name="add", aliases=["upload"])
    async def sb_add(self, ctx: commands.Context, name: str = None) -> None:
        """Attach an audio file to use as a new sound. Requires Admin."""
        if not name:
            await ctx.send("❌ නමක් දෙන්න! `!sb add <name>` සහ attach MP3 file එකක්")
            return
        name = name.lower().replace(" ", "_")
        if not ctx.message.attachments:
            await ctx.send("❌ MP3 file එකක් attach කරන්න!")
            return
        attachment = ctx.message.attachments[0]
        if attachment.size > MAX_SOUND_BYTES:
            await ctx.send(f"❌ File size limit: {MAX_SOUND_BYTES // 1024 // 1024}MB")
            return
        if not any(attachment.filename.lower().endswith(ext) for ext in ALLOWED_EXT):
            await ctx.send(f"❌ Allowed extensions: {', '.join(ALLOWED_EXT)}")
            return
        target = SOUNDS_DIR / f"{name}{Path(attachment.filename).suffix.lower()}"
        await attachment.save(target.as_posix())
        self.refresh_sounds()
        await ctx.send(f"✅ Sound added: **{name}** ({target.name})")

    @commands.has_permissions(administrator=True)
    @soundboard_group.command(name="remove", aliases=["delete", "rm"])
    async def sb_remove(self, ctx: commands.Context, name: str) -> None:
        target_name = name.lower()
        target_path = None
        for stem, path in self.sounds.items():
            if stem == target_name:
                target_path = path
                break
        if target_path is None:
            await ctx.send(f"❌ '{name}' කියන sound එක නෑ!")
            return
        try:
            target_path.unlink()
            self.refresh_sounds()
            await ctx.send(f"🗑️ Removed: **{name}**")
        except Exception as e:
            await ctx.send(f"❌ Delete කරන්න බෑ: {e}")

    @commands.command(name="sb-add", hidden=True)
    async def legacy_sb_add(self, ctx: commands.Context, name: str = None) -> None:
        """Backward compatibility for `!sb-add`."""
        await self.sb_add(ctx, name)

    @commands.command(name="sb-remove", hidden=True)
    async def legacy_sb_remove(self, ctx: commands.Context, name: str) -> None:
        await self.sb_remove(ctx, name)

    # ------------------------------------------------------------------
    # Core actions
    # ------------------------------------------------------------------
    async def list_sounds(self, ctx: commands.Context) -> None:
        self.refresh_sounds()
        if not self.sounds:
            await ctx.send(
                f"📂 Sounds folder එකේ sounds නෑ!\n"
                f"ඔයාගේ MP3 files මේ folder එකට දාන්න: `{SOUNDS_DIR.absolute()}`"
            )
            return
        embed = discord.Embed(
            title="🎺 Soundboard",
            description="මේ sounds ඔක්කොම voice channel එකේ instantly play කරන්න පුළුවන්!",
            color=0xFF6B35,
        )
        for stem, path in sorted(self.sounds.items()):
            embed.add_field(name=f"🔊 {stem}", value=f"`!sb {stem}`", inline=True)
        embed.set_footer(text=f"Total: {len(self.sounds)} sounds | Admin: !sb add/remove")
        await ctx.send(embed=embed)

    async def play_sound(self, ctx: commands.Context, name: str) -> None:
        target_name = name.lower()
        target_path = None
        for stem, path in self.sounds.items():
            if stem == target_name:
                target_path = path
                break
        if target_path is None:
            await ctx.send(
                f"❌ '{name}' sound එක නෑ! `!sounds` බලන්න available list."
            )
            return
        vc = await self.ensure_voice(ctx)
        if not vc:
            return
        # If music is playing, duck it (lower volume) until soundboard finishes
        was_playing = vc.is_playing()
        original_vol = 100
        if was_playing and hasattr(vc, "source") and vc.source:
            try:
                original_vol = getattr(vc.source, "volume", 100)
                vc.source.volume = 0.2
            except Exception:
                pass
        try:
            if vc.is_playing():
                vc.stop()
            source = discord.FFmpegPCMAudio(target_path.as_posix())
            vc.play(source, after=lambda e: self._after_sound(vc, was_playing, original_vol))
            embed = discord.Embed(
                title="🔊 Soundboard",
                description=f"Playing: **{target_path.stem}**",
                color=0xFF6B35,
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Play කරන්න බෑ: {e}")

    def _after_sound(self, vc: discord.VoiceClient, was_playing: bool, original_vol: int) -> None:
        if was_playing and hasattr(vc, "source") and vc.source:
            try:
                vc.source.volume = original_vol / 100
            except Exception:
                pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Soundboard(bot))