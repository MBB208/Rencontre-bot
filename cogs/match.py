import discord
from discord.ext import commands
from discord import app_commands
from .utils import db_instance, deserialize_interests, deserialize_vector, cosine_similarity, calculate_interests_similarity
import json

class Match(commands.Cog):
    """Cog pour la logique de matching entre utilisateurs"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="findmatch", description="Trouver une correspondance basée sur vos intérêts")
    async def findmatch(self, interaction: discord.Interaction):
        """Trouver et proposer un match pour l'utilisateur"""
        user_id = str(interaction.user.id)
        
        try:
            # Récupérer le profil de l'utilisateur
            async with db_instance.connection.execute(
                "SELECT * FROM profiles WHERE user_id = ?", 
                (user_id,)
            ) as cursor:
                user_profile = await cursor.fetchone()
            
            if not user_profile:
                await interaction.response.send_message(
                    "❌ Vous devez créer un profil avant de chercher des correspondances.\n"
                    "Utilisez `/createprofile` pour commencer !",
                    ephemeral=True
                )
                return
            
            # Extraire les données du profil utilisateur
            user_age = user_profile[3]
            user_interests = deserialize_interests(user_profile[4])
            user_vector = deserialize_vector(user_profile[7])
            
            # Récupérer tous les autres profils (excluant l'utilisateur actuel)
            async with db_instance.connection.execute(
                "SELECT * FROM profiles WHERE user_id != ?", 
                (user_id,)
            ) as cursor:
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
                profile_user_id = profile[0]
                profile_age = profile[3]
                profile_interests = deserialize_interests(profile[4])
                profile_vector = deserialize_vector(profile[7])
                
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
                
                # Calculer le score basé sur les intérêts communs
                interests_score = calculate_interests_similarity(user_interests, profile_interests)
                
                # Calculer la similarité cosinus des vecteurs
                vector_score = cosine_similarity(user_vector, profile_vector)
                
                # Score final (pondération: 70% intérêts, 30% vecteur)
                final_score = (interests_score * 0.7) + (vector_score * 0.3)
                
                # Ajouter à la liste si score significatif
                if final_score > 0.1:  # Seuil minimum
                    matches.append({
                        'user_id': profile_user_id,
                        'prenom': profile[1],
                        'pronoms': profile[2],
                        'age': profile_age,
                        'interests': profile_interests,
                        'description': profile[5],
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
            
            # Trier par score décroissant et prendre le meilleur
            matches.sort(key=lambda x: x['score'], reverse=True)
            best_match = matches[0]
            
            # RÉPONDRE IMMÉDIATEMENT à l'interaction pour éviter l'expiration
            await interaction.response.send_message(
                "🔍 **Recherche de correspondance...**\n\n"
                f"Correspondance trouvée avec un score de {best_match['score']:.0%} ! "
                "Je vous envoie les détails en message privé. 📩",
                ephemeral=True
            )
            
            # Puis traiter l'envoi du DM (après avoir répondu à l'interaction)
            try:
                dm_channel = await interaction.user.create_dm()
                
                # Calculer les intérêts communs
                common_interests = list(set(user_interests) & set(best_match['interests']))
                common_interests_str = ", ".join(common_interests[:5])  # Max 5 intérêts
                if len(common_interests) > 5:
                    common_interests_str += f" (+{len(common_interests)-5} autres)"
                
                embed = discord.Embed(
                    title="💖 Correspondance trouvée !",
                    description="Voici une personne qui pourrait vous intéresser :",
                    color=discord.Color.pink()
                )
                
                embed.add_field(
                    name="👤 Profil", 
                    value=f"**Prénom :** {best_match['prenom']}\n"
                          f"**Pronoms :** {best_match['pronoms']}\n"
                          f"**Âge :** {best_match['age']} ans", 
                    inline=True
                )
                
                embed.add_field(
                    name="🎯 Compatibilité", 
                    value=f"**Score :** {best_match['score']:.0%}\n"
                          f"**Intérêts communs :** {len(common_interests)}", 
                    inline=True
                )
                
                embed.add_field(
                    name="💭 Description", 
                    value=best_match['description'][:200] + ('...' if len(best_match['description']) > 200 else ''), 
                    inline=False
                )
                
                if common_interests:
                    embed.add_field(
                        name="🤝 Vos intérêts communs", 
                        value=common_interests_str, 
                        inline=False
                    )
                
                embed.add_field(
                    name="🎯 Répondre à cette correspondance", 
                    value="• Réagissez ✅ pour **accepter** cette correspondance\n"
                          "• Réagissez ❌ pour **refuser** et passer au suivant\n"
                          "• Utilisez `/findmatch` à nouveau pour d'autres suggestions", 
                    inline=False
                )
                
                embed.set_footer(text="💡 Ce profil a été anonymisé pour votre sécurité")
                
                match_message = await dm_channel.send(embed=embed)
                
                # Ajouter les réactions pour accepter/refuser
                await match_message.add_reaction('✅')
                await match_message.add_reaction('❌')
                
                # Sauvegarder l'info du match pour traiter les réactions
                await self.save_match_proposal(
                    interaction.user.id, 
                    best_match['user_id'], 
                    match_message.id,
                    best_match['score']
                )
                
                # Envoyer un message de suivi si possible
                try:
                    await interaction.followup.send(
                        "✅ **Message privé envoyé avec succès !**",
                        ephemeral=True
                    )
                except:
                    pass  # Ignore les erreurs de followup
                    
            except discord.Forbidden:
                # Si l'envoi en DM échoue, envoyer un followup
                try:
                    # Recalculer common_interests au cas où
                    common_interests_fallback = list(set(user_interests) & set(best_match['interests']))
                    await interaction.followup.send(
                        "🔒 **Impossible d'envoyer en privé**\n\n"
                        f"**Correspondance trouvée** (Score: {best_match['score']:.0%})\n"
                        f"**Âge :** {best_match['age']} ans\n"
                        f"**Intérêts communs :** {len(common_interests_fallback)}\n\n"
                        "Activez les messages privés pour recevoir plus de détails !",
                        ephemeral=True
                    )
                except:
                    pass  # Ignore les erreurs de followup
                
        except Exception as e:
            print(f"❌ Erreur lors de la recherche de match pour {user_id}: {e}")
            # Vérifier si l'interaction a déjà été répondue
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Une erreur s'est produite lors de la recherche de correspondances. "
                    "Veuillez réessayer plus tard.",
                    ephemeral=True
                )
    
    async def save_match_proposal(self, requester_id: int, target_id: str, message_id: int, score: float):
        """Sauvegarder une proposition de match pour traitement des réactions"""
        try:
            # Créer table si elle n'existe pas
            await db_instance.connection.execute("""
                CREATE TABLE IF NOT EXISTS match_proposals (
                    message_id TEXT PRIMARY KEY,
                    requester_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    score REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending'
                )
            """)
            
            await db_instance.connection.execute("""
                INSERT OR REPLACE INTO match_proposals (message_id, requester_id, target_id, score)
                VALUES (?, ?, ?, ?)
            """, (str(message_id), str(requester_id), target_id, score))
            
            await db_instance.connection.commit()
            
        except Exception as e:
            print(f"❌ Erreur sauvegarde match proposal: {e}")
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Gérer les réactions sur les messages de correspondance"""
        # Ignorer les réactions du bot
        if user.bot:
            return
            
        # Vérifier si c'est une réaction sur un message de match
        try:
            async with db_instance.connection.execute(
                "SELECT requester_id, target_id, score FROM match_proposals WHERE message_id = ? AND status = 'pending'",
                (str(reaction.message.id),)
            ) as cursor:
                match_data = await cursor.fetchone()
            
            if not match_data:
                return  # Pas un message de match ou déjà traité
            
            requester_id, target_id, score = match_data
            
            # Vérifier que c'est le bon utilisateur qui réagit
            if str(user.id) != requester_id:
                return
            
            if str(reaction.emoji) == '✅':
                # Accepter la correspondance
                await self.handle_match_acceptance(user, target_id, score, reaction.message.id)
            elif str(reaction.emoji) == '❌':
                # Refuser la correspondance
                await self.handle_match_rejection(user, target_id, reaction.message.id)
                
        except Exception as e:
            print(f"❌ Erreur gestion réaction: {e}")
    
    async def handle_match_acceptance(self, accepter_user, target_id: str, score: float, message_id: int):
        """Gérer l'acceptation d'une correspondance"""
        try:
            # Récupérer les profils
            async with db_instance.connection.execute(
                "SELECT prenom FROM profiles WHERE user_id = ?", 
                (str(accepter_user.id),)
            ) as cursor:
                accepter_profile = await cursor.fetchone()
            
            async with db_instance.connection.execute(
                "SELECT prenom FROM profiles WHERE user_id = ?", 
                (target_id,)
            ) as cursor:
                target_profile = await cursor.fetchone()
            
            if not accepter_profile or not target_profile:
                return
            
            # Marquer le match comme accepté
            await db_instance.connection.execute(
                "UPDATE match_proposals SET status = 'accepted' WHERE message_id = ?",
                (str(message_id),)
            )
            await db_instance.connection.commit()
            
            # Notifier l'autre utilisateur
            try:
                target_user = await self.bot.fetch_user(int(target_id))
                if target_user:
                    dm_channel = await target_user.create_dm()
                    
                    embed = discord.Embed(
                        title="💝 Correspondance acceptée !",
                        description=f"**{accepter_profile[0]}** a accepté votre correspondance !",
                        color=discord.Color.green()
                    )
                    
                    embed.add_field(
                        name="🎉 Félicitations !",
                        value="Vous pouvez maintenant entrer en contact avec cette personne.\n"
                              "Nous vous encourageons à faire connaissance dans un environnement sûr !",
                        inline=False
                    )
                    
                    embed.add_field(
                        name="🛡️ Conseils de sécurité",
                        value="• Restez respectueux dans vos échanges\n"
                              "• Ne partagez pas d'informations personnelles sensibles\n" 
                              "• Signalez tout comportement inapproprié",
                        inline=False
                    )
                    
                    await dm_channel.send(embed=embed)
                    
            except Exception as notification_error:
                print(f"❌ Erreur notification acceptation: {notification_error}")
            
            # Confirmer à celui qui a accepté
            try:
                dm_channel = await accepter_user.create_dm()
                await dm_channel.send(
                    f"✅ **Correspondance acceptée !**\n\n"
                    f"J'ai notifié **{target_profile[0]}** que vous avez accepté la correspondance. "
                    f"Bonne chance pour la suite ! 🍀"
                )
            except:
                pass
                
        except Exception as e:
            print(f"❌ Erreur handle_match_acceptance: {e}")
    
    async def handle_match_rejection(self, rejecter_user, target_id: str, message_id: int):
        """Gérer le refus d'une correspondance"""
        try:
            # Marquer le match comme refusé
            await db_instance.connection.execute(
                "UPDATE match_proposals SET status = 'rejected' WHERE message_id = ?",
                (str(message_id),)
            )
            await db_instance.connection.commit()
            
            # Confirmer à celui qui a refusé
            try:
                dm_channel = await rejecter_user.create_dm()
                await dm_channel.send(
                    "❌ **Correspondance refusée.**\n\n"
                    "Utilisez `/findmatch` à nouveau pour voir d'autres suggestions !"
                )
            except:
                pass
                
        except Exception as e:
            print(f"❌ Erreur handle_match_rejection: {e}")

async def setup(bot):
    """Fonction obligatoire pour charger le cog"""
    await bot.add_cog(Match(bot))