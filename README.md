# 🐙 Octo Discovery

This project aims to automatiOcto Discovery is a Python automation tool that bridges the gap between ListenBrainz recommendations and your local Subsonic/Navidrome music server.

It automatically fetches your "Weekly Discovery" playlist from ListenBrainz, checks your local library for matches using fuzzy logic, downloads missing tracks (via Subsonic or YouTube fallback), and manages the playlist on your server. It also features a smart cleaning mechanism to keep your library from bloating.caly fetch ListenBrainz Weekly Discovery playlist from ListenBrainz using octo-fiesta or youtube if octo-fiesta can't find the file.

✨ Features
🔗 ListenBrainz Integration: Automatically retrieves the "Weekly Discovery" playlist metadata.

🧠 Smart Matching: Uses thefuzz to compare track titles and artists, handling slight variations in naming (e.g., ignoring "feat.", "Official Video") to prevent duplicate downloads.

📥 Hybrid Download System:

Local Check: Checks if the track already exists in your library.

Subsonic/Server Download: Attempts to download via the Subsonic API first (if supported).

YouTube Fallback: Uses yt-dlp to find and download high-quality audio if not found on the server.

🏷️ Auto-Tagging: Automatically embeds Artist and Title metadata into downloaded files.

📂 Playlist Management: Creates or updates the weekly playlist on your Subsonic server.

🧹 Auto-Cleanup: Smartly deletes tracks from previous weekly discoveries to save disk space, unless they were starred/favorited or added to another playlist.

🛠️ Prerequisites
Python 3.8+

FFmpeg (Required for audio conversion/tagging)

A Subsonic-compatible server (tested with Navidrome)

A ListenBrainz account

📦 Installation
Clone the repository

Bash

git clone https://github.com/yourusername/octo-discovery.git
cd octo-discovery
Install dependencies

Bash

pip install -r requirements.txt
(Note: Ensure requests, yt-dlp, thefuzz, and python-dotenv are in your requirements.txt)

Install FFmpeg

Debian/Ubuntu: sudo apt install ffmpeg

Windows: Download binaries and add to PATH.

⚙️ Configuration
Create a .env file in the root directory and configure the following variables:

Ini, TOML

# ListenBrainz Configuration
LB_BASE_URL=https://api.listenbrainz.org
LB_USER=your_listenbrainz_username

# Subsonic / Navidrome Configuration
SUBSONIC_URL=http://your-server-ip:4533
SUBSONIC_USER=your_subsonic_username
SUBSONIC_PASS=your_subsonic_password

# Local Path for Downloads (where YouTube rips are saved)
# Ideally, this folder should be scanned by your Navidrome server
LOCAL_DOWNLOAD_PATH=/path/to/your/music/library/OctoDiscovery
🚀 Usage
Simply run the script:

Bash

python main.py
Automation
You can set this up as a cron job to run every Monday (when ListenBrainz updates the playlist).

Bash

# Example: Run every Monday at 8:00 AM
0 8 * * 1 /usr/bin/python3 /path/to/octo-discovery/main.py >> /var/log/octo_discovery.log 2>&1
🔄 Workflow Logic
Fetch: Connects to ListenBrainz to get the current "Weekly Discovery" MBIDs.

Search & Compare:

The script searches your Subsonic server for each track.

It calculates a Similarity Score (0-100) between the LB metadata and your local files.

If score > 80%, it links the existing file instead of downloading.

Download:

If missing, it queues the track for download.

If YouTube is required, it strips "junk" words (e.g., "(Official Audio)", "[Lyrics]") to find the best match.

Scan & Verify: Triggers a server scan and verifies the file is now available via the API.

Playlist: Creates the new playlist on the server.

Cleanup: Identifies tracks from previous runs. If a track is not in any other playlist and not starred, it is deleted to save space.

⚠️ Disclaimer
This tool is intended for personal archiving and discovery purposes. Please respect copyright laws in your country and the Terms of Service of the platforms used.
