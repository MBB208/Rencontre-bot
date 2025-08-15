
import aiosqlite
import json
import math
import os
import re
import unicodedata
from discord.ext import commands

class DatabaseManager:
    """Gestionnaire principal de la base de données SQLite"""
    
    def __init__(self, db_path: str = "data/matching_bot.db"):
        self.db_path = db_path
        self.connection = None
        
    async def connect(self):
        """Établir la connexion à la base de données"""
        # S'assurer que le dossier existe
        os.makedirs("data", exist_ok=True)
        
        self.connection = await aiosqlite.connect(self.db_path)
        
        # Activer les foreign keys
        await self.connection.execute("PRAGMA foreign_keys = ON")
        
        # Créer les tables de base
        await self.init_tables()
        
        print("✅ Base de données initialisée")
        
    async def init_tables(self):
        """Créer toutes les tables nécessaires"""
        # Table profiles principale
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                user_id TEXT PRIMARY KEY,
                prenom TEXT NOT NULL,
                pronoms TEXT NOT NULL,
                age INTEGER NOT NULL,
                interets TEXT NOT NULL,
                interets_canonical TEXT,
                description TEXT,
                avatar_url TEXT,
                vector TEXT,
                prefs TEXT DEFAULT '{}',
                activity_score REAL DEFAULT 1.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table matches pour le système de matching
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_id TEXT NOT NULL,
                user2_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table match_history pour éviter les répétitions
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS match_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_id TEXT NOT NULL,
                user2_id TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table reports pour la modération
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id TEXT NOT NULL,
                reported_id TEXT NOT NULL,
                reason TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await self.connection.commit()
        
    async def close(self):
        """Fermer la connexion"""
        if self.connection:
            await self.connection.close()

# Instance globale
db_instance = DatabaseManager()

def serialize_interests(interests_list: list) -> str:
    """Convertit une liste d'intérêts en JSON"""
    if not interests_list:
        return "[]"
    # Nettoyer et normaliser
    clean_interests = [interest.strip() for interest in interests_list if interest.strip()]
    return json.dumps(clean_interests, ensure_ascii=False)

def deserialize_interests(interests_json: str) -> list:
    """Convertit un JSON d'intérêts en liste"""
    try:
        if not interests_json or interests_json.strip() == "":
            return []
        return json.loads(interests_json)
    except (json.JSONDecodeError, TypeError):
        return []

def serialize_vector(vector_data) -> str:
    """Sérialise un vecteur en JSON"""
    if vector_data is None:
        return "[]"
    if isinstance(vector_data, (list, tuple)):
        return json.dumps(list(vector_data))
    return str(vector_data)

def normalize_text(text: str) -> str:
    """Normalise un texte (minuscules, sans accents)"""
    if not text:
        return ""
    # Convertir en minuscules
    text = text.lower().strip()
    # Supprimer les accents
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text

def calculate_interests_similarity(interests_a: list, interests_b: list) -> float:
    """Calcule la similarité entre deux listes d'intérêts"""
    if not interests_a or not interests_b:
        return 0.0
    
    # Normaliser les intérêts
    norm_a = set(normalize_text(interest) for interest in interests_a)
    norm_b = set(normalize_text(interest) for interest in interests_b)
    
    # Calculer la similarité de Jaccard
    intersection = len(norm_a & norm_b)
    union = len(norm_a | norm_b)
    
    if union == 0:
        return 0.0
    
    base_score = intersection / union
    
    # Bonus pour les intérêts rares (approximation simple)
    rare_bonus = 0.1 * min(intersection, 2)  # Bonus pour jusqu'à 2 intérêts communs rares
    
    return min(base_score + rare_bonus, 1.0)  # Cap à 100%

class Utils(commands.Cog):
    """Cog contenant les fonctions utilitaires"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        """Initialiser la base de données quand le cog est chargé"""
        await db_instance.connect()

async def setup(bot):
    """Fonction obligatoire pour charger le cog"""
    await bot.add_cog(Utils(bot))
