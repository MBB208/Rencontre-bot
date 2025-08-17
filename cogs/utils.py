import aiosqlite
import json
import os
import logging
from datetime import datetime
from typing import List, Optional

# Définir le chemin de la base de données
DB_PATH = "data/matching_bot.db"

# Configuration du logging réduit
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/matching_debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('MatchingBot')

class DatabaseManager:
    """Gestionnaire de base de données centralisé"""

    def __init__(self, db_path: str = "data/matching_bot.db"):
        self.db_path = db_path
        self.connection = None

    async def connect(self):
        """Connexion à la base de données"""
        try:
            # Créer le dossier data s'il n'existe pas
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            self.connection = await aiosqlite.connect(self.db_path)
            await self.create_tables()
            print("✅ Base de données connectée")
            return True
        except Exception as e:
            print(f"❌ Erreur connexion DB: {e}")
            return False

    async def create_tables(self):
        """Créer les tables nécessaires"""
        try:
            # Table des profils
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    user_id TEXT PRIMARY KEY,
                    prenom TEXT NOT NULL,
                    pronoms TEXT,
                    age INTEGER NOT NULL,
                    interets TEXT,
                    description TEXT,
                    avatar_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Table historique des matches
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS match_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user1_id TEXT NOT NULL,
                    user2_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

            # Vérifier et corriger la structure de la table matches si nécessaire
            try:
                # Vérifier si les colonnes existent
                async with self.connection.execute("PRAGMA table_info(matches)") as cursor:
                    columns = await cursor.fetchall()
                    column_names = [col[1] for col in columns]
                
                if 'user1_id' not in column_names or 'user2_id' not in column_names:
                    # Recréer la table avec la bonne structure
                    await self.connection.execute("DROP TABLE IF EXISTS matches")
                    await self.connection.execute("""
                        CREATE TABLE matches (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user1_id TEXT NOT NULL,
                            user2_id TEXT NOT NULL,
                            status TEXT DEFAULT 'pending',
                            created_at TEXT NOT NULL
                        )
                    """)
                    print("🔧 Table matches recréée avec la bonne structure")
            except Exception as e:
                print(f"⚠️ Erreur lors de la vérification des colonnes: {e}")

            # Table des matches
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user1_id TEXT NOT NULL,
                    user2_id TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL
                )
            """)

            # Table des vues (pour l'historique temporaire)
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS viewed_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    viewer_id TEXT NOT NULL,
                    viewed_id TEXT NOT NULL,
                    viewed_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    UNIQUE(viewer_id, viewed_id)
                )
            """)

            # Table des signalements
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reporter_id TEXT NOT NULL,
                    reported_id TEXT NOT NULL,
                    reason TEXT,
                    timestamp TEXT NOT NULL
                )
            """)

            # Table de configuration serveur
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS server_config (
                    guild_id TEXT PRIMARY KEY,
                    setup_channel_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            await self.connection.commit()
            print("✅ Tables créées/vérifiées")

        except Exception as e:
            print(f"❌ Erreur création tables: {e}")

    async def is_connected(self):
        """Vérifier si la connexion est active"""
        if not self.connection:
            return False
        try:
            await self.connection.execute("SELECT 1")
            return True
        except:
            return False

    async def reconnect(self):
        """Reconnecter à la base"""
        if self.connection:
            await self.connection.close()
        return await self.connect()

    async def close(self):
        """Fermer la connexion"""
        if self.connection:
            await self.connection.close()
            self.connection = None

# Instance globale de la base de données
db_instance = DatabaseManager()

def serialize_interests(interests_list: List[str]) -> str:
    """Sérialise une liste d'intérêts en JSON"""
    try:
        return json.dumps(interests_list, ensure_ascii=False)
    except Exception:
        return "[]"

def deserialize_interests(interests_json: str) -> List[str]:
    """Désérialise des intérêts JSON en liste"""
    try:
        return json.loads(interests_json) if interests_json else []
    except Exception:
        return []

def validate_age(age_str: str) -> Optional[int]:
    """Valide un âge (13-30 ans)"""
    try:
        age = int(age_str)
        if 13 <= age <= 30:
            return age
    except ValueError:
        pass
    return None

def is_minor(age: int) -> bool:
    """Vérifie si l'utilisateur est mineur"""
    return age < 18

def check_age_compatibility(age1: int, age2: int) -> bool:
    """Vérifie la compatibilité d'âge"""
    # Séparation stricte mineurs/majeurs
    if is_minor(age1) != is_minor(age2):
        return False

    # Écart maximum de 8 ans
    return abs(age1 - age2) <= 8

async def init_database():
    """Initialise la base de données avec toutes les tables nécessaires"""
    try:
        # S'assurer que l'instance DB est connectée
        if not await db_instance.is_connected():
            await db_instance.connect()

        print("✅ Base de données initialisée avec succès")
        return True

    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation de la base: {e}")
        return False