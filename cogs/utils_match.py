"""
Utilitaires pour le système de matching avancé
Inclut normalisation, IDF, scores de similarité et helpers DB
"""
import json
import math
import re
import unicodedata
from typing import List, Dict, Set, Tuple, Optional
from difflib import SequenceMatcher
import aiosqlite

# Configuration par défaut
DEFAULT_WEIGHTS = {
    "interests": 0.55,
    "personality": 0.25,
    "age": 0.20
}

DEFAULT_AGE_SIGMA = 4.0
FUZZY_THRESHOLD = 0.8

# Map de synonymes configurables
SYNONYMS_MAP = {
    "musique": ["music", "son", "audio", "chant", "melody"],
    "sport": ["fitness", "exercice", "gym", "athletique"],
    "lecture": ["livre", "roman", "litterature", "lire"],
    "cinema": ["film", "movie", "serie", "tv"],
    "voyage": ["vacances", "tourisme", "exploration"],
    "cuisine": ["cooking", "food", "gastronomie", "chef"],
    "art": ["peinture", "dessin", "creativite", "artistic"],
    "technologie": ["tech", "informatique", "computer", "digital"],
    "jeu": ["gaming", "video_game", "game", "jouer"],
    "nature": ["outdoor", "randonnee", "camping", "ecologie"]
}

def normalize_tag(tag: str) -> str:
    """
    Normalise un tag d'intérêt : lowercase, sans accents, espaces->underscore, sans ponctuation
    """
    if not tag:
        return ""
    
    # Lowercase
    tag = tag.lower().strip()
    
    # Supprimer les accents
    tag = unicodedata.normalize('NFD', tag)
    tag = ''.join(c for c in tag if unicodedata.category(c) != 'Mn')
    
    # Remplacer espaces par underscore
    tag = re.sub(r'\s+', '_', tag)
    
    # Supprimer la ponctuation
    tag = re.sub(r'[^\w_]', '', tag)
    
    return tag

async def canonicalize_interests(interests: str) -> str:
    """
    Canonicalise une chaîne d'intérêts séparés par virgules
    """
    if not interests:
        return ""
        
    interests_list = [i.strip() for i in interests.split(',')]
    canonical = []
    
    for interest in interests_list:
        normalized = normalize_tag(interest)
        if not normalized:
            continue
            
        # Chercher dans la map de synonymes
        found_canonical = None
        for canonical_form, synonyms in SYNONYMS_MAP.items():
            if normalized == canonical_form or normalized in synonyms:
                found_canonical = canonical_form
                break
        
        # Si pas trouvé, garder la forme normalisée
        canonical.append(found_canonical or normalized)
    
    return json.dumps(list(set(canonical)))  # Supprimer doublons et retourner JSON

def fuzzy_similarity(a: str, b: str) -> float:
    """
    Calcule la similarité fuzzy entre deux chaînes
    """
    return SequenceMatcher(None, a, b).ratio()

def compute_fuzzy_matches(interests_a: List[str], interests_b: List[str]) -> Dict[str, str]:
    """
    Trouve les correspondances fuzzy entre deux listes d'intérêts
    Retourne un dict {interest_a: best_match_b}
    """
    matches = {}
    
    for interest_a in interests_a:
        best_match = None
        best_score = 0.0
        
        for interest_b in interests_b:
            score = fuzzy_similarity(interest_a, interest_b)
            if score >= FUZZY_THRESHOLD and score > best_score:
                best_score = score
                best_match = interest_b
        
        if best_match:
            matches[interest_a] = best_match
    
    return matches

async def compute_idf_weights(db_connection: aiosqlite.Connection) -> Dict[str, float]:
    """
    Calcule les poids IDF pour tous les tags d'intérêts
    IDF = log((1 + N) / (1 + df(tag))) + 1
    """
    # Compter le nombre total de profils
    async with db_connection.execute("SELECT COUNT(*) FROM profiles") as cursor:
        total_profiles = (await cursor.fetchone())[0]
    
    if total_profiles == 0:
        return {}
    
    # Compter la fréquence de chaque tag
    tag_frequencies = {}
    
    async with db_connection.execute("SELECT interets_canonical FROM profiles WHERE interets_canonical IS NOT NULL") as cursor:
        async for row in cursor:
            try:
                interests = json.loads(row[0])
                for interest in interests:
                    tag_frequencies[interest] = tag_frequencies.get(interest, 0) + 1
            except (json.JSONDecodeError, TypeError):
                continue
    
    # Calculer IDF
    idf_weights = {}
    for tag, freq in tag_frequencies.items():
        idf_weights[tag] = math.log((1 + total_profiles) / (1 + freq)) + 1
    
    return idf_weights

