import aiosqlite
import logging
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

# Configuration du logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gestionnaire de base de données SQLite avec aiosqlite"""

    def __init__(self, db_path: str = "data/matching_bot.db"):
        self.db_path = db_path
        self.connection: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Établir la connexion à la base de données"""
        try:
            # Créer le dossier data s'il n'existe pas
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            self.connection = await aiosqlite.connect(self.db_path)
            self.connection.row_factory = aiosqlite.Row
            await self.create_tables()
            logger.info("✅ Connexion à la base de données établie")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur connexion DB: {e}")
            return False

    async def disconnect(self):
        """Fermer la connexion à la base de données"""
        if self.connection:
            await self.connection.close()
            self.connection = None
            logger.info("🔌 Connexion DB fermée")

    async def is_connected(self) -> bool:
        """Vérifier si la connexion est active"""
        if not self.connection:
            return False
        try:
            await self.connection.execute("SELECT 1")
            return True
        except:
            return False

    async def reconnect(self):
        """Reconnecter à la base de données"""
        await self.disconnect()
        return await self.connect()

    async def create_tables(self):
        """Créer toutes les tables nécessaires"""
        try:
            # Table des profils
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    user_id TEXT PRIMARY KEY,
                    prenom TEXT NOT NULL,
                    pronoms TEXT,
                    age INTEGER NOT NULL,
                    interets TEXT,
                    ville TEXT,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                )
            """)

            # Table des matches
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user1_id TEXT NOT NULL,
                    user2_id TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    UNIQUE(user1_id, user2_id)
                )
            """)

            # Table de l'historique des matches
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS match_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user1_id TEXT NOT NULL,
                    user2_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

            # Table des profils passés
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS passed_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    passed_profile_id TEXT NOT NULL,
                    passed_at TEXT NOT NULL,
                    UNIQUE(user_id, passed_profile_id)
                )
            """)

            # Table des likes
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS profile_likes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    liker_id TEXT NOT NULL,
                    liked_profile_id TEXT NOT NULL,
                    liked_at TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    UNIQUE(liker_id, liked_profile_id)
                )
            """)

            # Table des signalements
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reporter_id TEXT NOT NULL,
                    reported_id TEXT NOT NULL,
                    reason TEXT,
                    status TEXT DEFAULT 'pending',
                    timestamp TEXT NOT NULL
                )
            """)

            await self.connection.commit()
            logger.info("✅ Tables créées/vérifiées")

        except Exception as e:
            logger.error(f"❌ Erreur création tables: {e}")

# Instance globale
db_instance = DatabaseManager()

async def init_database():
    """Initialiser la base de données"""
    return await db_instance.connect()

def serialize_interests(interests):
    """Sérialiser les intérêts en JSON"""
    if isinstance(interests, list):
        return json.dumps(interests)
    return interests

def deserialize_interests(interests_str):
    """Désérialiser les intérêts depuis JSON"""
    if not interests_str:
        return []
    try:
        if interests_str.startswith('['):
            return json.loads(interests_str)
        return [interests_str]
    except:
        return [interests_str]