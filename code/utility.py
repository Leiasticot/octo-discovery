from thefuzz import fuzz
import re

def normalize_text(text):
    if not text:
        return ""
    text = text.lower()
    # Remplacement des caractères spéciaux et leet speak
    text = text.replace('$', 's').replace('€', 'e').replace('@', 'a')
    text = text.replace('“', '"').replace('”', '"') # Gestion smart quotes
    # On garde seulement les lettres, chiffres et espaces
    text = re.sub(r'[^\w\s]', '', text) 
    return text.strip()

def remove_youtube_junk(text):
    if not text:
        return ""
    text = text.replace('“', '').replace('”', '').replace('"', '')
    junk_patterns = [
            # ANGLAIS
            r"\(?official video\)?", 
            r"\(?official audio\)?",
            r"\(?official lyric video\)?",
            r"\(?official music video\)?",
            r"\[?official video\]?",
            r"\(?lyrics\)?", 
            r"\[?lyrics\]?",
            r"\(?hq\)?", 
            r"\(?4k\)?",
            r"\(?live\)?",
            r"\(?visualizer\)?",
            r"\(?from.*?\)",       
            r"\[?audio\]?",        # Enlève [Audio] ou (Audio)
            r"\[?mv\]?",           # Enlève [MV] ou (MV)
            r"\[?video\]?",        # Enlève [Video]
            r"\(?clip officiel\)?",
            r"\(?clip vidéo\)?",
            r"\(?audio officiel\)?",
            r"\(?paroles\)?",
            r"\[?paroles\]?",
            r"\(?letra\)?",
        ]
    
    cleaned = text.lower()
    for pattern in junk_patterns:
        cleaned = re.sub(pattern, "", cleaned)
    
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()    
    return cleaned

def clean_artist_name(artist):
    if not artist: return ""
    
    # 1. Cas : (feat. xxx) ou [feat. xxx]
    # On cherche : espace optionnel + ( ou [ + espace optionnel + feat/ft + tout le reste
    # On force un espace ou une fin de chaine après le mot clé pour éviter de couper "features"
    pattern_parenthesis = r"(?i)\s*[\(\[]\s*(?:feat|ft|featuring|vs|x|with|&)\.?\s+.*"
    artist = re.sub(pattern_parenthesis, "", artist)

    # 2. Cas : feat. xxx (sans parenthèse)
    # On cherche : espace + feat/ft + espace + tout le reste
    pattern_no_parenthesis = r"(?i)\s+(?:feat|ft|featuring|vs|x|with|&)\.?\s+.*"
    artist = re.sub(pattern_no_parenthesis, "", artist)

    return artist.strip()

def clean_title(title):
    return re.sub(r'[^\w\s]', '', title).strip()

def similarity(expected_artist, expected_title, found_artist, found_title):
    ea = normalize_text(expected_artist)
    et = normalize_text(expected_title)
    fa = normalize_text(found_artist)
    ft = normalize_text(found_title)

    # Si l'un des titres est vide après nettoyage, pas de match
    if not et or not ft: 
        return 0.0

    score_title = fuzz.token_sort_ratio(et, ft)
    if score_title < 55: 
        return 0.0
    
    score_artist = fuzz.token_sort_ratio(ea, fa)

    # --- NOUVELLE PROTECTION ANTI "STYLETO vs LETO" ---
    # Si l'artiste attendu ou trouvé est très court (<= 4 lettres), 
    # on exige une quasi-perfection sur le nom.
    if len(ea) <= 4 or len(fa) <= 4:
        # Si le score n'est pas 100, on vérifie si c'est exactement le même mot
        if score_artist < 100 and ea != fa:
            # Pénalité massive si ce n'est pas exact pour un nom court
            return 0.0 

    if score_artist < 70:
        if (len(ea) > 3 and ea in fa) or (len(fa) > 3 and fa in ea):
            score_artist = 85 
        else:
            return 0.0

    final_score = (score_artist + score_title) / 2
    return final_score / 100.0

def sanitize_filename(name):
    """Remplace les caractères interdits dans les noms de fichiers."""
    if not name: return "Unknown"
    # On garde alphanumérique, espaces, tirets, points
    return "".join([c for c in name if c.isalnum() or c in " .-_()"]).strip()