def weighted_interest_score(interests_a: List[str], interests_b: List[str], 
                          idf_weights: Dict[str, float]) -> float:
    """
    Calcule le score de similarité d'intérêts avec Jaccard pondéré + IDF + fuzzy
    """
    if not interests_a or not interests_b:
        return 0.0
    
    # Convertir en sets pour faciliter les opérations
    set_a = set(interests_a)
    set_b = set(interests_b)
    
    # Intersection exacte
    exact_intersection = set_a & set_b
    
    # Fuzzy matches pour les tags non exactement matchés
    remaining_a = set_a - exact_intersection
    remaining_b = set_b - exact_intersection
    
    fuzzy_matches = compute_fuzzy_matches(list(remaining_a), list(remaining_b))
    
    # Calculer le score pondéré
    weighted_intersection = 0.0
    weighted_union = 0.0
    
    # Poids pour intersection exacte
    for tag in exact_intersection:
        weight = idf_weights.get(tag, 1.0)
        weighted_intersection += weight
    
    # Poids pour matches fuzzy (score réduit)
    for tag_a, tag_b in fuzzy_matches.items():
        weight_a = idf_weights.get(tag_a, 1.0)
        weight_b = idf_weights.get(tag_b, 1.0)
        fuzzy_score = fuzzy_similarity(tag_a, tag_b)
        weighted_intersection += (weight_a + weight_b) / 2 * fuzzy_score * 0.8  # Réduction pour fuzzy
    
    # Poids pour union
    all_tags = set_a | set_b
    for tag in all_tags:
        weight = idf_weights.get(tag, 1.0)
        weighted_union += weight
    
    return weighted_intersection / weighted_union if weighted_union > 0 else 0.0

def age_score(age_a: int, age_b: int, sigma: float = DEFAULT_AGE_SIGMA) -> float:
    """
    Calcule le score de compatibilité d'âge avec une fonction gaussienne
    S_age = exp(-(|ageA - ageB|²) / (2 * sigma²))
    """
    age_diff = abs(age_a - age_b)
    return math.exp(-(age_diff ** 2) / (2 * sigma ** 2))

def cosine_similarity(vector_a: List[float], vector_b: List[float]) -> float:
    """
    Calcule la similarité cosinus entre deux vecteurs de personnalité
    """
    if not vector_a or not vector_b or len(vector_a) != len(vector_b):
        return 0.0
    
    # Produit scalaire
    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    
    # Normes
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))
    
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)

