"""
Cog principal pour le système de matching avancé avec double opt-in
Inclut commandes slash, handlers de boutons et logique de matching
"""
import discord
from discord.ext import commands
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import aiosqlite
import math
import re

import hashlib
import random
import string

# Fonctions utilitaires intégrées
def normalize_tag(tag: str) -> str:
    """Normalise un tag (lowercase, sans accents, etc.)"""
    import unicodedata
    tag = tag.lower().strip()
    tag = unicodedata.normalize('NFD', tag).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z0-9]', '_', tag)

def canonicalize_interests(interests: list) -> list:
    """Canonicalise une liste d'intérêts"""
    return [normalize_tag(interest) for interest in interests if interest.strip()]

async def compute_idf_weights(connection) -> dict:
    """Calcule les poids IDF pour tous les tags"""
    weights = {}
    try:
        async with connection.execute("SELECT COUNT(*) FROM profiles") as cursor:
            total_profiles = (await cursor.fetchone())[0]

        if total_profiles == 0:
            return weights

        async with connection.execute("SELECT interets FROM profiles WHERE interets IS NOT NULL AND interets != '' AND interets != 'null'") as cursor:
            async for row in cursor:
                try:
                    interests_json = row[0]
                    if not interests_json or interests_json.strip() == '':
                        continue

                    interests = json.loads(interests_json)
                    if not isinstance(interests, list):
                        continue

                    for interest in interests:
                        if interest and isinstance(interest, str):
                            normalized = normalize_tag(interest)
                            if normalized:  # Vérifier que la normalisation a donné un résultat
                                weights[normalized] = weights.get(normalized, 0) + 1
                except (json.JSONDecodeError, TypeError, AttributeError):
                    continue

        # Calculer IDF
        for tag, count in weights.items():
            weights[tag] = math.log((1 + total_profiles) / (1 + count)) + 1

    except Exception as e:
        print(f"Erreur compute_idf_weights: {e}")

    return weights

def compute_match_score(user_a: dict, user_b: dict, idf_weights: dict, weights: dict) -> float:
    """Calcule le score de compatibilité entre deux utilisateurs"""
    try:
        # Sécuriser les intérêts avec valeurs par défaut
        interests_json_a = user_a.get('interets', '[]')
        interests_json_b = user_b.get('interets', '[]')

        # Vérifier et corriger les valeurs vides/None
        if not interests_json_a or interests_json_a.strip() == '' or interests_json_a == 'null':
            interests_json_a = '[]'
        if not interests_json_b or interests_json_b.strip() == '' or interests_json_b == 'null':
            interests_json_b = '[]'

        # Parser JSON de façon sécurisée
        try:
            interests_list_a = json.loads(interests_json_a)
            if not isinstance(interests_list_a, list):
                interests_list_a = []
        except (json.JSONDecodeError, TypeError):
            interests_list_a = []

        try:
            interests_list_b = json.loads(interests_json_b)
            if not isinstance(interests_list_b, list):
                interests_list_b = []
        except (json.JSONDecodeError, TypeError):
            interests_list_b = []

        # Score d'intérêts
        interests_a = set(canonicalize_interests(interests_list_a))
        interests_b = set(canonicalize_interests(interests_list_b))

        common = interests_a & interests_b
        union = interests_a | interests_b

        if not union:
            interests_score = 0
        else:
            # Score pondéré par IDF
            weighted_common = sum(idf_weights.get(tag, 1) for tag in common)
            weighted_union = sum(idf_weights.get(tag, 1) for tag in union)
            interests_score = weighted_common / weighted_union if weighted_union > 0 else 0

        # Score d'âge (gaussien) avec vérification de type
        try:
            age_a = int(user_a.get('age', 18))
            age_b = int(user_b.get('age', 18))
            age_diff = abs(age_a - age_b)
            age_score = math.exp(-(age_diff ** 2) / (2 * 4.0 ** 2))
        except (ValueError, TypeError):
            age_score = 0.5  # Score neutre si âge invalide

        # Score final avec vérification des poids
        interests_weight = weights.get('interests', 0.7) if isinstance(weights, dict) else 0.7
        age_weight = weights.get('age', 0.3) if isinstance(weights, dict) else 0.3

        final_score = interests_weight * interests_score + age_weight * age_score

        return min(1.0, max(0.0, final_score))

    except Exception as e:
        print(f"Erreur compute_match_score: {e}")
        print(f"Debug - user_a: {user_a}")
        print(f"Debug - user_b: {user_b}")
        return 0.0

