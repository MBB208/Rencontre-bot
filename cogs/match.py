
import discord
from discord.ext import commands
from discord import app_commands
from .utils import db_instance, deserialize_interests, calculate_interests_similarity

class Match(commands.Cog):
    """Cog pour la logique de matching entre utilisateurs"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="findmatch", description="Trouver une correspondance basée sur vos intérêts")
    async def findmatch(self, interaction: discord.Interaction):
        """Trouver et proposer un match pour l'utilisateur"""
        user_id = str(interaction.user.id)
        
        try:
            # Vérifier que la connexion DB existe
            if not db_instance.connection:
                await interaction.response.send_message(
                    "❌ Erreur de base de données. Veuillez réessayer.",
                    ephemeral=True
                )
                return

            # Récupérer le profil de l'utilisateur
            cursor = await db_instance.connection.execute(
                "SELECT user_id, prenom, pronoms, age, interets, description FROM profiles WHERE user_id = ?", 
                (user_id,)
            )
            user_profile = await cursor.fetchone()
            
            if not user_profile:
                await interaction.response.send_message(
                    "❌ **Vous devez créer un profil avant de chercher des correspondances.**\n\n"
                    "Utilisez `/createprofile` pour commencer !",
                    ephemeral=True
                )
                return
            
            # Extraire les données du profil utilisateur
            user_age = user_profile[3]
            user_interests = deserialize_interests(user_profile[4])
            
            # Récupérer tous les autres profils (excluant l'utilisateur actuel)
            cursor = await db_instance.connection.execute(
                "SELECT user_id, prenom, pronoms, age, interets, description FROM profiles WHERE user_id != ?", 
                (user_id,)
            )
            all_profiles = await cursor.fetchall()
            
            if not all_profiles:
                await interaction.response.send_message(
                    "😔 **Aucune correspondance trouvée**\n\n"
                    "Il n'y a pas encore d'autres utilisateurs avec un profil. "
                    "Revenez plus tard quand d'autres personnes auront rejoint !",
                    ephemeral=True
                )
                return
            
            # Calculer les scores de matching
            matches = []
            
            for profile in all_profiles:
                profile_age = profile[3]
                profile_interests = deserialize_interests(profile[4])
                
                # FILTRAGE STRICT : Jamais mélanger mineurs et majeurs
                user_is_minor = user_age < 18
                profile_is_minor = profile_age < 18
                
                # Exclure si mélange mineur/majeur
                if user_is_minor != profile_is_minor:
                    continue
                
                # Filtrage par écart d'âge (maximum 8 ans)
                age_diff = abs(user_age - profile_age)
                if age_diff > 8:
                    continue
                
                # Vérifier la tranche d'âge autorisée (13-30 ans)
                if profile_age < 13 or profile_age > 30:
                    continue
                
                # Calculer le score basé uniquement sur les intérêts communs
                interests_score = calculate_interests_similarity(user_interests, profile_interests)
                
                # Score final (pondération: 100% intérêts)
                final_score = interests_score
                
                # Ajouter à la liste si score significatif
                if final_score > 0.05:  # Seuil minimum réduit
                    matches.append({
                        'user_id': profile[0],
                        'prenom': profile[1],
                        'pronoms': profile[2],
                        'age': profile_age,
                        'interests': profile_interests,
                        'description': profile[5] if profile[5] else "Pas de description",
                        'score': final_score
                    })
            
            if not matches:
                await interaction.response.send_message(
                    "😔 **Aucune correspondance trouvée**\n\n"
                    "Aucun utilisateur ne correspond à vos critères actuellement. "
                    "Essayez de diversifier vos intérêts ou revenez plus tard !",
                    ephemeral=True
                )
                return
            
            # Trier par score décroissant
            matches.sort(key=lambda x: x['score'], reverse=True)
            
            # Afficher le premier match
            await self.show_match(interaction, matches, 0, user_interests)
            
        except Exception as e:
            print(f"❌ Erreur findmatch pour {user_id}: {e}")
            import traceback
            traceback.print_exc()
            
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Une erreur s'est produite lors de la recherche de correspondances. "
                    "Veuillez réessayer plus tard.",
                    ephemeral=True
                )
    
    async def show_match(self, interaction, matches, index, user_interests):
        """Afficher un match spécifique avec navigation"""
        try:
            if index >= len(matches):
                msg = ("😔 **Plus de correspondances disponibles**\n\n"
                       "Vous avez vu tous les profils compatibles. "
                       "Utilisez à nouveau `/findmatch` plus tard !")
                
                if interaction.response.is_done():
                    await interaction.edit_original_response(content=msg, embed=None, view=None)
                else:
                    await interaction.response.send_message(msg, ephemeral=True)
                return
            
            current_match = matches[index]
            
            # Trouver les intérêts en commun
            common_interests = list(set(user_interests) & set(current_match['interests']))
            common_text = ", ".join(common_interests[:3]) if common_interests else "Découvrez vos affinités"
            if len(common_interests) > 3:
                common_text += f" (+{len(common_interests)-3} autres)"
            
            # Afficher le match avec boutons d'action
            embed = discord.Embed(
                title=f"🔍 Correspondance {index + 1}/{len(matches)}",
                description=f"Voici une personne qui pourrait vous intéresser :",
                color=discord.Color.green()
            )
            embed.add_field(name="👤 Prénom", value=current_match['prenom'], inline=True)
            embed.add_field(name="🏷️ Pronoms", value=current_match['pronoms'], inline=True)
            embed.add_field(name="🎂 Âge", value=f"{current_match['age']} ans", inline=True)
            embed.add_field(name="💖 Compatibilité", value=f"{current_match['score']:.0%}", inline=True)
            embed.add_field(name="🎯 En commun", value=common_text, inline=True)
            
            description = current_match['description']
            if len(description) > 150:
                description = description[:150] + "..."
                
            embed.add_field(name="💭 Description", value=description, inline=False)
            
            # Créer la vue avec boutons
            view = MatchView(
                current_match['user_id'], 
                str(interaction.user.id), 
                current_match['prenom'],
                matches,
                index,
                user_interests,
                self
            )
            
            if interaction.response.is_done():
                await interaction.edit_original_response(embed=embed, view=view)
            else:
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                
        except Exception as e:
            print(f"❌ Erreur show_match: {e}")
            import traceback
            traceback.print_exc()

