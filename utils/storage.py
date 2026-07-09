"""Persistent JSON storage helpers."""

from __future__ import annotations

import json
import asyncio
from pathlib import Path
from typing import Any, Optional

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

FAVORITES_FILE = DATA_DIR / "favorites.json"
PLAYLISTS_FILE = DATA_DIR / "playlists.json"
STATS_FILE = DATA_DIR / "stats.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

_locks: dict[str, asyncio.Lock] = {}


def _lock_for(path: Path) -> asyncio.Lock:
    key = str(path)
    if key not in _locks:
        _locks[key] = asyncio.Lock()
    return _locks[key]


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


async def load(path: Path) -> dict:
    async with _lock_for(path):
        return _read(path)


async def save(path: Path, data: dict) -> None:
    async with _lock_for(path):
        _write(path, data)


async def update(path: Path, mutator) -> dict:
    async with _lock_for(path):
        data = _read(path)
        result = mutator(data)
        if result is not None:
            data = result
        _write(path, data)
        return data


# --------------------------------------------------------------------------------------
# Favorites
# --------------------------------------------------------------------------------------
async def add_favorite(user_id: int, track_info: dict) -> None:
    """track_info must contain 'uri', 'title', 'author', 'duration'."""

    async def mut(data):
        data.setdefault(str(user_id), [])
        existing = [t for t in data[str(user_id)] if t.get("uri") != track_info["uri"]]
        existing.insert(0, track_info)
        existing = existing[:100]  # max 100 favorites per user
        data[str(user_id)] = existing
        return data

    await update(FAVORITES_FILE, mut)


async def remove_favorite(user_id: int, uri: str) -> bool:
    removed = []

    async def mut(data):
        key = str(user_id)
        if key not in data:
            return data
        before = len(data[key])
        data[key] = [t for t in data[key] if t.get("uri") != uri]
        removed.append(before - len(data[key]))
        return data

    await update(FAVORITES_FILE, mut)
    return bool(removed and removed[0] > 0)


async def get_favorites(user_id: int) -> list[dict]:
    data = await load(FAVORITES_FILE)
    return list(data.get(str(user_id), []))


# --------------------------------------------------------------------------------------
# Playlists
# --------------------------------------------------------------------------------------
async def save_playlist(user_id: int, name: str, tracks: list[dict]) -> None:
    async def mut(data):
        data.setdefault(str(user_id), {})
        data[str(user_id)][name.lower()] = {
            "name": name,
            "tracks": tracks,
            "created": data[str(user_id)].get(name.lower(), {}).get("created", None),
        }
        return data

    await update(PLAYLISTS_FILE, mut)


async def delete_playlist(user_id: int, name: str) -> bool:
    deleted = []

    async def mut(data):
        key = str(user_id)
        if key in data and name.lower() in data[key]:
            del data[key][name.lower()]
            deleted.append(True)
        return data

    await update(PLAYLISTS_FILE, mut)
    return bool(deleted)


async def get_playlist(user_id: int, name: str) -> Optional[dict]:
    data = await load(PLAYLISTS_FILE)
    return data.get(str(user_id), {}).get(name.lower())


async def list_playlists(user_id: int) -> list[dict]:
    data = await load(PLAYLISTS_FILE)
    return list(data.get(str(user_id), {}).values())


# --------------------------------------------------------------------------------------
# Stats
# --------------------------------------------------------------------------------------
async def record_play(guild_id: int, user_id: int, track_info: dict) -> None:
    async def mut(data):
        gid = str(guild_id)
        uid = str(user_id)
        title = track_info.get("title", "Unknown")
        author = track_info.get("author", "Unknown")
        data.setdefault(gid, {"plays": 0, "songs": {}, "users": {}})
        data[gid]["plays"] += 1
        songs = data[gid]["songs"]
        users = data[gid]["users"]
        songs[title] = songs.get(title, {"count": 0, "author": author, "uri": track_info.get("uri", "")})
        songs[title]["count"] += 1
        users[uid] = users.get(uid, 0) + 1
        return data

    await update(STATS_FILE, mut)


async def get_stats(guild_id: int) -> dict:
    data = await load(STATS_FILE)
    return data.get(str(guild_id), {"plays": 0, "songs": {}, "users": {}})


# --------------------------------------------------------------------------------------
# Per-guild settings (DJ role, language, etc.)
# --------------------------------------------------------------------------------------
DEFAULT_SETTINGS = {
    "dj_role": None,         # role ID
    "language": "si",         # 'si' | 'en'
    "vote_skip_threshold": 0.5,
    "auto_leave": True,
    "auto_leave_timeout": 180,
    "announce_songs": True,
    "max_queue": 100,
}


async def get_settings(guild_id: int) -> dict:
    data = await load(SETTINGS_FILE)
    stored = data.get(str(guild_id), {})
    merged = {**DEFAULT_SETTINGS, **stored}
    return merged


async def update_settings(guild_id: int, **kwargs) -> dict:
    async def mut(data):
        key = str(guild_id)
        merged = {**DEFAULT_SETTINGS, **data.get(key, {}), **kwargs}
        data[key] = merged
        return data

    return await update(SETTINGS_FILE, mut)
