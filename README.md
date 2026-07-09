# 🎵 Nextus Sounds v1.0

> **High-Quality Discord Music Bot** — YouTube, Spotify, SoundCloud + Soundboard, Filters, Favorites, Playlists, Stats, DJ Roles, Slash Commands, and more.

---

## ✨ Features

### Core
- 🎵 **Music** — Play / Pause / Skip / Stop / Queue / Loop / Shuffle / Seek / Volume (0–150%)
- 🎧 **Multi-source** — YouTube, Spotify (albums/playlists/tracks), SoundCloud, Twitch, Bandcamp, direct URLs
- 🎚️ **Audio Filters** — Bass Boost, Nightcore, Vaporwave, 8D, Karaoke, EQ presets, custom speed/pitch
- 🎺 **Soundboard** — Quick-play custom MP3s from `sounds/` folder (admin upload supported)
- 👋 **Welcome Sound** — Super beat plays when bot joins a VC
- 🔁 **24/7 Mode** — Bot stays in voice channel forever

### Extras (v1.0)
- ⭐ **Favorites** — Save songs, persistent across restarts (`!fav add/list/play/remove`)
- 📜 **Playlists** — Save/load user playlists (`!playlist make/load/list/delete`)
- 📈 **Stats** — Top songs & top listeners per server (`!top`, `!topuser`)
- 🛡️ **DJ Role** — Restrict music commands to specific role (`!djrole @role`)
- 🎛️ **Now Playing Buttons** — Interactive ⏯⏭⏹🔀🔁📃 controls on Now Playing embed
- 💬 **Slash Commands** — `/play`, `/skip`, `/pause`, `/queue`, `/filter`, `/volume`, `/join`
- 🌍 **Multi-language** — Sinhala (default) and English (`!language si|en`)
- 🗳️ **Vote Skip** — 50% listener threshold
- 📜 **History** — Last 15 played songs (`!history`)
- 🧹 **Dedup Queue** — Remove duplicates (`!dedupe`)

---

## 📦 Project Structure

```
Nextus Sounds v.1/
├── bot.py                    # Main entry point
├── config.json               # Bot configuration
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── .gitignore
├── README.md                 # This file
├── bot.log                   # Auto-generated log file
├── sounds/                   # 🎺 Soundboard folder (drop MP3s here)
│   └── welcome.mp3           # 👋 Plays when bot joins VC
├── data/                     # 💾 Auto-created persistent storage
│   ├── favorites.json        # ⭐ User favorites
│   ├── playlists.json        # 📜 Saved playlists
│   ├── stats.json            # 📈 Server stats
│   └── settings.json         # ⚙️ Per-server settings (DJ role, language)
├── cogs/
│   ├── music.py              # 🎵 Core music player
│   ├── filters.py            # 🎚️ Audio filters
│   ├── soundboard.py         # 🎺 Soundboard system
│   ├── welcome.py            # 👋 Welcome sound
│   ├── utilities.py          # 🛠️ Help, ping, lyrics, search, 24/7
│   ├── events.py             # 📡 Error handler, member welcome
│   ├── extras.py             # ⭐ Favorites, playlists, history, stats
│   ├── moderation.py         # 🛡️ DJ role checks
│   ├── controls.py           # 🎛️ Now Playing buttons
│   └── slash.py              # 💬 Slash commands
└── utils/
    ├── storage.py            # 💾 Persistent JSON storage
    └── i18n.py               # 🌍 Multi-language strings
```

---

## 🚀 Setup Guide

### 1. Install Python

Python **3.10+** required. Download: https://www.python.org/downloads/

> ⚠️ During install, **check "Add Python to PATH"**.

### 2. Install FFmpeg

FFmpeg required for audio processing.

**Windows:**
```bash
winget install Gyan.FFmpeg
# or chocolatey
choco install ffmpeg
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt update && sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

Verify: `ffmpeg -version`

### 3. Install Dependencies

```bash
cd "Nextus Sounds v.1"
pip install -r requirements.txt
```

### 4. Create Discord Bot

1. https://discord.com/developers/applications → **New Application** → "Nextus Sounds"
2. **Bot** tab → **Add Bot** → copy **Token**
3. Enable **Privileged Intents**:
   - ✅ Presence Intent
   - ✅ Server Members Intent
   - ✅ Message Content Intent
4. Invite: **OAuth2 → URL Generator** → scopes `bot`, `applications.commands` + permissions

### 5. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```env
DISCORD_TOKEN=your_token_here
LAVALINK_HOST=lavalink.jockie.dev
LAVALINK_PORT=443
LAVALINK_PASSWORD=password
LAVALINK_SECURE=true
ENABLE_WELCOME_SOUND=true
WELCOME_SOUND_FILE=welcome.mp3
DEFAULT_LANGUAGE=si

