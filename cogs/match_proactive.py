"""
Système de suggestions proactives automatiques
Envoie des suggestions de matching automatiquement selon la configuration
"""
import discord
from discord.ext import commands, tasks
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import aiosqlite

from .utils_match import (
    compute_match_score, generate_nonce, is_minor_major_mix,
    format_age_range, truncate_description, get_top_interests
)

class ProactiveMatching(commands.Cog):
    """Système de suggestions proactives automatiques"""


class MatchProactive(commands.Cog):
    """Système de suggestions proactives automatiques"""
    
    def __init__(self, bot):
        self.bot = bot
        self.proactive_task = None
        self.config = {
            "enabled": False,
            "interval_minutes": 60,
            "max_daily_suggestions": 3,
            "cooldown_hours": 24,
            "min_activity_score": 0.5
        }
    
    async def is_admin(self, interaction: discord.Interaction) -> bool:
        """Vérifier si l'utilisateur est administrateur"""
        # Propriétaire du bot
        if await self.bot.is_owner(interaction.user):
            return True
        
        # Vérifier les permissions d'administrateur
        if interaction.guild and interaction.user.guild_permissions.administrator:
            return True
            
        return False
    
    @discord.app_commands.command(name="config_proactive", description="[ADMIN] Configurer le système de suggestions automatiques")
    @discord.app_commands.describe(
        enabled="Activer/désactiver le système proactif",
        interval="Intervalle en minutes entre les cycles (défaut: 60)",
        max_daily="Nombre max de suggestions par utilisateur par jour (défaut: 3)"
    )
    async def config_proactive(
        self,
        interaction: discord.Interaction,
        enabled: bool = None,
        interval: int = None,
        max_daily: int = None
    ):
        """Configurer le système de suggestions proactives (admin uniquement)"""
        
        # Vérification STRICTE des permissions d'administration
        if not await self.is_admin(interaction):
            await interaction.response.send_message(
                "❌ Cette commande est réservée aux administrateurs du serveur uniquement.",
                ephemeral=True
            )
            return
        
        try:
            # Mettre à jour la configuration si des paramètres sont fournis
            if enabled is not None:
                self.config["enabled"] = enabled
                if enabled:
                    await self.start_proactive_task()
                else:
                    await self.stop_proactive_task()
            
            if interval is not None:
                if interval < 1 or interval > 1440:  # Entre 1 minute et 24h
                    await interaction.response.send_message(
                        "❌ L'intervalle doit être entre 1 et 1440 minutes.",
                        ephemeral=True
                    )
                    return
                self.config["interval_minutes"] = interval
            
            if max_daily is not None:
                if max_daily < 1 or max_daily > 10:
                    await interaction.response.send_message(
                        "❌ Le nombre max de suggestions doit être entre 1 et 10.",
                        ephemeral=True
                    )
                    return
                self.config["max_daily_suggestions"] = max_daily
            
            # Afficher la configuration actuelle
            embed = discord.Embed(
                title="⚙️ Configuration du Système Proactif",
                color=discord.Color.blue()
            )
            
            status_icon = "🟢" if self.config["enabled"] else "🔴"
            embed.add_field(
                name="État",
                value=f"{status_icon} {'Activé' if self.config['enabled'] else 'Désactivé'}",
                inline=True
            )
            
            embed.add_field(
                name="Intervalle",
                value=f"{self.config['interval_minutes']} minutes",
                inline=True
            )
            
            embed.add_field(
                name="Max quotidien",
                value=f"{self.config['max_daily_suggestions']} suggestions/utilisateur",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            print(f"🔧 ADMIN CONFIG: {interaction.user.id} a modifié la config proactive")
            
        except Exception as e:
            print(f"❌ Erreur config_proactive: {e}")
            await interaction.response.send_message(
                "❌ Erreur lors de la configuration.",
                ephemeral=True
            )
    
    async def start_proactive_task(self):
        """Démarrer la tâche proactive"""
        if self.proactive_task and not self.proactive_task.done():
            self.proactive_task.cancel()
        
        self.proactive_task = asyncio.create_task(self.proactive_loop())
        print(f"🚀 Système proactif démarré (intervalle: {self.config['interval_minutes']} min)")
    
    async def stop_proactive_task(self):
        """Arrêter la tâche proactive"""
        if self.proactive_task and not self.proactive_task.done():
            self.proactive_task.cancel()
            print("⏹️ Système proactif arrêté")
    
    async def proactive_loop(self):
        """Boucle principale du système proactif"""
        while self.config["enabled"]:
            try:
                await self.send_proactive_suggestions()
                await asyncio.sleep(self.config["interval_minutes"] * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Erreur dans la boucle proactive: {e}")
                await asyncio.sleep(300)  # Attendre 5 minutes en cas d'erreur
    
    async def send_proactive_suggestions(self):
        """Envoyer des suggestions proactives aux utilisateurs éligibles"""
        # Implémentation à venir
        print("📤 Envoi de suggestions proactives...")

async def setup(bot):
    """Fonction obligatoire pour charger le cog"""
    await bot.add_cog(MatchProactive(bot))


    def __init__(self, bot):
        self.bot = bot
        self.config = {
            "enabled": False,
            "interval_minutes": 60,  # Vérification toutes les heures
            "cooldown_hours": 24,    # 24h entre suggestions pour un utilisateur
            "max_per_user_per_day": 3,
            "min_activity_score": 0.5
        }
        self.idf_cache = {}

    async def cog_load(self):
        """Démarrage du système proactif"""
        # Le loop sera démarré manuellement via commande admin
        pass

    def start_proactive_loop(self):
        """Démarre la boucle de suggestions proactives"""
        if not self.proactive_loop.is_running() and self.config["enabled"]:
            self.proactive_loop.start()

    def stop_proactive_loop(self):
        """Arrête la boucle de suggestions proactives"""
        if self.proactive_loop.is_running():
            self.proactive_loop.cancel()

    @tasks.loop(minutes=60)  # Par défaut, sera ajusté par config
    async def proactive_loop(self):
        """Boucle principale des suggestions proactives"""
        if not self.config["enabled"]:
            return

        try:
            print("🔄 Démarrage cycle suggestions proactives")
            eligible_users = await self.get_eligible_users()

            for user_id in eligible_users:
                try:
                    await self.send_proactive_suggestion(user_id)
                    await asyncio.sleep(2)  # Éviter le rate limit
                except Exception as e:
                    print(f"❌ Erreur suggestion proactive pour {user_id}: {e}")

            print(f"✅ Cycle terminé: {len(eligible_users)} suggestions envoyées")

        except json.JSONDecodeError as e:
            print(f"❌ Erreur JSON lors des suggestions proactives: Réponse vide ou invalide")
        except Exception as e:
            print(f"❌ Erreur boucle proactive: {e}")

    @proactive_loop.before_loop
    async def before_proactive_loop(self):
        """Attendre que le bot soit prêt"""
        await self.bot.wait_until_ready()

    async def get_eligible_users(self) -> List[str]:
        """Trouve les utilisateurs éligibles pour des suggestions proactives"""
        from .utils import db_instance
        eligible = []

        try:
            # Récupérer les utilisateurs avec profils complets
            async with db_instance.connection.execute("""
                SELECT user_id, prefs, activity_score, created_at 
                FROM profiles 
                WHERE activity_score >= ?
            """, (self.config["min_activity_score"],)) as cursor:

                async for row in cursor:
                    user_id, prefs_json, activity_score, created_at = row

                    # Parser les préférences
                    try:
                        prefs = json.loads(prefs_json or '{}')
                    except:
                        prefs = {}

                    # Vérifier opt-out
                    if prefs.get('opt_out_proactive', False):
                        continue

                    # Vérifier cooldown
                    if await self.user_in_cooldown(user_id):
                        continue

                    # Vérifier limite quotidienne
                    if await self.user_exceeded_daily_limit(user_id):
                        continue

                    eligible.append(user_id)

            return eligible[:50]  # Limiter pour éviter la surcharge

        except Exception as e:
            print(f"❌ Erreur get_eligible_users: {e}")
            return []

    async def user_in_cooldown(self, user_id: str) -> bool:
        """Vérifie si l'utilisateur est en cooldown"""
        from .utils import db_instance

        cooldown_time = datetime.now() - timedelta(hours=self.config["cooldown_hours"])

        async with db_instance.connection.execute("""
            SELECT COUNT(*) FROM suggestions 
            WHERE user_id = ? AND created_at > ?
        """, (user_id, cooldown_time.isoformat())) as cursor:
            count = (await cursor.fetchone())[0]

        return count > 0

    async def user_exceeded_daily_limit(self, user_id: str) -> bool:
        """Vérifie si l'utilisateur a dépassé sa limite quotidienne"""
        from .utils import db_instance

        day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        async with db_instance.connection.execute("""
            SELECT COUNT(*) FROM suggestions 
            WHERE user_id = ? AND created_at > ?
        """, (user_id, day_start.isoformat())) as cursor:
            count = (await cursor.fetchone())[0]

        return count >= self.config["max_per_user_per_day"]

    async def send_proactive_suggestion(self, user_id: str):
        """Envoie une suggestion proactive à un utilisateur"""
        from .utils import db_instance

        try:
            # Récupérer le profil utilisateur
            async with db_instance.connection.execute(
                "SELECT * FROM profiles WHERE user_id = ?", (user_id,)
            ) as cursor:
                user_profile = await cursor.fetchone()

            if not user_profile:
                return

            # Trouver des candidats (utiliser la même logique que match_advanced)
            candidates = await self.find_candidates_for_user(user_profile)

            if not candidates:
                return

            best_candidate = candidates[0]

            # Récupérer l'utilisateur Discord
            try:
                user = await self.bot.fetch_user(int(user_id))
            except:
                return

            # Générer nonce et enregistrer suggestion
            nonce = generate_nonce()
            await db_instance.connection.execute("""
                INSERT INTO suggestions (user_id, candidate_id, status, nonce, score)
                VALUES (?, ?, 'pending', ?, ?)
            """, (user_id, best_candidate['profile']['user_id'], nonce, best_candidate['score']))

            await db_instance.connection.commit()

            # Envoyer DM proactif
            await self.send_proactive_dm(user, best_candidate, nonce)

        except Exception as e:
            print(f"❌ Erreur send_proactive_suggestion: {e}")

    async def find_candidates_for_user(self, user_profile) -> List[Dict]:
        """Trouve les candidats pour un utilisateur (même logique que match_advanced)"""
        from .utils import db_instance
        from .match_advanced import MatchingSystem

        # Récupérer une instance du système de matching
        matching_cog = self.bot.get_cog('MatchingSystem')
        if matching_cog:
            return await matching_cog.find_candidates(user_profile)

        return []  # Fallback vide si cog non trouvé

    async def send_proactive_dm(self, user: discord.User, candidate: Dict, nonce: str):
        """Envoie un DM de suggestion proactive"""
        try:
            dm_channel = await user.create_dm()
            candidate_profile = candidate['profile']

            # Préparer embed proactif
            embed = discord.Embed(
                title="💌 Suggestion automatique !",
                description="J'ai trouvé quelqu'un qui pourrait vous intéresser :",
                color=discord.Color.purple()
            )

            interests_canonical = json.loads(candidate_profile.get('interets_canonical', '[]'))
            top_interests = get_top_interests(interests_canonical, 4)
            age_range = format_age_range(candidate_profile['age'])
            description = truncate_description(candidate_profile['description'], 120)

            embed.add_field(
                name="👤 Aperçu",
                value=f"**Âge :** {age_range}\n**Score :** {candidate['score']:.0%}",
                inline=True
            )

            embed.add_field(
                name="🎨 Intérêts",
                value=top_interests,
                inline=True
            )

            embed.add_field(
                name="💭 Bio",
                value=description,
                inline=False
            )

            embed.set_footer(text="💡 Suggestion automatique • Profil anonymisé")

            # Boutons proactifs
            view = ProactiveActionView(self, candidate_profile['user_id'], nonce)

            await dm_channel.send(embed=embed, view=view)

        except discord.Forbidden:
            print(f"❌ DM fermé pour suggestion proactive: {user.id}")
        except Exception as e:
            print(f"❌ Erreur send_proactive_dm: {e}")

    async def handle_proactive_accept(self, interaction: discord.Interaction, candidate_id: str, nonce: str):
        """Gère l'acceptation d'une suggestion proactive"""
        # Même logique que match_accept dans match_advanced
        matching_cog = self.bot.get_cog('MatchingSystem')
        if matching_cog:
            await matching_cog.handle_match_accept(interaction, candidate_id, nonce)
        else:
            await interaction.response.send_message(
                "❌ Service de matching temporairement indisponible.",
                ephemeral=True
            )

    # Commandes admin pour contrôler le système proactif
    @discord.app_commands.command(name="config_proactive", description="[ADMIN] Configurer le système proactif")
    @discord.app_commands.describe(
        enabled="Activer/désactiver les suggestions proactives",
        interval="Intervalle en minutes entre les cycles",
        max_daily="Maximum de suggestions par utilisateur par jour"
    )
    async def config_proactive(
        self, 
        interaction: discord.Interaction,
        enabled: Optional[bool] = None,
        interval: Optional[int] = None,
        max_daily: Optional[int] = None
    ):
        """Configure le système de suggestions proactives"""

        # Vérifier permissions admin (simple vérification)
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Seuls les administrateurs peuvent configurer le système proactif.",
                ephemeral=True
            )
            return

        changes = []

        if enabled is not None:
            old_enabled = self.config["enabled"]
            self.config["enabled"] = enabled
            changes.append(f"Activé: {old_enabled} → {enabled}")

            if enabled and not self.proactive_loop.is_running():
                self.start_proactive_loop()
            elif not enabled and self.proactive_loop.is_running():
                self.stop_proactive_loop()

        if interval is not None and 10 <= interval <= 1440:  # Entre 10 min et 24h
            self.config["interval_minutes"] = interval
            changes.append(f"Intervalle: {interval} minutes")

            # Redémarrer loop avec nouveau timing
            if self.proactive_loop.is_running():
                self.proactive_loop.cancel()
                self.proactive_loop.change_interval(minutes=interval)
                self.start_proactive_loop()

        if max_daily is not None and 1 <= max_daily <= 10:
            self.config["max_per_user_per_day"] = max_daily
            changes.append(f"Max quotidien: {max_daily}")

        if changes:
            await interaction.response.send_message(
                f"✅ **Configuration mise à jour:**\n" + "\n".join(changes),
                ephemeral=True
            )
        else:
            # Afficher config actuelle
            await interaction.response.send_message(
                f"⚙️ **Configuration actuelle:**\n"
                f"• Activé: {self.config['enabled']}\n"
                f"• Intervalle: {self.config['interval_minutes']} min\n"
                f"• Max quotidien: {self.config['max_per_user_per_day']}\n"
                f"• Cooldown: {self.config['cooldown_hours']}h",
                ephemeral=True
            )

class ProactiveActionView(discord.ui.View):
    """Vue pour les actions sur suggestions proactives"""

    def __init__(self, cog: ProactiveMatching, candidate_id: str, nonce: str):
        super().__init__(timeout=86400)  # 24h
        self.cog = cog
        self.candidate_id = candidate_id
        self.nonce = nonce

    @discord.ui.button(label="👁️ Voir détails", style=discord.ButtonStyle.gray)
    async def pro_view(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🔍 Vue détaillée (à implémenter)",
            ephemeral=True
        )

    @discord.ui.button(label="✅ Intéressé(e)", style=discord.ButtonStyle.green)
    async def pro_accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_proactive_accept(interaction, self.candidate_id, self.nonce)
        self.stop()

    @discord.ui.button(label="⏭️ Passer", style=discord.ButtonStyle.secondary)
    async def pro_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .utils import db_instance

        # Marquer comme passé
        await db_instance.connection.execute("""
            UPDATE suggestions SET status = 'passed', updated_at = ?
            WHERE candidate_id = ? AND nonce = ?
        """, (datetime.now().isoformat(), self.candidate_id, self.nonce))
        await db_instance.connection.commit()

        await interaction.response.send_message(
            "⏭️ Suggestion ignorée. Vous en recevrez d'autres prochainement !",
            ephemeral=True
        )
        self.stop()

    @discord.ui.button(label="🚨 Signaler", style=discord.ButtonStyle.red)
    async def pro_report(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🚨 Profil signalé (à implémenter)",
            ephemeral=True
        )
        self.stop()

    @discord.ui.button(label="⚙️ Désactiver suggestions", style=discord.ButtonStyle.secondary)
    async def pro_opt_out(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .utils import db_instance

        # Mettre à jour préférences pour opt-out
        await db_instance.connection.execute("""
            UPDATE profiles SET prefs = json_set(COALESCE(prefs, '{}'), '$.opt_out_proactive', true)
            WHERE user_id = ?
        """, (str(interaction.user.id),))
        await db_instance.connection.commit()

        await interaction.response.send_message(
            "⚙️ **Suggestions automatiques désactivées.**\n"
            "Vous pouvez toujours utiliser `/findmatch` manuellement.",
            ephemeral=True
        )
        self.stop()

async def setup(bot):
    """Fonction obligatoire pour charger le cog"""
    await bot.add_cog(ProactiveMatching(bot))