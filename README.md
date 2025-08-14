# Matching Bot Discord

Un bot Discord de matching sophistiqué qui permet aux utilisateurs de créer des profils et de trouver des correspondances basées sur leurs intérêts communs.

## 🌟 Fonctionnalités

- 🏷️ **Gestion de Profils**: Création, suppression et consultation de profils personnalisés
- 💖 **Système de Matching**: Algorithme intelligent basé sur les intérêts communs et la similarité vectorielle  
- 🔒 **Sécurité & Confidentialité**: Filtrage d'âge, messages anonymisés, aucune donnée sensible collectée
- 📱 **Interface Moderne**: Commandes slash Discord avec interface intuitive
- 🗄️ **Base de Données Asynchrone**: Utilisation d'aiosqlite pour des performances optimales
- 🛡️ **Administration**: Outils d'export, statistiques et gestion pour les administrateurs

## 🚀 Installation sur Replit

### 1. Configuration du Token Discord

1. Allez sur le [Discord Developer Portal](https://discord.com/developers/applications)
2. Créez une nouvelle application et donnez-lui un nom
3. Allez dans la section "Bot" et cliquez sur "Add Bot"
4. Copiez le token du bot
5. Dans "Privileged Gateway Intents", activez:
   - Message Content Intent
   - Server Members Intent (optionnel)
6. Dans "OAuth2" > "URL Generator":
   - **Scopes**: Cochez `bot` et `applications.commands`
   - **Bot Permissions**: Cochez au minimum :
     - Send Messages
     - Use Slash Commands
     - Read Message History
     - Send Messages in Threads
     - Embed Links
     - Read Messages/View Channels
7. **IMPORTANT**: Copiez l'URL générée et utilisez-la pour inviter le bot sur votre serveur
   - Sans cette invitation, les utilisateurs ne pourront pas utiliser le bot
   - L'URL ressemble à : `https://discord.com/oauth2/authorize?client_id=VOTRE_BOT_ID&permissions=XXXXX&scope=bot%20applications.commands`

### 2. Configuration sur Replit

1. Dans votre projet Replit, allez dans l'onglet "Secrets" (🔒)
2. Ajoutez un nouveau secret:
   - **Clé**: `DISCORD_TOKEN`
   - **Valeur**: Votre token Discord (celui copié à l'étape 1.4)

### 3. Installation des dépendances

Les dépendances seront installées automatiquement au premier lancement:
- `discord.py>=2.2.0`
- `aiosqlite` 
- `python-dotenv`

### 4. Lancement

Cliquez simplement sur le bouton "Run" ou exécutez:
```bash
python3 bot.py
```

## ⚠️ Problème Courant : "Je ne peux pas utiliser le bot"

Si vous ne voyez pas les commandes slash ou ne pouvez pas utiliser le bot, c'est que **le bot n'est pas invité correctement** sur votre serveur.

### Solution Rapide
1. Retournez sur le [Discord Developer Portal](https://discord.com/developers/applications)
2. Sélectionnez votre application bot  
3. Allez dans **OAuth2 > URL Generator**
4. Cochez exactement :
   - **Scopes** : `bot` + `applications.commands`
   - **Permissions** : Send Messages, Use Slash Commands, Read Message History
5. **Copiez l'URL générée** (elle commence par `https://discord.com/oauth2/authorize...`)
6. **Ouvrez cette URL** et sélectionnez votre serveur pour inviter le bot
7. Attendez 1-2 minutes puis tapez `/` dans un canal → Les commandes doivent apparaître

### Vérification
- Le bot apparaît dans la liste des membres de votre serveur
- Quand vous tapez `/`, vous voyez 9 commandes du bot
- Le bot a le rôle avec les bonnes permissions
- **Important**: Toutes vos commandes sont invisibles (ephemeral) - personne d'autre ne les voit

## 📋 Commandes Disponibles

### 👤 Gestion de Profil
- `/createprofile` - Créer votre profil de matching
- `/viewprofile` - Voir votre profil actuel  
- `/deleteprofile` - Supprimer votre profil

### 💕 Matching
- `/findmatch` - Trouver une correspondance (réponse par réactions ✅/❌)

### 🛡️ Administration (Réservé aux admins)
- `/setup_channel` - Configurer le salon d'information du bot
- `/update_info` - Mettre à jour l'embed d'information
- `/export_profiles` - Exporter tous les profils
- `/list_profiles` - Lister les profils existants
- `/stats` - Statistiques du bot

## 🧪 Plan de Tests Manuels

### Test 1: Création de Profil
1. Utilisez `/createprofile`
2. Remplissez tous les champs:
   - Prénom: "Alex"
   - Pronoms: "il/elle"  
   - Âge: 20 (entre 13 et 30 ans)
   - Intérêts: "musique, cinéma, voyage"
   - Description: "Passionné de cinéma et de musique"

**Résultat attendu**: ✅ Confirmation de création avec résumé du profil

### Test 2: Recherche de Match
1. Créez un second profil avec un autre compte
2. Utilisez `/findmatch` avec le premier compte
3. Vérifiez vos messages privés

**Résultat attendu**: 💖 Match trouvé envoyé en DM avec score et détails

### Test 3: Réaction aux Matches
1. Dans vos MP, cliquez sur ✅ pour accepter ou ❌ pour refuser
2. Vérifiez que l'autre utilisateur reçoit une notification si vous acceptez

**Résultat attendu**: ✅ Réactions fonctionnelles et notifications automatiques

### Test 4: Configuration Administration
1. Utilisez `/setup_channel #general` (en tant qu'admin)
2. Vérifiez que l'embed apparaît dans le salon
3. Utilisez `/stats` pour voir les statistiques

**Résultat attendu**: 📊 Embed informatif publié et statistiques accessibles

## 🔒 Sécurité et Confidentialité

### Données Collectées
- ✅ Prénom (anonymisé dans les matches)
- ✅ Pronoms et âge
- ✅ Intérêts et description
- ✅ Avatar Discord (URL uniquement)

### Données NON Collectées
- ❌ Numéros de téléphone
- ❌ Adresses personnelles  
- ❌ Informations financières
- ❌ Messages privés entre utilisateurs

### Sécurité Intégrée
- 🔒 Filtrage automatique par âge (13-30 ans, max 8 ans d'écart)
- 🔒 Messages anonymisés pour les matches
- 🔒 Notifications en DM pour la confidentialité
- 🔒 Base de données locale (pas de cloud externe)

## ⚠️ Important - Sécurité

- **JAMAIS** committer ou partager votre token Discord
- Le token doit rester dans les Secrets de Replit uniquement
- Les données des utilisateurs sont confidentielles
- Signalez tout comportement inapproprié

## 🛠️ Structure du Projet

```
matching-bot/
├── bot.py                    # Point d'entrée principal
├── README.md                # Documentation
├── pyproject.toml          # Dépendances Python
├── cogs/                   # Modules du bot
│   ├── utils.py           # Base de données et utilitaires
│   ├── profile.py         # Gestion des profils
│   ├── match.py           # Logique de matching
│   └── admin.py           # Administration
├── database/              # Base de données SQLite
│   └── profiles.db       # (créé automatiquement)
└── data/                 # Données et sauvegardes
    └── backups/         # Exports JSON
```

## 🔧 Développement

### Ajout de Nouvelles Fonctionnalités
1. Créez un nouveau cog dans `cogs/`
2. Ajoutez-le à la liste `COGS` dans `bot.py`
3. Utilisez `db_instance` pour les interactions base de données
4. Testez en mode développement avant déploiement

### Debugging
- Consultez les logs console pour les erreurs
- La base de données se trouve dans `database/profiles.db`
- Les backups sont dans `data/backups/`

---

**Créé avec ❤️ pour faciliter les rencontres respectueuses dans la communauté Discord**
   