# 🐙 Octo Discovery
## Weekly Discovery Sync (ListenBrainz → Subsonic/Navidrome + YouTube fallback)

_Disclaimer, this is my first long script, it was created helped by AI. I'm not a developper, I tried to do things at my way and sent it to AI to correct for more robustness. Every PR are welcomed even forks from people that know better than me how to code !_

Sync your **ListenBrainz Weekly Discovery** playlist into your **Subsonic-compatible server** (e.g. **Navidrome**) using **[Octo-Fiesta]([url](https://github.com/V1ck3s/octo-fiesta))**:

- Fetches the current **Weekly Discovery** playlist from ListenBrainz
- Searches tracks in Subsonic (`search3`) using multiple cleaned/matched variants
- If a track is found as **External** (via an external provider such as *Octo-Fiesta*), it triggers a **download** and then **rescans** the library until it becomes local
- If Subsonic search/download fails, it falls back to **YouTube** using **yt-dlp** + **FFmpeg**, writes the audio into your music library, and rescans
- Creates a Subsonic playlist containing the resulting track IDs
- Cleanup old playlist except : starred or added in another playlist or already locales tracks

---

## How it works

1. Detect the current ListenBrainz “Weekly Discovery” playlist (based on date in the playlist name)
2. Retrieve tracks (artist / title / album)
3. Search in Subsonic with fuzzy/normalized queries
4. If found:
   - **Local** result → add directly to the final playlist
   - **External** result → trigger download, rescan, verify it becomes local → add
5. If not found / download failed:
   - **YouTube fallback** → search, download audio, tag it, save to your library → rescan → add
6. Create a new Subsonic playlist
7. Save `data.json` (renaming previous to `old_data.json`)
8. Cleanup old playlist and old downloaded files safely (avoids removing tracks still in playlists or starred or that were already downloaded)

---

## Requirements

### System requirements
- **Python 3.10+**
- A **Subsonic-compatible server** (tested logic is suited for Navidrome)
- **Octo-Fiesta**
- **FFmpeg** (required for yt-dlp audio extraction/conversion)
- A library path on disk where the script can **write music files** and your server can **scan** them

### Python dependencies
The code uses these main Python packages:
- `requests`
- `python-dotenv`
- `thefuzz`
- `yt-dlp`

---
## To-do
- Some tracks didn't match
- 
## Installation

### 1) Clone the repository

```bash
git clone <your-repo-url>
cd <your-repo-folder>
```

### 2) Create & activate a virtual environment
```bash
python -m venv .venv
```

# Linux/macOS
```bash
source .venv/bin/activate
```
# Windows (PowerShell)
```bash
# .venv\Scripts\Activate.ps1
```

### 3) Install Python dependencies
```bash
pip install -r requirements.txt
```

### 4) Configuration

Create a .env file at the project root:
```bash
# ListenBrainz
LB_BASE_URL=https://api.listenbrainz.org
LB_USER=your_listenbrainz_username
# Subsonic / Navidrome
SUBSONIC_URL=http://your-server:4533
SUBSONIC_USER=your_subsonic_username
SUBSONIC_PASS=your_subsonic_password
# Local music library path (where YouTube downloads will be saved)
# IMPORTANT: this must be inside (or equal to) the folder your server scans.
LOCAL_DOWNLOAD_PATH=/path/to/your/music/library
```
#### Notes
LOCAL_DOWNLOAD_PATH must be part of your server’s scanned library, otherwise the rescan step won’t pick up new YouTube downloads.
The script writes data.json and keeps old_data.json to manage cleanup between weekly runs.

### Usage

Run:
```bash
python main.py
```
Or use a cron to auto-launch it

### Behavior:

If the current weekly playlist name matches what’s stored in data.json, the script stops (prevents duplicates).

### Project structure

- main.py — orchestration (fetch → search → download → rescan → playlist → cleanup)
- lb.py — ListenBrainz API (playlist + tracks)
- subsonic.py — Subsonic API (search, download external, scan, playlist management, cleanup)
- youtube.py — YouTube search + download via yt-dlp + matching logic
- utility.py — normalization, fuzzy scoring, helper utilities
#### Output files
- data.json
_Stores the state of the latest run:_
- playlist_name
- subsonic_downloaded (IDs downloaded via external provider and confirmed local after scan)
- youtube_downloaded (IDs detected after YouTube download + scan)
- all_tracks_ids (final IDs added to the playlist)
- not_found (tracks that could not be resolved)
- already_local (tracks already in the library)
- old_data.json

# Cleanup & safety

Cleanup is designed to avoid dangerous deletions:

Targets files associated with the previous Weekly Discovery run

Avoids deleting tracks that are:

- still present in any playlist
- starred/favorited
- Were already local
- 
## ⚠️ If you care about your library integrity, test on a copy or ensure you have backups before enabling aggressive cleanup.

### MIT License
```
Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
