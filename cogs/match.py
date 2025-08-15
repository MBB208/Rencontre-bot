import discord
from discord.ext import commands
from discord import app_commands
import re
import json
import asyncio
from datetime import datetime, timedelta
from .utils import db_instance

class Match(commands.Cog):
    """Système de matching intelligent avec notifications fonctionnelles"""

    def __init__(self, bot):
        self.bot = bot
        self.matches_cache = {}  # Cache des matches en cours

    def calculate_compatibility(self, profile1, profile2):
        """Calcul de compatibilité avancé entre deux profils"""
        try:
            # Récupération des données
            age1, age2 = profile1[3], profile2[3]
            interests1 = profile1[4].lower() if profile1[4] else ""
            interests2 = profile2[4].lower() if profile2[4] else ""
            description1 = profile1[6].lower() if profile1[6] else ""
            description2 = profile2[6].lower() if profile2[6] else ""

            # 1. Vérification de la compatibilité d'âge
            age_diff = abs(age1 - age2)
            if age_diff > 8:  # Écart maximum de 8 ans
                return 0

            # Séparation mineurs/majeurs stricte
            if (age1 < 18 and age2 >= 18) or (age1 >= 18 and age2 < 18):
                return 0

            # 2. Score d'intérêts (60% du score final)
            interests_score = self.calculate_interests_similarity(interests1, interests2)

            # 3. Score d'âge (25% du score final)
            age_score = max(0, 1 - (age_diff / 8)) * 100

            # 4. Score de description (15% du score final)
            description_score = self.calculate_text_similarity(description1, description2)

            # Score final pondéré
            final_score = (
                interests_score * 0.60 +
                age_score * 0.25 +
                description_score * 0.15
            )

            return min(100, max(0, final_score))

        except Exception as e:
            print(f"Erreur calcul compatibilité: {e}")
            return 0

    def calculate_interests_similarity(self, interests1, interests2):
        """Calcul de similarité d'intérêts avec synonymes"""
        try:
            # Normalisation et extraction des mots-clés
            words1 = set(self.extract_keywords(interests1))
            words2 = set(self.extract_keywords(interests2))

            if not words1 or not words2:
                return 0

            # Calcul de l'intersection directe
            direct_matches = len(words1.intersection(words2))

            # Recherche de synonymes
            synonym_matches = 0
            for word1 in words1:
                for word2 in words2:
                    if self.are_synonyms(word1, word2):
                        synonym_matches += 0.8  # Poids réduit pour les synonymes

            # Score final
            total_matches = direct_matches + synonym_matches
            max_possible = max(len(words1), len(words2))

            return min(100, (total_matches / max_possible) * 100)

        except:
            return 0

    def extract_keywords(self, text):
        """Extraction des mots-clés pertinents"""
        if not text:
            return []

        # Mots vides à ignorer
        stop_words = {
            'le', 'la', 'les', 'de', 'du', 'des', 'et', 'ou', 'un', 'une',
            'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles',
            'mon', 'ma', 'mes', 'ton', 'ta', 'tes', 'son', 'sa', 'ses',
            'dans', 'sur', 'avec', 'pour', 'par', 'sans', 'sous', 'entre'
        }

        # Extraction des mots (lettres uniquement, longueur > 2)
        words = re.findall(r'\b[a-záàâäéèêëíìîïóòôöúùûüýÿç]{3,}\b', text.lower())

        # Filtrage des mots vides
        return [word for word in words if word not in stop_words]

    def are_synonyms(self, word1, word2):
        """Détection de synonymes simples"""
        synonyms = {
            ('musique', 'son', 'audio', 'chanson', 'mélodi'),
            ('sport', 'fitness', 'entrainement', 'exercice'),
            ('lecture', 'livre', 'lire', 'roman'),
            ('voyage', 'vacances', 'tourisme', 'découverte'),
            ('cuisine', 'cuisinier', 'gastronomie', 'recette'),
            ('art', 'dessin', 'peinture', 'création'),
            ('technologie', 'tech', 'informatique', 'ordinateur'),
            ('nature', 'environnement', 'écologie', 'plante'),
            ('cinéma', 'film', 'série', 'télé'),
            ('danse', 'chorégraphie', 'ballet', 'mouvement')
        }

        for synonym_group in synonyms:
            if word1 in synonym_group and word2 in synonym_group:
                return True
        return False

    def calculate_text_similarity(self, text1, text2):
        """Calcul de similarité textuelle simple"""
        try:
            words1 = set(self.extract_keywords(text1))
            words2 = set(self.extract_keywords(text2))

            if not words1 or not words2:
                return 0

            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))

            return (intersection / union) * 100 if union > 0 else 0

        except:
            return 0

    @app_commands.command(name="findmatch", description="Trouver des correspondances compatibles")
    async def findmatch(self, interaction: discord.Interaction):
        """Recherche de correspondances avec l'algorithme d'IA"""

        await interaction.response.defer(ephemeral=True)

        try:
            user_id = str(interaction.user.id)

            # Vérifier si l'utilisateur a un profil
            async with db_instance.connection.execute(
                "SELECT * FROM profiles WHERE user_id = ?", (user_id,)
            ) as cursor:
                user_profile = await cursor.fetchone()

            if not user_profile:
                embed = discord.Embed(
                    title="❌ Aucun Profil Trouvé",
                    description="Vous devez créer un profil avant de chercher des correspondances.\n\nUtilisez `/createprofile` pour commencer !",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Créer la table d'historique si nécessaire
            await db_instance.connection.execute("""
                CREATE TABLE IF NOT EXISTS match_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user1_id TEXT NOT NULL,
                    user2_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Nettoyer l'historique ancien (18 jours)
            cutoff_date = (datetime.now() - timedelta(days=18)).isoformat()
            await db_instance.connection.execute(
                "DELETE FROM match_history WHERE timestamp < ?", (cutoff_date,)
            )
            await db_instance.connection.execute(
                "DELETE FROM matches WHERE created_at < ?", (cutoff_date,)
            )
            await db_instance.connection.commit()

            # Récupérer les utilisateurs déjà vus/contactés
            async with db_instance.connection.execute("""
                SELECT DISTINCT user2_id FROM match_history 
                WHERE user1_id = ? AND action IN ('viewed', 'contacted', 'matched')
                UNION
                SELECT DISTINCT user1_id FROM match_history 
                WHERE user2_id = ? AND action IN ('viewed', 'contacted', 'matched')
            """, (user_id, user_id)) as cursor:
                seen_users = [row[0] for row in await cursor.fetchall()]

            # Récupérer les profils non vus
            seen_users_str = ', '.join(['?'] * len(seen_users)) if seen_users else "''"
            query = f"SELECT * FROM profiles WHERE user_id != ? AND user_id NOT IN ({seen_users_str})"
            params = [user_id] + seen_users
            
            async with db_instance.connection.execute(query, params) as cursor:
                all_profiles = await cursor.fetchall()

            if not all_profiles:
                embed = discord.Embed(
                    title="😔 Aucune Correspondance",
                    description="Il n'y a pas encore d'autres profils dans la base de données.\n\nRevenez plus tard quand d'autres utilisateurs auront rejoint !",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Calculer la compatibilité avec chaque profil
            matches = []
            for profile in all_profiles:
                compatibility = self.calculate_compatibility(user_profile, profile)
                if compatibility >= 60:  # Seuil minimum de 60%
                    matches.append((profile, compatibility))

            # Trier par score de compatibilité
            matches.sort(key=lambda x: x[1], reverse=True)

            if not matches:
                embed = discord.Embed(
                    title="🔍 Aucune Correspondance Trouvée",
                    description=(
                        "Notre algorithme n'a pas trouvé de correspondance suffisamment compatible (60%+).\n\n"
                        "**Conseils pour améliorer vos chances :**\n"
                        "• Enrichissez vos intérêts avec plus de détails\n"
                        "• Utilisez des mots-clés variés\n"
                        "• Attendez que plus d'utilisateurs rejoignent\n\n"
                        "Réessayez dans quelques jours !"
                    ),
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Envoyer la liste des correspondances en DM
            await self.send_matches_dm(interaction.user, user_profile, matches)

            await interaction.followup.send(
                "✅ **Correspondances trouvées !**\nConsultez vos messages privés pour voir les suggestions. 📩",
                ephemeral=True
            )

        except Exception as e:
            print(f"❌ Erreur findmatch: {e}")
            embed = discord.Embed(
                title="❌ Erreur Système",
                description="Une erreur s'est produite lors de la recherche. Veuillez réessayer.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    async def send_matches_dm(self, user, user_profile, matches):
        """Envoyer les correspondances en DM avec boutons fonctionnels"""
        try:
            # Créer le canal DM
            dm_channel = await user.create_dm()

            # Limiter à 5 premiers matches
            top_matches = matches[:5]

            for i, (profile, compatibility) in enumerate(top_matches):
                # Récupérer l'utilisateur Discord pour l'avatar
                try:
                    target_user = await self.bot.fetch_user(int(profile[0]))
                    avatar_url = target_user.avatar.url if target_user.avatar else target_user.default_avatar.url
                except:
                    avatar_url = None

                # Créer l'embed anonymisé
                embed = discord.Embed(
                    title=f"💖 Correspondance #{i + 1}",
                    description=f"**Compatibilité : {compatibility:.1f}%**",
                    color=discord.Color.pink()
                )

                embed.add_field(
                    name="👤 Profil Anonyme",
                    value=f"**Âge :** {profile[3]} ans\n**Pronoms :** {profile[2]}",
                    inline=True
                )

                embed.add_field(
                    name="🎯 Intérêts",
                    value=profile[4][:200] + ("..." if len(profile[4]) > 200 else ""),
                    inline=False
                )

                if len(profile) > 6 and profile[6]:  # Description
                    embed.add_field(
                        name="📝 Description",
                        value=profile[6][:150] + ("..." if len(profile[6]) > 150 else ""),
                        inline=False
                    )

                embed.set_footer(text=f"Match {i + 1}/{len(top_matches)} • Que voulez-vous faire ?")

                if avatar_url:
                    embed.set_thumbnail(url=avatar_url)

                # Boutons d'action
                view = MatchActionView(self, profile[0], user_profile[0])

                # Enregistrer que ce profil a été vu
                await db_instance.connection.execute("""
                    INSERT INTO match_history (user1_id, user2_id, action, timestamp)
                    VALUES (?, ?, 'viewed', ?)
                """, (user_profile[0], profile[0], datetime.now().isoformat()))

                # Envoyer le message avec délai pour éviter le spam
                await dm_channel.send(embed=embed, view=view)
                await asyncio.sleep(1)  # Délai d'1 seconde entre chaque match

        except discord.Forbidden:
            print(f"❌ Impossible d'envoyer DM à {user.id}")
        except Exception as e:
            print(f"❌ Erreur send_matches_dm: {e}")

    async def send_notification(self, target_user_id, requester_profile):
        """Envoie une notification à l'utilisateur ciblé"""
        try:
            target_user = await self.bot.fetch_user(int(target_user_id))
            dm_channel = await target_user.create_dm()

            embed = discord.Embed(
                title="💌 Quelqu'un s'intéresse à vous !",
                description="Une personne souhaite faire votre connaissance.",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="👤 Profil de l'intéressé(e)",
                value=(
                    f"**Prénom :** {requester_profile[1]}\n"
                    f"**Âge :** {requester_profile[3]} ans\n"
                    f"**Pronoms :** {requester_profile[2]}"
                ),
                inline=True
            )

            embed.add_field(
                name="🎯 Intérêts",
                value=requester_profile[4][:200] + ("..." if len(requester_profile[4]) > 200 else ""),
                inline=False
            )

            if len(requester_profile) > 6 and requester_profile[6]:  # Description
                embed.add_field(
                    name="📝 Description",
                    value=requester_profile[6][:150] + ("..." if len(requester_profile[6]) > 150 else ""),
                    inline=False
                )

            embed.set_footer(text="Que voulez-vous faire ?")

            # Boutons pour répondre à la notification
            view = NotificationView(self, requester_profile[0], target_user_id)
            await dm_channel.send(embed=embed, view=view)

            print(f"✅ Notification envoyée à {target_user.name}")

        except discord.Forbidden:
            print(f"❌ DM fermé pour {target_user_id}")
        except Exception as e:
            print(f"❌ Erreur send_notification: {e}")

    async def create_mutual_match(self, user1_id, user2_id):
        """Créer un match mutuel et révéler les identités"""
        try:
            # Récupérer les profils complets
            async with db_instance.connection.execute(
                "SELECT * FROM profiles WHERE user_id IN (?, ?)", (user1_id, user2_id)
            ) as cursor:
                profiles = await cursor.fetchall()

            if len(profiles) != 2:
                return

            profile1 = next((p for p in profiles if p[0] == user1_id), None)
            profile2 = next((p for p in profiles if p[0] == user2_id), None)

            # Envoyer révélation à user1
            await self.send_match_reveal(user1_id, profile2)

            # Envoyer révélation à user2
            await self.send_match_reveal(user2_id, profile1)

            # Enregistrer le match dans la base
            await db_instance.connection.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user1_id TEXT NOT NULL,
                    user2_id TEXT NOT NULL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Créer aussi la table des interactions pour éviter les répétitions
            await db_instance.connection.execute("""
                CREATE TABLE IF NOT EXISTS match_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user1_id TEXT NOT NULL,
                    user2_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db_instance.connection.execute("""
                INSERT INTO matches (user1_id, user2_id, created_at) VALUES (?, ?, ?)
            """, (user1_id, user2_id, datetime.now().isoformat()))

            await db_instance.connection.commit()

        except Exception as e:
            print(f"❌ Erreur create_mutual_match: {e}")

    async def send_match_reveal(self, user_id, partner_profile):
        """Révéler l'identité complète du partenaire"""
        try:
            user = await self.bot.fetch_user(int(user_id))
            partner_user = await self.bot.fetch_user(int(partner_profile[0]))
            dm_channel = await user.create_dm()

            embed = discord.Embed(
                title="🎉 MATCH MUTUEL !",
                description="Vous avez un match ! Voici les détails complets :",
                color=discord.Color.gold()
            )

            embed.add_field(
                name="👤 Votre Match",
                value=(
                    f"**Prénom :** {partner_profile[1]}\n"
                    f"**Âge :** {partner_profile[3]} ans\n"
                    f"**Pronoms :** {partner_profile[2]}\n"
                    f"**Contact :** {partner_user.mention}"
                ),
                inline=False
            )

            embed.add_field(
                name="🎯 Intérêts complets",
                value=partner_profile[4][:400] + ("..." if len(partner_profile[4]) > 400 else ""),
                inline=False
            )

            if len(partner_profile) > 6 and partner_profile[6]:
                embed.add_field(
                    name="📝 Description complète",
                    value=partner_profile[6][:500] + ("..." if len(partner_profile[6]) > 500 else ""),
                    inline=False
                )

            embed.add_field(
                name="💌 Prochaines Étapes",
                value="Vous pouvez maintenant vous contacter directement pour faire connaissance !",
                inline=False
            )

            embed.set_thumbnail(url=partner_user.avatar.url if partner_user.avatar else partner_user.default_avatar.url)
            embed.set_footer(text="Félicitations ! Soyez respectueux dans vos échanges.")

            await dm_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erreur send_match_reveal: {e}")

    @app_commands.command(name="report_profile", description="Signaler un profil inapproprié")
    @app_commands.describe(
        user="Utilisateur à signaler",
        reason="Raison du signalement"
    )
    async def report_profile(self, interaction: discord.Interaction, user: discord.User, reason: str):
        """Signaler un profil"""

        try:
            # Vérifier que l'utilisateur signalé a un profil
            async with db_instance.connection.execute(
                "SELECT * FROM profiles WHERE user_id = ?", (str(user.id),)
            ) as cursor:
                profile = await cursor.fetchone()

            if not profile:
                await interaction.response.send_message(
                    "❌ Cet utilisateur n'a pas de profil à signaler.",
                    ephemeral=True
                )
                return

            # Créer la table de signalements si nécessaire
            await db_instance.connection.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reporter_id TEXT NOT NULL,
                    reported_user_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending'
                )
            """)

            # Enregistrer le signalement
            await db_instance.connection.execute("""
                INSERT INTO reports (reporter_id, reported_user_id, reason)
                VALUES (?, ?, ?)
            """, (str(interaction.user.id), str(user.id), reason))

            await db_instance.connection.commit()

            embed = discord.Embed(
                title="✅ Signalement Enregistré",
                description=(
                    f"Votre signalement contre **{user.display_name}** a été enregistré.\n\n"
                    f"**Raison :** {reason}\n\n"
                    "Notre équipe de modération examinera ce signalement rapidement.\n"
                    "Merci de contribuer à la sécurité de la communauté !"
                ),
                color=discord.Color.green()
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erreur signalement: {e}")
            await interaction.response.send_message(
                "❌ Erreur lors de l'enregistrement du signalement.",
                ephemeral=True
            )


class MatchActionView(discord.ui.View):
    """Boutons d'action pour les correspondances"""

    def __init__(self, cog, target_user_id, requester_user_id):
        super().__init__(timeout=3600)  # 1 heure
        self.cog = cog
        self.target_user_id = target_user_id
        self.requester_user_id = requester_user_id

    @discord.ui.button(label="💖 Smash", style=discord.ButtonStyle.green, emoji="💖")
    async def smash(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Action Smash - Envoie notification à la cible"""
        try:
            # Récupérer le profil du requester
            async with db_instance.connection.execute(
                "SELECT * FROM profiles WHERE user_id = ?", (self.requester_user_id,)
            ) as cursor:
                requester_profile = await cursor.fetchone()

            if not requester_profile:
                await interaction.response.send_message("❌ Erreur : profil non trouvé.", ephemeral=True)
                return

            # Enregistrer l'action dans l'historique
            await db_instance.connection.execute("""
                INSERT INTO match_history (user1_id, user2_id, action, timestamp)
                VALUES (?, ?, 'contacted', ?)
            """, (self.requester_user_id, self.target_user_id, datetime.now().isoformat()))
            await db_instance.connection.commit()

            # Envoyer notification à la cible
            await self.cog.send_notification(self.target_user_id, requester_profile)

            await interaction.response.send_message(
                "✅ **Notification envoyée !**\n"
                "Cette personne a reçu votre profil. Si elle est intéressée aussi, vous serez mis en contact !",
                ephemeral=True
            )

            # Désactiver le bouton
            button.disabled = True
            await interaction.edit_original_response(view=self)

        except Exception as e:
            print(f"❌ Erreur smash: {e}")
            await interaction.response.send_message("❌ Erreur lors de l'envoi.", ephemeral=True)

    @discord.ui.button(label="⏭️ Pass", style=discord.ButtonStyle.gray, emoji="⏭️")
    async def pass_match(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Action Pass"""
        await interaction.response.send_message(
            "⏭️ **Correspondance passée.**\nVous pouvez voir d'autres suggestions ci-dessous.",
            ephemeral=True
        )

        # Désactiver tous les boutons
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

    @discord.ui.button(label="🚨 Signaler", style=discord.ButtonStyle.red, emoji="🚨")
    async def report(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Signaler la correspondance"""
        try:
            # Enregistrer le signalement
            await db_instance.connection.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reporter_id TEXT NOT NULL,
                    reported_user_id TEXT NOT NULL,
                    reason TEXT NOT NULL DEFAULT 'Signalé via match',
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending'
                )
            """)

            await db_instance.connection.execute("""
                INSERT INTO reports (reporter_id, reported_user_id, reason)
                VALUES (?, ?, ?)
            """, (self.requester_user_id, self.target_user_id, "Signalé via correspondance"))

            await db_instance.connection.commit()

            await interaction.response.send_message(
                "✅ **Profil signalé**\nMerci de contribuer à la sécurité ! 🛡️",
                ephemeral=True
            )

            # Désactiver tous les boutons
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)

        except Exception as e:
            print(f"❌ Erreur report: {e}")
            await interaction.response.send_message("❌ Erreur lors du signalement.", ephemeral=True)


class NotificationView(discord.ui.View):
    """Boutons pour répondre aux notifications"""

    def __init__(self, cog, requester_id, target_id):
        super().__init__(timeout=86400)  # 24 heures
        self.cog = cog
        self.requester_id = requester_id
        self.target_id = target_id

    @discord.ui.button(label="💖 Accepter", style=discord.ButtonStyle.green, emoji="💖")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Accepter la correspondance - créer un match mutuel"""
        try:
            await interaction.response.send_message(
                "🎉 **Match créé !**\nVous allez recevoir les détails complets de votre correspondance.",
                ephemeral=True
            )

            # Enregistrer le match mutuel dans l'historique
            await db_instance.connection.execute("""
                INSERT INTO match_history (user1_id, user2_id, action, timestamp)
                VALUES (?, ?, 'matched', ?)
            """, (self.requester_id, self.target_id, datetime.now().isoformat()))
            await db_instance.connection.commit()

            # Créer le match mutuel
            await self.cog.create_mutual_match(self.requester_id, self.target_id)

            # Désactiver tous les boutons
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)

        except Exception as e:
            print(f"❌ Erreur accept: {e}")
            await interaction.followup.send("❌ Erreur lors de la création du match.", ephemeral=True)

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.red, emoji="❌")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refuser la correspondance"""
        await interaction.response.send_message(
            "❌ **Correspondance refusée.**\nLa personne ne sera pas notifiée de votre refus.",
            ephemeral=True
        )

        # Désactiver tous les boutons
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

    @discord.ui.button(label="🚨 Signaler", style=discord.ButtonStyle.red, emoji="🚨")
    async def report(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Signaler la personne qui a envoyé la notification"""
        try:
            await db_instance.connection.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reporter_id TEXT NOT NULL,
                    reported_user_id TEXT NOT NULL,
                    reason TEXT NOT NULL DEFAULT 'Signalé via notification',
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending'
                )
            """)

            await db_instance.connection.execute("""
                INSERT INTO reports (reporter_id, reported_user_id, reason)
                VALUES (?, ?, ?)
            """, (self.target_id, self.requester_id, "Signalé via notification"))

            await db_instance.connection.commit()

            await interaction.response.send_message(
                "✅ **Profil signalé**\nMerci de contribuer à la sécurité ! 🛡️",
                ephemeral=True
            )

            # Désactiver tous les boutons
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)

        except Exception as e:
            print(f"❌ Erreur report: {e}")
            await interaction.response.send_message("❌ Erreur lors du signalement.", ephemeral=True)


async def setup(bot):
    """Fonction obligatoire pour charger le cog"""
    await bot.add_cog(Match(bot))