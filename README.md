
<old_str># Discord Matching Bot

Un bot Discord sophistiqué pour connecter des utilisateurs basé sur leurs intérêts communs.

## Fonctionnalités

- Création de profils personnalisés
- Algorithme de matching intelligent
- Sécurité et modération intégrées
- Interface intuitive avec boutons Discord

## Installation

1. Cloner le projet
2. Installer les dépendances : `pip install -r requirements.txt`
3. Configurer le token Discord dans les variables d'environnement
4. Lancer avec `python bot.py`

## Utilisation

- `/createprofile` - Créer un profil
- `/findmatch` - Trouver des correspondances
- `/viewprofile` - Voir son profil
- `/deleteprofile` - Supprimer son profil

## Sécurité

Le bot applique une séparation stricte entre mineurs et majeurs et respecte la confidentialité des utilisateurs.</old_str>
<new_str># 🌟 Discord Matching Bot - Système de Rencontres Intelligent

Un bot Discord avancé qui connecte des utilisateurs basé sur leurs intérêts communs, utilisant un algorithme de matching sophistiqué avec un système de sécurité complet.

## ✨ Fonctionnalités Principales

### 🔍 **Système de Matching Avancé**
- **Algorithme intelligent** avec normalisation des synonymes (musique = music)
- **Navigation fluide** entre plusieurs correspondances
- **Score de compatibilité** affiché en pourcentage
- **Filtrage automatique** par tranches d'âge
- **Interface interactive** avec boutons Discord

### 👤 **Gestion de Profils Complète**
- **Création guidée** avec validation des données
- **Modification en temps réel** de tous les champs
- **Conseils personnalisés** pour optimiser son profil
- **Suppression sécurisée** avec effacement complet

### 🛡️ **Sécurité & Modération**
- **Séparation stricte** mineurs (13-17) / majeurs (18+)
- **Écart d'âge limité** à 8 ans maximum
- **Système de signalement** intégré
- **Modération administrative** avec outils dédiés
- **Anonymisation** des données jusqu'à acceptation mutuelle

### 🎯 **Expérience Utilisateur Optimisée**
- **Double opt-in** - révélation mutuelle après accord des deux parties
- **Navigation intuitive** - passer facilement d'un profil à l'autre
- **Guide interactif** avec boutons d'aide contextuels
- **Feedback instantané** sur la compatibilité

## 🚀 Installation et Configuration

