import requests
import time
import utility
import os

def subsonic_error_from_json(data):
    try:
        sr = data.get("subsonic-response", {})
        if sr.get("status") == "failed":
            err = sr.get("error", {}) or {}
            code = err.get("code")
            msg = err.get("message", "Unknown Subsonic error")
            return code, msg
    except Exception:
        pass
    return None

def subsonic_get_json(url, params, tries=3, timeout=30):
    last_exc = None
    for attempt in range(1, tries + 1):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            # JSON decode
            data = r.json()
            # Check Subsonic "status"
            err = subsonic_error_from_json(data)
            if err:
                code, msg = err
                print(f"[Subsonic FAILED] {url} code={code} message={msg}")
                return None
            return data
        except requests.exceptions.RequestException as e:
            last_exc = e
            wait = 2 ** (attempt - 1)
            print(f"[Network error] {url} attempt {attempt}/{tries}: {e} (retry in {wait}s)")
            time.sleep(wait)

        except ValueError as e:
            # JSON invalide
            print(f"[JSON decode error] {url}: {e}")
            return None
    print(f"[Giving up] {url}: {last_exc}")
    return None

def perform_requests(url, params):
    return subsonic_get_json(url, params, tries=3, timeout=30)
    
def parse_search(data, target_artist, target_title):
    if not data or 'subsonic-response' not in data or 'searchResult3' not in data['subsonic-response']:
            return []
        
    search_res = data['subsonic-response']['searchResult3']
    if 'song' not in search_res:
            print(f"   [DEBUG] No songs found in this search batch.")
            return []
            
    # tracks = octo-fiesta tracks informations       
    tracks = search_res['song']
    tracks_dict = []
    
    # DEBUG : On affiche combien de candidats on a trouvés
    print(f"   [DEBUG] Found {len(tracks)} candidates. processing...")

    for track in tracks:
        track_artist = track['artist']
        track_title = track['title']
        
        # Nettoyage pour comparaison
        clean_target_artist = utility.clean_artist_name(target_artist).lower()
        clean_track_artist = utility.clean_artist_name(track_artist).lower()
        
        # 1. Calcul du score standard
        similarity_note = utility.similarity(target_artist, target_title, track_artist, track_title)
        original_score = similarity_note # pour l'affichage debug
        
        # 2. OPTIMISATION "FEAT" : Tentative avec le titre trouvé "nettoyé"
        clean_track_title = utility.clean_artist_name(track_title)
        
        score_boosted = False
        if clean_track_title != track_title:
             similarity_note_optimized = utility.similarity(target_artist, target_title, track_artist, clean_track_title)
             if similarity_note_optimized > similarity_note:
                 similarity_note = similarity_note_optimized
                 score_boosted = True

        # Logique d'inclusion artiste (inchangée)
        artist_included = False
        if clean_target_artist in clean_track_artist and similarity_note > 0.60:
             similarity_note = max(similarity_note, 0.85)
             artist_included = True

        # --- BLOC D'AFFICHAGE BAVARD ---
        # On affiche uniquement si le score est un minimum pertinent (> 0.4) pour ne pas spammer,
        # OU si c'est le morceau spécifique qui pose problème (Jungle Jack).
        if similarity_note > 0.4 or "Jungle" in track_artist:
            print(f"      [Candidate] {track_artist} - {track_title}")
            print(f"          Target: {target_artist} - {target_title}")
            print(f"          Raw Score: {original_score:.2f}")
            if score_boosted:
                print(f"          Boosted Score (feat removed): {similarity_note:.2f} (Cleaned title: {clean_track_title})")
            if artist_included:
                print(f"          Artist inclusion boost applied.")
            print(f"          -> Final Decision: {'KEEP' if similarity_note >= 0.80 else 'REJECT'}")
            print("-" * 10)
        # -------------------------------

        if similarity_note < 0.80:
            continue
            
        track_info = {
            "title": track_title,
            "artist": track_artist,
            "similarity": similarity_note,
            "download_id": track['id'],
            "isexternal": track['isExternal']
        }
        tracks_dict.append(track_info)
    return tracks_dict    

