
# 🚀 Guide du Développeur - Matching Bot Discord

## 📋 Table des Matières

1. [Architecture du Projet](#architecture)
2. [Modules et Responsabilités](#modules)
3. [Zones Critiques](#zones-critiques)
4. [Processus de Développement](#processus)
5. [Tests et Validation](#tests)
6. [Problèmes Connus](#problemes)
7. [Roadmap](#roadmap)

---

## 🏗️ Architecture du Projet {#architecture}

```
matching-bot/
├── bot.py                    # 🚀 Point d'entrée principal
├── cogs/                     # 📦 Modules fonctionnels
│   ├── __init__.py
│   ├── utils.py             # 🔧 Base de données et utilitaires
│   ├── profile.py           # 👤 Gestion des profils utilisateur
│   ├── match.py             # 💕 Système de matching core
│   ├── admin.py             # 🛡️ Outils d'administration
│   └── setup.py             # ⚙️ Configuration et diagnostic
├── data/
│   └── matching_bot.db      # 🗄️ Base SQLite
├── config/
│   └── message_templates.json # 📝 Templates de messages
├── logs/
│   └── bot.log              # 📊 Logs système
└── tests/
    └── test_advanced_system.py # 🧪 Tests automatisés
```

---

## 📦 Modules et Responsabilités {#modules}

### 🔧 `cogs/utils.py` - Base Technique
**CRITIQUE** - Ne pas modifier sans tests approfondis

**Responsabilités:**
- Connexion base de données (`DatabaseManager`)
- Création/migration des tables
- Logging système
- Configuration globale

**Points sensibles:**
```python
# ⚠️ ATTENTION: Structure des tables
async def create_tables(self):
    # Toute modification = migration obligatoire
    
# ⚠️ ATTENTION: Connexion DB
async def is_connected(self):
    # Vérification critique pour la stabilité
```

### 👤 `cogs/profile.py` - Gestion Utilisateurs
**Fonctionnalités:**
- Création/modification de profils
- Validation des données
- Suppression et export

**Zones à surveiller:**
- **Validation d'âge** (protection mineurs)
- **Normalisation des intérêts** (impacts sur le matching)
- **Sanitisation des entrées** (sécurité)

```python
# 🔥 CRITIQUE: Validation d'âge
if age < 13 or age > 99:
    # Protection absolue - NE PAS MODIFIER

# 🎯 IMPORTANT: Normalisation intérêts
interests_normalized = json.dumps(interests_list)
# Format JSON requis pour l'algorithme
```

### 💕 `cogs/match.py` - Cœur du Système
**ULTRA-CRITIQUE** - Chaque modification impact tous les utilisateurs

**Algorithme de compatibilité:**
```python
def calculate_compatibility(self, profile1, profile2):
    # 🚨 SÉGRÉGATION MINEURS/MAJEURS - INVIOLABLE
    if (age1 < 18 and age2 >= 18) or (age1 >= 18 and age2 < 18):
        return 0
    
    # 📊 FORMULE DE SCORE
    final_score = (interests_score * 0.6) + (age_score * 0.25) + (desc_score * 0.15)
    # Poids testés et optimisés - modifier avec précaution
```

**Composants clés:**
- `calculate_compatibility()` - Algorithme principal
- `extract_keywords()` - Analyse textuelle
- `send_matches_dm()` - Interface utilisateur
- `cleanup_passed_profiles` - Nettoyage automatique

### 🛡️ `cogs/admin.py` - Outils Modération
**Fonctionnalités admin:**
- Gestion des signalements
- Export/import de données
- Tests de compatibilité
- Statistiques avancées

### ⚙️ `cogs/setup.py` - Configuration
**Diagnostic et initialisation:**
- Vérification système
- État des composants
- Informations publiques

---

## 🚨 Zones Critiques {#zones-critiques}

### 🔒 Protection des Mineurs - INVIOLABLE
```python
# Dans match.py - calculate_compatibility()
if (age1 < 18 and age2 >= 18) or (age1 >= 18 and age2 < 18):
    return 0  # JAMAIS de matching mineur/majeur
```
**⚠️ RÈGLE ABSOLUE:** Aucun contact possible entre mineurs et majeurs

### 🗄️ Schéma Base de Données
```sql
-- Table profiles - STRUCTURE FIXE
CREATE TABLE profiles (
    user_id TEXT PRIMARY KEY,     -- Discord ID
    prenom TEXT NOT NULL,         -- Prénom public
    pronoms TEXT,                 -- Pronoms optionnels
    age INTEGER NOT NULL,         -- Âge (validation 13-99)
    interests TEXT,               -- JSON array des intérêts
    created_at TEXT,              -- Timestamp création
    description TEXT              -- Description libre
);
```

**🚨 Migration requise** si modification de structure

### 🎯 Algorithme de Matching
**Paramètres testés et optimisés:**
- Seuil minimum: 10% de compatibilité
- Écart d'âge max: 12 ans
- Bonus intérêts communs: +20% si 3+ correspondances
- Nettoyage auto: toutes les heures

---

## 🔄 Processus de Développement {#processus}

### 1. Avant Toute Modification

```bash
# 1. Sauvegarder la DB
cp data/matching_bot.db data/backup_$(date +%Y%m%d_%H%M%S).db

# 2. Lancer les tests
python test_advanced_system.py

# 3. Vérifier les logs
tail -f logs/bot.log
```

### 2. Zones par Priorité de Risque

**🔴 CRITIQUE (Tests obligatoires):**
- `calculate_compatibility()` - Algorithme principal
- Validation d'âge - Protection mineurs
- Structure DB - Migration requise

**🟡 SENSIBLE (Tests recommandés):**
- Interface utilisateur (embeds, boutons)
- Commandes admin
- Gestion des erreurs

**🟢 SAFE (Modification libre):**
- Messages et textes
- Couleurs et styling
- Logs et documentation

### 3. Workflow de Test

```python
# Tests automatisés - OBLIGATOIRES avant mise en prod
def test_age_segregation():
    """CRITIQUE: Vérifier séparation mineurs/majeurs"""
    
def test_compatibility_algorithm():
    """Vérifier cohérence des scores"""
    
def test_database_integrity():
    """Vérifier structure et contraintes DB"""
```

---

## 🧪 Tests et Validation {#tests}

### Tests Automatisés
```bash
# Lancer tous les tests
python test_advanced_system.py

# Tests spécifiques
python -c "from test_advanced_system import *; test_age_segregation()"
```

### Tests Manuels Discord
```
1. Créer profils test (mineur + majeur)
2. Vérifier ségrégation avec /findmatch
3. Tester signalement et modération
4. Vérifier notifications et matches
```

### Métriques à Surveiller
- Taux de matching (objectif: 15-25%)
- Temps de réponse commandes (<3s)
- Erreurs dans logs (objectif: 0/jour)
- Signalements traités (<24h)

---

## ⚠️ Problèmes Connus {#problemes}

### 1. Limitations Actuelles
- **Pas de matching géographique** (fonctionnalité future)
- **Algorithme textuel simple** (pas d'IA avancée)
- **Pas de photos/médias** (par design pour sécurité)

### 2. Points d'Amélioration Identifiés
```python
# TODO: Améliorer l'extraction de mots-clés
def extract_keywords(self, text: str):
    # Ajouter stemming/lemmatisation
    # Gérer mieux les langues multiples
    
# TODO: Système de feedback
def collect_match_feedback():
    # Permettre aux utilisateurs d'évaluer les matches
    # Améliorer l'algorithme avec les retours
```

### 3. Gestion d'Erreurs
```python
# Pattern standard pour toutes les commandes
try:
    await self.ensure_db_connection()
    # Logique métier
    await interaction.followup.send(success_message)
except Exception as e:
    logger.error(f"❌ Erreur {command_name}: {e}")
    await interaction.followup.send("❌ Erreur temporaire", ephemeral=True)
```

---

## 🗺️ Roadmap {#roadmap}

### Version 2.0 - Améliorations Core
- [ ] **Matching géographique** (ville/région)
- [ ] **Système de feedback** sur les matches
- [ ] **Algorithme ML** pour la compatibilité
- [ ] **Notifications push** intelligentes

### Version 2.1 - Fonctionnalités Sociales
- [ ] **Groupes d'intérêts** communs
- [ ] **Événements** organisés par le bot
- [ ] **Système de karma** utilisateur
- [ ] **Matching temporaire** (amis vs romantique)

### Version 2.2 - Administration Avancée
- [ ] **Dashboard web** pour admins
- [ ] **Analytics avancées** 
- [ ] **Modération automatique** IA
- [ ] **API externe** pour intégrations

---

## 📞 Support Développeur

### Logs Importants
```bash
# Erreurs système
grep "❌" logs/bot.log | tail -20

# Activité matching
grep "🔍 Findmatch\|💖 Like\|🎉 Match" logs/bot.log

# Performance DB
grep "DB:" logs/bot.log
```

### Commandes de Debug
```
/test_compatibility @user1 @user2  # Tester algo
/stats                            # Vue système
/list_profiles                    # Profils actifs
```

### Contacts et Ressources
- **Documentation Discord.py:** https://discordpy.readthedocs.io/
- **SQLite Async:** https://aiosqlite.omnilib.dev/
- **Tests en local:** `python test_advanced_system.py`

---

**⚡ Règle d'Or:** En cas de doute, TOUJOURS tester sur une copie avant la production !

**🛡️ Priorité #1:** Protection des mineurs - Aucun compromis possible

**📊 Objectif:** Expérience utilisateur fluide et sécurisée
