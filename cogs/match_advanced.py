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

from .utils_match import (
    normalize_tag, canonicalize_interests, compute_idf_weights,
    compute_match_score, generate_nonce, is_minor_major_mix,
    format_age_range, truncate_description, get_top_interests,
    DEFAULT_WEIGHTS
)

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
    
    async def cog_load(self):
        """Initialisation du cog"""
        await self.init_database()
        await self.refresh_idf_cache()
    
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
        
        # Table matches pour le double opt-in
        await db_instance.connection.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_a TEXT NOT NULL,
                user_b TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending_b',
                nonce TEXT NOT NULL,
                score REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_a, user_b, nonce)
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
                reporter TEXT NOT NULL,
                reported TEXT NOT NULL,
                reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db_instance.connection.commit()
    
    async def refresh_idf_cache(self):
        """Met à jour le cache des poids IDF"""
        from .utils import db_instance
        self.idf_cache = await compute_idf_weights(db_instance.connection)
    
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
                user_profile = await cursor.fetchone()
            
            if not user_profile:
                await interaction.response.send_message(
                    "❌ Vous devez créer un profil avant de chercher des correspondances.\n"
                    "Utilisez `/createprofile` pour commencer !",
                    ephemeral=True
                )
                return
            
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
            best_candidate = candidates[0]
            await self.send_match_dm(interaction.user, user_profile, best_candidate, candidates[1:])
            
            await interaction.followup.send(
                f"✅ **Correspondance trouvée !**\n"
                f"Score de compatibilité : {best_candidate['score']:.0%}\n"
                "Consultez vos messages privés pour voir les détails. 📩",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"❌ Erreur findmatch pour {user_id}: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Une erreur s'est produite lors de la recherche.",
                    ephemeral=True
                )
    
    async def find_candidates(self, user_profile) -> List[Dict]:
        """Trouve et classe les candidats compatibles"""
        from .utils import db_instance
        
        user_age = user_profile[3]  # age column
        user_id = user_profile[0]  # user_id column
        candidates = []
        
        # Récupérer tous les profils potentiels
        async with db_instance.connection.execute(
            "SELECT * FROM profiles WHERE user_id != ?", (user_id,)
        ) as cursor:
            async for profile in cursor:
                candidate_age = profile[3]
                
                # Filtres de base
                if is_minor_major_mix(user_age, candidate_age):
                    continue
                
                if abs(user_age - candidate_age) > 8:  # Max 8 ans d'écart
                    continue
                
                if not (13 <= candidate_age <= 30):
                    continue
                
                # Calculer le score de matching
                profile_dict = {
                    'user_id': profile[0],
                    'prenom': profile[1],
                    'pronoms': profile[2],
                    'age': profile[3],
                    'interets': profile[4],
                    'interets_canonical': profile[5] or profile[4],  # Fallback
                    'description': profile[6],
                    'avatar_url': profile[7],
                    'vector': profile[8]
                }
                
                user_dict = {
                    'user_id': user_profile[0],
                    'prenom': user_profile[1],
                    'pronoms': user_profile[2],
                    'age': user_profile[3],
                    'interets': user_profile[4],
                    'interets_canonical': user_profile[5] or user_profile[4],
                    'description': user_profile[6],
                    'avatar_url': user_profile[7],
                    'vector': user_profile[8]
                }
                
                score = compute_match_score(user_dict, profile_dict, self.idf_cache, self.config["weights"])
                
                if score > 0.1:  # Seuil minimum
                    candidates.append({
                        'profile': profile_dict,
                        'score': score
                    })
        
        # Trier par score décroissant
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:10]  # Top 10
    
    async def send_match_dm(self, user: discord.User, user_profile, candidate: Dict, queue: List[Dict]):
        """Envoie une suggestion de match anonymisée en DM"""
        try:
            dm_channel = await user.create_dm()
            candidate_profile = candidate['profile']
            
            # Préparer les données anonymisées
            interests_canonical = json.loads(candidate_profile.get('interets_canonical', '[]'))
            top_interests = get_top_interests(interests_canonical, 5)
            age_range = format_age_range(candidate_profile['age'])
            description = truncate_description(candidate_profile['description'])
            
            # Créer l'embed anonymisé
            embed = discord.Embed(
                title="💖 Correspondance trouvée !",
                description="Voici une personne qui pourrait vous intéresser :",
                color=discord.Color.pink()
            )
            
            embed.add_field(
                name="👤 Profil anonyme",
                value=f"**Âge :** {age_range}\n**Pronoms :** {candidate_profile['pronoms']}",
                inline=True
            )
            
            embed.add_field(
                name="🎯 Compatibilité",
                value=f"**Score :** {candidate['score']:.0%}\n**Algorithme :** IA avancée",
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
    
    # Handlers de boutons
    async def handle_match_accept(self, interaction: discord.Interaction, candidate_id: str, nonce: str):
        """Gère l'acceptation d'une correspondance"""
        user_id = str(interaction.user.id)
        
        try:
            from .utils import db_instance
            
            if self.config["double_opt_in"]:
                # Créer une entrée pending dans matches
                await db_instance.connection.execute("""
                    INSERT INTO matches (user_a, user_b, status, nonce, created_at)
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
            
            profile_a = next(p for p in profiles if p[0] == user_a)
            profile_b = next(p for p in profiles if p[0] == user_b)
            
            # Envoyer révélation à A
            await self.send_reveal_dm(user_a, profile_b, "Votre correspondance a accepté !")
            
            # Envoyer révélation à B  
            await self.send_reveal_dm(user_b, profile_a, "Match confirmé !")
            
            # Marquer le match comme accepté
            await db_instance.connection.execute("""
                UPDATE matches SET status = 'accepted', updated_at = ?
                WHERE (user_a = ? AND user_b = ?) OR (user_a = ? AND user_b = ?)
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
            
            interests = json.loads(partner_profile[4])
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

class MatchActionView(discord.ui.View):
    """Vue avec boutons pour les actions sur une correspondance"""
    
    def __init__(self, cog: MatchingSystem, candidate_id: str, nonce: str, queue: List[Dict]):
        super().__init__(timeout=3600)  # 1 heure
        self.cog = cog
        self.candidate_id = candidate_id
        self.nonce = nonce
        self.queue = queue
    
    @discord.ui.button(label="✅ Accepter", style=discord.ButtonStyle.green)
    async def accept_match(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_match_accept(interaction, self.candidate_id, self.nonce)
        self.stop()
    
    @discord.ui.button(label="👁️ Voir profil", style=discord.ButtonStyle.gray)
    async def view_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
        # TODO: Implémenter vue détaillée du profil anonyme
        await interaction.response.send_message("🔍 Profil détaillé (à implémenter)", ephemeral=True)
    
    @discord.ui.button(label="⏭️ Passer", style=discord.ButtonStyle.secondary)
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
    
    @discord.ui.button(label="🚨 Signaler", style=discord.ButtonStyle.red)
    async def report_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
        # TODO: Implémenter système de rapport
        await interaction.response.send_message("🚨 Profil signalé (à implémenter)", ephemeral=True)
        self.stop()

class PendingMatchView(discord.ui.View):
    """Vue pour les notifications de double opt-in"""
    
    def __init__(self, cog: MatchingSystem, requester_id: str, nonce: str):
        super().__init__(timeout=86400)  # 24 heures
        self.cog = cog
        self.requester_id = requester_id
        self.nonce = nonce
    
    @discord.ui.button(label="👁️ Voir profil", style=discord.ButtonStyle.gray)
    async def view_requester(self, interaction: discord.Interaction, button: discord.ui.Button):
        # TODO: Afficher profil anonyme du requester
        await interaction.response.send_message("🔍 Profil de la personne intéressée", ephemeral=True)
    
    @discord.ui.button(label="✅ Accepter", style=discord.ButtonStyle.green)
    async def accept_pending(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.reveal_match(self.requester_id, str(interaction.user.id), self.nonce)
        await interaction.response.send_message(
            "🎉 **Match confirmé !** Consultez vos DMs pour les détails complets.",
            ephemeral=True
        )
        self.stop()
    
    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.red)
    async def decline_pending(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .utils import db_instance
        await db_instance.connection.execute("""
            UPDATE matches SET status = 'rejected', updated_at = ?
            WHERE user_a = ? AND user_b = ? AND nonce = ?
        """, (datetime.now().isoformat(), self.requester_id, str(interaction.user.id), self.nonce))
        await db_instance.connection.commit()
        
        await interaction.response.send_message("❌ Correspondance refusée.", ephemeral=True)
        self.stop()

class SuggestCandidateView(discord.ui.View):
    """Vue pour suggérer un candidat manuel"""
    
    def __init__(self, cog: MatchingSystem):
        super().__init__(timeout=300)
        self.cog = cog
    
    @discord.ui.button(label="💡 Suggérer un candidat", style=discord.ButtonStyle.primary)
    async def suggest_candidate(self, interaction: discord.Interaction, button: discord.ui.Button):
        # TODO: Ouvrir modal pour saisir user_id candidat
        await interaction.response.send_message(
            "💡 Fonctionnalité de suggestion manuelle (à implémenter)",
            ephemeral=True
        )
        self.stop()

async def setup(bot):
    """Fonction obligatoire pour charger le cog"""
    await bot.add_cog(MatchingSystem(bot))