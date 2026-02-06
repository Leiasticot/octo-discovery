import yt_dlp
import utility
import re
import os

def parse_youtube_video(video_entry, target_artist, target_title):
    yt_raw_title = video_entry.get('title','')
    yt_uploader = video_entry.get('uploader','')

    yt_clean_title = utility.remove_youtube_junk(yt_raw_title)

    best_score = 0.0
    detected_infos = {}

    # Regex intelligente pour séparer :
    # \s* : espaces optionnels
    # (?: ... ) : groupe non capturant de séparateurs possibles
    # -|–|:|\||// : tiret standard, tiret long (ALT+0150), deux points, pipe, ou double slash
    # \s* : espaces optionnels
    separator_pattern = r"\s*(?:-|–|:|\||//)\s*"
    parts = re.split(separator_pattern, yt_clean_title, maxsplit=1)

    if len(parts) == 2:
        p1 = parts[0].strip()
        p2 = parts[1].strip()

        # ASTUCE ICI : On nettoie aussi les 'feat' dans les morceaux extraits
        # Cela transforme "Synora Ft. A. Atak Tos" en "Synora"
        p1_clean = utility.clean_artist_name(p1)
        p2_clean = utility.clean_artist_name(p2)

        # A. artist - title
        # On compare p1 (artist) et p2_clean (title sans feat)
        score_a = utility.similarity(target_artist, target_title, p1, p2_clean)
        if score_a > best_score:
            best_score = score_a
            detected_infos = {'artist': p1, 'title': p2_clean}

        # B. title - artist
        # On compare p2 (artist) et p1_clean (title sans feat)
        score_b = utility.similarity(target_artist, target_title, p2, p1_clean)
        if score_b > best_score:
            best_score = score_b
            detected_infos = {'artist': p2, 'title': p1_clean}
    # 3. Fallback : UPLOADER IS THE ARTIST
    # On compare l'uploader avec l'artiste cible, et le titre complet avec le titre cible
    yt_title_no_feat = utility.clean_artist_name(yt_clean_title)
    score_uploader_raw = utility.similarity(target_artist, target_title, yt_uploader, yt_clean_title)
    score_uploader_clean = utility.similarity(target_artist, target_title, yt_uploader, yt_title_no_feat)
    
    # On prend le meilleur des deux scores
    score_uploader = max(score_uploader_raw, score_uploader_clean) 
    
    if score_uploader > best_score:
        best_score = score_uploader
        detected_infos = {
            'artist': yt_uploader,
            'title': yt_clean_title
        }

    return best_score, detected_infos

def search_yt(artist, title, limit=5):
    print(f"Searching YT for: {artist} - {title}")

    cleaned_artist = utility.clean_artist_name(artist)

    search_queries = [
        f"{artist} {title} audio",
        f"{artist} {title}",
        f"{artist} {title} lyrics",
        f"{cleaned_artist} {title}",
    ]

    search_queries = list(dict.fromkeys(search_queries)) # deduplication

    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'ignoreerrors': True,
        'noplaylist': True,
        'search_sort': 'relevance'
    }

    best_match = None
    highest_score = 0.0

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for query in search_queries:
            try:
                search_query = f"ytsearch{limit}:{query}"
                result = ydl.extract_info(search_query, download=False)
                if result['entries']:
                    for entry in result['entries']:
                        if not entry:
                            continue
                        score, info = parse_youtube_video(entry, artist, title)
                        print(f"Analyzed: {entry.get('title')} | Score: {score:.2f}")
                        video_id = entry.get('id')
                        if score > highest_score and score >= 0.70 and info:
                            highest_score = score
                            best_match = {
                                'id': video_id,
                                'title': info['title'],
                                'artist': info['artist'],
                                'target_artist': artist, 
                                'target_title': title, 
                                'original_title': entry.get('title'),
                                'url': f"https://www.youtube.com/watch?v={video_id}",
                                'score': score                                
                            }

            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"YT Search Error: {e}")    
                return None            
    if best_match:
        print(f"-> Selected: {best_match['original_title']} (Score: {best_match['score']:.2f})")
    else:
        best_match = None
        print("-> No valid match found on YouTube.")
    return best_match

def download_yt(match_info, BASE_FOLDER):
    if not match_info or not match_info['url']:
        print("No valid information.")
        return False
    
    folder_artist = match_info.get('target_artist', match_info['artist'])
    file_title = match_info.get('target_title', match_info['title'])

    artist_clean = utility.sanitize_filename(folder_artist) 
    title_clean = utility.sanitize_filename(file_title)

    output_path = os.path.join(BASE_FOLDER, artist_clean)
    
    # Création des dossiers si inexistants
    if not os.path.exists(output_path):
        os.makedirs(output_path)
        print(f"Dossier créé : {output_path}")
    filename_template = os.path.join(output_path, f"{title_clean}.%(ext)s")
    print(f"Lancement du téléchargement pour : {artist_clean} - {title_clean}")

    ydl_opts = {
        'format': 'bestaudio/best',             # Meilleure qualité audio
        'outtmpl': filename_template,           # Chemin de sortie complet
        'postprocessors': [{                    # Conversion en MP3 (optionnel mais recommandé pour la musique)
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': False,
        'no_warnings': True,
        'addmetadata': True,
        'postprocessor_args': [
            '-metadata', f'artist={folder_artist}',
            '-metadata', f'title={file_title}'      
        ],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([match_info['url']])
        print(f"Téléchargement terminé avec succès dans : {output_path}")
        return True
    except Exception as e:
        print(f"Erreur lors du téléchargement : {e}")
        return False
