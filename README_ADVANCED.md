# Matching Bot Discord - Système Avancé

## Vue d'ensemble

Ce bot Discord implémente un système de matching sophistiqué avec:
- Algorithme avancé (IDF + fuzzy matching + synonymes)
- Double opt-in par défaut avec révélation mutuelle
- Suggestions proactives automatiques
- Boutons interactifs pour une meilleure UX
- Système de rapports et modération
- Séparation stricte mineur/majeur

## Installation sur Replit

### 1. Configuration des Secrets
Dans l'onglet "Secrets" de Replit, ajoutez:
- `DISCORD_TOKEN`: Votre token de bot Discord

### 2. Installation des dépendances
Les dépendances sont automatiquement installées :
- discord.py >= 2.2.0
- aiosqlite (base de données)
- python-dotenv (variables d'environnement)
- psutil (monitoring système)

### 3. Configuration Discord Bot
1. Allez sur https://discord.com/developers/applications
2. Créez une nouvelle application
3. Dans "Bot", créez un bot et copiez le token
4. Dans "OAuth2 > URL Generator":
   - Scopes: `bot`, `applications.commands`
   - Permissions: Send Messages, Read Message History, Use Slash Commands, Send Messages in Threads

### 4. Lancement
Cliquez sur "Run" dans Replit. Le bot va :
- Créer automatiquement la base de données SQLite
- Synchroniser les commandes slash
- Démarrer le système (proactif désactivé par défaut)

## Architecture du Système

### Modules principaux
- `bot.py` - Point d'entrée, chargement des cogs
- `cogs/utils_match.py` - Algorithmes de matching et utilitaires
- `cogs/match_advanced.py` - Système de matching avec double opt-in  
- `cogs/match_proactive.py` - Suggestions automatiques
- `cogs/utils.py` - Database manager et utilitaires base

### Base de données (SQLite)
- `profiles` - Profils utilisateurs avec intérêts canoniques
- `matches` - Historique des correspondances (pending/accepted/rejected)
- `suggestions` - Log des suggestions proactives
- `reports` - Signalements de profils pour modération

## Commandes Utilisateur

### Gestion de profil
- `/createprofile` - Créer son profil (1 seul par utilisateur)
- `/viewprofile` - Consulter son profil
- `/deleteprofile` - Supprimer définitivement son profil  
- `/editprofile` - Modifier son profil existant

### Matching
- `/findmatch` - Lancer une recherche de correspondances
- Boutons en DM: [Accepter] [Voir profil] [Passer] [Signaler]
- Système double opt-in: révélation mutuelle après accord des deux

### Suggestions proactives
- Désactivables via bouton dans les DMs
- Configurables par les admins
- Respectent les cooldowns et limites quotidiennes

## Commandes Admin

### Configuration
- `/config_proactive` - Configurer le système automatique
  - `enabled: true/false` - Activer/désactiver  
  - `interval: 60` - Minutes entre cycles
  - `max_daily: 3` - Suggestions max par jour/utilisateur

### Monitoring  
- `/stats` - Statistiques générales
- `/export_profiles` - Export JSON des profils
- `/list_profiles` - Liste des profils actifs

## Algorithme de Matching

### Étapes de calcul
1. **Normalisation**: lowercase, sans accents, underscore
2. **Canonicalisation**: mapping vers synonymes configurables
3. **IDF**: `weight(tag) = log((1 + N) / (1 + df(tag))) + 1`
4. **Scores partiels**:
   - `S_interests = weighted_jaccard + fuzzy_matches`  
   - `S_age = exp(-(|ageA - ageB|²) / (2 * σ²))` avec σ=4
   - `S_personality = cosine(vectorA, vectorB)` si disponible

### Score final
```
Score = 0.55 × S_interests + 0.25 × S_personality + 0.20 × S_age
```

Poids configurables dans `cogs/match_advanced.py`.

## Flux de Matching Détaillé

### Manuel (`/findmatch`)
1. Utilisateur A lance `/findmatch`
2. Algorithme trouve candidats compatibles  
3. DM anonymisé envoyé à A avec boutons
4. Si A clique [Accepter]:
   - Mode double opt-in (défaut): notification anonyme à B
   - Si B accepte aussi → révélation mutuelle
5. Si A clique [Passer]: suggestion suivante automatique

### Proactif (automatique) 
1. Boucle vérifie users éligibles (opt-in, pas en cooldown)
2. Trouve meilleur match pour chaque utilisateur
3. Envoie suggestion via DM avec boutons spécialisés
4. Même flux d'acceptation que manuel

### Double Opt-In
1. A exprime intérêt → notification anonyme à B
2. B peut voir "profil anonyme" et accepter/refuser
3. Si B accepte → révélation complète aux deux avec identités
4. Match enregistré comme 'accepted' en base

## Sécurité & Confidentialité

### Filtres stricts
- **Jamais de mix mineur ↔ majeur** (filtrage hard-codé)
- Maximum 8 ans d'écart d'âge
- Tranche 13-30 ans uniquement

### Anonymisation
- Profils anonymisés dans suggestions (pas de pseudo/avatar)
- Tranches d'âge au lieu d'âge exact
- Bio tronquée à 150 caractères
- Révélation complète uniquement après double accord

### Modération
- Système de signalement intégré
- Opt-out global pour suggestions proactives  
- Logs complets pour audit admin
- Suppression complète possible (`/deleteprofile`)

## Configuration Avancée

### Map des synonymes (`cogs/utils_match.py`)
```python
SYNONYMS_MAP = {
    "musique": ["music", "son", "audio", "chant", "melody"],
    "sport": ["fitness", "exercice", "gym", "athletique"],
    # ... personnalisable
}
```

### Paramètres d'algorithme
```python
DEFAULT_WEIGHTS = {
    "interests": 0.55,
    "personality": 0.25, 
    "age": 0.20
}
DEFAULT_AGE_SIGMA = 4.0
FUZZY_THRESHOLD = 0.8
```

### Options système proactif
```python
config = {
    "enabled": False,
    "interval_minutes": 60,
    "cooldown_hours": 24, 
    "max_per_user_per_day": 3,
    "min_activity_score": 0.5
}
```

## Tests Manuels

### Test 1: Matching de base
```
1. Créer profil A: âge=20, intérêts="musique,sport,lecture"  
2. Créer profil B: âge=22, intérêts="music,fitness,livre"
3. A fait /findmatch → doit proposer B avec score élevé
✅ Résultat: B proposé avec score >70% via synonymes
```

### Test 2: Double opt-in
```
1. A accepte suggestion de B
2. Vérifier DM anonyme reçu par B  
3. B accepte → révélation mutuelle
4. Vérifier identités complètes révélées aux deux
✅ Résultat: Flow complet fonctionnel  
```

### Test 3: Filtres de sécurité
```
1. Créer profil mineur (17 ans) et majeur (18 ans)
2. Chacun fait /findmatch → ne doivent jamais se voir  
3. Tester écart >8 ans → pas de match
✅ Résultat: Filtres stricts respectés
```

### Test 4: Système proactif
```
1. Admin: /config_proactive enabled:true interval:1  
2. Attendre 1-2 minutes
3. Vérifier DM proactif reçu par utilisateurs éligibles
4. Tester bouton [Désactiver suggestions] 
✅ Résultat: Boucle active et opt-out fonctionnel
```

### Test 5: DMs fermés
```
1. Fermer DMs Discord pour utilisateur B
2. A accepte suggestion de B  
3. Vérifier gestion gracieuse de l'erreur
✅ Résultat: Fallback informatif pour A
```

## Monitoring & Logs

### Logs dans console
- Démarrages de cycles proactifs
- Erreurs de DM (forbidden/not found)  
- Statistiques de matching par cycle
- Erreurs de base de données

### Métriques disponibles
- Nb profils actifs
- Matches réussis vs échoués
- Taux d'acceptation double opt-in
- Suggestions proactives envoyées/acceptées

## Dépannage

### Bot ne répond pas
1. Vérifier `DISCORD_TOKEN` dans Secrets
2. Vérifier permissions bot sur serveur
3. Consulter logs pour erreurs de sync

### Pas de suggestions
1. Vérifier filtres d'âge (13-30, max 8 ans écart)
2. Créer plus de profils de test variés
3. Ajuster weights d'algorithme si besoin

### Erreurs de base
1. Database recréée au redémarrage si corrompue
2. Migrations automatiques des tables
3. Cache IDF rechargé au démarrage

## Support

Pour questions spécifiques:
1. Consulter logs console Replit
2. Tester commandes en mode debug  
3. Vérifier configuration dans code source

**Note**: Système conçu pour serveurs moyens (~100-1000 utilisateurs). Pour plus gros volumes, optimisations nécessaires (cache Redis, pagination, etc.).