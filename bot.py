
import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# ──────────────── CONFIG ────────────────
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ Erreur : DISCORD_TOKEN non trouvé dans les variables d'environnement.")
    print("💡 Ajoutez votre token Discord dans les Secrets de Replit avec la clé 'DISCORD_TOKEN'")
    exit(1)

# ──────────────── BOT SETUP ────────────────
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Liste des cogs à charger
COGS = [
    'cogs.utils',
    'cogs.setup',
    'cogs.profile', 
    'cogs.admin',
    'cogs.match_advanced'
    # 'cogs.match' # Désactivé - conflit avec match_advanced
    # 'cogs.match_proactive' # Désactivé pour l'instant
]

@bot.event
async def on_ready():
    """Événement déclenché quand le bot est prêt"""
    try:
        # Synchroniser les commandes slash
        synced = await bot.tree.sync()
        print(f"✅ Bot connecté : {bot.user} (ID: {bot.user.id})")
        print(f"✅ {len(synced)} commandes slash synchronisées")
    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation des commandes: {e}")

async def load_cogs():
    """Charger tous les cogs de manière asynchrone"""
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            print(f"✅ Cog chargé : {cog}")
        except Exception as e:
            print(f"❌ Erreur lors du chargement de {cog}: {e}")

# ──────────────── MAIN ────────────────
async def main():
    """Fonction principale asynchrone"""
    async with bot:
        # Charger les cogs
        await load_cogs()
        # Démarrer le bot
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