def search_octo(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS, artist, title):
    url = SUBSONIC_URL+"/rest/search3"
    query = f"{artist} {title}"
    base_params = {
        'u': SUBSONIC_USER,
        'p': SUBSONIC_PASS,
        'v': '1.16.1',
        'c': 'python-script',
        'f': 'json',
        'query': query,
        'songCount': 20,
        'artistCount': 0,
        'albumCount': 0
    }

    cleaned_artist = utility.clean_artist_name(artist)
    cleaned_title = utility.clean_title(title)
    search_queries = [
        f"{artist} {title}",
        f"{cleaned_artist} {cleaned_title}",
        f"{cleaned_artist} {title}",
        f"{artist} {cleaned_title}"
    ]
    all_tracks_found = []
    for query in search_queries:
        # if perfect local match already exist : stop
        if any(t['isexternal'] is False and t['similarity'] > 0.9 for t in all_tracks_found):
            break
        params = base_params.copy()
        params['query'] = query
        # get all the 50 search result 
        data = perform_requests(url, params)
        # get the similarity between request and found tracks, if < 80 don't keep it
        results = parse_search(data, artist, title)
        # results is from each similare tracks : track title, artist, similarity note, download_id and isexternal value
        all_tracks_found.extend(results)
    unique_tracks = {t['download_id']: t for t in all_tracks_found}.values() # get only unique ID of tracks founds from octo-fiesta
    return list(unique_tracks)
    
def compare_tracks(tracks_dict):
    # if isexternal false we take the biggest similarity between false isexternal, if not then we stil take the biggest similarity between all
    # priorize internal sound
    if tracks_dict:
        result = max(tracks_dict, key=lambda x: (not x['isexternal'], x['similarity'])) 
        return result
    return None

def download_tracks(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS, id):
    url = SUBSONIC_URL+"/rest/stream"
    params = {
        'u': SUBSONIC_USER,
        'p': SUBSONIC_PASS,
        'v': '1.16.1',
        'c': 'python-script',
        'id': id,
        'maxBitRate': 1 # Optionnel : demande du mp3 pour aller plus vite, Octo téléchargera quand même le max dispo
    }
    try:
        # stream=True est CRUCIAL ici
        with requests.get(url, params=params, stream=True, timeout=10) as r:
            r.raise_for_status()
            for _ in r.iter_content(chunk_size=1024):
                break 
        print(f"Download trigger successful for ID: {id} (Trigger only)")
    except Exception as e:
        print(f"Error triggering download: {e}")
        return None
    
def start_scan(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS):
    scan_url = SUBSONIC_URL+"/rest/startScan"
    status_url = SUBSONIC_URL + "/rest/getScanStatus"
    params = {
        'u': SUBSONIC_USER,
        'p': SUBSONIC_PASS,
        'v': '1.16.1',
        'c': 'python-script',
        'f': 'json'
    }

    if not subsonic_get_json(scan_url, params, tries=3, timeout=30):
        print("startScan failed.")
        return None
    print("Scan command sent")
    time.sleep(2)
    consecutive_fail = 0
    while True:
        data = subsonic_get_json(status_url, params, tries=1, timeout=30)
        if not data:
            consecutive_fail +=1
            if consecutive_fail >= 10:
                print("Too many failures reading scan status. Aborting scan wait.")
                return None
            time.sleep(2)
            continue

        consecutive_fail = 0
        scan_status = data['subsonic-response'].get('scanStatus', {})
        is_scanning = scan_status.get('scanning')
        count = scan_status.get('count', 0)
        if is_scanning is False:
            print(f"\nScan finished. Total items scanned: {count}")
            break

        print(f"Scanning in progress... ({count} items)", end="\r")
        time.sleep(2)

    print("\nScan ended.")
    return True


