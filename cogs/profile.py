import discord
from discord.ext import commands
from discord import app_commands
from .utils import db_instance, serialize_interests
import json
import re

class ProfileModal(discord.ui.Modal):
    """Modal pour la création/modification de profil"""

    def __init__(self, title="Créer votre profil", existing_profile=None):
        super().__init__(title=title)

        # Pré-remplir avec les données existantes si modification
        default_prenom = existing_profile[1] if existing_profile else ""
        default_pronoms = existing_profile[2] if existing_profile else ""
        default_age = str(existing_profile[3]) if existing_profile else ""
        default_interets = ", ".join(json.loads(existing_profile[4])) if existing_profile and existing_profile[4] else ""
        default_description = existing_profile[6] if existing_profile and len(existing_profile) > 6 else ""

        self.prenom = discord.ui.TextInput(
            label="Prénom",
            placeholder="Votre prénom (visible pour les correspondances)",
            required=True,
            max_length=50,
            default=default_prenom
        )

        self.pronoms = discord.ui.TextInput(
            label="Pronoms",
            placeholder="il/elle, iel, etc.",
            required=True,
            max_length=20,
            default=default_pronoms
        )

        self.age = discord.ui.TextInput(
            label="Âge",
            placeholder="Votre âge (13-30 ans)",
            required=True,
            max_length=2,
            default=default_age
        )

        self.interets = discord.ui.TextInput(
            label="Centres d'intérêt",
            placeholder="Séparés par des virgules (ex: jeux vidéo, musique, lecture)",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500,
            default=default_interets
        )

        self.description = discord.ui.TextInput(
            label="Description (optionnelle)",
            placeholder="Parlez un peu de vous...",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000,
            default=default_description
        )

        self.add_item(self.prenom)
        self.add_item(self.pronoms)
        self.add_item(self.age)
        self.add_item(self.interets)
        self.add_item(self.description)

        self.existing_profile = existing_profile

    async def on_submit(self, interaction: discord.Interaction):
        """Traitement du formulaire soumis"""
        try:
            # Validation de l'âge
            try:
                age_value = int(self.age.value)
                if not (13 <= age_value <= 30):
                    raise ValueError()
            except ValueError:
                await interaction.response.send_message(
                    "❌ L'âge doit être un nombre entre 13 et 30 ans.",
                    ephemeral=True
                )
                return

            # Validation du prénom
            prenom_clean = self.prenom.value.strip()
            if not re.match(r"^[a-zA-ZÀ-ÿ\s\-']{2,}$", prenom_clean):
                await interaction.response.send_message(
                    "❌ Le prénom doit contenir au moins 2 caractères alphabétiques.",
                    ephemeral=True
                )
                return

            # Traitement des intérêts
            interests_list = [interest.strip() for interest in self.interets.value.split(",")]
            interests_list = [interest for interest in interests_list if interest]

            if len(interests_list) < 3:
                await interaction.response.send_message(
                    "❌ Veuillez saisir au moins 3 centres d'intérêt.",
                    ephemeral=True
                )
                return

            if len(interests_list) > 20:
                await interaction.response.send_message(
                    "❌ Veuillez limiter à 20 centres d'intérêt maximum.",
                    ephemeral=True
                )
                return

            # Sérialiser les données
            interests_json = serialize_interests(interests_list)
            user_id = str(interaction.user.id)

            # Récupérer l'avatar
            avatar_url = str(interaction.user.display_avatar.url) if interaction.user.display_avatar else None

            if self.existing_profile:
                # Mise à jour
                await db_instance.connection.execute("""
                    UPDATE profiles 
                    SET prenom = ?, pronoms = ?, age = ?, interets = ?, 
                        description = ?, avatar_url = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (prenom_clean, self.pronoms.value, age_value, interests_json, 
                      self.description.value, avatar_url, user_id))

                action = "modifié"
            else:
                # Création
                await db_instance.connection.execute("""
                    INSERT INTO profiles (user_id, prenom, pronoms, age, interets, description, avatar_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, prenom_clean, self.pronoms.value, age_value, interests_json, 
                      self.description.value, avatar_url))

                action = "créé"

            await db_instance.connection.commit()

            # Créer l'embed de confirmation
            embed = discord.Embed(
                title=f"✅ Profil {action} avec succès !",
                color=discord.Color.green()
            )

            embed.add_field(name="👤 Prénom", value=prenom_clean, inline=True)
            embed.add_field(name="🏷️ Pronoms", value=self.pronoms.value, inline=True)
            embed.add_field(name="🎂 Âge", value=f"{age_value} ans", inline=True)

            interests_text = ", ".join(interests_list[:5])
            if len(interests_list) > 5:
                interests_text += f" (+{len(interests_list)-5} autres)"

            embed.add_field(name="🎨 Intérêts", value=interests_text, inline=False)

            if self.description.value:
                description_preview = self.description.value[:100] + ("..." if len(self.description.value) > 100 else "")
                embed.add_field(name="💭 Description", value=description_preview, inline=False)

            embed.set_footer(text="Vous pouvez maintenant utiliser /findmatch pour chercher des correspondances !")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erreur ProfileModal.on_submit: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite lors de la sauvegarde. Veuillez réessayer.",
                ephemeral=True
            )