# Optional
GENIUS_API_KEY=                # for !lyrics
SPOTIFY_CLIENT_ID=             # for advanced Spotify metadata
SPOTIFY_CLIENT_SECRET=
```

### 6. Add Welcome Sound

Put a beat/sound file in `sounds/welcome.mp3`.

### 7. Run

```bash
python bot.py
```

Bot should log in within seconds. ✅

---

## 🎛️ Command Reference

### 🎵 Music
| Command | Description |
|---|---|
| `!play <query>` | Play a song / add to queue |
| `!pause` / `!resume` | Pause / resume |
| `!skip` / `!stop` | Skip / stop |
| `!queue [page]` | Show queue |
| `!nowplaying` | Current track embed |
| `!volume <0-150>` | Set volume |
| `!loop <off\|track\|queue>` | Loop mode |
| `!shuffle` | Shuffle queue |
| `!seek <seconds>` | Jump position |
| `!remove <pos>` | Remove queue item |
| `!clearqueue` | Clear queue |
| `!dedupe` | Remove duplicates |
| `!vote-skip` | Vote to skip |

### 🎺 Soundboard
| Command | Description |
|---|---|
| `!sb <name>` | Play sound effect |
| `!sounds` | List all sounds |
| `!sb stop` | Stop soundboard |
| `!sb add <name>` (Admin) | Upload new sound |
| `!sb remove <name>` (Admin) | Delete sound |

### 🎚️ Filters
| Command | Description |
|---|---|
| `!filter <name>` | Apply filter |
| `!filters` | List all |
| `!speed <0.25-3.0>` | Speed |
| `!pitch <0.25-3.0>` | Pitch |

Filters: `none`, `bassboost`, `soft`, `pop`, `rock`, `treblebass`, `electronic`, `nightcore`, `vaporwave`, `8d`, `karaoke`, `tremolo`, `vibrato`.

### ⭐ Favorites
| Command | Description |
|---|---|
| `!fav` / `!fav list` | Show your favorites |
| `!fav add` | Add current song |
| `!fav play <#>` | Play favorite |
| `!fav remove <uri\|#>` | Remove favorite |

### 📜 Playlists
| Command | Description |
|---|---|
| `!playlist list` | Your playlists |
| `!playlist make <name>` | Save current + queue as playlist |
| `!playlist load <name>` | Load & play playlist |
| `!playlist delete <name>` | Delete playlist |

### 📈 Stats & History
| Command | Description |
|---|---|
| `!top` | Top 10 songs in this server |
| `!topuser` | Top 10 listeners |
| `!history` | Recently played |

### 🛡️ Moderation
| Command | Description |
|---|---|
| `!djrole @role` (Admin) | Set DJ role |
| `!djinfo` | Show DJ role |

### 🛠️ Utilities
| Command | Description |
|---|---|
| `!help` | Show all commands |
| `!ping` | Latency |
| `!stats` | Bot stats |
| `!lyrics <song>` | Lyrics (Genius) |
| `!search <query>` | YouTube search |
| `!24/7` | Toggle stay-in-VC |
| `!invite` | Invite link |
| `!language si\|en` | Change server language |

### 💬 Slash Commands
`/play`, `/skip`, `/pause`, `/queue`, `/filter`, `/volume`, `/join`

### 🎛️ Now Playing Buttons
The Now Playing embed has interactive buttons: ⏯ Pause/Resume · ⏭ Skip · ⏹ Stop · 🔀 Shuffle · 🔁 Loop · 📃 Queue

---

## 🎨 Adding Sounds

1. Drop MP3/WAV/OGG into `sounds/` folder
2. Restart bot (or next refresh)
3. `!sb <filename>` to play

**Welcome beat:**
- `sounds/welcome.mp3` (or change `WELCOME_SOUND_FILE` in `.env`)
- Plays when bot joins VC

---

## 🛡️ DJ Role System

```bash
!djrole @DJ          # Admin sets DJ role
!djinfo              # View current DJ role
```

Once a DJ role is set, only users with that role (or `Administrator`) can use music commands. Other users will get a permission denied message.

---

## 🌍 Language System

```bash
!language si         # Sinhala (default)
!language en         # English
```

Strings are stored in `utils/i18n.py` — easily extendable.

---

## 💾 Persistent Data

All user/server data is stored as JSON in `data/`:

| File | Purpose |
|---|---|
| `favorites.json` | Per-user saved songs |
| `playlists.json` | Per-user playlists |
| `stats.json` | Per-guild play counts |
| `settings.json` | Per-guild DJ role, language |

All writes are atomic (write to `.tmp`, then rename). Safe for crashes.

---

## 🌐 Lavalink Setup (Optional)

Public node used by default. For self-hosted:

1. Download Lavalink: https://github.com/lavalink-devs/Lavalink/releases
2. Create `application.yml`:
   ```yaml
   server:
     port: 2333
   lavalink:
     serverPassword: "youshallnotpass"
   ```
3. Run: `java -jar Lavalink.jar`
4. Update `.env`:
   ```
   LAVALINK_HOST=localhost
   LAVALINK_PORT=2333
   LAVALINK_PASSWORD=youshallnotpass
   LAVALINK_SECURE=false
   ```

---

## 🚀 Hosting 24/7

### VPS (best)
```bash
screen -S nextus python bot.py
# Detach: Ctrl+A, D
```

### Docker
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

### Railway / Render / Replit
Connect GitHub repo and deploy.

---

## 🐛 Troubleshooting

**Bot doesn't connect to voice:**
- Verify FFmpeg: `ffmpeg -version`
- Bot needs `Connect` + `Speak` permissions

**Lavalink errors:**
- Public node may be down — self-host
- Check firewall

**Spotify not working:**
- For Lyrics: configure `GENIUS_API_KEY`
- For advanced metadata: `SPOTIFY_CLIENT_ID` + `SPOTIFY_CLIENT_SECRET`

**Bot won't start:**
- Reset Discord token in Developer Portal
- Check `.env` has no extra spaces
- View `bot.log`

---

## 📜 License

MIT License — free to use, modify, distribute.

## 💚 Credits

Made with 💚 by **Nextus Sounds**
- discord.py — https://discordpy.readthedocs.io
- Wavelink — https://wavelink.dev
- Lavalink — https://lavalink.dev
- yt-dlp — https://github.com/yt-dlp/yt-dlp