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
            name="⚙️ Commandes Admin",
            value=(
                "`/setup` - Configurer le canal de présentation\n"
                "`/reload` - Recharger un cog (administrateurs)\n"
                "`/export_profiles` - Exporter les données"
            ),
            inline=False
        )

        embed.add_field(
            name="🔒 Sécurité",
            value=(
                "• Séparation stricte mineurs/majeurs\n"
                "• Système de double opt-in\n"
                "• Toutes les interactions sont privées et sécurisées\n"
                "• Version 2.1"
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setup_channel", description="[ADMIN] Configurer le canal de présentation du bot")
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
            await db_instance.connection.commit()

            # Sauvegarder la configuration
            await db_instance.connection.execute("""
                INSERT OR REPLACE INTO server_config (guild_id, setup_channel_id, updated_at)
                VALUES (?, ?, ?)
            """, (str(interaction.guild.id), str(channel.id), datetime.now().isoformat()))
            await db_instance.connection.commit()

            # Envoyer le guide dans le canal configuré
            embed = discord.Embed(
                title="🤖 Matching Bot - Guide Complet",
                description="Bot de rencontre sécurisé avec système de double opt-in",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="🚀 Commandes de Base",
                value="`/help` - Guide complet\n`/createprofile` - Créer son profil\n`/findmatch` - Trouver des matches",
                inline=False
            )

            embed.add_field(
                name="🛡️ Sécurité",
                value="Séparation stricte mineurs/majeurs • Double opt-in • Interactions privées",
                inline=False
            )

            await channel.send(embed=embed)

            await interaction.response.send_message(
                f"✅ Canal de présentation configuré : {channel.mention}",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erreur lors de la configuration : {str(e)}",
                ephemeral=True
            )

    async def send_bot_presentation(self, channel: discord.TextChannel):
        """Présentation du bot dans le canal configuré"""
        try:
            # Utiliser l'icône du serveur si disponible
            guild_icon = channel.guild.icon.url if channel.guild.icon else None

            embed = discord.Embed(
                title="💖 **MATCHING BOT** - *Rencontres Sécurisées*",
                description=(
                    "🎯 ***Trouvez des personnes compatibles grâce à notre algorithme intelligent !***\n\n"
                    "**__Protection absolue des mineurs__** • **__Double validation__** • **__Anonymat garanti__**"
                ),
                color=0xFF69B4  # Rose vibrant
            )

            # Icône du serveur dans l'embed
            if guild_icon:
                embed.set_thumbnail(url=guild_icon)

            embed.add_field(
                name="🚀 **COMMANDES PRINCIPALES**",
                value=(
                    "**`/createprofile`** - *Créer votre profil de rencontre*\n"
                    "**`/viewprofile`** - *Consulter votre profil ou celui d'un autre*\n"
                    "**`/findmatch`** - *Rechercher des correspondances compatibles*\n"
                    "**`/deleteprofile`** - *Supprimer définitivement votre profil*"
                ),
                inline=False
            )

            embed.add_field(
                name="🛡️ **SÉCURITÉ & MODÉRATION**",
                value=(
                    "**`/report_profile`** - *Signaler un profil inapproprié*\n"
                    "• ***Protection stricte*** : Séparation mineurs/majeurs\n"
                    "• ***Double opt-in*** : Les 2 personnes doivent accepter\n"
                    "• ***Anonymat initial*** : Identité révélée après accord mutuel"
                ),
                inline=False
            )

            embed.add_field(
                name="💡 **AIDE & SUPPORT**",
                value=(
                    "**`/help`** - *Guide complet d'utilisation*\n"
                    "**`/setup`** - *(Admin) Configurer le canal de présentation*\n\n"
                    "**📞 Support :** *Contactez les administrateurs du serveur*"
                ),
                inline=False
            )

            embed.add_field(
                name="✨ **FONCTIONNALITÉS AVANCÉES**",
                value=(
                    "🧠 **Algorithme IA** : *Compatibilité basée sur les centres d'intérêts*\n"
                    "🔄 **Historique intelligent** : *Évite les répétitions de suggestions*\n"
                    "🗑️ **Auto-nettoyage** : *Historique effacé après 18 jours*\n"
                    "⚡ **Notifications DM** : *Toutes les interactions en privé*\n"
                    "🎭 **Interface moderne** : *Boutons interactifs et embeds colorés*"
                ),
                inline=False
            )

            embed.add_field(
                name="🎯 **COMMENT COMMENCER ?**",
                value=(
                    "**1️⃣** Tapez **`/createprofile`** pour créer votre profil\n"
                    "**2️⃣** Utilisez **`/findmatch`** pour trouver des correspondances\n"
                    "**3️⃣** Acceptez ou passez les suggestions reçues en DM\n"
                    "**4️⃣** Si match mutuel, vous serez mis en contact ! 💕"
                ),
                inline=False
            )

            embed.set_footer(
                text="🔒 Bot 100% sécurisé et confidentiel • Version 2.1 • Toutes les interactions sont privées",
                icon_url=guild_icon
            )

            await channel.send(embed=embed)
            print(f"✅ Présentation améliorée envoyée dans {channel.name}")

        except Exception as e:
            print(f"❌ Erreur présentation: {e}")
            raise

async def setup(bot):
    """Fonction obligatoire pour charger le cog"""
    await bot.add_cog(Setup(bot))