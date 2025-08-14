# Guide de Test - Système de Matching Avancé Discord Bot

## État du Système ✅

Le bot Discord est maintenant opérationnel avec le système de matching avancé complet :

- **Bot actif** : CHDFZ#3938 (ID: 1266896676765831259)
- **10 commandes** synchronisées avec Discord
- **Tous les cogs** chargés avec succès
- **Base de données** migrée automatiquement
- **Tests automatisés** : 100% réussis

## Tests Live sur Discord

### 1. Test des Commandes de Base

#### Créer des profils de test
```
/createprofile
- prenom: Alice
- pronoms: elle/she  
- age: 22
- interets: musique,lecture,art,voyage,cinema
- description: Passionnée de musique et d'art, j'adore voyager et découvrir de nouvelles cultures.

/createprofile
- prenom: Bob
- pronoms: il/he
- age: 24  
- interets: sport,fitness,nature,photographie
- description: Sportif dans l'âme, passionné de nature et de photographie outdoor.

/createprofile (profil mineur pour test ségrégation)
- prenom: Sophie
- pronoms: elle/she
- age: 16
- interets: étude,sciences,lecture,mathematics
- description: Lycéenne passionnée de sciences et mathématiques.
```

### 2. Test du Système de Matching

#### Test recherche manuelle
1. Alice fait `/findmatch`
2. Vérifier que Bob apparaît avec un score de compatibilité
3. Vérifier que Sophie (16 ans) n'apparaît JAMAIS dans les résultats
4. Tester les boutons interactifs : [Accepter] [Voir profil] [Passer] [Signaler]

#### Test double opt-in
1. Alice clique [Accepter] sur Bob
2. Vérifier que Bob reçoit une notification anonyme en DM
3. Bob peut voir le profil anonymisé d'Alice
4. Si Bob accepte → révélation mutuelle des identités complètes

### 3. Test Critique - Ségrégation d'âge

⚠️ **Test le plus important** : S'assurer que le système NE MÉLANGE JAMAIS mineurs et majeurs

```
Étapes critiques :
1. Sophie (16 ans) fait /findmatch
2. Vérifier qu'AUCUN profil 18+ n'apparaît
3. Alice (22 ans) fait /findmatch  
4. Vérifier que Sophie n'apparaît pas dans les résultats
5. Si un mineur/majeur apparaît dans les mauvais résultats = BUG CRITIQUE
```

### 4. Test du Système Proactif

#### Activation par admin
```
/config_proactive enabled:true interval:2 max_daily:5
```

#### Vérification
- Attendre 2-3 minutes
- Vérifier que des utilisateurs éligibles reçoivent des suggestions automatiques en DM
- Tester le bouton [Désactiver suggestions]
- Vérifier respect des cooldowns quotidiens

### 5. Test des Fonctionnalités Admin

```
/stats - Affiche statistiques générales
/export_profiles - Export JSON des profils
/list_profiles - Liste des profils actifs
```

## Résultats Attendus

### ✅ Fonctionnement Normal

1. **Matching intelligent** : Scores basés sur IDF + fuzzy matching + synonymes
2. **Interface intuitive** : Boutons interactifs remplacent les réactions
3. **Double opt-in** : Révélation progressive avec accord mutuel
4. **Suggestions proactives** : Envois automatiques respectant les préférences
5. **Ségrégation stricte** : Aucun mix mineur/majeur sous aucune circonstance

### ❌ Signes de Problème

1. **Bug critique** : Mineur/majeur dans mêmes résultats
2. **Erreurs DM** : Impossibilité d'envoyer messages privés  
3. **Timeouts** : Interactions Discord qui expirent
4. **Scores incorrects** : Algorithme qui ne fonctionne pas
5. **Buttons non fonctionnels** : Interactions qui ne répondent pas

## Algorithme de Matching - Détails Techniques

### Étapes du Calcul
1. **Canonicalisation** : `musique,sport` → `["musique", "sport"]`
2. **IDF Weighting** : Tags rares = poids plus élevé
3. **Fuzzy Matching** : `music` ≈ `musique` (80% similarité)  
4. **Score Final** : `0.55×S_interests + 0.25×S_personality + 0.20×S_age`

### Exemple de Score
```
Alice (22, musique/art) vs Bob (24, sport/nature)
- Intérêts communs: 0 (mais fuzzy matches possibles)
- Âge compatible: score élevé (diff = 2 ans)
- Score final: ~0.20-0.40 (moyen-faible)

Alice vs Charlie (20, musique/gaming)  
- Intérêts: "musique" en commun (poids IDF)
- Âge compatible: score très élevé (diff = 2 ans)
- Score final: ~0.60-0.80 (élevé)
```

## Monitoring et Logs

### Dans la console Replit
- Messages de démarrage des cogs
- Erreurs de DM (forbidden/not_found)
- Calculs de scores IDF
- Activité du système proactif

### Commandes de debug
```python
# Dans le code, ajouter des print() pour débugger
print(f"Score calculé: {score:.3f} pour {candidate['prenom']}")
print(f"Intérêts canoniques: {canonical_interests}")
```

## Déploiement

Une fois tous les tests validés, le système est prêt pour déploiement sur serveurs Discord réels.

**Note importante** : Le système a été testé avec succès en mode automatisé. Les tests live sur Discord confirmeront le bon fonctionnement de l'interface utilisateur et des interactions en temps réel.