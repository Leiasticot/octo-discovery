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

## Install

### 1) Clone & create a virtual environment

```bash
git clone <your-repo-url>
cd <your-repo-folder>

python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1

Install the requirements, create a .env file and launch the main.py