def generate_nonce() -> str:
    """Génère un nonce unique"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

def is_minor_major_mix(age_a: int, age_b: int) -> bool:
    """Vérifie si c'est un mélange mineur/majeur"""
    return (age_a < 18) != (age_b < 18)

def format_age_range(age: int) -> str:
    """Formate l'âge en tranche"""
    if age < 16:
        return "13-15 ans"
    elif age < 18:
        return "16-17 ans"
    elif age < 21:
        return "18-20 ans"
    elif age < 25:
        return "21-24 ans"
    else:
        return "25+ ans"

def truncate_description(description: str, max_length: int = 150) -> str:
    """Tronque une description"""
    if not description:
        return "Aucune description fournie."
    return description[:max_length] + ("..." if len(description) > max_length else "")

def get_top_interests(interests: list, limit: int = 5) -> str:
    """Récupère les top intérêts formatés"""
    if not interests:
        return "Intérêts non spécifiés"
    top = interests[:limit]
    result = ", ".join(top)
    if len(interests) > limit:
        result += f" (+{len(interests) - limit} autres)"
    return result

DEFAULT_WEIGHTS = {
    'interests': 0.7,
    'age': 0.3
}

class MatchingSystem(commands.Cog):
    """Système de matching avancé avec double opt-in et suggestions proactives"""

    def __init__(self, bot):
        self.bot = bot
        self.idf_cache = {}  # Cache des poids IDF
        self.config = {
            "double_opt_in": True,
            "notify_on_single_accept": False,  # Legacy option
            "proactive_enabled": False,
            "weights": DEFAULT_WEIGHTS,
            "age_sigma": 4.0,
            "max_suggestions_per_day": 3,
            "proactive_cooldown_hours": 24
        }
        self.matched_users_today = {} # Pour suivre les suggestions quotidiennes

    async def cog_load(self):
        """Initialisation du cog"""
        await self.init_database()
        await self.refresh_idf_cache()
        # Charger la configuration si elle existe (non implémenté ici)

    async def init_database(self):
        """Initialise les tables nécessaires pour le matching avancé"""
        from .utils import db_instance

        # Table profiles existe déjà, ajouter nouvelles colonnes si nécessaire
        try:
            # Ajouter colonne interets_canonical
            await db_instance.connection.execute("ALTER TABLE profiles ADD COLUMN interets_canonical TEXT")
        except:
            pass  # Colonne existe déjà

        try:
            # Ajouter colonne prefs
            await db_instance.connection.execute("ALTER TABLE profiles ADD COLUMN prefs TEXT DEFAULT '{}'")
        except:
            pass

        try:
            # Ajouter colonne activity_score
            await db_instance.connection.execute("ALTER TABLE profiles ADD COLUMN activity_score REAL DEFAULT 1.0")
        except:
            pass

        # Vérifier si la table matches existe avec les bonnes colonnes
        try:
            await db_instance.connection.execute("SELECT requester_id FROM matches LIMIT 1")
        except:
            # Recréer la table avec les bonnes colonnes
            await db_instance.connection.execute("DROP TABLE IF EXISTS matches")
            await db_instance.connection.execute("""
                CREATE TABLE matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    requester_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending_b',
                    nonce TEXT NOT NULL,
                    score REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(requester_id, target_id, nonce)
                )
            """)

        # Table suggestions pour les propositions proactives
        await db_instance.connection.execute("""
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                nonce TEXT NOT NULL,
                score REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table reports pour la modération
        await db_instance.connection.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id TEXT NOT NULL,
                reported_id TEXT NOT NULL,
                reason TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db_instance.connection.commit()

    async def refresh_idf_cache(self):
        """Met à jour le cache des poids IDF"""
        from .utils import db_instance
        self.idf_cache = await compute_idf_weights(db_instance.connection)

    async def is_admin(self, interaction: discord.Interaction) -> bool:
        """Vérifier si l'utilisateur est administrateur"""
        # Propriétaire du bot
        if await self.bot.is_owner(interaction.user):
            return True

        # Vérifier les permissions d'administrateur
        if interaction.guild and interaction.user.guild_permissions.administrator:
            return True

        return False

    @discord.app_commands.command(name="findmatch", description="Trouver une correspondance compatible")
    async def findmatch(self, interaction: discord.Interaction):
        """Commande principale de recherche de correspondance"""
        user_id = str(interaction.user.id)

        try:
            from .utils import db_instance

            # Vérifier que l'utilisateur a un profil
            async with db_instance.connection.execute(
                "SELECT * FROM profiles WHERE user_id = ?", (user_id,)
            ) as cursor:
                user_profile_row = await cursor.fetchone()

            if not user_profile_row:
                await interaction.response.send_message(
                    "❌ Vous devez créer un profil avant de chercher des correspondances.\n"
                    "Utilisez `/createprofile` pour commencer !",
                    ephemeral=True
                )
                return

            # Préparer le profil utilisateur en dictionnaire pour les fonctions utilitaires
            user_profile = {
                'user_id': user_profile_row[0],
                'prenom': user_profile_row[1],
                'pronoms': user_profile_row[2],
                'age': user_profile_row[3] if isinstance(user_profile_row[3], int) else 18,
                'interets': user_profile_row[4] or '[]',
                'interets_canonical': user_profile_row[5] or user_profile_row[4] or '[]',
                'description': user_profile_row[6] or '',
                'avatar_url': user_profile_row[7] or '',
                'vector': user_profile_row[8] or '[]'
            }


            # Répondre immédiatement pour éviter l'expiration
            await interaction.response.send_message(
                "🔍 **Recherche de correspondances en cours...**\n"
                "Je cherche des profils compatibles selon vos critères.",
                ephemeral=True
            )

            # Chercher des correspondances
            candidates = await self.find_candidates(user_profile)

            if not candidates:
                await interaction.followup.send(
                    "😔 **Aucune correspondance trouvée pour le moment.**\n\n"
                    "Essayez de diversifier vos intérêts ou revenez plus tard !\n"
                    "Vous pouvez aussi suggérer un candidat spécifique.",
                    ephemeral=True,
                    view=SuggestCandidateView(self)
                )
                return

            # Envoyer la première suggestion en DM
            best_candidate_data = candidates[0]
            await self.send_match_dm(interaction.user, user_profile, best_candidate_data, candidates[1:])

            await interaction.followup.send(
                f"✅ **Correspondance trouvée !**\n"
                f"Score de compatibilité : {best_candidate_data['score']:.0%}\n"
                "Consultez vos messages privés pour voir les détails. 📩",
                ephemeral=True
            )

        except json.JSONDecodeError as e:
            print(f"❌ Erreur JSON findmatch pour {user_id}: Réponse vide ou invalide")
            await interaction.followup.send(
                "❌ Erreur temporaire du système. Veuillez réessayer dans quelques instants.",
                ephemeral=True
            )
        except Exception as e:
            print(f"❌ Erreur findmatch pour {user_id}: {e}")
            await interaction.followup.send(
                "❌ Une erreur inattendue s'est produite. Veuillez réessayer.",
                ephemeral=True
            )

    async def find_candidates(self, user_profile: Dict) -> List[Dict]:
        """Trouve et classe les candidats compatibles"""
        from .utils import db_instance

        user_age = user_profile.get('age', 18)
        user_id = user_profile.get('user_id')
        candidates = []

        # Récupérer tous les profils potentiels
        async with db_instance.connection.execute(
            "SELECT * FROM profiles WHERE user_id != ?", (user_id,)
        ) as cursor:
            async for profile_row in cursor:
                try:
                    candidate_age = profile_row[3]

                    # Filtres de base
                    if is_minor_major_mix(user_age, candidate_age):
                        continue

                    if abs(user_age - candidate_age) > 8:  # Max 8 ans d'écart
                        continue

                    if not (13 <= candidate_age <= 30):
                        continue

                    # Sécuriser les données avant de créer les dictionnaires
                    def safe_get_column(row, index, default=""):
                        try:
                            val = row[index]
                            if val is None or val == 'null': return default
                            if isinstance(val, str) and not val.strip(): return default
                            return val
                        except (IndexError, TypeError):
                            return default

                    # Préparer le profil candidat en dictionnaire
                    profile_dict = {
                        'user_id': safe_get_column(profile_row, 0, ""),
                        'prenom': safe_get_column(profile_row, 1, "Anonyme"),
                        'pronoms': safe_get_column(profile_row, 2, "iel"),
                        'age': profile_row[3] if isinstance(profile_row[3], int) else 18,
                        'interets': safe_get_column(profile_row, 4, "[]"),
                        'interets_canonical': safe_get_column(profile_row, 5, None) or safe_get_column(profile_row, 4, "[]"),
                        'description': safe_get_column(profile_row, 6, ""),
                        'avatar_url': safe_get_column(profile_row, 7, ""),
                        'vector': safe_get_column(profile_row, 8, "[]")
                    }
                    
                    # Assurer que user_profile est bien un dictionnaire pour compute_match_score
                    if not isinstance(user_profile, dict):
                        print(f"Erreur: user_profile n'est pas un dictionnaire.")
                        continue

                    score = compute_match_score(user_profile, profile_dict, self.idf_cache, self.config["weights"])

                    if score > 0.1:  # Seuil minimum
                        candidates.append({
                            'profile': profile_dict,
                            'score': score
                        })

                except Exception as e:
                    print(f"Erreur traitement candidat {profile_row[0] if profile_row else 'unknown'}: {e}")
                    continue

        # Trier par score décroissant
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:10]  # Top 10

    async def send_match_dm(self, user: discord.User, user_profile: Dict, candidate_data: Dict, queue: List[Dict]):
        """Envoie une suggestion de match anonymisée en DM"""
        try:
            dm_channel = await user.create_dm()
            candidate_profile = candidate_data['profile']

            # Préparer les données anonymisées avec sécurisation JSON
            interests_json = candidate_profile.get('interets_canonical', '[]')
            if not interests_json or interests_json.strip() == '' or interests_json == 'null':
                interests_json = '[]'

            try:
                interests_canonical = json.loads(interests_json)
                if not isinstance(interests_canonical, list):
                    interests_canonical = []
            except (json.JSONDecodeError, TypeError):
                interests_canonical = []

            top_interests = get_top_interests(interests_canonical, 5)
            age_range = format_age_range(candidate_profile.get('age', 18))
            description = truncate_description(candidate_profile.get('description', ''))

            # Créer l'embed anonymisé
            embed = discord.Embed(
                title="💖 Correspondance trouvée !",
                description="Voici une personne qui pourrait vous intéresser :",
                color=discord.Color.pink()
            )

            embed.add_field(
                name="👤 Profil anonyme",
                value=f"**Âge :** {age_range}\n**Pronoms :** {candidate_profile.get('pronoms', 'iel')}",
                inline=True
            )

            embed.add_field(
                name="🎯 Compatibilité",
                value=f"**Score :** {candidate_data['score']:.0%}\n**Algorithme :** IA avancée",
                inline=True
            )

            embed.add_field(
                name="🎨 Intérêts",
                value=top_interests,
                inline=False
            )

            embed.add_field(
                name="💭 Description",
                value=description,
                inline=False
            )

            embed.set_footer(text="💡 Profil anonymisé pour votre sécurité et confidentialité")

            # Générer nonce pour cette interaction
            nonce = generate_nonce()

            # Créer les boutons d'action
            view = MatchActionView(self, candidate_profile['user_id'], nonce, queue)

            await dm_channel.send(embed=embed, view=view)

        except discord.Forbidden:
            print(f"❌ Impossible d'envoyer DM à {user.id}")
            # TODO: Fallback en guild si possible

    async def handle_button_interaction(self, interaction: discord.Interaction, action: str, requester_id: str, candidate_id: str, nonce: str):
        """Gère toutes les interactions via boutons"""
        if action == "accept_match":
            await self.handle_match_accept(interaction, candidate_id, nonce)
        elif action == "next_match":
            # Logique pour passer au candidat suivant (déjà gérée dans la vue)
            pass
        elif action == "match_report":
            await self.handle_report_button(interaction, candidate_id, action)
        elif action == "pending_accept":
            await self.reveal_match(requester_id, str(interaction.user.id), nonce)
            await interaction.response.send_message(
                "🎉 **Match confirmé !** Consultez vos DMs pour les détails complets.",
                ephemeral=True
            )
        elif action == "pending_decline":
            await self.handle_decline_pending(interaction, requester_id, str(interaction.user.id), nonce)
        elif action == "pending_report":
            await self.handle_report_button(interaction, requester_id, action) # Signalement de celui qui a reçu la notification
        elif action == "pro_opt_out":
            # Désactiver les suggestions proactives
            await self.handle_opt_out(interaction, requester_id)
            return

        elif action in ["match_report", "pro_report", "pending_report"]:
            # Gérer le signalement
            await self.handle_report_button(interaction, candidate_id, action)
            return

    async def handle_match_accept(self, interaction: discord.Interaction, candidate_id: str, nonce: str):
        """Gère l'acceptation d'une correspondance"""
        user_id = str(interaction.user.id)

        try:
            from .utils import db_instance

            if self.config["double_opt_in"]:
                # Créer une entrée pending dans matches
                await db_instance.connection.execute("""
                    INSERT INTO matches (requester_id, target_id, status, nonce, created_at)
                    VALUES (?, ?, 'pending_b', ?, ?)
                """, (user_id, candidate_id, nonce, datetime.now().isoformat()))

                await db_instance.connection.commit()

                # Envoyer notification anonyme à la cible
                await self.send_pending_notification(candidate_id, user_id, nonce)

                await interaction.response.send_message(
                    "✅ **Intérêt exprimé !**\n\n"
                    "J'ai envoyé une notification anonyme à cette personne.\n"
                    "Si elle accepte aussi, vous serez mis en contact ! 🤞",
                    ephemeral=True
                )

            else:
                # Mode legacy : notification directe
                await self.reveal_match(user_id, candidate_id, nonce)
                await interaction.response.send_message(
                    "✅ **Match confirmé !** Vérifiez vos DMs pour les détails complets.",
                    ephemeral=True
                )

        except Exception as e:
            print(f"❌ Erreur accept match {user_id}->{candidate_id}: {e}")
            await interaction.response.send_message(
                "❌ Erreur lors du traitement de votre acceptation.",
                ephemeral=True
            )

    async def send_pending_notification(self, target_id: str, requester_id: str, nonce: str):
        """Envoie une notification de double opt-in à la cible"""
        try:
            target_user = await self.bot.fetch_user(int(target_id))
            dm_channel = await target_user.create_dm()

            embed = discord.Embed(
                title="💌 Quelqu'un s'intéresse à vous !",
                description="Une personne correspondant à vos critères souhaite se connecter.",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="🤔 Que faire maintenant ?",
                value="Vous pouvez voir son profil anonymisé et décider si vous souhaitez le rencontrer.",
                inline=False
            )

            view = PendingMatchView(self, requester_id, nonce)
            await dm_channel.send(embed=embed, view=view)

        except discord.Forbidden:
            print(f"❌ Impossible d'envoyer notification pending à {target_id}")
        except Exception as e:
            print(f"❌ Erreur notification pending: {e}")

    async def reveal_match(self, user_a: str, user_b: str, nonce: str):
        """Révèle l'identité des deux utilisateurs après match mutuel"""
        try:
            from .utils import db_instance

            # Récupérer les profils complets
            async with db_instance.connection.execute(
                "SELECT * FROM profiles WHERE user_id IN (?, ?)", (user_a, user_b)
            ) as cursor:
                profiles = await cursor.fetchall()

            if len(profiles) != 2:
                return

            profile_a = next((p for p in profiles if p[0] == user_a), None)
            profile_b = next((p for p in profiles if p[0] == user_b), None)

            if not profile_a or not profile_b:
                return

            # Envoyer révélation à A
            await self.send_reveal_dm(user_a, profile_b, "Votre correspondance a accepté !")

            # Envoyer révélation à B
            await self.send_reveal_dm(user_b, profile_a, "Match confirmé !")

            # Marquer le match comme accepté
            await db_instance.connection.execute("""
                UPDATE matches SET status = 'accepted', updated_at = ?
                WHERE (requester_id = ? AND target_id = ?) OR (requester_id = ? AND target_id = ?)
            """, (datetime.now().isoformat(), user_a, user_b, user_b, user_a))

            await db_instance.connection.commit()

        except Exception as e:
            print(f"❌ Erreur reveal_match: {e}")

    async def send_reveal_dm(self, user_id: str, partner_profile, title: str):
        """Envoie la révélation complète du profil partenaire"""
        try:
            user = await self.bot.fetch_user(int(user_id))
            dm_channel = await user.create_dm()

            embed = discord.Embed(
                title=f"🎉 {title}",
                description="Voici les détails complets de votre correspondance :",
                color=discord.Color.green()
            )

            embed.add_field(
                name="👤 Identité",
                value=f"**Prénom :** {partner_profile[1]}\n"
                      f"**Pronoms :** {partner_profile[2]}\n"
                      f"**Âge :** {partner_profile[3]} ans",
                inline=True
            )

            interests_json = partner_profile[4] or '[]'
            try:
                interests = json.loads(interests_json)
                if not isinstance(interests, list): interests = []
            except (json.JSONDecodeError, TypeError):
                interests = []

            embed.add_field(
                name="🎨 Intérêts",
                value=", ".join(interests[:8]) + ("..." if len(interests) > 8 else ""),
                inline=True
            )

            embed.add_field(
                name="💭 Description complète",
                value=partner_profile[6][:500] + ("..." if len(partner_profile[6]) > 500 else ""),
                inline=False
            )

            if partner_profile[7]:  # avatar_url
                embed.set_thumbnail(url=partner_profile[7])

            embed.add_field(
                name="📞 Contact",
                value=f"Vous pouvez maintenant contacter <@{partner_profile[0]}> directement !",
                inline=False
            )

            embed.set_footer(text="💡 Soyez respectueux et bienveillant dans vos échanges")

            await dm_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erreur send_reveal_dm: {e}")

    @discord.app_commands.command(name="report_profile", description="Signaler un profil inapproprié")
    @discord.app_commands.describe(user_id="ID de l'utilisateur à signaler", reason="Raison du signalement")
    async def report_profile(self, interaction: discord.Interaction, user_id: str, reason: str = None):
        """Permet de signaler un profil inapproprié"""
        reporter_id = str(interaction.user.id)

        if reporter_id == user_id:
            await interaction.response.send_message("❌ Vous ne pouvez pas vous signaler vous-même.", ephemeral=True)
            return

        try:
            from .utils import db_instance

            # Vérifier si l'utilisateur signalé existe dans les profils
            async with db_instance.connection.execute(
                "SELECT user_id FROM profiles WHERE user_id = ?", (user_id,)
            ) as cursor:
                profile_exists = await cursor.fetchone()

            if not profile_exists:
                await interaction.response.send_message(f"❌ Aucun profil trouvé pour cet utilisateur.", ephemeral=True)
                return

            # Créer le signalement
            await db_instance.connection.execute("""
                INSERT INTO reports (reporter_id, reported_id, reason, timestamp)
                VALUES (?, ?, ?, ?)
            """, (reporter_id, user_id, reason or "Aucune raison spécifiée", datetime.now().isoformat()))

            await db_instance.connection.commit()

            await interaction.response.send_message(
                f"✅ **Signalement enregistré**\n\n"
                f"Merci d'avoir signalé ce profil. Les administrateurs examineront votre signalement.",
                ephemeral=True
            )

        except Exception as e:
            print(f"❌ Erreur report_profile: {e}")
            await interaction.response.send_message("❌ Erreur lors du signalement.", ephemeral=True)

    # Nouvelle méthode pour gérer les boutons de signalement
    async def handle_report_button(self, interaction: discord.Interaction, reported_id: str, action: str):
        """Gérer le signalement via bouton"""
        try:
            reporter_id = str(interaction.user.id)

            if reporter_id == reported_id:
                await interaction.response.send_message("❌ Vous ne pouvez pas vous signaler vous-même.", ephemeral=True)
                return

            from .utils import db_instance

            # Créer la table reports si elle n'existe pas (déjà fait dans init_database, mais pour la robustesse)
            await db_instance.connection.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reporter_id TEXT NOT NULL,
                    reported_id TEXT NOT NULL,
                    reason TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Vérifier si ce signalement existe déjà par ce reporter pour ce reported_id
            async with db_instance.connection.execute(
                "SELECT id FROM reports WHERE reporter_id = ? AND reported_id = ?",
                (reporter_id, reported_id)
            ) as cursor:
                existing = await cursor.fetchone()

            if existing:
                await interaction.response.send_message("❌ Vous avez déjà signalé ce profil.", ephemeral=True)
                return

            # Créer le signalement
            reason = f"Signalement via bouton ({action})"
            await db_instance.connection.execute("""
                INSERT INTO reports (reporter_id, reported_id, reason, timestamp)
                VALUES (?, ?, ?, ?)
            """, (reporter_id, reported_id, reason, datetime.now().isoformat()))

            await db_instance.connection.commit()

            # Log du signalement
            print(f"🚨 SIGNALEMENT BOUTON: {reporter_id} a signalé {reported_id} via {action}")

            await interaction.response.send_message(
                f"✅ **Profil signalé**\n\n"
                f"Ce profil a été signalé aux administrateurs.\n"
                f"Merci de contribuer à la sécurité ! 🛡️",
                ephemeral=True
            )

        except Exception as e:
            print(f"❌ Erreur handle_report_button: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite lors du signalement.",
                ephemeral=True
            )

    async def handle_decline_pending(self, interaction: discord.Interaction, requester_id: str, current_user_id: str, nonce: str):
        """Gère le refus d'une notification de correspondance en attente"""
        from .utils import db_instance
        try:
            await db_instance.connection.execute("""
                UPDATE matches SET status = 'rejected', updated_at = ?
                WHERE requester_id = ? AND target_id = ? AND nonce = ?
            """, (datetime.now().isoformat(), requester_id, current_user_id, nonce))
            await db_instance.connection.commit()
            await interaction.response.send_message("❌ Correspondance refusée.", ephemeral=True)
        except Exception as e:
            print(f"❌ Erreur handle_decline_pending: {e}")
            await interaction.response.send_message("❌ Une erreur s'est produite.", ephemeral=True)

    async def handle_opt_out(self, interaction: discord.Interaction, user_id: str):
        """Désactive les suggestions proactives pour un utilisateur"""
        try:
            from .utils import db_instance
            # Ici, il faudrait une colonne 'proactive_enabled' dans la table 'profiles'
            # Supposons que cette colonne existe et est initialement True par défaut
            await db_instance.connection.execute(
                "UPDATE profiles SET proactive_enabled = 0 WHERE user_id = ?", (user_id,)
            )
            await db_instance.connection.commit()
            await interaction.response.send_message(
                "😞 Vous avez désactivé les suggestions proactives. Vous ne recevrez plus de propositions automatiques.",
                ephemeral=True
            )
        except Exception as e:
            print(f"❌ Erreur handle_opt_out: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite.",
                ephemeral=True
            )