def compute_match_score(profile_a: Dict, profile_b: Dict, idf_weights: Dict[str, float],
                       weights: Dict[str, float] = None) -> float:
    """
    Calcule le score de matching final entre deux profils
    Score = w_i*S_interests + w_p*S_personality + w_a*S_age
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS
    
    # Score d'intérêts
    interests_a = json.loads(profile_a.get('interets_canonical', '[]'))
    interests_b = json.loads(profile_b.get('interets_canonical', '[]'))
    s_interests = weighted_interest_score(interests_a, interests_b, idf_weights)
    
    # Score d'âge
    s_age = age_score(profile_a['age'], profile_b['age'])
    
    # Score de personnalité (si vecteurs disponibles)
    s_personality = 0.0
    if profile_a.get('vector') and profile_b.get('vector'):
        try:
            vector_a = json.loads(profile_a['vector'])
            vector_b = json.loads(profile_b['vector'])
            s_personality = cosine_similarity(vector_a, vector_b)
        except (json.JSONDecodeError, TypeError):
            pass
    
    # Score final pondéré
    final_score = (
        weights["interests"] * s_interests +
        weights["personality"] * s_personality +
        weights["age"] * s_age
    )
    
    return final_score

async def update_idf_incremental(db_connection: aiosqlite.Connection, 
                                old_interests: List[str], new_interests: List[str]):
    """
    Met à jour les poids IDF de manière incrémentale après modification d'un profil
    """
    # Cette fonction pourrait être implémentée pour optimiser les performances
    # Pour l'instant, on peut recalculer complètement (plus simple)
    pass

def generate_nonce() -> str:
    """
    Génère un nonce unique pour les interactions
    """
    import secrets
    return secrets.token_urlsafe(8)

def is_minor_major_mix(age_a: int, age_b: int) -> bool:
    """
    Vérifie si on mélange mineur et majeur (interdit)
    """
    return (age_a < 18) != (age_b < 18)

def format_age_range(age: int, range_size: int = 3) -> str:
    """
    Formate l'âge en tranche pour l'anonymisation
    """
    min_age = max(13, age - range_size)
    max_age = min(30, age + range_size)
    return f"{min_age}-{max_age} ans"

def truncate_description(description: str, max_length: int = 150) -> str:
    """
    Tronque la description pour l'anonymisation
    """
    if len(description) <= max_length:
        return description
    return description[:max_length] + "..."

def get_top_interests(interests: List[str], count: int = 5) -> str:
    """
    Retourne les top intérêts formatés pour l'affichage
    """
    if not interests:
        return "Aucun intérêt spécifié"
    
    displayed = interests[:count]
    if len(interests) > count:
        return ", ".join(displayed) + f" (+{len(interests) - count} autres)"
    return ", ".join(displayed)

def fuzzy_match_interests(interests_a: List[str], interests_b: List[str], threshold: float = 0.7) -> List[Tuple[str, str]]:
    """
    Trouve les correspondances fuzzy entre deux listes d'intérêts
    Retourne une liste de tuples (interest_a, interest_b)
    """
    matches = []
    
    for interest_a in interests_a:
        for interest_b in interests_b:
            score = fuzzy_similarity(interest_a, interest_b)
            if score >= threshold:
                matches.append((interest_a, interest_b))
    
    return matches

async def advanced_matching_algorithm(db_connection: aiosqlite.Connection, 
                                     user_id: str, 
                                     idf_weights: Dict[str, float],
                                     max_candidates: int = 10) -> List[Dict]:
    """
    Algorithme principal de matching avancé avec filtres de sécurité
    """
    # Récupérer le profil utilisateur
    async with db_connection.execute(
        "SELECT * FROM profiles WHERE user_id = ?", (user_id,)
    ) as cursor:
        user_profile = await cursor.fetchone()
    
    if not user_profile:
        return []
    
    user_age = user_profile[3]  # Colonne age
    is_user_minor = user_age < 18
    
    # Filtres de sécurité STRICTS
    if is_user_minor:
        # Mineur : uniquement autres mineurs (13-17)
        age_filter = "age >= 13 AND age <= 17 AND user_id != ?"
    else:
        # Majeur : uniquement autres majeurs (18-30)  
        age_filter = "age >= 18 AND age <= 30 AND user_id != ?"
    
    # Filtre d'écart d'âge maximum (8 ans)
    min_age = max(13 if is_user_minor else 18, user_age - 8)
    max_age = min(17 if is_user_minor else 30, user_age + 8)
    
    # Récupérer candidats potentiels avec filtres stricts
    query = f"""
        SELECT * FROM profiles 
        WHERE {age_filter} AND age >= ? AND age <= ?
        ORDER BY activity_score DESC
        LIMIT 50
    """
    
    candidates = []
    async with db_connection.execute(query, (user_id, min_age, max_age)) as cursor:
        async for row in cursor:
            # Créer dict du profil candidat
            candidate = {
                'user_id': row[0],
                'prenom': row[1], 
                'pronoms': row[2],
                'age': row[3],
                'interets': row[4],
                'interets_canonical': row[5] or '[]',
                'description': row[6],
                'avatar_url': row[7],
                'vector': row[8],
                'activity_score': row[10] if len(row) > 10 else 1.0
            }
            
            # Vérification sécurité double (ne jamais mixer mineur/majeur)
            if is_minor_major_mix(user_age, candidate['age']):
                continue  # Skip ce candidat
            
            # Convertir user_profile (tuple) en dict
            user_dict = {
                'user_id': user_profile[0],
                'prenom': user_profile[1],
                'pronoms': user_profile[2], 
                'age': user_profile[3],
                'interets': user_profile[4],
                'interets_canonical': user_profile[5] or '[]',
                'description': user_profile[6],
                'avatar_url': user_profile[7] if len(user_profile) > 7 else None,
                'vector': user_profile[8] if len(user_profile) > 8 else '[0,0,0,0,0]'
            }
            
            # Calculer score de matching
            score = compute_match_score(user_dict, candidate, idf_weights)
            
            candidate['score'] = score
            candidates.append(candidate)
    
    # Trier par score décroissant
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    return candidates[:max_candidates]