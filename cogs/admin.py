import discord
from discord.ext import commands
from discord import app_commands
from .utils import db_instance
import json
import os
from datetime import datetime

class Admin(commands.Cog):
    """Cog pour les commandes d'administration du bot"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def is_admin(self, interaction: discord.Interaction) -> bool:
        """Vérifier si l'utilisateur est administrateur"""
        # Propriétaire du bot
        if await self.bot.is_owner(interaction.user):
            return True
        
        # Vérifier les permissions d'administrateur
        if interaction.guild and interaction.user.guild_permissions.administrator:
            return True
            
        return False
    
    @app_commands.command(name="export_profiles", description="[ADMIN] Exporter tous les profils en JSON")
    async def export_profiles(self, interaction: discord.Interaction):
        """Exporter tous les profils dans un fichier JSON de sauvegarde"""
        
        # Vérification des permissions
        if not await self.is_admin(interaction):
            await interaction.response.send_message(
                "❌ Cette commande est réservée aux administrateurs.",
                ephemeral=True
            )
            return
        
        try:
            # Récupérer tous les profils
            async with db_instance.connection.execute("SELECT * FROM profiles") as cursor:
                profiles = await cursor.fetchall()
            
            if not profiles:
                await interaction.response.send_message(
                    "📭 Aucun profil à exporter.",
                    ephemeral=True
                )
                return
            
            # Convertir en format JSON exportable
            profiles_data = []
            for profile in profiles:
                profile_dict = {
                    'user_id': profile[0],
                    'prenom': profile[1],
                    'pronoms': profile[2], 
                    'age': profile[3],
                    'interets': profile[4],  # Déjà en JSON
                    'description': profile[5],
                    'avatar_url': profile[6],
                    'vector': profile[7]  # Déjà en JSON
                }
                profiles_data.append(profile_dict)
            
            # Créer le fichier de sauvegarde
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"profiles_backup_{timestamp}.json"
            filepath = f"data/backups/{filename}"
            
            # S'assurer que le dossier existe
            os.makedirs("data/backups", exist_ok=True)
            
            # Écrire le fichier
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'export_date': datetime.now().isoformat(),
                    'total_profiles': len(profiles_data),
                    'profiles': profiles_data
                }, f, indent=2, ensure_ascii=False)
            
            # Confirmation
            await interaction.response.send_message(
                f"✅ **Export terminé !**\n\n"
                f"**Fichier :** `{filename}`\n"
                f"**Profils exportés :** {len(profiles_data)}\n"
                f"**Localisation :** `data/backups/`\n\n"
                f"💾 Sauvegarde créée le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"❌ Erreur lors de l'export des profils: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite lors de l'export des profils.",
                ephemeral=True
            )
    
    @app_commands.command(name="list_profiles", description="[ADMIN] Lister les profils existants")
    @app_commands.describe(limit="Nombre maximum de profils à afficher (défaut: 10)")
    async def list_profiles(self, interaction: discord.Interaction, limit: int = 10):
        """Afficher la liste des profils avec informations de base"""
        
        # Vérification des permissions
        if not await self.is_admin(interaction):
            await interaction.response.send_message(
                "❌ Cette commande est réservée aux administrateurs.",
                ephemeral=True
            )
            return
        
        try:
            # Compter le total des profils
            async with db_instance.connection.execute("SELECT COUNT(*) FROM profiles") as cursor:
                total_count = await cursor.fetchone()
                total_profiles = total_count[0] if total_count else 0
            
            if total_profiles == 0:
                await interaction.response.send_message(
                    "📭 Aucun profil trouvé dans la base de données.",
                    ephemeral=True
                )
                return
            
            # Limiter entre 1 et 50 profils
            limit = max(1, min(limit, 50))
            
            # Récupérer les profils avec limite
            async with db_instance.connection.execute(
                "SELECT user_id, prenom, pronoms, age FROM profiles ORDER BY rowid DESC LIMIT ?", 
                (limit,)
            ) as cursor:
                profiles = await cursor.fetchall()
            
            # Créer l'embed
            embed = discord.Embed(
                title="👥 Liste des Profils",
                description=f"Affichage de {len(profiles)} profils sur {total_profiles} au total",
                color=discord.Color.blue()
            )
            
            # Ajouter les profils
            profiles_text = ""
            for i, profile in enumerate(profiles, 1):
                user_id, prenom, pronoms, age = profile
                profiles_text += f"**{i}.** {prenom} ({pronoms}, {age} ans) - ID: `{user_id}`\n"
            
            if profiles_text:
                embed.add_field(
                    name="📋 Profils récents",
                    value=profiles_text[:1024],  # Limite Discord
                    inline=False
                )
            
            # Statistiques supplémentaires
            embed.add_field(
                name="📊 Statistiques",
                value=f"**Total des profils :** {total_profiles}\n"
                      f"**Profils affichés :** {len(profiles)}\n"
                      f"**Limite actuelle :** {limit}",
                inline=True
            )
            
            embed.set_footer(text=f"Utilisez limit=X pour afficher plus de profils (max: 50)")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"❌ Erreur lors de l'affichage des profils: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite lors de l'affichage des profils.",
                ephemeral=True
            )
    
    @app_commands.command(name="stats", description="[ADMIN] Statistiques générales du bot")
    async def stats(self, interaction: discord.Interaction):
        """Afficher des statistiques générales sur le bot et la base de données"""
        
        # Vérification des permissions
        if not await self.is_admin(interaction):
            await interaction.response.send_message(
                "❌ Cette commande est réservée aux administrateurs.",
                ephemeral=True
            )
            return
        
        try:
            # Statistiques des profils
            async with db_instance.connection.execute("SELECT COUNT(*) FROM profiles") as cursor:
                total_profiles = (await cursor.fetchone())[0]
            
            # Statistiques par âge
            async with db_instance.connection.execute(
                "SELECT AVG(age), MIN(age), MAX(age) FROM profiles"
            ) as cursor:
                age_stats = await cursor.fetchone()
                avg_age = round(age_stats[0], 1) if age_stats[0] else 0
                min_age = age_stats[1] or 0
                max_age = age_stats[2] or 0
            
            # Créer l'embed
            embed = discord.Embed(
                title="📊 Statistiques du Bot",
                color=discord.Color.gold()
            )
            
            # Informations du bot
            embed.add_field(
                name="🤖 Bot",
                value=f"**Nom :** {self.bot.user.name}\n"
                      f"**ID :** {self.bot.user.id}\n"
                      f"**Serveurs :** {len(self.bot.guilds)}",
                inline=True
            )
            
            # Statistiques des profils
            embed.add_field(
                name="👥 Profils",
                value=f"**Total :** {total_profiles}\n"
                      f"**Âge moyen :** {avg_age} ans\n"
                      f"**Âges :** {min_age}-{max_age} ans",
                inline=True
            )
            
            # Informations système
            try:
                import psutil
                cpu_percent = psutil.cpu_percent()
                memory_percent = psutil.virtual_memory().percent
                
                embed.add_field(
                    name="💻 Système",
                    value=f"**CPU :** {cpu_percent}%\n"
                          f"**RAM :** {memory_percent}%\n"
                          f"**Latence :** {round(self.bot.latency * 1000)}ms",
                    inline=True
                )
            except ImportError:
                pass
            
            embed.set_footer(text=f"Dernière mise à jour: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"❌ Erreur lors de l'affichage des stats: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite lors de l'affichage des statistiques.",
                ephemeral=True
            )

async def setup(bot):
    """Fonction obligatoire pour charger le cog"""
    await bot.add_cog(Admin(bot))