class MatchView(discord.ui.View):
    """Vue avec boutons pour accepter/refuser un match"""
    
    def __init__(self, target_user_id, requester_id, target_name, matches=None, current_index=0, user_interests=None, match_cog=None):
        super().__init__(timeout=300)  # 5 minutes
        self.target_user_id = target_user_id
        self.requester_id = requester_id
        self.target_name = target_name
        self.matches = matches or []
        self.current_index = current_index
        self.user_interests = user_interests or []
        self.match_cog = match_cog
    
    @discord.ui.button(label="💖 Accepter", style=discord.ButtonStyle.success)
    async def accept_match(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Accepter le match proposé"""
        try:
            # Récupérer les profils complets
            async with db_instance.connection.execute(
                "SELECT prenom, pronoms, age, description, interets FROM profiles WHERE user_id = ?", 
                (self.requester_id,)
            ) as cursor:
                requester_profile = await cursor.fetchone()
            
            async with db_instance.connection.execute(
                "SELECT prenom, pronoms, age, description, interets FROM profiles WHERE user_id = ?", 
                (self.target_user_id,)
            ) as cursor:
                target_profile = await cursor.fetchone()
            
            if not requester_profile or not target_profile:
                await interaction.response.send_message(
                    "❌ Erreur lors de la récupération des profils.",
                    ephemeral=True
                )
                return
            
            # Envoyer notification détaillée à la personne ciblée
            try:
                target_user = await interaction.client.fetch_user(int(self.target_user_id))
                if target_user:
                    # Créer le DM channel
                    dm_channel = await target_user.create_dm()
                    
                    # Corriger l'ordre des indices pour les intérêts et description
                    interests_text = requester_profile[4] if requester_profile[4] else "Aucun intérêt spécifié"
                    description_text = requester_profile[3] if requester_profile[3] else "Aucune description"
                    
                    embed_target = discord.Embed(
                        title="💌 Quelqu'un s'intéresse à vous !",
                        description=f"**{requester_profile[0]}** souhaite faire votre connaissance !",
                        color=discord.Color.blue()
                    )
                    embed_target.add_field(name="👤 Prénom", value=requester_profile[0], inline=True)
                    embed_target.add_field(name="🏷️ Pronoms", value=requester_profile[1], inline=True)
                    embed_target.add_field(name="🎂 Âge", value=f"{requester_profile[2]} ans", inline=True)
                    embed_target.add_field(name="🎯 Intérêts", value=interests_text[:100] + ("..." if len(interests_text) > 100 else ""), inline=False)
                    embed_target.add_field(name="💭 Description", value=description_text[:150] + ("..." if len(description_text) > 150 else ""), inline=False)
                    embed_target.add_field(name="📩 Pour répondre", value=f"Contactez directement <@{self.requester_id}> si vous êtes intéressé(e) !", inline=False)
                    embed_target.set_footer(text="💡 Soyez respectueux et bienveillant dans vos échanges")
                    
                    await dm_channel.send(embed=embed_target)
                    print(f"✅ Notification envoyée à {self.target_user_id} ({target_profile[0]})")
                    
            except discord.Forbidden:
                print(f"❌ Impossible d'envoyer DM à {self.target_user_id} (DMs fermés)")
            except discord.NotFound:
                print(f"❌ Utilisateur {self.target_user_id} introuvable")
            except Exception as e:
                print(f"❌ Erreur envoi DM à {self.target_user_id}: {e}")
            
            # Réponse dans l'interaction
            await interaction.response.send_message(
                f"💖 **Match accepté avec {target_profile[0]} !**\n\n"
                f"✅ J'ai envoyé une notification détaillée à cette personne.\n"
                f"🤞 Si l'intérêt est mutuel, vous serez contacté(e) directement !",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"❌ Erreur accept_match: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite. Veuillez réessayer.",
                ephemeral=True
            )
        
        self.stop()
    
    @discord.ui.button(label="👎 Suivant", style=discord.ButtonStyle.secondary)
    async def next_match(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Passer au match suivant"""
        if self.matches and self.match_cog:
            next_index = self.current_index + 1
            if next_index < len(self.matches):
                await self.match_cog.show_match(interaction, self.matches, next_index, self.user_interests)
            else:
                await interaction.response.send_message(
                    "😔 **Plus de correspondances disponibles**\n\n"
                    "Vous avez vu tous les profils compatibles. "
                    "Utilisez à nouveau `/findmatch` plus tard pour de nouveaux profils !",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                "⏭️ **Match ignoré.**\n\n"
                "Utilisez à nouveau `/findmatch` pour voir d'autres correspondances !",
                ephemeral=True
            )
        self.stop()
    
    @discord.ui.button(label="🚨 Signaler", style=discord.ButtonStyle.danger)
    async def report_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Signaler un profil problématique"""
        try:
            # Enregistrer le signalement
            await db_instance.connection.execute(
                "INSERT INTO reports (reporter_id, reported_id, reason, timestamp) VALUES (?, ?, ?, datetime('now'))",
                (self.requester_id, self.target_user_id, "Signalement via match")
            )
            await db_instance.connection.commit()
            
            print(f"🚨 SIGNALEMENT: {self.requester_id} a signalé {self.target_user_id} ({self.target_name})")
            
            await interaction.response.send_message(
                f"🚨 **Profil signalé**\n\n"
                f"**Utilisateur signalé :** {self.target_name}\n\n"
                f"✅ Merci de nous avoir alertés. Ce profil sera examiné par notre équipe de modération.",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"❌ Erreur signalement: {e}")
            await interaction.response.send_message(
                "❌ Erreur lors du signalement. Veuillez réessayer.",
                ephemeral=True
            )
        
        self.stop()

async def setup(bot):
    """Fonction obligatoire pour charger le cog"""
    await bot.add_cog(Match(bot))