def create_playlist(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS, playlist_name, songs_id):
    url = SUBSONIC_URL+"/rest/createPlaylist"
    params = {
        'u': SUBSONIC_USER,
        'p': SUBSONIC_PASS,
        'v': '1.16.1',
        'c': 'python-script',
        'f': 'json',
        'name': playlist_name,
        'songId': songs_id
    }
    data = subsonic_get_json(url, params, tries=3, timeout=30)
    if not data:
        print(f"Playlist NOT created: '{playlist_name}'")
        return None
    print(f"Playlist '{playlist_name}' created with {len(songs_id)} titles")
    return data

def get_all_playlists(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS):
    url = SUBSONIC_URL + "/rest/getPlaylists"
    params = {
        'u': SUBSONIC_USER,
        'p': SUBSONIC_PASS,
        'v': '1.16.1',
        'c': 'python-script',
        'f': 'json'
    }
    data = subsonic_get_json(url, params)
    if not data:
        return []
    try:
        resp = data.get("subsonic-response", {})
        playlists_container = resp.get("playlists", {})
        playlists = playlists_container.get("playlist", [])
        return playlists
    except Exception as e:
        print(f"Error parsing playlists: {e}")
        return []

def get_playlists_songs(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS):
    all_songs_ids = []
    url = SUBSONIC_URL + "/rest/getPlaylist"
    playlists = get_all_playlists(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS)
    for playlist in playlists:
        id = playlist.get('id')
        params = {
            'u': SUBSONIC_USER,
            'p': SUBSONIC_PASS,
            'v': '1.16.1',
            'c': 'python-script',
            'f': 'json',
            'id': id
        }
        data = subsonic_get_json(url, params)
        if not data:
            continue
        try:
            resp = data.get("subsonic-response", {})
            json_playlist = resp.get("playlist", {})
            entry = json_playlist.get('entry', [])
            if not entry:
                return []
            for ent in entry:
                song_id = ent.get('id')
                if song_id:
                    all_songs_ids.append(song_id)
        except Exception as e:
            print(f"Error parsing playlists: {e}")
            continue
    all_songs_ids = list(dict.fromkeys(all_songs_ids))
    return all_songs_ids

def get_liked_songs(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS):
    url = SUBSONIC_URL + "/rest/getStarred"
    params = {
        'u': SUBSONIC_USER,
        'p': SUBSONIC_PASS,
        'v': '1.16.1',
        'c': 'python-script',
        'f': 'json'
    }
    all_songs_ids = []
    data = subsonic_get_json(url, params)
    if not data:
        return []
    try:
        resp = data.get("subsonic-response", {})
        starred = resp.get('starred', {})
        starred_songs = starred.get('song', [])
        if not starred_songs:
            return []
        for star in starred_songs:
            song_id = star.get('id')
            all_songs_ids.append(song_id)
    except Exception as e:
        print(f"Error parsing starred songs: {e}")
        return []
    all_songs_ids = list(dict.fromkeys(all_songs_ids))
    return all_songs_ids

