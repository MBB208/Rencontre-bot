
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

class Setup(commands.Cog):
    """Cog pour les commandes de configuration initiale"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Affiche l'aide et les commandes disponibles")
    async def help_command(self, interaction: discord.Interaction):
        """Affiche l'aide complète du bot"""
        
        embed = discord.Embed(
            title="🤖 Guide du Matching Bot",
            description="Bot de rencontre sécurisé avec système de double opt-in",
            color=discord.Color.blue()
        )
        
        # Commandes principales
        embed.add_field(
            name="📋 Commandes Profil",
            value=(
                "`/createprofile` - Créer/modifier votre profil\n"
                "`/viewprofile` - Voir votre profil ou celui d'un autre\n"
                "`/deleteprofile` - Supprimer définitivement votre profil"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💖 Commandes Matching",
            value=(
                "`/findmatch` - Trouver des correspondances compatibles\n"
                "`/report_profile` - Signaler un profil inapproprié"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔧 Commandes Admin",
            value=(
                "`/stats` - Statistiques du bot\n"
                "`/list_profiles` - Liste des profils\n"
                "`/export_profiles` - Export JSON des profils\n"
                "`/consultsignal` - Voir les signalements\n"
                "`/deleteprofileadmin` - Supprimer un profil (admin)"
            ),
            inline=False
        )
        
        # Informations de sécurité
        embed.add_field(
            name="🛡️ Sécurité & Confidentialité",
            value=(
                "• **Protection mineurs** : Séparation absolue mineur/majeur\n"
                "• **Double opt-in** : Les deux personnes doivent accepter\n"
                "• **Anonymat initial** : Identité révélée après accord mutuel\n"
                "• **Signalement** : Système de modération intégré"
            ),
            inline=False
        )
        
        # Comment commencer
        embed.add_field(
            name="🚀 Comment commencer ?",
            value=(
                "1️⃣ Créez votre profil avec `/createprofile`\n"
                "2️⃣ Cherchez des correspondances avec `/findmatch`\n"
                "3️⃣ Acceptez ou passez les suggestions reçues\n"
                "4️⃣ Si match mutuel, vous serez mis en contact !"
            ),
            inline=False
        )
        
        embed.set_footer(
            text="💡 Toutes les interactions sont privées et sécurisées • Version 2.0"
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="about", description="Informations sur le bot et ses fonctionnalités")
    async def about(self, interaction: discord.Interaction):
        """Informations détaillées sur le bot"""
        
        embed = discord.Embed(
            title="ℹ️ À propos du Matching Bot",
            description="Bot de rencontre nouvelle génération pour Discord",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="🎯 Objectif",
            value="Faciliter les rencontres sécurisées et respectueuses entre utilisateurs Discord avec des centres d'intérêt communs.",
            inline=False
        )
        
        embed.add_field(
            name="🧠 Algorithme de Matching",
            value=(
                "• **Similarité d'intérêts** : Analyse TF-IDF avancée\n"
                "• **Compatibilité d'âge** : Fonction gaussienne adaptée\n"
                "• **Score composite** : Pondération intelligente\n"
                "• **Filtres de sécurité** : Protection automatique"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔒 Sécurité",
            value=(
                "• **Séparation d'âge** : Mineurs et majeurs séparés\n"
                "• **Double consentement** : Accord mutuel obligatoire\n"
                "• **Anonymat** : Révélation progressive d'identité\n"
                "• **Modération** : Système de signalement intégré"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 Statistiques",
            value=f"• **Serveurs** : {len(self.bot.guilds)}\n• **Latence** : {round(self.bot.latency * 1000)}ms\n• **Version** : 2.0",
            inline=True
        )
        
        embed.add_field(
            name="⚡ Performance",
            value="• **Base de données** : SQLite optimisée\n• **Cache intelligent** : Réponses ultra-rapides\n• **Async** : Architecture moderne",
            inline=True
        )
        
        embed.set_footer(text="Développé avec ❤️ • discord.py • Open Source")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="privacy", description="Politique de confidentialité et gestion des données")
    async def privacy(self, interaction: discord.Interaction):
        """Affiche la politique de confidentialité"""
        
        embed = discord.Embed(
            title="🔐 Politique de Confidentialité",
            description="Comment nous protégeons vos données personnelles",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="📋 Données Collectées",
            value=(
                "• **Profil** : Prénom, pronoms, âge, intérêts, description\n"
                "• **Avatar Discord** : Pour l'affichage du profil\n"
                "• **ID Discord** : Pour l'identification unique\n"
                "• **Interactions** : Historique de matching anonymisé"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🛡️ Protection des Données",
            value=(
                "• **Stockage local** : Base de données SQLite sécurisée\n"
                "• **Pas de revente** : Vos données ne sont jamais vendues\n"
                "• **Accès restreint** : Seuls les admins autorisés\n"
                "• **Chiffrement** : Communications sécurisées"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🎭 Anonymat et Révélation",
            value=(
                "• **Phase 1** : Profil anonyme (âge, intérêts)\n"
                "• **Phase 2** : Prénom et pronoms révélés\n"
                "• **Phase 3** : Contact Discord après double accord\n"
                "• **Contrôle total** : Vous décidez quoi partager"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🗑️ Suppression des Données",
            value=(
                "• **Droit à l'oubli** : `/deleteprofile` supprime tout\n"
                "• **Suppression immédiate** : Pas de conservation\n"
                "• **Matches supprimés** : Toutes les correspondances effacées\n"
                "• **Signalements supprimés** : Historique nettoyé"
            ),
            inline=False
        )
        
        embed.add_field(
            name="👶 Protection des Mineurs",
            value=(
                "• **Séparation totale** : Mineurs et majeurs isolés\n"
                "• **Filtre d'âge** : Algorithme de protection automatique\n"
                "• **Surveillance renforcée** : Modération prioritaire\n"
                "• **Signalement facilité** : Bouton dans chaque profil"
            ),
            inline=False
        )
        
        embed.set_footer(text="Contact admin pour questions • Dernière mise à jour: 2024")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setup_channel", description="[ADMIN] Configurer le canal de présentation du bot")
    @app_commands.describe(channel="Canal où le bot postera ses informations")
    async def setup_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Configurer le canal où le bot postera son guide d'utilisation"""
        
        # Vérifier les permissions d'administrateur
        if not (interaction.user.guild_permissions.administrator or await self.bot.is_owner(interaction.user)):
            await interaction.response.send_message(
                "❌ Cette commande est réservée aux administrateurs du serveur.",
                ephemeral=True
            )
            return
        
        try:
            from .utils import db_instance
            
            # Créer la table de configuration si elle n'existe pas
            await db_instance.connection.execute("""
                CREATE TABLE IF NOT EXISTS server_config (
                    guild_id TEXT PRIMARY KEY,
                    setup_channel_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Sauvegarder la configuration
            await db_instance.connection.execute("""
                INSERT OR REPLACE INTO server_config (guild_id, setup_channel_id, updated_at)
                VALUES (?, ?, ?)
            """, (str(interaction.guild.id), str(channel.id), datetime.now().isoformat()))
            
            await db_instance.connection.commit()
            
            # Envoyer le guide d'utilisation dans le canal
            await self.send_bot_guide(channel)
            
            await interaction.response.send_message(
                f"✅ **Configuration terminée !**\n\n"
                f"Canal configuré : {channel.mention}\n"
                f"Le guide d'utilisation a été posté dans le canal.\n\n"
                f"Les utilisateurs peuvent maintenant découvrir le bot ! 🚀",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"❌ Erreur setup_channel: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite lors de la configuration.",
                ephemeral=True
            )

    @app_commands.command(name="update_info", description="[ADMIN] Mettre à jour le guide dans le canal configuré")
    async def update_info(self, interaction: discord.Interaction):
        """Mettre à jour le guide d'utilisation dans le canal configuré"""
        
        # Vérifier les permissions d'administrateur
        if not (interaction.user.guild_permissions.administrator or await self.bot.is_owner(interaction.user)):
            await interaction.response.send_message(
                "❌ Cette commande est réservée aux administrateurs du serveur.",
                ephemeral=True
            )
            return
        
        try:
            from .utils import db_instance
            
            # Récupérer la configuration du serveur
            async with db_instance.connection.execute(
                "SELECT setup_channel_id FROM server_config WHERE guild_id = ?",
                (str(interaction.guild.id),)
            ) as cursor:
                config = await cursor.fetchone()
            
            if not config or not config[0]:
                await interaction.response.send_message(
                    "❌ Aucun canal configuré. Utilisez `/setup_channel` d'abord.",
                    ephemeral=True
                )
                return
            
            # Récupérer le canal
            channel = self.bot.get_channel(int(config[0]))
            if not channel:
                await interaction.response.send_message(
                    "❌ Canal configuré introuvable. Utilisez `/setup_channel` pour le reconfigurer.",
                    ephemeral=True
                )
                return
            
            # Envoyer le guide mis à jour
            await self.send_bot_guide(channel)
            
            await interaction.response.send_message(
                f"✅ **Guide mis à jour !**\n\n"
                f"Le guide d'utilisation a été mis à jour dans {channel.mention}.",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"❌ Erreur update_info: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite lors de la mise à jour.",
                ephemeral=True
            )

    async def send_bot_guide(self, channel: discord.TextChannel):
        """Envoyer le guide complet d'utilisation du bot dans un canal"""
        try:
            # Embed principal de présentation
            main_embed = discord.Embed(
                title="🤖 Bienvenue sur le Matching Bot !",
                description="**Bot de rencontre sécurisé avec système de double opt-in**\n\n"
                           "Trouvez des personnes compatibles avec vos centres d'intérêt grâce à notre algorithme IA avancé !",
                color=discord.Color.blue()
            )
            
            main_embed.add_field(
                name="🚀 Pour commencer",
                value="1️⃣ Utilisez `/createprofile` pour créer votre profil\n"
                      "2️⃣ Utilisez `/findmatch` pour trouver des correspondances\n"
                      "3️⃣ Acceptez ou passez les suggestions reçues en DM\n"
                      "4️⃣ Si match mutuel, vous serez mis en contact !",
                inline=False
            )
            
            main_embed.add_field(
                name="🛡️ Sécurité Garantie",
                value="• **Protection mineurs** : Séparation absolue mineur/majeur\n"
                      "• **Anonymat initial** : Identité révélée après accord mutuel\n"
                      "• **Double validation** : Les deux personnes doivent accepter\n"
                      "• **Signalement** : Système de modération intégré",
                inline=False
            )
            
            main_embed.set_footer(text="💡 Toutes les commandes sont privées et sécurisées")
            
            await channel.send(embed=main_embed)
            
            # Embed des commandes
            commands_embed = discord.Embed(
                title="📋 Liste des Commandes",
                color=discord.Color.green()
            )
            
            commands_embed.add_field(
                name="👤 Gestion de Profil",
                value="`/createprofile` - Créer votre profil\n"
                      "`/viewprofile` - Voir votre profil\n"
                      "`/deleteprofile` - Supprimer votre profil",
                inline=True
            )
            
            commands_embed.add_field(
                name="💖 Matching",
                value="`/findmatch` - Chercher des correspondances\n"
                      "`/report_profile` - Signaler un profil",
                inline=True
            )
            
            commands_embed.add_field(
                name="ℹ️ Aide",
                value="`/help` - Guide complet\n"
                      "`/about` - À propos du bot\n"
                      "`/privacy` - Confidentialité",
                inline=True
            )
            
            await channel.send(embed=commands_embed)
            
            # Embed de l'algorithme
            algo_embed = discord.Embed(
                title="🧠 Notre Algorithme IA",
                description="Comment nous trouvons vos correspondances parfaites",
                color=discord.Color.purple()
            )
            
            algo_embed.add_field(
                name="🎯 Analyse des Intérêts",
                value="• **TF-IDF avancé** : Pondération intelligente\n"
                      "• **Fuzzy matching** : Détection de similitudes\n"
                      "• **Synonymes** : Reconnaissance de termes équivalents",
                inline=False
            )
            
            algo_embed.add_field(
                name="📊 Score de Compatibilité",
                value="• **Intérêts communs** : 55% du score\n"
                      "• **Compatibilité d'âge** : 20% du score\n"
                      "• **Personnalité** : 25% du score\n\n"
                      "Score minimum pour suggestion : **60%**",
                inline=False
            )
            
            await channel.send(embed=algo_embed)
            
            print(f"✅ Guide envoyé dans {channel.name} ({channel.id})")
            
        except Exception as e:
            print(f"❌ Erreur send_bot_guide: {e}")
            raise

async def setup(bot):
    """Fonction obligatoire pour charger le cog"""
    await bot.add_cog(Setup(bot))
