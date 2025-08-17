
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from .utils import db_instance, logger

class Setup(commands.Cog):
    """Commandes de configuration du bot"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_bot", description="[ADMIN] Initialiser le bot et vérifier la configuration")
    @app_commands.default_permissions(administrator=True)
    async def setup_bot(self, interaction: discord.Interaction):
        """Commande d'initialisation du bot"""
        await interaction.response.defer(ephemeral=True)

        try:
            # Vérifier la connexion DB
            if not await db_instance.is_connected():
                await db_instance.connect()

            # Vérifier les tables
            await db_instance.create_tables()

            # Compter les profils existants
            async with db_instance.connection.execute("SELECT COUNT(*) FROM profiles") as cursor:
                profile_count = (await cursor.fetchone())[0]

            # Compter les matches
            async with db_instance.connection.execute("SELECT COUNT(*) FROM matches") as cursor:
                match_count = (await cursor.fetchone())[0]

            # Vérifier les cogs chargés
            cog_status = []
            for cog_name in ['setup', 'profile', 'match', 'admin']:
                if f'cogs.{cog_name}' in self.bot.cogs:
                    cog_status.append(f"✅ {cog_name}")
                else:
                    cog_status.append(f"❌ {cog_name}")

            embed = discord.Embed(
                title="🤖 Matching Bot - Configuration Système",
                description="**Configuration et diagnostic complet du bot**\n\n*Bot de rencontres intelligent avec protection des mineurs*",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )

            embed.add_field(
                name="📊 Statistiques Actuelles",
                value=f"👥 **Profils actifs:** {profile_count}\n💕 **Matches créés:** {match_count}\n🎯 **Taux de réussite:** {'Calculé après 10+ profils' if profile_count < 10 else f'{(match_count/profile_count*100):.1f}%'}",
                inline=True
            )

            embed.add_field(
                name="🔧 État des Composants",
                value=f"🗄️ **Base de données:** ✅ Connectée\n📋 **Tables:** ✅ Initialisées\n⚙️ **Cogs:** {len([c for c in cog_status if '✅' in c])}/4 chargés",
                inline=True
            )

            embed.add_field(
                name="🏗️ Modules Chargés",
                value="\n".join(cog_status),
                inline=True
            )

            embed.add_field(
                name="🚀 Commandes Principales",
                value="🆕 `/createprofile` - Créer son profil\n🔍 `/findmatch` - Trouver des correspondances\n📊 `/match_stats` - Voir ses statistiques\n🔄 `/reset_passes` - Réinitialiser les profils passés",
                inline=False
            )

            embed.add_field(
                name="🛡️ Sécurité & Modération",
                value="🔒 **Protection mineurs:** Ségrégation stricte\n🚨 **Signalements:** Système intégré\n👮 **Admin:** `/admin_reports`, `/list_profiles`\n🧹 **Nettoyage:** Automatique toutes les heures",
                inline=False
            )

            embed.add_field(
                name="📈 Algorithme de Matching",
                value="🎯 **Compatibilité:** Intérêts (60%) + Âge (25%) + Description (15%)\n🔍 **Synonymes:** Détection automatique\n⚖️ **Filtres:** Âge max 12 ans d'écart\n🛡️ **Seuil minimum:** 10% de compatibilité",
                inline=False
            )

            embed.set_footer(
                text="🎉 Bot opérationnel • Prêt pour les utilisateurs • /info pour plus d'infos",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"❌ Erreur setup_bot: {e}")
            await interaction.followup.send(
                f"❌ Erreur lors de la configuration: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="info", description="Informations sur le bot")
    async def info(self, interaction: discord.Interaction):
        """Afficher les informations du bot"""
        embed = discord.Embed(
            title="🤖 Matching Bot Discord",
            description="Bot de rencontres avec système de compatibilité intelligent",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="✨ Fonctionnalités",
            value="• Création de profils\n• Matching intelligent\n• Système anonyme\n• Protection des mineurs",
            inline=True
        )

        embed.add_field(
            name="🔧 Commandes",
            value="• `/createprofile`\n• `/findmatch`\n• `/match_stats`\n• `/reset_passes`",
            inline=True
        )

        embed.add_field(
            name="🛡️ Sécurité",
            value="• Ségrégation âge\n• Signalement intégré\n• Modération active",
            inline=False
        )

        embed.set_footer(text="Utilisez /createprofile pour commencer !")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    """Fonction de setup du cog"""
    await bot.add_cog(Setup(bot))
