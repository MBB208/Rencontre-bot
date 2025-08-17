
import discord
from discord.ext import commands, tasks
from discord import app_commands
import re
import json
import asyncio
import math
import logging
from datetime import datetime, timedelta
from .utils import db_instance, logger
from typing import List, Tuple, Optional

class Match(commands.Cog):
    """Système de matching intelligent avec anonymat partiel"""

    def __init__(self, bot):
        self.bot = bot
        self.cleanup_passed_profiles.start()  # Démarrer la tâche de nettoyage

    def cog_unload(self):
        """Arrêter les tâches lors du déchargement du cog"""
        self.cleanup_passed_profiles.cancel()

    @tasks.loop(hours=1)
    async def cleanup_passed_profiles(self):
        """Nettoyer automatiquement les profils passés après 4h"""
        try:
            await self.ensure_db_connection()
            four_hours_ago = (datetime.now() - timedelta(hours=4)).isoformat()

            # Supprimer les profils passés expirés
            async with db_instance.connection.execute(
                "DELETE FROM passed_profiles WHERE passed_at < ?", 
                (four_hours_ago,)
            ) as cursor:
                deleted_count = cursor.rowcount

            await db_instance.connection.commit()

            if deleted_count > 0:
                logger.info(f"🧹 Nettoyage automatique: {deleted_count} profils passés supprimés")

        except Exception as e:
            logger.error(f"❌ Erreur nettoyage automatique: {e}")

    async def ensure_db_connection(self):
        """Assurer que la connexion DB est active"""
        if not await db_instance.is_connected():
            logger.info("🔄 Reconnexion à la base...")
            await db_instance.reconnect()

    async def ensure_tables_exist(self):
        """S'assurer que toutes les tables nécessaires existent"""
        try:
            await self.ensure_db_connection()

            # Table pour les profils passés (historique temporaire 4h)
            await db_instance.connection.execute("""
                CREATE TABLE IF NOT EXISTS passed_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    passed_profile_id TEXT NOT NULL,
                    passed_at TEXT NOT NULL,
                    UNIQUE(user_id, passed_profile_id)
                )
            """)

            # Table pour les likes/intérêts
            await db_instance.connection.execute("""
                CREATE TABLE IF NOT EXISTS profile_likes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    liker_id TEXT NOT NULL,
                    liked_profile_id TEXT NOT NULL,
                    liked_at TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    UNIQUE(liker_id, liked_profile_id)
                )
            """)

            # Table pour les matches
            await db_instance.connection.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user1_id TEXT NOT NULL,
                    user2_id TEXT NOT NULL,
                    status TEXT DEFAULT 'matched',
                    created_at TEXT NOT NULL,
                    UNIQUE(user1_id, user2_id)
                )
            """)

            # Table pour l'historique des matches
            await db_instance.connection.execute("""
                CREATE TABLE IF NOT EXISTS match_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user1_id TEXT NOT NULL,
                    user2_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

            # Table pour les signalements
            await db_instance.connection.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reporter_id TEXT NOT NULL,
                    reported_id TEXT NOT NULL,
                    reason TEXT,
                    timestamp TEXT NOT NULL,
                    status TEXT DEFAULT 'pending'
                )
            """)

            await db_instance.connection.commit()
            logger.info("✅ Tables vérifiées/créées")

        except Exception as e:
            logger.error(f"❌ Erreur création tables: {e}")

    def calculate_compatibility(self, profile1, profile2) -> float:
        """Calcul de compatibilité optimisé"""
        try:
            # Vérification des données de base
            if len(profile1) < 4 or len(profile2) < 4:
                return 0

            age1, age2 = profile1[3], profile2[3]
            interests1 = profile1[4] if profile1[4] else ""
            interests2 = profile2[4] if profile2[4] else ""

            # Protection mineurs/majeurs STRICTE
            if (age1 < 18 and age2 >= 18) or (age1 >= 18 and age2 < 18):
                return 0

            # Écart d'âge maximum
            age_diff = abs(age1 - age2)
            max_age_diff = 12  # Un peu plus large
            if age_diff > max_age_diff:
                return 0

            # Score d'intérêts
            interests_score = self.calculate_interests_similarity(interests1, interests2)

            # Score d'âge (plus on est proche en âge, mieux c'est)
            age_score = max(0, 100 - (age_diff * 8))  # -8 points par année d'écart

            # Score de description si disponible
            desc_score = 0
            if len(profile1) > 6 and len(profile2) > 6:
                desc1 = profile1[6] if profile1[6] else ""
                desc2 = profile2[6] if profile2[6] else ""
                desc_score = self.calculate_description_similarity(desc1, desc2)

            # Score final pondéré
            final_score = (interests_score * 0.6) + (age_score * 0.25) + (desc_score * 0.15)
            return min(100, max(0, final_score))

        except Exception as e:
            logger.error(f"❌ Erreur calcul compatibilité: {e}")
            return 0

    def calculate_interests_similarity(self, interests1: str, interests2: str) -> float:
        """Calcul de similarité d'intérêts optimisé"""
        try:
            if not interests1 or not interests2:
                return 25  # Score de base pour éviter 0

            # Normaliser le format JSON si nécessaire
            interests1 = self.normalize_interests(interests1)
            interests2 = self.normalize_interests(interests2)

            words1 = set(self.extract_keywords(interests1))
            words2 = set(self.extract_keywords(interests2))

            if not words1 or not words2:
                return 25

            # Calculs de similarité
            common_words = words1.intersection(words2)
            total_unique = len(words1.union(words2))

            if total_unique == 0:
                return 25

            # Score Jaccard avec bonus
            similarity = (len(common_words) / total_unique) * 100

            # Bonus pour correspondances multiples
            if len(common_words) >= 3:
                similarity *= 1.4
            elif len(common_words) >= 2:
                similarity *= 1.2

            # Bonus pour synonymes
            synonym_bonus = self.calculate_synonym_bonus(words1, words2)
            similarity += synonym_bonus

            return min(100, max(25, similarity))

        except Exception as e:
            logger.error(f"❌ Erreur calcul similarité intérêts: {e}")
            return 25

    def normalize_interests(self, interests: str) -> str:
        """Normaliser les intérêts depuis JSON vers texte"""
        try:
            if interests.startswith('[') and interests.endswith(']'):
                interests_list = json.loads(interests)
                return ', '.join(interests_list).lower()
            return interests.lower()
        except:
            return interests.lower()

    def calculate_description_similarity(self, desc1: str, desc2: str) -> float:
        """Calcul de similarité entre descriptions"""
        try:
            if not desc1 or not desc2:
                return 0

            words1 = set(self.extract_keywords(desc1))
            words2 = set(self.extract_keywords(desc2))

            if not words1 or not words2:
                return 0

            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))

            if union == 0:
                return 0

            # Score Jaccard avec bonus pour descriptions
            jaccard = intersection / union
            return min(100, jaccard * 100 * 1.3)  # Bonus description

        except:
            return 0

    def calculate_synonym_bonus(self, words1: set, words2: set) -> float:
        """Calcul du bonus pour synonymes"""
        synonym_groups = [
            {'musique', 'son', 'audio', 'chanson', 'concert'},
            {'sport', 'fitness', 'exercice', 'gym', 'musculation'},
            {'lecture', 'livre', 'lire', 'littérature'},
            {'voyage', 'vacances', 'tourisme', 'aventure'},
            {'cuisine', 'cuisinier', 'gastronomie', 'cooking'},
            {'art', 'dessin', 'peinture', 'créatif'},
            {'technologie', 'tech', 'informatique', 'code'},
            {'nature', 'environnement', 'écologie', 'randonnée'},
            {'cinéma', 'film', 'série', 'netflix'},
            {'danse', 'chorégraphie', 'ballet', 'mouvement'},
            {'jeux', 'gaming', 'vidéo', 'game'},
            {'photo', 'photographie', 'image', 'appareil'}
        ]

        bonus = 0
        for group in synonym_groups:
            words1_in_group = words1.intersection(group)
            words2_in_group = words2.intersection(group)

            if words1_in_group and words2_in_group and not words1_in_group.intersection(words2_in_group):
                bonus += 8  # Bonus pour synonymes

        return min(20, bonus)  # Max 20% de bonus

    def extract_keywords(self, text: str) -> List[str]:
        """Extraction optimisée des mots-clés"""
        if not text:
            return []

        # Mots vides étendus
        stop_words = {
            'le', 'la', 'les', 'de', 'du', 'des', 'et', 'ou', 'un', 'une', 
            'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles',
            'mon', 'ma', 'mes', 'ton', 'ta', 'tes', 'son', 'sa', 'ses',
            'ce', 'cette', 'ces', 'dans', 'sur', 'avec', 'pour', 'par',
            'que', 'qui', 'quoi', 'où', 'quand', 'comment', 'pourquoi',
            'très', 'plus', 'moins', 'bien', 'mal', 'beaucoup', 'peu',
            'aussi', 'encore', 'déjà', 'toujours', 'jamais', 'parfois'
        }

        # Extraction avec regex optimisée
        words = re.findall(r'\b[a-záàâäéèêëíìîïóòôöúùûüýÿç]{2,}\b', text.lower())
        keywords = [word for word in words if word not in stop_words and len(word) >= 3]

        return list(set(keywords))  # Supprimer les doublons

    @app_commands.command(name="findmatch", description="Trouver des correspondances compatibles")
    async def findmatch(self, interaction: discord.Interaction):
        """Recherche de correspondances avec système de pass 4h"""
        await interaction.response.defer(ephemeral=True)

        try:
            await self.ensure_tables_exist()
            user_id = str(interaction.user.id)

            # Vérifier si l'utilisateur a un profil
            async with db_instance.connection.execute(
                "SELECT * FROM profiles WHERE user_id = ?", (user_id,)
            ) as cursor:
                user_profile = await cursor.fetchone()

            if not user_profile:
                embed = discord.Embed(
                    title="❌ Aucun Profil",
                    description="Créez votre profil avec `/createprofile` !",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            logger.info(f"🔍 Findmatch: {interaction.user.name} ({user_profile[3]} ans)")

            # Récupérer les utilisateurs exclus (matches existants + profils passés)
            excluded_users = await self.get_excluded_users(user_id)

            # Récupérer les profils disponibles
            available_profiles = await self.get_available_profiles(user_id, excluded_users)

            if not available_profiles:
                embed = discord.Embed(
                    title="😔 Aucune Correspondance",
                    description="Aucun nouveau profil disponible.\n\n💡 Réessayez plus tard ou utilisez `/reset_passes` pour revoir des profils passés.",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Calculer la compatibilité
            matches = []
            for profile in available_profiles:
                try:
                    compatibility = self.calculate_compatibility(user_profile, profile)
                    if compatibility >= 10:  # Seuil minimum
                        matches.append((profile, compatibility))
                except Exception as e:
                    logger.error(f"❌ Erreur calcul pour {profile[0]}: {e}")

            # Trier par compatibilité
            matches.sort(key=lambda x: x[1], reverse=True)

            if not matches:
                embed = discord.Embed(
                    title="🔍 Aucune Correspondance Compatible",
                    description="Aucune correspondance trouvée avec vos critères.\n\n💡 Modifiez vos intérêts avec `/createprofile` pour élargir vos possibilités.",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Prendre les 8 meilleures correspondances
            top_matches = matches[:8]

            # Envoyer les matches en DM
            success = await self.send_matches_dm(interaction.user, user_profile, top_matches)

            if success:
                await interaction.followup.send(
                    f"✅ **{len(top_matches)} correspondances trouvées !**\n\n"
                    f"📩 Consultez vos messages privés.\n"
                    f"🔄 Tapez `/findmatch` à nouveau pour voir d'autres profils.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "⚠️ **Impossible d'envoyer les DM.**\n\n"
                    "Vérifiez que vos messages privés sont ouverts aux membres du serveur.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"❌ Erreur findmatch: {e}")
            await interaction.followup.send(
                "❌ Une erreur s'est produite lors de la recherche.",
                ephemeral=True
            )

    async def get_excluded_users(self, user_id: str) -> List[str]:
        """Récupérer les utilisateurs à exclure (matches + profils passés)"""
        excluded = []

        # Matches existants
        async with db_instance.connection.execute("""
            SELECT DISTINCT user2_id FROM matches WHERE user1_id = ? AND status = 'matched'
            UNION
            SELECT DISTINCT user1_id FROM matches WHERE user2_id = ? AND status = 'matched'
        """, (user_id, user_id)) as cursor:
            matches = await cursor.fetchall()
            excluded.extend([row[0] for row in matches])

        # Profils passés dans les 4 dernières heures
        four_hours_ago = (datetime.now() - timedelta(hours=4)).isoformat()
        async with db_instance.connection.execute(
            "SELECT passed_profile_id FROM passed_profiles WHERE user_id = ? AND passed_at > ?",
            (user_id, four_hours_ago)
        ) as cursor:
            passed = await cursor.fetchall()
            excluded.extend([row[0] for row in passed])

        return excluded

    async def get_available_profiles(self, user_id: str, excluded_users: List[str]) -> List:
        """Récupérer les profils disponibles"""
        if excluded_users:
            placeholders = ', '.join(['?'] * len(excluded_users))
            query = f"""
                SELECT * FROM profiles 
                WHERE user_id != ? AND user_id NOT IN ({placeholders})
                ORDER BY created_at DESC 
                LIMIT 50
            """
            params = [user_id] + excluded_users
        else:
            query = """
                SELECT * FROM profiles 
                WHERE user_id != ? 
                ORDER BY created_at DESC 
                LIMIT 50
            """
            params = [user_id]

        async with db_instance.connection.execute(query, params) as cursor:
            return await cursor.fetchall()

    async def send_matches_dm(self, user: discord.User, user_profile, matches: List[Tuple]) -> bool:
        """Envoyer les correspondances en DM avec anonymat partiel"""
        try:
            dm_channel = await user.create_dm()

            for i, (profile, compatibility) in enumerate(matches):
                try:
                    # Calculer les intérêts communs
                    user_interests = set(self.extract_keywords(user_profile[4] or ""))
                    profile_interests = set(self.extract_keywords(profile[4] or ""))
                    common_interests = user_interests.intersection(profile_interests)

                    embed = discord.Embed(
                        title=f"💖 Correspondance #{i + 1}",
                        description=f"**Compatibilité : {compatibility:.1f}%**",
                        color=self.get_compatibility_color(compatibility)
                    )

                    # Informations révélées (PRÉNOM visible selon vos règles)
                    embed.add_field(
                        name="👤 Profil",
                        value=f"**Prénom :** {profile[1]}\n**Âge :** {profile[3]} ans\n**Pronoms :** {profile[2] or 'Non spécifiés'}",
                        inline=True
                    )

                    # Intérêts communs en premier
                    if common_interests:
                        common_text = ", ".join(list(common_interests)[:4])
                        if len(common_interests) > 4:
                            common_text += f" (+{len(common_interests)-4} autres)"
                        embed.add_field(name="🎯 En Commun", value=common_text, inline=True)

                    # Tous les intérêts
                    if profile[4]:
                        interests = profile[4][:300] + ("..." if len(profile[4]) > 300 else "")
                        embed.add_field(name="💭 Intérêts", value=interests, inline=False)

                    # DESCRIPTION TOUJOURS AFFICHÉE selon vos règles
                    if len(profile) > 6 and profile[6]:
                        description = profile[6][:400] + ("..." if len(profile[6]) > 400 else "")
                        embed.add_field(name="📝 Description", value=description, inline=False)

                    embed.set_footer(text=f"Match {i + 1}/{len(matches)} • Que souhaitez-vous faire ?")

                    # Boutons d'action
                    view = MatchActionView(self, profile[0], user_profile[0])

                    await dm_channel.send(embed=embed, view=view)
                    await asyncio.sleep(1)  # Éviter le spam

                except Exception as e:
                    logger.error(f"⚠️ Erreur envoi match {i+1}: {e}")
                    continue

            return True

        except discord.Forbidden:
            return False
        except Exception as e:
            logger.error(f"❌ Erreur send_matches_dm: {e}")
            return False

    def get_compatibility_color(self, compatibility: float) -> discord.Color:
        """Couleur selon le score de compatibilité"""
        if compatibility >= 80:
            return discord.Color.gold()
        elif compatibility >= 60:
            return discord.Color.green()
        elif compatibility >= 40:
            return discord.Color.blue()
        else:
            return discord.Color.orange()

    async def record_pass(self, user_id: str, passed_profile_id: str):
        """Enregistrer un profil passé"""
        try:
            await db_instance.connection.execute("""
                INSERT OR REPLACE INTO passed_profiles (user_id, passed_profile_id, passed_at)
                VALUES (?, ?, ?)
            """, (user_id, passed_profile_id, datetime.now().isoformat()))

            await db_instance.connection.commit()
            logger.info(f"📝 Profil passé enregistré: {user_id} -> {passed_profile_id}")

        except Exception as e:
            logger.error(f"❌ Erreur record_pass: {e}")

    async def record_like(self, liker_id: str, liked_profile_id: str):
        """Enregistrer un like"""
        try:
            await db_instance.connection.execute("""
                INSERT OR REPLACE INTO profile_likes (liker_id, liked_profile_id, liked_at)
                VALUES (?, ?, ?)
            """, (liker_id, liked_profile_id, datetime.now().isoformat()))

            await db_instance.connection.commit()
            logger.info(f"💖 Like enregistré: {liker_id} -> {liked_profile_id}")

        except Exception as e:
            logger.error(f"❌ Erreur record_like: {e}")

    async def send_notification(self, target_user_id: str, liker_profile, action: str = "like"):
        """Envoyer notification AVEC boutons pour répondre directement"""
        try:
            target_user = await self.bot.fetch_user(int(target_user_id))
            dm_channel = await target_user.create_dm()

            if action == "like":
                title = "💖 Quelqu'un s'intéresse à vous !"
                description = f"**{liker_profile[1]}** a montré de l'intérêt pour votre profil.\n\n💡 Vous pouvez répondre directement avec les boutons ci-dessous !"
                color = discord.Color.green()
            else:  # pass
                title = "👋 Information"
                description = f"**{liker_profile[1]}** a passé votre profil."
                color = discord.Color.orange()

            embed = discord.Embed(
                title=title,
                description=description,
                color=color
            )

            # Informations sur le profil (PRÉNOM visible)
            embed.add_field(
                name="👤 Son Profil",
                value=f"**Prénom :** {liker_profile[1]}\n**Âge :** {liker_profile[3]} ans\n**Pronoms :** {liker_profile[2] or 'Non spécifiés'}",
                inline=True
            )

            if liker_profile[4]:
                interests = liker_profile[4][:200] + ("..." if len(liker_profile[4]) > 200 else "")
                embed.add_field(name="🎯 Intérêts", value=interests, inline=False)

            # DESCRIPTION TOUJOURS AFFICHÉE
            if len(liker_profile) > 6 and liker_profile[6]:
                description_text = liker_profile[6][:300] + ("..." if len(liker_profile[6]) > 300 else "")
                embed.add_field(name="📝 Description", value=description_text, inline=False)

            # Ajouter boutons seulement pour les likes
            if action == "like":
                view = NotificationResponseView(self, liker_profile[0], target_user_id)
                await dm_channel.send(embed=embed, view=view)
            else:
                await dm_channel.send(embed=embed)

            return True

        except Exception as e:
            logger.error(f"❌ Erreur send_notification: {e}")
            return False

    @app_commands.command(name="reset_passes", description="Réinitialiser vos profils passés (permet de les revoir)")
    async def reset_passes(self, interaction: discord.Interaction):
        """Réinitialiser les profils passés"""
        await interaction.response.defer(ephemeral=True)

        try:
            await self.ensure_db_connection()
            user_id = str(interaction.user.id)

            # Compter les profils passés
            async with db_instance.connection.execute(
                "SELECT COUNT(*) FROM passed_profiles WHERE user_id = ?", (user_id,)
            ) as cursor:
                count = (await cursor.fetchone())[0]

            if count == 0:
                embed = discord.Embed(
                    title="📭 Aucun Profil Passé",
                    description="Vous n'avez aucun profil passé à réinitialiser.",
                    color=discord.Color.blue()
                )
            else:
                # Supprimer tous les profils passés
                await db_instance.connection.execute(
                    "DELETE FROM passed_profiles WHERE user_id = ?", (user_id,)
                )
                await db_instance.connection.commit()

                embed = discord.Embed(
                    title="✅ Profils Passés Réinitialisés !",
                    description=f"Vos **{count} profils passés** ont été effacés.\n\n🔄 Vous pouvez maintenant les revoir avec `/findmatch` !",
                    color=discord.Color.green()
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"❌ Erreur reset_passes: {e}")
            await interaction.followup.send(
                "❌ Une erreur s'est produite lors de la réinitialisation.",
                ephemeral=True
            )

    @app_commands.command(name="match_stats", description="Voir vos statistiques de matching")
    async def match_stats(self, interaction: discord.Interaction):
        """Afficher les statistiques de l'utilisateur"""
        await interaction.response.defer(ephemeral=True)

        try:
            await self.ensure_db_connection()
            user_id = str(interaction.user.id)

            # Vérifier le profil
            async with db_instance.connection.execute(
                "SELECT prenom FROM profiles WHERE user_id = ?", (user_id,)
            ) as cursor:
                profile = await cursor.fetchone()

            if not profile:
                await interaction.followup.send("❌ Créez d'abord votre profil avec `/createprofile` !", ephemeral=True)
                return

            # Statistiques
            stats = {}

            # Likes donnés
            async with db_instance.connection.execute(
                "SELECT COUNT(*) FROM profile_likes WHERE liker_id = ?", (user_id,)
            ) as cursor:
                stats['likes_given'] = (await cursor.fetchone())[0]

            # Likes reçus
            async with db_instance.connection.execute(
                "SELECT COUNT(*) FROM profile_likes WHERE liked_profile_id = ?", (user_id,)
            ) as cursor:
                stats['likes_received'] = (await cursor.fetchone())[0]

            # Profils passés
            async with db_instance.connection.execute(
                "SELECT COUNT(*) FROM passed_profiles WHERE user_id = ?", (user_id,)
            ) as cursor:
                stats['profiles_passed'] = (await cursor.fetchone())[0]

            # Matches
            async with db_instance.connection.execute("""
                SELECT COUNT(*) FROM matches 
                WHERE (user1_id = ? OR user2_id = ?) AND status = 'matched'
            """, (user_id, user_id)) as cursor:
                stats['matches'] = (await cursor.fetchone())[0]

            embed = discord.Embed(
                title=f"📊 Statistiques de {profile[0]}",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="💖 Likes",
                value=f"**Donnés :** {stats['likes_given']}\n**Reçus :** {stats['likes_received']}",
                inline=True
            )

            embed.add_field(
                name="⏭️ Profils Passés",
                value=f"{stats['profiles_passed']} (temporaire 4h)",
                inline=True
            )

            embed.add_field(
                name="🎉 Matches",
                value=f"{stats['matches']} connexions réussies",
                inline=True
            )

            if stats['likes_given'] > 0:
                success_rate = (stats['matches'] / stats['likes_given']) * 100
                embed.add_field(
                    name="📈 Taux de Réussite",
                    value=f"{success_rate:.1f}%",
                    inline=True
                )

            embed.set_footer(text="💡 Utilisez /findmatch pour découvrir de nouveaux profils !")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"❌ Erreur match_stats: {e}")
            await interaction.followup.send("❌ Erreur lors de la récupération des statistiques.", ephemeral=True)

    @app_commands.command(name="admin_reports", description="[ADMIN] Voir les signalements en attente")
    @app_commands.default_permissions(administrator=True)
    async def admin_reports(self, interaction: discord.Interaction):
        """Commande admin pour gérer les signalements"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            async with db_instance.connection.execute(
                "SELECT * FROM reports WHERE status IS NULL OR status = 'pending' ORDER BY timestamp DESC LIMIT 10"
            ) as cursor:
                reports = await cursor.fetchall()

            if not reports:
                await interaction.followup.send(
                    "✅ Aucun signalement en attente.", ephemeral=True
                )
                return

            for report in reports:
                try:
                    reporter_user = await interaction.client.fetch_user(int(report[1]))
                    reported_user = await interaction.client.fetch_user(int(report[2]))

                    embed = discord.Embed(
                        title="🚨 Signalement",
                        color=discord.Color.red(),
                        timestamp=datetime.fromisoformat(report[4])
                    )

                    embed.add_field(
                        name="👤 Signalé par",
                        value=f"{reporter_user.mention}\n({reporter_user.name})",
                        inline=True
                    )

                    embed.add_field(
                        name="🎯 Profil signalé",
                        value=f"{reported_user.mention}\n({reported_user.name})",
                        inline=True
                    )

                    embed.add_field(
                        name="📝 Raison",
                        value=report[3] or "Aucune raison spécifiée",
                        inline=False
                    )

                    embed.set_footer(text=f"ID: {report[0]}")

                    view = AdminMatchView({
                        'id': report[0],
                        'reported_id': report[2]
                    })

                    await interaction.followup.send(embed=embed, view=view, ephemeral=True)

                except Exception as e:
                    logger.error(f"❌ Erreur traitement signalement {report[0]}: {e}")
                    continue

        except Exception as e:
            logger.error(f"❌ Erreur admin_reports: {e}")
            await interaction.followup.send(
                "❌ Erreur lors de la récupération des signalements.", ephemeral=True
            )


class MatchActionView(discord.ui.View):
    """Boutons d'action pour les correspondances"""

    def __init__(self, cog, target_user_id: str, requester_user_id: str):
        super().__init__(timeout=3600)  # 1 heure
        self.cog = cog
        self.target_user_id = target_user_id
        self.requester_user_id = requester_user_id

    @discord.ui.button(label="💖 Intéressé(e)", style=discord.ButtonStyle.green)
    async def interested(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Action Intéressé - Enregistrer le like et notifier"""
        try:
            await self.cog.ensure_db_connection()

            # Récupérer le profil du requester
            async with db_instance.connection.execute(
                "SELECT * FROM profiles WHERE user_id = ?", (self.requester_user_id,)
            ) as cursor:
                requester_profile = await cursor.fetchone()

            if not requester_profile:
                await interaction.response.send_message("❌ Erreur : profil non trouvé.", ephemeral=True)
                return

            # Enregistrer le like
            await self.cog.record_like(self.requester_user_id, self.target_user_id)

            # Vérifier si c'est un match mutuel
            async with db_instance.connection.execute(
                "SELECT * FROM profile_likes WHERE liker_id = ? AND liked_profile_id = ?",
                (self.target_user_id, self.requester_user_id)
            ) as cursor:
                mutual_like = await cursor.fetchone()

            if mutual_like:
                # C'est un match mutuel ! Créer la connexion
                await self.create_mutual_match(interaction, requester_profile)
            else:
                # Simple like, envoyer notification sans boutons
                await self.cog.send_notification(self.target_user_id, requester_profile, "like")

                await interaction.response.send_message(
                    "✅ **Intérêt envoyé !**\n\n"
                    "Cette personne a été notifiée de votre intérêt.\n"
                    "Si elle s'intéresse aussi à vous, vous serez mis en contact ! 💕",
                    ephemeral=True
                )

            # Désactiver les boutons
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)

        except Exception as e:
            logger.error(f"❌ Erreur interested: {e}")
            await interaction.response.send_message("❌ Erreur lors de l'envoi de l'intérêt.", ephemeral=True)

    async def create_mutual_match(self, interaction: discord.Interaction, requester_profile):
        """Créer un match mutuel et révéler les identités"""
        try:
            # Récupérer le profil target
            async with db_instance.connection.execute(
                "SELECT * FROM profiles WHERE user_id = ?", (self.target_user_id,)
            ) as cursor:
                target_profile = await cursor.fetchone()

            if not target_profile:
                await interaction.response.send_message("❌ Erreur : profil target non trouvé.", ephemeral=True)
                return

            # Créer le match en base
            timestamp = datetime.now().isoformat()
            await db_instance.connection.execute("""
                INSERT INTO matches (user1_id, user2_id, status, created_at)
                VALUES (?, ?, 'matched', ?)
            """, (self.requester_user_id, self.target_user_id, timestamp))

            # Enregistrer dans l'historique
            await db_instance.connection.execute("""
                INSERT INTO match_history (user1_id, user2_id, action, timestamp)
                VALUES (?, ?, 'matched', ?)
            """, (self.requester_user_id, self.target_user_id, timestamp))

            await db_instance.connection.execute("""
                INSERT INTO match_history (user1_id, user2_id, action, timestamp)
                VALUES (?, ?, 'matched', ?)
            """, (self.target_user_id, self.requester_user_id, timestamp))

            await db_instance.connection.commit()

            # Récupérer les utilisateurs Discord
            requester_user = await self.cog.bot.fetch_user(int(self.requester_user_id))
            target_user = await self.cog.bot.fetch_user(int(self.target_user_id))

            # Désactiver les boutons AVANT de répondre
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)

            # Notifier le requester (celui qui vient de cliquer)
            await interaction.response.send_message(
                f"🎉 **C'est un Match !**\n\n"
                f"**{target_profile[1]}** s'intéresse aussi à vous !\n\n"
                f"🆔 **Identité révélée :**\n"
                f"**Discord :** {target_user.mention}\n"
                f"**Prénom :** {target_profile[1]}\n\n"
                f"💕 Vous pouvez maintenant vous contacter directement !",
                ephemeral=True
            )

            # Notifier le target user
            try:
                target_dm = await target_user.create_dm()
                embed = discord.Embed(
                    title="🎉 C'est un Match !",
                    description=f"**{requester_profile[1]}** et vous vous intéressez mutuellement !",
                    color=discord.Color.gold()
                )

                embed.add_field(
                    name="🆔 Identité révélée",
                    value=f"**Discord :** {requester_user.mention}\n**Prénom :** {requester_profile[1]}",
                    inline=False
                )

                embed.add_field(
                    name="💕 Félicitations !",
                    value="Vous pouvez maintenant vous contacter directement !",
                    inline=False
                )

                await target_dm.send(embed=embed)

            except Exception as e:
                logger.error(f"❌ Erreur notification target: {e}")

            logger.info(f"🎉 Match créé: {requester_profile[1]} ↔ {target_profile[1]}")

        except Exception as e:
            logger.error(f"❌ Erreur create_mutual_match: {e}")
            await interaction.response.send_message("❌ Erreur lors de la création du match.", ephemeral=True)

    @discord.ui.button(label="⏭️ Passer", style=discord.ButtonStyle.gray)
    async def pass_match(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Passer cette correspondance - stockage temporaire 4h"""
        try:
            await self.cog.ensure_db_connection()

            # Enregistrer le pass (temporaire 4h)
            await self.cog.record_pass(self.requester_user_id, self.target_user_id)

            # Récupérer le profil pour notification
            async with db_instance.connection.execute(
                "SELECT * FROM profiles WHERE user_id = ?", (self.requester_user_id,)
            ) as cursor:
                requester_profile = await cursor.fetchone()

            # Notifier la personne passée (optionnel, selon vos préférences)
            if requester_profile:
                await self.cog.send_notification(self.target_user_id, requester_profile, "pass")

            await interaction.response.send_message(
                "⏭️ **Correspondance passée**\n\n"
                "Cette personne ne vous sera pas reproposée pendant 4 heures.\n"
                "Utilisez `/reset_passes` pour revoir tous les profils passés.",
                ephemeral=True
            )

            # Désactiver les boutons
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)

        except Exception as e:
            logger.error(f"❌ Erreur pass_match: {e}")
            await interaction.response.send_message("❌ Erreur lors du passage.", ephemeral=True)

    @discord.ui.button(label="🚨 Signaler", style=discord.ButtonStyle.red)
    async def report(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Signaler ce profil"""
        try:
            await self.cog.ensure_db_connection()

            # Enregistrer le signalement
            await db_instance.connection.execute("""
                INSERT INTO reports (reporter_id, reported_id, reason, timestamp)
                VALUES (?, ?, ?, ?)
            """, (
                self.requester_user_id,
                self.target_user_id,
                "Signalé via correspondance",
                datetime.now().isoformat()
            ))

            await db_instance.connection.commit()

            # Aussi enregistrer comme passé pour ne plus le voir
            await self.cog.record_pass(self.requester_user_id, self.target_user_id)

            await interaction.response.send_message(
                "✅ **Profil signalé**\n\n"
                "Merci pour votre signalement ! 🛡️\n"
                "Les modérateurs examineront ce profil.\n\n"
                "Ce profil ne vous sera plus proposé.",
                ephemeral=True
            )

            # Désactiver les boutons
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)

        except Exception as e:
            logger.error(f"❌ Erreur report: {e}")
            await interaction.response.send_message("❌ Erreur lors du signalement.", ephemeral=True)


class NotificationResponseView(discord.ui.View):
    """Boutons de réponse dans les notifications de match"""

    def __init__(self, cog, liker_user_id: str, target_user_id: str):
        super().__init__(timeout=3600)  # 1 heure
        self.cog = cog
        self.liker_user_id = liker_user_id
        self.target_user_id = target_user_id

    @discord.ui.button(label="💖 Intéressé(e) aussi", style=discord.ButtonStyle.green)
    async def accept_interest(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Accepter l'intérêt - Créer un match mutuel"""
        try:
            await self.cog.ensure_db_connection()

            # Récupérer les profils
            async with db_instance.connection.execute(
                "SELECT * FROM profiles WHERE user_id = ?", (self.target_user_id,)
            ) as cursor:
                target_profile = await cursor.fetchone()

            async with db_instance.connection.execute(
                "SELECT * FROM profiles WHERE user_id = ?", (self.liker_user_id,)
            ) as cursor:
                liker_profile = await cursor.fetchone()

            if not target_profile or not liker_profile:
                await interaction.response.send_message("❌ Erreur : profils non trouvés.", ephemeral=True)
                return

            # Enregistrer le like retour
            await self.cog.record_like(self.target_user_id, self.liker_user_id)

            # Créer le match mutuel
            timestamp = datetime.now().isoformat()
            await db_instance.connection.execute("""
                INSERT INTO matches (user1_id, user2_id, status, created_at)
                VALUES (?, ?, 'matched', ?)
            """, (self.liker_user_id, self.target_user_id, timestamp))

            await db_instance.connection.commit()

            # Récupérer les utilisateurs Discord
            liker_user = await self.cog.bot.fetch_user(int(self.liker_user_id))
            target_user = await self.cog.bot.fetch_user(int(self.target_user_id))

            # Répondre à celui qui vient d'accepter
            await interaction.response.send_message(
                f"🎉 **C'est un Match !**\n\n"
                f"**{liker_profile[1]}** et vous vous intéressez mutuellement !\n\n"
                f"🆔 **Identité révélée :**\n"
                f"**Discord :** {liker_user.mention}\n"
                f"**Prénom :** {liker_profile[1]}\n\n"
                f"💕 Vous pouvez maintenant vous contacter directement !",
                ephemeral=True
            )

            # Notifier l'autre personne
            try:
                liker_dm = await liker_user.create_dm()
                embed = discord.Embed(
                    title="🎉 C'est un Match !",
                    description=f"**{target_profile[1]}** s'intéresse aussi à vous !",
                    color=discord.Color.gold()
                )

                embed.add_field(
                    name="🆔 Identité révélée",
                    value=f"**Discord :** {target_user.mention}\n**Prénom :** {target_profile[1]}",
                    inline=False
                )

                embed.add_field(
                    name="💕 Félicitations !",
                    value="Vous pouvez maintenant vous contacter directement !",
                    inline=False
                )

                await liker_dm.send(embed=embed)

            except Exception as e:
                logger.error(f"❌ Erreur notification liker: {e}")

            # Désactiver les boutons
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)

            logger.info(f"🎉 Match créé via notification: {liker_profile[1]} ↔ {target_profile[1]}")

        except Exception as e:
            logger.error(f"❌ Erreur accept_interest: {e}")
            await interaction.response.send_message("❌ Erreur lors de l'acceptation.", ephemeral=True)

    @discord.ui.button(label="❌ Pas intéressé(e)", style=discord.ButtonStyle.red)
    async def decline_interest(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refuser l'intérêt"""
        try:
            await interaction.response.send_message(
                "👋 **Réponse envoyée**\n\n"
                "Vous avez poliment décliné cette correspondance.\n"
                "L'autre personne ne sera pas notifiée du refus.",
                ephemeral=True
            )

            # Désactiver les boutons
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)

        except Exception as e:
            logger.error(f"❌ Erreur decline_interest: {e}")
            await interaction.response.send_message("❌ Erreur lors du refus.", ephemeral=True)

    @discord.ui.button(label="🚨 Signaler", style=discord.ButtonStyle.gray)
    async def report_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Signaler l'utilisateur"""
        try:
            await self.cog.ensure_db_connection()

            # Enregistrer le signalement
            await db_instance.connection.execute("""
                INSERT INTO reports (reporter_id, reported_id, reason, timestamp)
                VALUES (?, ?, ?, ?)
            """, (
                self.target_user_id,
                self.liker_user_id,
                "Signalé via notification",
                datetime.now().isoformat()
            ))

            await db_instance.connection.commit()

            await interaction.response.send_message(
                "✅ **Profil signalé**\n\n"
                "Merci pour votre signalement ! 🛡️\n"
                "Les modérateurs examineront ce profil.",
                ephemeral=True
            )

            # Désactiver les boutons
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)

        except Exception as e:
            logger.error(f"❌ Erreur report_user: {e}")
            await interaction.response.send_message("❌ Erreur lors du signalement.", ephemeral=True)


class AdminMatchView(discord.ui.View):
    """Vue admin pour gérer les signalements"""

    def __init__(self, report_data):
        super().__init__(timeout=300)  # 5 minutes
        self.report_data = report_data

    @discord.ui.button(label="✅ Traité", style=discord.ButtonStyle.green)
    async def mark_resolved(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Marquer le signalement comme traité"""
        try:
            await db_instance.connection.execute(
                "UPDATE reports SET status = 'resolved' WHERE id = ?",
                (self.report_data['id'],)
            )
            await db_instance.connection.commit()

            await interaction.response.send_message("✅ Signalement marqué comme traité.", ephemeral=True)

            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)

        except Exception as e:
            logger.error(f"❌ Erreur mark_resolved: {e}")
            await interaction.response.send_message("❌ Erreur lors de la mise à jour.", ephemeral=True)

    @discord.ui.button(label="🚫 Bannir Profil", style=discord.ButtonStyle.red)
    async def ban_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Bannir le profil signalé"""
        try:
            # Supprimer le profil
            await db_instance.connection.execute(
                "DELETE FROM profiles WHERE user_id = ?",
                (self.report_data['reported_id'],)
            )

            # Marquer le signalement comme traité
            await db_instance.connection.execute(
                "UPDATE reports SET status = 'banned' WHERE id = ?",
                (self.report_data['id'],)
            )

            await db_instance.connection.commit()

            await interaction.response.send_message(
                f"🚫 Profil banni et supprimé.\nUtilisateur: {self.report_data['reported_id']}", 
                ephemeral=True
            )

            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)

        except Exception as e:
            logger.error(f"❌ Erreur ban_profile: {e}")
            await interaction.response.send_message("❌ Erreur lors du bannissement.", ephemeral=True)


async def setup(bot):
    """Fonction de setup du cog"""
    await bot.add_cog(Match(bot))