class MatchActionView(discord.ui.View):
    """Vue avec boutons pour les actions sur une correspondance"""

    def __init__(self, cog: MatchingSystem, candidate_id: str, nonce: str, queue: List[Dict]):
        super().__init__(timeout=3600)  # 1 heure
        self.cog = cog
        self.candidate_id = candidate_id
        self.nonce = nonce
        self.queue = queue

    @discord.ui.button(label="✅ Accepter", style=discord.ButtonStyle.green, custom_id="match_accept")
    async def accept_match(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_match_accept(interaction, self.candidate_id, self.nonce)
        self.stop()

    @discord.ui.button(label="⏭️ Passer", style=discord.ButtonStyle.secondary, custom_id="next_match")
    async def next_match(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.queue:
            next_candidate = self.queue.pop(0)
            await self.cog.send_match_dm(interaction.user, None, next_candidate, self.queue)
            await interaction.response.send_message("⏭️ Suggestion suivante envoyée !", ephemeral=True)
        else:
            await interaction.response.send_message(
                "😔 Plus de suggestions pour le moment.\nRevenez plus tard !",
                ephemeral=True
            )
        self.stop()

    @discord.ui.button(label="🚨 Signaler", style=discord.ButtonStyle.red, custom_id="match_report")
    async def report_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_report_button(interaction, self.candidate_id, "match_report")
        self.stop()

class PendingMatchView(discord.ui.View):
    """Vue pour les notifications de double opt-in"""

    def __init__(self, cog: MatchingSystem, requester_id: str, nonce: str):
        super().__init__(timeout=86400)  # 24 heures
        self.cog = cog
        self.requester_id = requester_id
        self.nonce = nonce

    @discord.ui.button(label="✅ Accepter", style=discord.ButtonStyle.green, custom_id="pending_accept")
    async def accept_pending(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_button_interaction(interaction, "pending_accept", self.requester_id, str(interaction.user.id), self.nonce)
        self.stop()

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.red, custom_id="pending_decline")
    async def decline_pending(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_button_interaction(interaction, "pending_decline", self.requester_id, str(interaction.user.id), self.nonce)
        self.stop()

    @discord.ui.button(label="🚨 Signaler", style=discord.ButtonStyle.red, custom_id="pending_report")
    async def report_pending(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Le reported_id ici est celui qui reçoit la notification, donc le current_user.id
        await self.cog.handle_report_button(interaction, str(interaction.user.id), "pending_report")
        self.stop()

class SuggestCandidateView(discord.ui.View):
    """Vue pour suggérer un candidat manuel"""

    def __init__(self, cog: MatchingSystem):
        super().__init__(timeout=300)
        self.cog = cog

    @discord.ui.button(label="💡 Suggérer un candidat", style=discord.ButtonStyle.primary, custom_id="suggest_candidate")
    async def suggest_candidate(self, interaction: discord.Interaction, button: discord.ui.Button):
        # TODO: Ouvrir modal pour saisir user_id candidat
        await interaction.response.send_message(
            "💡 Fonctionnalité de suggestion manuelle (à implémenter)",
            ephemeral=True
        )
        self.stop()

async def setup(bot):
    """Setup function pour charger le cog"""
    # Vérifier si le cog MatchingSystem est déjà chargé
    if not any(isinstance(cog, MatchingSystem) for cog in bot.cogs.values()):
        await bot.add_cog(MatchingSystem(bot))
        print("Cog MatchingSystem chargé avec succès.")
    else:
        print("Cog MatchingSystem déjà chargé.")