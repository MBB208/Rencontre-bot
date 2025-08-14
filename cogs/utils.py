import aiosqlite
import json
import math
import os
from discord.ext import commands

class DatabaseManager:
    """Gestionnaire de base de données asynchrone utilisant aiosqlite"""
    
    def __init__(self, db_path="database/profiles.db"):
        self.db_path = db_path
        self.connection = None
    
    async def connect(self):
        """Connexion à la base de données et création des tables si nécessaire"""
        # Créer le dossier database s'il n'existe pas
        os.makedirs("database", exist_ok=True)
        
        self.connection = await aiosqlite.connect(self.db_path)
        
        # Créer la table profiles si elle n'existe pas
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                user_id TEXT PRIMARY KEY,
                prenom TEXT NOT NULL,
                pronoms TEXT NOT NULL,
                age INTEGER NOT NULL,
                interets TEXT NOT NULL,
                description TEXT NOT NULL,
                avatar_url TEXT,
                vector TEXT DEFAULT '[0,0,0,0,0]'
            )
        """)
        
        # Migration : Ajouter la colonne vector si elle n'existe pas
        try:
            await self.connection.execute("ALTER TABLE profiles ADD COLUMN vector TEXT DEFAULT '[0,0,0,0,0]'")
            await self.connection.commit()
            print("✅ Migration : colonne 'vector' ajoutée")
        except:
            # La colonne existe déjà ou autre erreur non critique
            pass
            
        await self.connection.commit()
        print("✅ Base de données initialisée")
    
    async def close(self):
        """Fermer la connexion à la base de données"""
        if self.connection:
            await self.connection.close()

# Instance globale de la base de données
db_instance = DatabaseManager()

def serialize_interests(interests_list):
    """Convertir une liste d'intérêts en JSON"""
    if isinstance(interests_list, str):
        # Si c'est une chaîne CSV, la convertir en liste
        interests_list = [interest.strip() for interest in interests_list.split(',')]
    return json.dumps(interests_list)

def deserialize_interests(interests_json):
    """Convertir du JSON en liste d'intérêts"""
    try:
        return json.loads(interests_json)
    except (json.JSONDecodeError, TypeError):
        return []

def serialize_vector(vector_list):
    """Convertir une liste (vecteur) en JSON"""
    return json.dumps(vector_list)

def deserialize_vector(vector_json):
    """Convertir du JSON en liste (vecteur)"""
    try:
        return json.loads(vector_json)
    except (json.JSONDecodeError, TypeError):
        return [0, 0, 0, 0, 0]  # Vecteur par défaut

def cosine_similarity(vector_a, vector_b):
    """
    Calculer la similarité cosinus entre deux vecteurs
    Gestion sécurisée des normes nulles
    """
    if len(vector_a) != len(vector_b):
        return 0.0
    
    # Calculer le produit scalaire
    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    
    # Calculer les normes
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))
    
    # Éviter la division par zéro
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)

def calculate_interests_similarity(interests_a, interests_b):
    """Calculer la similarité basée sur les intérêts communs"""
    if not interests_a or not interests_b:
        return 0.0
    
    # Convertir en ensembles pour faciliter les opérations
    set_a = set(interest.lower().strip() for interest in interests_a)
    set_b = set(interest.lower().strip() for interest in interests_b)
    
    # Calculer l'intersection et l'union
    intersection = set_a & set_b
    union = set_a | set_b
    
    # Indice de Jaccard
    if len(union) == 0:
        return 0.0
    
    return len(intersection) / len(union)

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