def flag_for_cleaning(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS, old_playlist_datas):
    playlist_or_starred = []
    in_playlist_songs = get_playlists_songs(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS)
    liked_songs = get_liked_songs(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS)
    playlist_or_starred = set(in_playlist_songs) | set(liked_songs)
    
    # deduplication
    playlist_or_starred = list(dict.fromkeys(playlist_or_starred))

    external_downloaded_subsonic = old_playlist_datas.get("subsonic_downloaded", [])
    external_downloaded_youtube = old_playlist_datas.get("youtube_downloaded", [])
    external_downloaded = set(external_downloaded_subsonic) | set(external_downloaded_youtube)

    # get list of all the ID that are starred or inside a playlist from the OLD weekly discovery
    matches = list(set(playlist_or_starred) & set(external_downloaded))
    already_local = old_playlist_datas.get("already_local", [])
    already_local_ids = [track['download_id'] for track in already_local if 'download_id' in track]

    not_delete = set(already_local_ids) | set(matches)

    all_tracks_ids = old_playlist_datas.get("all_tracks_ids", [])

    to_delete = []

    for track_id in all_tracks_ids:
        if track_id not in not_delete:
            to_delete.append(track_id)

    print(f"Starred or in playlist from weekly discovery = {matches}")
    print("-"*30)
    print(f"Already local = {already_local}")
    print("-"*30)
    print(f"Full list of id from weekly discovery = {all_tracks_ids} with {len(all_tracks_ids)}")
    print("-"*30)
    print(f"To not delete : {not_delete}")
    print(f"To delete : {to_delete}, with {len(to_delete)}")
    return to_delete

def cleaning(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS, LOCAL_DOWNLOAD_PATH, to_delete):
    url = SUBSONIC_URL + "/rest/getSong"
    song_id = None
    base_params = {
        'u': SUBSONIC_USER,
        'p': SUBSONIC_PASS,
        'v': '1.16.1',
        'c': 'python-script',
        'f': 'json',
        'id': song_id
    }
    deleted_count = 0
    print(f"Starting cleanup for {len(to_delete)} items...")

    for song in to_delete:
        params = base_params.copy()
        params['id'] = song
        data = subsonic_get_json(url, params)
        if not data:
            return []
        try:
            resp = data.get("subsonic-response", {})
            song = resp.get('song', {})
            relative_path = song.get('path')
            title = song.get('title')
            if not relative_path:
                print(f"[Warn] No path returned for ID {song_id}")
                continue
            full_path = os.path.join(LOCAL_DOWNLOAD_PATH, relative_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                print(f"[Deleted] Direct match: {full_path}")
                deleted_count += 1
                continue
            folder_path = os.path.dirname(full_path)
            if not os.path.isdir(folder_path):
                print(f"[Error] Folder not found: {folder_path}")
                continue
                
            # On liste les fichiers du dossier
            files_in_dir = os.listdir(folder_path)
            found_file = None
            
            # Nettoyage du titre cible pour la comparaison (ex: enlever ponctuation)
            clean_target_title = utility.clean_title(title).lower() if title else ""

            for f in files_in_dir:
                # On ignore les fichiers non audio (images, nfo, etc) pour éviter les faux positifs
                if not f.lower().endswith(('.mp3', '.flac', '.m4a', '.wav', '.opus')):
                    continue
                
                # Comparaison : est-ce que le titre est dans le nom de fichier ?
                # On utilise utility.clean_title sur le nom du fichier aussi
                f_name_clean = utility.clean_title(f).lower()
                
                if clean_target_title and clean_target_title in f_name_clean:
                    found_file = f
                    break
            
            if found_file:
                real_file_path = os.path.join(folder_path, found_file)
                os.remove(real_file_path)
                print(f"[Deleted] Fuzzy match: {found_file} (Target was: {title})")
                deleted_count += 1
            else:
                print(f"[Failed] Could not locate file for: {title} in {folder_path}")
                print(f"   -> Expected path was: {relative_path}")

        except Exception as e:
            print(f"Error cleaning song ID {song_id}: {e}")
            
    return deleted_count
            
def delete_playlist(SUBSONIC_URL, SUBSONIC_USER, SUBSONIC_PASS, playlist_id):
    url = SUBSONIC_URL + "/rest/deletePlaylist"
    params = {
        'u': SUBSONIC_USER,
        'p': SUBSONIC_PASS,
        'v': '1.16.1',
        'c': 'python-script',
        'f': 'json',
        'id': playlist_id
    }
    data = subsonic_get_json(url, params)
    if data:
        print(f"Playlist {playlist_id} deleted successfully.")
    return data