class Profile(commands.Cog):
    """Cog pour la gestion des profils utilisateur"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="createprofile", description="Créer ou modifier votre profil")
    async def createprofile(self, interaction: discord.Interaction):
        """Créer un nouveau profil ou modifier le profil existant"""
        user_id = str(interaction.user.id)

        try:
            # Vérifier si l'utilisateur a déjà un profil
            async with db_instance.connection.execute(
                "SELECT * FROM profiles WHERE user_id = ?", (user_id,)
            ) as cursor:
                existing_profile = await cursor.fetchone()

            if existing_profile:
                modal = ProfileModal("Modifier votre profil", existing_profile)
            else:
                modal = ProfileModal("Créer votre profil")

            await interaction.response.send_modal(modal)

        except Exception as e:
            print(f"❌ Erreur createprofile: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite. Veuillez réessayer.",
                ephemeral=True
            )

    @app_commands.command(name="viewprofile", description="Voir votre profil ou celui d'un autre utilisateur")
    @app_commands.describe(user="Utilisateur dont voir le profil (optionnel)")
    async def viewprofile(self, interaction: discord.Interaction, user: discord.User = None):
        """Afficher le profil d'un utilisateur avec protection anonymat"""
        target_user = user or interaction.user
        user_id = str(target_user.id)
        requester_id = str(interaction.user.id)

        try:
            # Si c'est son propre profil, pas de restrictions
            if target_user == interaction.user:
                async with db_instance.connection.execute(
                    "SELECT * FROM profiles WHERE user_id = ?", (user_id,)
                ) as cursor:
                    profile = await cursor.fetchone()

                if not profile:
                    await interaction.response.send_message(
                        "❌ Vous n'avez pas encore créé de profil.\n"
                        "Utilisez `/createprofile` pour commencer !",
                        ephemeral=True
                    )
                    return
            else:
                # Vérifier qu'il y a un match mutuel pour voir le profil d'autrui
                async with db_instance.connection.execute("""
                    SELECT * FROM matches 
                    WHERE ((user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?))
                    AND status = 'matched'
                """, (requester_id, user_id, user_id, requester_id)) as cursor:
                    match = await cursor.fetchone()

                if not match:
                    await interaction.response.send_message(
                        f"🔒 **Profil protégé**\n\n"
                        f"Vous ne pouvez voir le profil de {target_user.mention} que si vous avez un match mutuel.\n\n"
                        f"💡 Utilisez `/findmatch` pour découvrir de nouveaux profils !",
                        ephemeral=True
                    )
                    return

                # Récupérer le profil si match confirmé
                async with db_instance.connection.execute(
                    "SELECT * FROM profiles WHERE user_id = ?", (user_id,)
                ) as cursor:
                    profile = await cursor.fetchone()

                if not profile:
                    await interaction.response.send_message(
                        f"❌ {target_user.mention} n'a pas de profil disponible.",
                        ephemeral=True
                    )
                    return

            # Créer l'embed du profil
            embed = discord.Embed(
                title=f"👤 Profil de {profile[1]}",
                color=discord.Color.blue()
            )

            embed.add_field(name="🏷️ Pronoms", value=profile[2], inline=True)
            embed.add_field(name="🎂 Âge", value=f"{profile[3]} ans", inline=True)
            embed.add_field(name="⭐", value="‎", inline=True)  # Spacer

            # Intérêts
            interests = json.loads(profile[4]) if profile[4] else []
            interests_text = ", ".join(interests) if interests else "Non spécifiés"
            if len(interests_text) > 1024:
                interests_text = interests_text[:1020] + "..."
            embed.add_field(name="🎨 Centres d'intérêt", value=interests_text, inline=False)

            # Description
            if profile[6]:  # description
                description = profile[6][:500] + ("..." if len(profile[6]) > 500 else "")
                embed.add_field(name="💭 Description", value=description, inline=False)

            # Avatar
            if profile[7]:  # avatar_url
                embed.set_thumbnail(url=profile[7])

            # Footer avec infos techniques pour son propre profil
            if target_user == interaction.user:
                embed.set_footer(text="💡 Utilisez /createprofile pour modifier votre profil")
            else:
                embed.set_footer(text=f"Profil consulté le {interaction.created_at.strftime('%d/%m/%Y')}")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erreur viewprofile: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite lors de l'affichage du profil.",
                ephemeral=True
            )

    @app_commands.command(name="deleteprofile", description="Supprimer définitivement votre profil")
    async def deleteprofile(self, interaction: discord.Interaction):
        """Supprimer définitivement son propre profil"""
        user_id = str(interaction.user.id)

        try:
            # Vérifier que l'utilisateur a un profil
            async with db_instance.connection.execute(
                "SELECT prenom FROM profiles WHERE user_id = ?", (user_id,)
            ) as cursor:
                profile = await cursor.fetchone()

            if not profile:
                await interaction.response.send_message(
                    "❌ Vous n'avez pas de profil à supprimer.",
                    ephemeral=True
                )
                return

            # Créer la vue de confirmation
            view = DeleteConfirmView(user_id, profile[0])

            embed = discord.Embed(
                title="⚠️ Confirmation de suppression",
                description=f"Êtes-vous sûr de vouloir supprimer définitivement votre profil **{profile[0]}** ?",
                color=discord.Color.red()
            )

            embed.add_field(
                name="📋 Cette action supprimera :",
                value="• Votre profil complet\n• Vos correspondances\n• Vos signalements\n• Toutes vos données",
                inline=False
            )

            embed.set_footer(text="Cette action est irréversible !")

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            print(f"❌ Erreur deleteprofile: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite. Veuillez réessayer.",
                ephemeral=True
            )

