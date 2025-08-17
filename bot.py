import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

# ──────────────── CHARGEMENT DES VARIABLES D'ENVIRONNEMENT ────────────────
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ Erreur : DISCORD_TOKEN non trouvé dans les variables d'environnement.")
    exit(1)

# ──────────────── CONFIGURATION DU BOT ────────────────
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Variable pour éviter les synchronisations multiples
bot.synced = False

# ──────────────── LISTE DES COGS À CHARGER ────────────────
COGS = [
    'cogs.setup',    # Configuration de base
    'cogs.admin',    # Administration  
    'cogs.profile',  # Gestion des profils
    'cogs.match'     # Système de matching
]

# ──────────────── ÉVÉNEMENTS ────────────────
@bot.event
async def on_ready():
    print(f"✅ Bot connecté : {bot.user} (ID: {bot.user.id})")
    print(f"✅ Connecté à {len(bot.guilds)} serveur(s)")

    # Initialiser la base de données
    try:
        from cogs.utils import db_instance
        if not await db_instance.is_connected():
            await db_instance.connect()
        print("✅ Base de données connectée dans on_ready")
    except Exception as e:
        print(f"❌ Erreur connexion DB dans on_ready: {e}")

    # Afficher les cogs chargés
    loaded_cogs = list(bot.extensions.keys())
    print(f"📦 Cogs chargés ({len(loaded_cogs)}) : {loaded_cogs}")

    # Synchroniser les commandes slash UNE SEULE FOIS quand le bot est prêt
    if not bot.synced:
        try:
            print("🔄 Synchronisation des commandes slash...")
            synced = await bot.tree.sync()
            bot.synced = True
            print(f"✅ {len(synced)} commandes slash synchronisées")

            print("📋 Commandes slash disponibles :")
            for cmd in synced:
                print(f" - {cmd.name}")

        except Exception as e:
            print(f"❌ Erreur lors de la synchronisation des commandes: {type(e).__name__}: {e}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")

    # Changer le statut du bot
    try:
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(bot.guilds)} serveurs | /findmatch"
        )
        await bot.change_presence(activity=activity)
    except Exception as e:
        print(f"⚠️ Erreur changement de statut: {e}")

# ──────────────── GESTION D'ERREURS AMÉLIORÉE ────────────────
@bot.event
async def on_application_command_error(interaction, error):
    """Gestion des erreurs pour les commandes slash"""
    print(f"❌ Erreur commande slash {interaction.command.name if interaction.command else 'Unknown'}: {error}")
    print(f"   Type d'erreur: {type(error).__name__}")

    # Log plus détaillé pour le debug
    import traceback
    print(f"   Traceback: {traceback.format_exc()}")

    # Message d'erreur pour l'utilisateur
    embed = discord.Embed(
        title="❌ Erreur",
        description=f"Une erreur s'est produite: `{str(error)[:200]}`",
        color=discord.Color.red()
    )

    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        print(f"❌ Impossible d'envoyer le message d'erreur: {e}")

