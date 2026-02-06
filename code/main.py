import lb
import subsonic
from dotenv import load_dotenv
import os
import json
import youtube
import time

load_dotenv()

LB_BASE_URL=os.getenv('LB_BASE_URL')
LB_USER=os.getenv('LB_USER')
SUBSONIC_USER = os.getenv('SUBSONIC_USER')
SUBSONIC_PASS = os.getenv('SUBSONIC_PASS')
SUBSONIC_URL = os.getenv('SUBSONIC_URL')
LOCAL_DOWNLOAD_PATH = os.getenv('LOCAL_DOWNLOAD_PATH')

def main():
    # --- STEP 0 : VERIFICATION ---
    # Get the actual "playlist name" on listenbrainz

    playlist_info = lb.get_weekly_playlist_infos(LB_BASE_URL, LB_USER)
    if not playlist_info:
        print("CRITICAL: Can't get playlist info from ListenBrainz")
        return

    playlist_name = playlist_info["name"]
    mbid = playlist_info["mbid"]

    old_data = None

    if os.path.exists('data.json'):
        try:
            with open('data.json', 'r', encoding='utf-8') as f:
                existing_data = json.load(f)                
                
                # Vérification si le nom de la playlist est identique
                if existing_data.get('playlist_name') == playlist_name:
                    print(f"Playlist '{playlist_name}' already exists (watch data.json).")
                    print("Script shutdown.")
                    return 
                try:
                    os.rename('data.json', 'old_data.json')
                    print("Old data.json moved as 'old_data.json'")
                except Exception as e:
                    print(f"Error when moving data.json : {e}")

            if os.path.exists('old_data.json'):
                try:
                    with open('old_data.json', 'r', encoding='utf-8') as f:
                        old_data = json.load(f)
                        print(f"Loaded old data for cleanup: {old_data.get('playlist_name')}")
                except Exception as e:
                    print(f"Warning: Could not read old_data.json: {e}")

        except json.JSONDecodeError:
            print("data.json is empty or corrupted, we continue the script.")

    print(f"New playlist detected: {playlist_name}. Processing...")

    # get the songs list of the current playlist on listenbrainz with artist, title and album
    lb_songs = lb.get_song_in_playlist(mbid, LB_BASE_URL) 

    already_local = [] #dict for local tracks that we don't want to process
    full_tracks_ids = [] # dict for all the tracks detected ids
    to_download_subsonic = [] # dict for download infos to give to subsonic
    to_download_youtube = [] # dict for download infos to give to youtube
    success_dl_subsonic = []
    success_dl_youtube = []
    not_found_tracks = [] # for tracks not found in subsonic or youtube

    print("--- STEP 1 : SEARCH ---")
    if not lb_songs:
        print("No song in ListenBrainz Playlist")
        return
    for song in lb_songs:
        time.sleep(0.5)
        artist = song['artist']
        title = song['title']
        album = song['album']
        # get a dict with unique ID from the search of octo fiesta
        tracks_dict = subsonic.search_octo(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS, artist, title)
        # find the only one with isexternal false + biggest similarity or isexternal true + biggest similarity
        best_match = subsonic.compare_tracks(tracks_dict)
        print("-"*30)
        print(f"extracted from LB : {artist} - {title}")
        print(f"Best match subsonic : {best_match}")
        if best_match:
            # 1. locally found
            if best_match['isexternal'] == False:
                print(f"Local found : {best_match['artist']} {best_match['title']} ; id = {best_match['download_id']}")
                print("-"*30)
                already_local.append(best_match)
                full_tracks_ids.append(best_match['download_id'])
            # 2. not locally found, to download with subsonic
            else:
                print(f"-> External found (queued for Subsonic DL)")
                best_match['original_album'] = album
                best_match['original_artist'] = artist 
                best_match['original_title'] = title
                to_download_subsonic.append(best_match)
                print(f"Added to download list {best_match['artist']} {best_match['title']} ; id = {best_match['download_id']}")
                print("-"*30)
        # 3. not found on subsonic -> queing for youtube
        else:
            print(f"-> Not found on Subsonic -> Queueing for YouTube")
            to_download_youtube.append(song)         


    print("--- STEP 2 : DOWNLOAD FROM SUBSONIC ---")
    if to_download_subsonic:
        for item in to_download_subsonic:
            time.sleep(3)
            print(f"Triggering Subsonic DL for: {item['artist']} - {item['title']}")            
            subsonic.download_tracks(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS, item['download_id'])
        
        # trigger a scan on navidrome to get new ids
        subsonic.start_scan(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS) 

        # verify if the subsonic downloaded file is available
        print("Verify subsonic dl ---")
        # to_download_subsonic contain track title from octo-fiesta, artist from octo-fiesta, similarity note with lb, download_id and isexternal value
        for item in to_download_subsonic:
            time.sleep(0.5)
            search_newly_downloaded = subsonic.search_octo(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS, item['artist'], item['title'])
            # get if the newly downloaded track isexternal false or true
            newly_downloaded_match = subsonic.compare_tracks(search_newly_downloaded)
            if newly_downloaded_match and newly_downloaded_match['isexternal'] == False:
                print(f"Success : {item['title']} is now local -> ID : {newly_downloaded_match['download_id']}")
                success_dl_subsonic.append(newly_downloaded_match['download_id'])
                full_tracks_ids.append(newly_downloaded_match['download_id'])
            else:
                print(f"Failure: {item['title']} download failed via Subsonic. Moving to YouTube fallback.")
                song_fallback = {
                        'artist': item['original_artist'],
                        'title': item['original_title'],
                        'album': item.get('original_album', 'Unknown Album')
                    }
                to_download_youtube.append(song_fallback)
    
    print("--- STEP 3 : PROCESS YT FALLBACKS ---")
    # to_download_youtube contain track title, artist and album
    if to_download_youtube:
        attempted_downloads = []
        for track in to_download_youtube:
            time.sleep(0.5)
            yt_track_data = youtube.search_yt(track['artist'], track['title'], limit=10)
            if yt_track_data: # trigger download
                print(f"Triggering Download of: {yt_track_data['original_title']}")
                success = youtube.download_yt(yt_track_data, LOCAL_DOWNLOAD_PATH)
                if success:
                    attempted_downloads.append(track)
                else:
                    not_found_tracks.append(track) # Echec DL malgré search ok    
            else:
                print(f"YT Search failed for {track['artist']} - {track['title']}")
                not_found_tracks.append(track) # Echec Search
        if attempted_downloads:
            print("Verify youtube dl ---")
            # trigger a scan on navidrome to get ids
            subsonic.start_scan(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS) 

            # to_download_youtube contain track title from LB and artist from LB, album
            for item in attempted_downloads:
                time.sleep(0.5)
                search_newly_downloaded = subsonic.search_octo(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS, item['artist'], item['title'])
                # get if the newly downloaded track isexternal false or true
                newly_downloaded_match = subsonic.compare_tracks(search_newly_downloaded)
                if newly_downloaded_match and newly_downloaded_match['isexternal'] == False:
                    print(f"Success YT : {item['title']} is now local -> ID : {newly_downloaded_match['download_id']}")
                    success_dl_youtube.append(newly_downloaded_match['download_id'])
                    full_tracks_ids.append(newly_downloaded_match['download_id'])
                else:
                    print(f"Warning: {item['title']} downloaded but not found in Subsonic scan yet.")
                    not_found_tracks.append(item)


    print("--- STEP 5 : CREATE PLAYLIST and data.json ---")
    if success_dl_subsonic or success_dl_youtube:
        data_to_save = {
            "playlist_name": playlist_name,
            "subsonic_downloaded": success_dl_subsonic, # IDs of downloaded songs from subsonic
            "youtube_downloaded": success_dl_youtube,
            "all_tracks_ids": full_tracks_ids,
            "not_found": not_found_tracks,
            "already_local": already_local
        }

    else:
        print("No tracks found or downloaded. Playlist not created.")

    if full_tracks_ids:
        subsonic.create_playlist(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS, playlist_name, list(full_tracks_ids))
    else:
        print("No new tracks to add to a playlist (only local tracks found ?).")

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=4)
    
    print("--- STEP 6 : CLEANUP (Old Playlist & Files) ---")
    if old_data:
        # 1. Récupérer le nom de l'ancienne playlist
        old_name = old_data.get("playlist_name")
        
        if old_name:
            # On cherche l'ID de cette ancienne playlist pour la supprimer
            all_playlists = subsonic.get_all_playlists(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS)
            # On trouve la playlist qui a le même nom
            old_playlist_id = next((p['id'] for p in all_playlists if p['name'] == old_name), None)

            if old_playlist_id:
                print(f"Deleting old playlist '{old_name}' (ID: {old_playlist_id})...")
                subsonic.delete_playlist(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS, old_playlist_id)
                # Petite pause pour laisser le temps à Navidrome de mettre à jour sa BDD
                time.sleep(2) 
            else:
                print(f"Old playlist '{old_name}' not found on server (already deleted?).")
        
        # 2. Calculer les fichiers à supprimer
        # Maintenant que l'ancienne playlist est supprimée, ses fichiers ne sont plus "protégés" 
        # par get_playlists_songs(), sauf s'ils sont dans la NOUVELLE playlist ou en favoris.
        to_delete_ids = subsonic.flag_for_cleaning(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS, old_data)
        
        if to_delete_ids:
            print(f"Starting cleanup of {len(to_delete_ids)} obsolete tracks...")
            # Appel de la fonction cleaning corrigée
            deleted_count = subsonic.cleaning(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS, LOCAL_DOWNLOAD_PATH, to_delete_ids)
            print(f"Cleanup finished. {deleted_count} files removed.")
        else:
            print("Nothing to clean up.")
            
    else:
        print("No old_data.json found. Skipping cleanup.")    

if __name__ == "__main__":
    main()