class DeleteConfirmView(discord.ui.View):
    """Vue de confirmation pour la suppression de profil"""

    def __init__(self, user_id: str, prenom: str):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.prenom = prenom

    @discord.ui.button(label="✅ Confirmer la suppression", style=discord.ButtonStyle.red)
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Supprimer toutes les données de l'utilisateur
            await db_instance.connection.execute("DELETE FROM profiles WHERE user_id = ?", (self.user_id,))
            await db_instance.connection.execute("DELETE FROM matches WHERE user1_id = ? OR user2_id = ?", (self.user_id, self.user_id))
            await db_instance.connection.execute("DELETE FROM match_history WHERE user1_id = ? OR user2_id = ?", (self.user_id, self.user_id))
            await db_instance.connection.execute("DELETE FROM reports WHERE reporter_id = ? OR reported_id = ?", (self.user_id, self.user_id))

            await db_instance.connection.commit()

            await interaction.response.send_message(
                f"✅ **Profil supprimé définitivement**\n\n"
                f"Le profil de **{self.prenom}** et toutes les données associées ont été supprimés.\n"
                f"Vous pouvez créer un nouveau profil à tout moment avec `/createprofile`.",
                ephemeral=True
            )

        except Exception as e:
            print(f"❌ Erreur confirm_delete: {e}")
            await interaction.response.send_message(
                "❌ Erreur lors de la suppression. Veuillez contacter un administrateur.",
                ephemeral=True
            )

        self.stop()

    @discord.ui.button(label="❌ Annuler", style=discord.ButtonStyle.secondary)
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "✅ Suppression annulée. Votre profil est conservé.",
            ephemeral=True
        )
        self.stop()

async def setup(bot):
    """Fonction obligatoire pour charger le cog"""
    await bot.add_cog(Profile(bot))
