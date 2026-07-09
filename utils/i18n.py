"""Multi-language string system (Sinhala default + English)."""

from __future__ import annotations

import os

DEFAULT_LANG = os.getenv("DEFAULT_LANGUAGE", "si")

STRINGS: dict[str, dict[str, str]] = {
    "si": {
        "join_vc_first": "❌ Voice channel එකක join වෙන්න ඕනේ!",
        "no_song_playing": "❌ දැන් play වෙන song එකක් නෑ!",
        "song_paused": "⏸️ Pause කරා",
        "song_resumed": "▶️ Resume කරා",
        "song_skipped": "⏭️ Skip කරා",
        "song_stopped": "⏹️ Stop කරා",
        "queue_empty": "📭 Queue හිස්!",
        "queue_added": "➕ Added to queue: **{title}**",
        "searching": "🔎 හොයනවා: **{query}**",
        "search_failed": "❌ ඒක හොයාගන්න බෑ: **{query}**",
        "now_playing_title": "🎵 දැන් Play වෙන්නේ",
        "queue_title": "📃 Queue",
        "volume_set": "🔊 Volume: **{vol}%**",
        "filter_applied": "🎚️ Filter: **{name}**",
        "filter_off": "🔄 Filter reset",
        "loop_off": "➡️ Loop off",
        "loop_track": "🔂 Track loop on",
        "loop_queue": "🔁 Queue loop on",
        "shuffled": "🔀 Queue shuffle කරා",
        "connected": "✅ Connect වුණා **{channel}**",
        "disconnected": "👋 Disconnect වුණා",
        "permission_denied": "❌ Permission නෑ!",
        "cooldown": "⏳ Cooldown! {time:.1f}s බලාගෙන ඉන්න",
        "error_generic": "❌ Error: {error}",
        "welcome_played": "👋 Welcome beat play කරා!",
        "sound_played": "🔊 Sound play: **{name}**",
        "sound_added": "✅ Sound added: **{name}**",
        "sound_removed": "🗑️ Removed: **{name}**",
        "sound_not_found": "❌ '{name}' sound එක නෑ!",
        "fav_added": "⭐ Favorite එකට add කරා",
        "fav_removed": "💔 Favorite එකෙන් remove කරා",
        "playlist_saved": "💾 Playlist save කරා: **{name}**",
        "playlist_deleted": "🗑️ Playlist delete කරා: **{name}**",
        "language_set": "🌍 Language set to **{name}**",
    },
    "en": {
        "no_song_playing": "❌ No song is currently playing!",
        "song_paused": "⏸️ Paused",
        "song_resumed": "▶️ Resumed",
        "song_skipped": "⏭️ Skipped",
        "song_stopped": "⏹️ Stopped",
        "queue_empty": "📭 Queue is empty!",
        "queue_added": "➕ Added to queue: **{title}**",
        "searching": "🔎 Searching: **{query}**",
        "search_failed": "❌ Could not find: **{query}**",
        "now_playing_title": "🎵 Now Playing",
        "queue_title": "📃 Queue",
        "volume_set": "🔊 Volume: **{vol}%**",
        "filter_applied": "🎚️ Filter: **{name}**",
        "filter_off": "🔄 Filter reset",
        "loop_off": "➡️ Loop off",
        "loop_track": "🔂 Track loop on",
        "loop_queue": "🔁 Queue loop on",
        "shuffled": "🔀 Queue shuffled",
        "connected": "✅ Connected to **{channel}**",
        "disconnected": "👋 Disconnected",
        "permission_denied": "❌ You don't have permission!",
        "cooldown": "⏳ Cooldown! Wait {time:.1f}s",
        "error_generic": "❌ Error: {error}",
        "welcome_played": "👋 Welcome beat played!",
        "sound_played": "🔊 Sound played: **{name}**",
        "sound_added": "✅ Sound added: **{name}**",
        "sound_removed": "🗑️ Removed: **{name}**",
        "sound_not_found": "❌ Sound '{name}' not found!",
        "fav_added": "⭐ Added to favorites",
        "fav_removed": "💔 Removed from favorites",
        "playlist_saved": "💾 Playlist saved: **{name}**",
        "playlist_deleted": "🗑️ Playlist deleted: **{name}**",
        "language_set": "🌍 Language set to **{name}**",
        "join_vc_first": "❌ You must join a voice channel first!",
    },
}


def t(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """Translate a key. Falls back to English then key name."""
    text = STRINGS.get(lang, {}).get(key) or STRINGS.get("en", {}).get(key) or key
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError):
        return text


def languages() -> list[str]:
    return list(STRINGS.keys())