import discord
from discord.ext import commands
from discord import app_commands
from .utils import db_instance, serialize_interests, serialize_vector

class Profile(commands.Cog):
    """Cog pour la gestion des profils utilisateur"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="createprofile", description="Créer votre profil de matching")
    @app_commands.describe(
        prenom="Votre prénom",
        pronoms="Vos pronoms (il/elle/iel/etc.)",
        age="Votre âge",
        interets="Vos intérêts séparés par des virgules (ex: musique, sport, lecture)",
        description="Une courte description de vous"
    )
    async def createprofile(
        self, 
        interaction: discord.Interaction, 
        prenom: str, 
        pronoms: str, 
        age: int, 
        interets: str, 
        description: str
    ):
        """Créer un nouveau profil utilisateur"""
        user_id = str(interaction.user.id)
        
        try:
            # Vérifier si l'utilisateur a déjà un profil
            async with db_instance.connection.execute(
                "SELECT user_id FROM profiles WHERE user_id = ?", 
                (user_id,)
            ) as cursor:
                existing_profile = await cursor.fetchone()
            
            if existing_profile:
                await interaction.response.send_message(
                    "❌ Vous avez déjà un profil de matching.\n"
                    "Utilisez `/deleteprofile` pour le supprimer avant d'en créer un nouveau.",
                    ephemeral=True
                )
                return
            
            # Validation de l'âge (13-30 ans)
            if age < 13 or age > 30:
                await interaction.response.send_message(
                    "❌ L'âge doit être compris entre 13 et 30 ans pour créer un profil.",
                    ephemeral=True
                )
                return
            
            # Parser les intérêts (CSV vers liste)
            interests_list = [interest.strip() for interest in interets.split(',') if interest.strip()]
            if not interests_list:
                await interaction.response.send_message(
                    "❌ Veuillez spécifier au moins un intérêt.",
                    ephemeral=True
                )
                return
            
            # Sérialiser les intérêts en JSON
            interests_json = serialize_interests(interests_list)
            
            # Vecteur par défaut [0,0,0,0,0]
            default_vector = serialize_vector([0, 0, 0, 0, 0])
            
            # Récupérer l'URL de l'avatar
            avatar_url = None
            if interaction.user.display_avatar:
                avatar_url = str(interaction.user.display_avatar.url)
            
            # Insérer le profil dans la base de données
            await db_instance.connection.execute("""
                INSERT INTO profiles (user_id, prenom, pronoms, age, interets, description, avatar_url, vector)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, prenom, pronoms, age, interests_json, description, avatar_url, default_vector))
            
            await db_instance.connection.commit()
            
            # Message de confirmation
            interests_display = ", ".join(interests_list[:3])  # Afficher max 3 intérêts
            if len(interests_list) > 3:
                interests_display += f" (+{len(interests_list)-3} autres)"
            
            await interaction.response.send_message(
                f"✅ **Profil créé avec succès !**\n\n"
                f"**Prénom :** {prenom}\n"
                f"**Pronoms :** {pronoms}\n"
                f"**Âge :** {age} ans\n"
                f"**Intérêts :** {interests_display}\n"
                f"**Description :** {description[:100]}{'...' if len(description) > 100 else ''}\n\n"
                f"Utilisez `/findmatch` pour commencer à chercher des correspondances !",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"❌ Erreur lors de la création du profil pour {user_id}: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite lors de la création de votre profil. "
                "Veuillez réessayer plus tard.",
                ephemeral=True
            )
    
    @app_commands.command(name="deleteprofile", description="Supprimer votre profil de matching")
    async def deleteprofile(self, interaction: discord.Interaction):
        """Supprimer le profil utilisateur"""
        user_id = str(interaction.user.id)
        
        try:
            # Vérifier si l'utilisateur a un profil
            async with db_instance.connection.execute(
                "SELECT user_id FROM profiles WHERE user_id = ?", 
                (user_id,)
            ) as cursor:
                existing_profile = await cursor.fetchone()
            
            if not existing_profile:
                await interaction.response.send_message(
                    "❌ Vous n'avez pas de profil à supprimer.",
                    ephemeral=True
                )
                return
            
            # Supprimer le profil
            await db_instance.connection.execute(
                "DELETE FROM profiles WHERE user_id = ?", 
                (user_id,)
            )
            await db_instance.connection.commit()
            
            await interaction.response.send_message(
                "🗑️ **Profil supprimé avec succès.**\n\n"
                "Vos données ont été complètement effacées de notre base de données.\n"
                "Vous pouvez créer un nouveau profil à tout moment avec `/createprofile`.",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"❌ Erreur lors de la suppression du profil pour {user_id}: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite lors de la suppression de votre profil. "
                "Veuillez réessayer plus tard.",
                ephemeral=True
            )
    
    @app_commands.command(name="viewprofile", description="Voir votre profil actuel")
    async def viewprofile(self, interaction: discord.Interaction):
        """Afficher le profil de l'utilisateur"""
        user_id = str(interaction.user.id)
        
        try:
            async with db_instance.connection.execute(
                "SELECT * FROM profiles WHERE user_id = ?", 
                (user_id,)
            ) as cursor:
                profile = await cursor.fetchone()
            
            if not profile:
                await interaction.response.send_message(
                    "❌ Vous n'avez pas encore de profil.\n"
                    "Créez-en un avec `/createprofile` !",
                    ephemeral=True
                )
                return
            
            # Désérialiser les intérêts
            try:
                import json
                interests = json.loads(profile[4])  # Column 4 = interets
                interests_display = ", ".join(interests)
            except:
                interests_display = "Aucun"
            
            # Créer l'embed
            embed = discord.Embed(
                title="🏷️ Votre Profil de Matching",
                color=discord.Color.blue()
            )
            embed.add_field(name="Prénom", value=profile[1], inline=True)
            embed.add_field(name="Pronoms", value=profile[2], inline=True)
            embed.add_field(name="Âge", value=f"{profile[3]} ans", inline=True)
            embed.add_field(name="Intérêts", value=interests_display, inline=False)
            embed.add_field(name="Description", value=profile[5], inline=False)
            
            if profile[6]:  # avatar_url
                embed.set_thumbnail(url=profile[6])
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"❌ Erreur lors de l'affichage du profil pour {user_id}: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite lors de l'affichage de votre profil.",
                ephemeral=True
            )

async def setup(bot):
    """Fonction obligatoire pour charger le cog"""
    await bot.add_cog(Profile(bot))