# ──────────────── FONCTIONS DE CHARGEMENT / RELOAD AMÉLIORÉES ────────────────
async def load_cog_safe(cog: str):
    """Charge ou recharge un cog en sécurité avec diagnostics détaillés."""
    print(f"🔄 Tentative de chargement: {cog}")

    try:
        # Vérifier si le fichier existe
        cog_path = cog.replace('.', '/') + '.py'
        if not os.path.exists(cog_path):
            print(f"❌ Fichier {cog_path} non trouvé")
            return False

        # Recharger si déjà chargé, sinon charger
        if cog in bot.extensions:
            await bot.reload_extension(cog)
            print(f"♻️ Cog rechargé : {cog}")
        else:
            await bot.load_extension(cog)
            print(f"✅ Cog chargé : {cog}")

        return True

    except commands.ExtensionNotFound:
        print(f"❌ Cog `{cog}` non trouvé (ExtensionNotFound)")
        print(f"   Vérifiez que le fichier {cog_path} existe")

    except commands.NoEntryPointError:
        print(f"❌ Cog `{cog}` ne contient pas de fonction setup()")
        print(f"   Ajoutez à la fin du fichier:")
        print(f"   async def setup(bot):")
        print(f"       await bot.add_cog(VotreClasse(bot))")

    except commands.ExtensionFailed as e:
        print(f"❌ Échec du chargement de {cog} (ExtensionFailed): {e}")
        print(f"   Erreur dans le code du cog:")
        import traceback
        traceback.print_exc()

    except Exception as e:
        print(f"❌ Erreur inattendue lors du chargement de {cog}: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    return False

async def load_cogs():
    """Charge tous les cogs de manière sécurisée avec compteurs."""
    print("🔧 Chargement des cogs...")
    print(f"📋 Cogs à charger: {COGS}")

    success_count = 0
    total_count = len(COGS)

    for cog in COGS:
        success = await load_cog_safe(cog)
        if success:
            success_count += 1

    print(f"📊 Résultat: {success_count}/{total_count} cogs chargés avec succès")

    if success_count == 0:
        print("🚨 ATTENTION: Aucun cog n'a été chargé !")
        print("   Le bot sera fonctionnel mais sans commandes personnalisées")
    elif success_count < total_count:
        print("⚠️  Certains cogs n'ont pas pu être chargés")
        print("   Le bot fonctionnera partiellement")
    else:
        print("🎉 Tous les cogs ont été chargés avec succès !")

# ──────────────── COMMANDE ADMIN POUR RELOAD À CHAUD ────────────────
@bot.tree.command(name="reload", description="Recharge un cog sans redémarrer le bot")
@discord.app_commands.checks.has_permissions(administrator=True)
async def reload(interaction: discord.Interaction, cog_name: str = None):
    await interaction.response.defer(ephemeral=True)

    if cog_name:
        # Ajouter le préfixe cogs. si pas présent
        if not cog_name.startswith('cogs.'):
            cog_name = f'cogs.{cog_name}'

        if cog_name in COGS:
            success = await load_cog_safe(cog_name)
            if success:
                try:
                    synced = await bot.tree.sync()
                    await interaction.followup.send(
                        f"♻️ **Cog `{cog_name}` rechargé avec succès !**\n"
                        f"🔄 {len(synced)} commandes re-synchronisées"
                    )
                except Exception as e:
                    await interaction.followup.send(
                        f"♻️ Cog `{cog_name}` rechargé, mais erreur de sync: {e}"
                    )
            else:
                await interaction.followup.send(f"❌ **Échec du reload** pour `{cog_name}`")
        else:
            available = ', '.join(COGS)
            await interaction.followup.send(
                f"❌ Cog `{cog_name}` non trouvé.\n"
                f"**Cogs disponibles:** {available}"
            )
    else:
        # Recharger tous les cogs
        await load_cogs()
        try:
            synced = await bot.tree.sync()
            loaded_count = len(bot.extensions)
            await interaction.followup.send(
                f"♻️ **Tous les cogs ont été rechargés !**\n"
                f"📦 {loaded_count} cogs chargés\n"
                f"🔄 {len(synced)} commandes re-synchronisées"
            )
        except Exception as e:
            await interaction.followup.send(f"♻️ Cogs rechargés, mais erreur de sync: {e}")

# ──────────────── FONCTION PRINCIPALE AMÉLIORÉE ────────────────
async def main():
    """Fonction principale avec diagnostic et gestion d'erreurs complète"""
    try:
        # Initialiser la base de données AVANT de charger les cogs
        try:
            from cogs.utils import init_database
            print("🔄 Initialisation de la base de données...")
            await init_database()
        except Exception as e:
            print(f"❌ Erreur initialisation DB: {e}")

        # Charger les cogs AVANT de démarrer le bot
        async with bot:
            await load_cogs()

            print("🚀 Démarrage du bot...")
            print("   (Les commandes seront synchronisées automatiquement dans on_ready)")
            await bot.start(TOKEN)

    except discord.LoginFailure:
        print("❌ ERREUR CRITIQUE: Token Discord invalide")
        print("   🔧 Solution: Vérifiez votre token dans le fichier .env")
        print("   📋 Format attendu: DISCORD_TOKEN=votre_token_ici")

    except discord.PrivilegedIntentsRequired:
        print("❌ ERREUR CRITIQUE: Intents privilégiés requis")
        print("   🔧 Solution: Activez les intents dans le Discord Developer Portal")
        print("   📋 Intents requis: message_content, members")

    except discord.HTTPException as e:
        print(f"❌ ERREUR HTTP Discord: {e}")
        print("   🔧 Vérifiez votre connexion internet et le statut de Discord")

    except KeyboardInterrupt:
        print("\n⚠️ Arrêt du bot par l'utilisateur (Ctrl+C)")

    except Exception as e:
        print(f"❌ ERREUR CRITIQUE INATTENDUE: {e}")
        print(f"   Type: {type(e).__name__}")
        import traceback
        print(f"   Traceback complet: {traceback.format_exc()}")

    finally:
        try:
            if not bot.is_closed():
                await bot.close()
                print("✅ Bot fermé proprement")
        except Exception as e:
            print(f"⚠️ Erreur lors de la fermeture: {e}")

# ──────────────── DÉMARRAGE DU BOT ────────────────
if __name__ == "__main__":
    print("🤖 Initialisation du bot de matching...")
    print(f"🔧 Python: {os.sys.version}")
    print(f"🔧 discord.py: {discord.__version__}")

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ ERREUR FATALE AU DÉMARRAGE: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        print("\n🆘 Si le problème persiste:")
        print("   1. Vérifiez votre fichier .env")
        print("   2. Vérifiez que tous les fichiers cogs existent")
        print("   3. Vérifiez les permissions du bot sur Discord")