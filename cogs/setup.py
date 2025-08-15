import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

class Setup(commands.Cog):
    """Cog pour les commandes de configuration et d'aide"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Guide complet du Matching Bot")
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
                "`/consultsignal` - Voir les signalements"
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
                "• **Historique intelligent** : Évite les répétitions\n"
                "• **Auto-nettoyage** : Données effacées après 18 jours"
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
            text="💡 Toutes les interactions sont privées et sécurisées • Version 2.1"
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setup", description="[ADMIN] Configurer le canal de présentation du bot")
    @app_commands.describe(channel="Canal où le bot postera ses informations")
    async def setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
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

            # Envoyer la présentation complète dans le canal
            await self.send_bot_presentation(channel)

            await interaction.response.send_message(
                f"✅ **Configuration terminée !**\n\n"
                f"Canal configuré : {channel.mention}\n"
                f"Le guide d'utilisation a été posté dans le canal.\n\n"
                f"Les utilisateurs peuvent maintenant découvrir le bot ! 🚀",
                ephemeral=True
            )

        except Exception as e:
            print(f"❌ Erreur setup: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite lors de la configuration.",
                ephemeral=True
            )

    async def send_bot_presentation(self, channel: discord.TextChannel):
        """Présentation du bot dans le canal configuré"""
        try:
            embed = discord.Embed(
                title="🤖 Matching Bot - Rencontres Sécurisées",
                description="Trouvez des personnes compatibles grâce à notre IA de matching !",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="🚀 Commencer",
                value="`/createprofile` puis `/findmatch`",
                inline=True
            )

            embed.add_field(
                name="🛡️ Sécurité",
                value="Double opt-in • Protection mineurs • Anonymat",
                inline=True
            )

            embed.add_field(
                name="💡 Aide",
                value="`/help` pour plus d'informations",
                inline=True
            )

            embed.add_field(
                name="🎯 Fonctionnalités",
                value=(
                    "• **Algorithme intelligent** : Compatibilité basée sur les intérêts\n"
                    "• **Historique smart** : Jamais les mêmes suggestions\n"
                    "• **Auto-nettoyage** : Données effacées après 18 jours\n"
                    "• **Système de signalement** intégré"
                ),
                inline=False
            )

            embed.set_footer(text="Utilisez /help pour le guide complet • Bot sécurisé et confidentiel")

            await channel.send(embed=embed)
            print(f"✅ Présentation envoyée dans {channel.name}")

        except Exception as e:
            print(f"❌ Erreur présentation: {e}")
            raise

async def setup(bot):
    """Fonction obligatoire pour charger le cog"""
    await bot.add_cog(Setup(bot))