### Prérequis
- Python 3.8+
- Un bot Discord configuré sur le [Developer Portal](https://discord.com/developers/applications)

### Installation sur Replit (Recommandé)
1. **Fork ce template** depuis Replit
2. **Configurer le token** :
   - Aller dans les **Secrets** (panneau de gauche)
   - Ajouter `DISCORD_TOKEN` avec votre token Discord
3. **Lancer le bot** : Cliquer sur **Run**

### Installation Locale
```bash
# Cloner le repository
git clone [url-du-repo]
cd discord-matching-bot

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
echo "DISCORD_TOKEN=votre_token_ici" > .env

# Lancer le bot
python bot.py
```

## 📖 Guide d'Utilisation

### 🏗️ **Première Utilisation**
1. **Créer son profil** : `/createprofile`
   ```
   Prénom: Alex
   Pronoms: il/lui
   Âge: 22
   Intérêts: guitare, randonnée, photographie, cuisine, jeux vidéo
   Description: Guitariste amateur passionné de nature et de cuisine !
   ```

2. **Lancer une recherche** : `/findmatch`
3. **Naviguer entre les profils** avec les boutons
4. **Accepter** ceux qui vous intéressent !

### ⚙️ **Commandes Disponibles**

#### **Utilisateurs**
- 🔍 `/findmatch` - Trouver des correspondances compatibles
- 👤 `/createprofile` - Créer son profil de matching
- 📄 `/viewprofile` - Consulter son profil actuel
- ✏️ `/editprofile` - Modifier un élément de son profil
- 💡 `/helpprofile` - Conseils pour un profil attractif
- 🗑️ `/deleteprofile` - Supprimer définitivement son profil
- 📖 `/guide` - Guide complet d'utilisation

#### **Administrateurs**
- 📊 `/stats` - Statistiques générales du bot
- 👥 `/list_profiles` - Lister les profils existants
- 📤 `/export_profiles` - Export JSON des profils
- 🚨 `/consultsignal` - Consulter les signalements
- 🔨 `/deleteprofileadmin` - Supprimer un profil par ID

## 🧠 Algorithme de Matching

### **Étapes de Calcul**
1. **Normalisation** - Conversion en minuscules, suppression des accents
2. **Synonymisation** - Mapping intelligent (musique ↔ music, sport ↔ fitness)
3. **Similarité Jaccard** - Calcul des intérêts communs avec bonus
4. **Score final** - Pondération avec boost pour correspondances multiples

### **Filtres de Sécurité**
```python
# Séparation stricte par âge
if user_age < 18 != profile_age < 18:
    continue  # Jamais de mélange mineur/majeur

# Écart d'âge maximum
if abs(user_age - profile_age) > 8:
    continue  # Maximum 8 ans d'écart

# Tranche d'âge autorisée
if not (13 <= profile_age <= 30):
    continue  # Âges autorisés: 13-30 ans
```

## 🎯 Processus de Matching Détaillé

### **Flow Standard**
1. **Recherche** `/findmatch` par Alice (20 ans, intérêts: guitare, randonnée)
2. **Algorithme** trouve Bob (22 ans) avec 85% de compatibilité
3. **Affichage** "En commun: guitare, randonnée (+2 autres)"
4. **Navigation** Alice peut voir plusieurs profils avec **Suivant**
5. **Acceptation** Alice clique **💖 Accepter**
6. **Notification** Bob reçoit un message anonyme
7. **Double opt-in** Si Bob accepte aussi → contact direct !

### **Interface Interactive**
```
🔍 Correspondance 1/5                    [85% compatibilité]
👤 Bob | 🏷️ il/lui | 🎂 22 ans
🎯 En commun: guitare, randonnée, photographie
💭 "Passionné de musique et de nature, toujours partant pour..."

[💖 Accepter] [👎 Suivant] [🚨 Signaler]
```

## 🛡️ Sécurité et Confidentialité

### **Protection des Mineurs**
- **Ségrégation absolue** - Aucun contact possible mineur ↔ majeur
- **Validation d'âge** - Contrôles stricts lors de la création
- **Surveillance** - Logs détaillés des interactions

### **Confidentialité**
- **Anonymisation initiale** - Pas de pseudo/avatar révélé
- **Révélation progressive** - Identité complète après double accord
- **Données minimales** - Seules les infos nécessaires sont stockées
- **Droit à l'oubli** - Suppression complète possible

### **Modération**
- **Signalement intégré** - Bouton dans chaque profil
- **Outils admin** - Consultation et suppression de profils
- **Logs complets** - Traçabilité de toutes les actions

## 📊 Architecture Technique

### **Structure du Projet**
```
├── bot.py                    # Point d'entrée principal
├── cogs/
│   ├── profile.py           # Gestion des profils utilisateur
│   ├── match.py             # Système de matching core
│   ├── admin.py             # Outils d'administration
│   ├── setup.py             # Commandes de configuration
│   └── utils.py             # Database manager et utilitaires
├── data/
│   └── matching_bot.db      # Base de données SQLite
└── config/
    └── message_templates.json # Templates de messages
```

### **Base de Données**
- **profiles** - Profils utilisateurs avec intérêts normalisés
- **reports** - Signalements pour modération
- **Sécurisée** - Chiffrement des données sensibles

### **Technologies**
- **discord.py 2.3+** - Framework Discord asynchrone
- **aiosqlite** - Base de données asynchrone
- **Python 3.8+** - Langage moderne avec type hints

## 🧪 Tests et Validation

### **Tests Critiques Automatisés**
- ✅ Séparation stricte mineurs/majeurs
- ✅ Normalisation des intérêts (synonymes)
- ✅ Calculs de compatibilité
- ✅ Filtres de sécurité

### **Commande de Test Manuel**
```bash
python test_advanced_system.py
```

## 🔧 Configuration Avancée

### **Personnalisation des Synonymes**
```python
# Dans cogs/match.py
synonyms = {
    'musique': ['music', 'son', 'audio', 'chant', 'melody'],
    'sport': ['fitness', 'exercice', 'gym', 'athletique'],
    # Ajoutez vos mappings...
}
```

### **Ajustement des Seuils**
```python
# Seuil minimum de compatibilité
if final_score > 0.1:  # 10% minimum

# Bonus pour correspondances multiples
if intersection >= 3:
    base_score *= 1.2  # +20% si 3+ intérêts communs
```

## 📈 Statistiques et Monitoring

### **Métriques Disponibles**
- Nombre total de profils actifs
- Répartition par tranches d'âge
- Statistiques de matching (succès/échecs)
- Signalements et modération

### **Logs Détaillés**
- Actions utilisateurs (création, modification, suppression)
- Matching et acceptations
- Signalements et actions de modération
- Erreurs système avec stack traces

## 🤝 Contribution et Support

### **Guidelines de Contribution**
1. **Fork** le repository
2. **Créer une branche** pour votre feature
3. **Tester** vos modifications
4. **Soumettre** une pull request avec description détaillée

### **Rapporter un Bug**
- Utiliser les **Issues** GitHub avec template
- Inclure les **logs d'erreur** complets
- Décrire les **étapes de reproduction**

### **Support**
- 📧 Email: support@bot-matching.com
- 💬 Discord: Server de support [Lien]
- 📚 Documentation: [Wiki complet]

---

## 📄 Licence

Ce projet est sous licence MIT. Voir [LICENSE](LICENSE) pour plus de détails.

## 🙏 Remerciements

Développé avec ❤️ pour faciliter les rencontres positives et sécurisées sur Discord.

**Version:** 2.0 | **Dernière mise à jour:** Décembre 2024</new_str>
