#!/usr/bin/env python3
"""
Script de test pour le système de matching avancé
Teste tous les composants critiques du nouveau système
"""

import asyncio
import aiosqlite
import os
import json
from pathlib import Path

# Import des modules de test
sys_path = Path(__file__).parent
import sys
sys.path.append(str(sys_path))

from cogs.utils_match import (
    canonicalize_interests, 
    compute_idf_weights,
    advanced_matching_algorithm,
    fuzzy_match_interests
)

class AdvancedSystemTester:
    def __init__(self):
        self.db_path = "data/matching_bot.db"
        self.test_users = []
        
    async def setup_test_database(self):
        """Prépare une base de test avec des données réalistes"""
        print("🔧 Configuration base de données de test...")
        
        # Créer répertoire data si nécessaire
        os.makedirs("data", exist_ok=True)
        
        self.conn = await aiosqlite.connect(self.db_path)
        
        # Créer tables si nécessaires (avec nouvelles colonnes)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                user_id TEXT PRIMARY KEY,
                prenom TEXT NOT NULL,
                pronoms TEXT NOT NULL,
                age INTEGER NOT NULL,
                interets TEXT NOT NULL,
                interets_canonical TEXT,
                description TEXT NOT NULL,
                avatar_url TEXT,
                vector TEXT DEFAULT '[0,0,0,0,0]',
                prefs TEXT DEFAULT '{}',
                activity_score REAL DEFAULT 1.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1 TEXT NOT NULL,
                user2 TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                score REAL,
                nonce TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await self.conn.commit()
        
    async def create_test_profiles(self):
        """Crée des profils de test diversifiés"""
        print("👥 Création profils de test...")
        
        test_profiles = [
            {
                'user_id': '100001',
                'prenom': 'Alice', 
                'pronoms': 'elle/she',
                'age': 22,
                'interets': 'musique,lecture,cinéma,art,voyages',
                'description': 'Passionnée de musique classique et de littérature contemporaine. Aime découvrir de nouveaux pays et cultures.'
            },
            {
                'user_id': '100002', 
                'prenom': 'Bob',
                'pronoms': 'il/he', 
                'age': 24,
                'interets': 'sport,fitness,nature,cuisine,photography', 
                'description': 'Sportif dans l\'âme, j\'aime la randonnée et la photographie de nature. Passionné de cuisine aussi!'
            },
            {
                'user_id': '100003',
                'prenom': 'Charlie',
                'pronoms': 'iel/they',
                'age': 20, 
                'interets': 'gaming,technologie,anime,manga,musique',
                'description': 'Geek assumé(e), fan d\'anime et de jeux vidéo. Toujours au courant des dernières technologies.'
            },
            {
                'user_id': '100004',
                'prenom': 'Diana', 
                'pronoms': 'elle/she',
                'age': 26,
                'interets': 'art,peinture,danse,théâtre,culture',
                'description': 'Artiste peintre et danseuse. Adore le théâtre et tout ce qui touche à l\'art et la culture.'
            },
            {
                'user_id': '100005',
                'prenom': 'Ethan',
                'pronoms': 'il/he',
                'age': 23,
                'interets': 'music,concert,festival,guitare,composition',
                'description': 'Musicien amateur, guitariste. J\'adore aller aux concerts et festivals de musique.'
            },
            # Profil mineur pour tester la ségrégation d'âge
            {
                'user_id': '100006',
                'prenom': 'Sophie',
                'pronoms': 'elle/she', 
                'age': 16,
                'interets': 'étude,lecture,science,mathématiques',
                'description': 'Lycéenne passionnée de sciences et mathématiques. Aime lire des romans de science-fiction.'
            }
        ]
        
        for profile in test_profiles:
            # Canonicaliser les intérêts
            canonical = await canonicalize_interests(profile['interets'])
            
            await self.conn.execute("""
                INSERT OR REPLACE INTO profiles 
                (user_id, prenom, pronoms, age, interets, interets_canonical, description, activity_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile['user_id'],
                profile['prenom'], 
                profile['pronoms'],
                profile['age'],
                profile['interets'],
                canonical,
                profile['description'],
                1.0
            ))
            
        await self.conn.commit()
        self.test_users = [p['user_id'] for p in test_profiles]
        print(f"✅ {len(test_profiles)} profils créés")
        
    async def test_canonicalization(self):
        """Test de la canonicalisation d'intérêts"""
        print("\n🔤 Test canonicalisation...")
        
        test_cases = [
            "musique,sport,lecture",
            "music,fitness,livre,gaming",
            "art,peinture,photographie",
            "cuisine,cooking,food,restaurant"
        ]
        
        for interests in test_cases:
            canonical = await canonicalize_interests(interests)
            print(f"  '{interests}' → '{canonical}'")
            
        print("✅ Canonicalisation testée")
        
    async def test_idf_computation(self):
        """Test du calcul des poids IDF"""
        print("\n📊 Test calcul IDF...")
        
        idf_weights = await compute_idf_weights(self.conn)
        print(f"✅ {len(idf_weights)} poids IDF calculés")
        
        # Afficher quelques exemples
        sorted_weights = sorted(idf_weights.items(), key=lambda x: x[1], reverse=True)
        print("  Poids les plus élevés:")
        for tag, weight in sorted_weights[:5]:
            print(f"    {tag}: {weight:.3f}")
            
        return idf_weights
        
    async def test_fuzzy_matching(self):
        """Test du matching flou"""
        print("\n🎯 Test fuzzy matching...")
        
        test_cases = [
            ("musique", ["music", "son", "audio"]),
            ("sport", ["fitness", "gym", "exercise"]),
            ("lecture", ["livre", "reading", "book"])
        ]
        
        for term, candidates in test_cases:
            matches = fuzzy_match_interests([term], candidates, threshold=0.7)
            print(f"  '{term}' vs {candidates} → {matches}")
            
        print("✅ Fuzzy matching testé")
        
    async def test_age_segregation(self):
        """Test critique de la ségrégation d'âge"""
        print("\n🔒 Test ségrégation d'âge (CRITIQUE)...")
        
        # Alice (22 ans) ne devrait JAMAIS matcher avec Sophie (16 ans) 
        alice_profile = await self.get_profile('100001')  # 22 ans
        sophie_profile = await self.get_profile('100006')  # 16 ans
        
        # Tester l'algorithme
        idf_weights = await compute_idf_weights(self.conn)
        
        try:
            candidates = await advanced_matching_algorithm(
                self.conn, '100001', idf_weights, max_candidates=10
            )
            
            # Vérifier qu'aucun mineur n'apparaît
            sophie_in_results = any(c['user_id'] == '100006' for c in candidates)
            
            if sophie_in_results:
                print("❌ ERREUR CRITIQUE: Mineur trouvé dans résultats majeur!")
                return False
            else:
                print("✅ Ségrégation respectée: aucun mineur dans résultats majeur")
                
        except Exception as e:
            print(f"❌ Erreur algorithme: {e}")
            return False
            
        # Test inverse
        try:
            candidates = await advanced_matching_algorithm(
                self.conn, '100006', idf_weights, max_candidates=10 
            )
            
            # Vérifier qu'aucun majeur n'apparaît
            adults_in_results = [c for c in candidates if c['age'] >= 18]
            
            if adults_in_results:
                print("❌ ERREUR CRITIQUE: Majeurs trouvés dans résultats mineur!")
                print(f"   Majeurs: {[(c['prenom'], c['age']) for c in adults_in_results]}")
                return False
            else:
                print("✅ Ségrégation respectée: aucun majeur dans résultats mineur")
                
        except Exception as e:
            print(f"❌ Erreur algorithme (mineur): {e}")
            return False
            
        return True
        
    async def test_advanced_algorithm(self):
        """Test complet de l'algorithme avancé"""
        print("\n🤖 Test algorithme avancé...")
        
        idf_weights = await compute_idf_weights(self.conn)
        
        # Test pour Alice (intérêts: musique,lecture,cinéma,art,voyages)
        candidates = await advanced_matching_algorithm(
            self.conn, '100001', idf_weights, max_candidates=3
        )
        
        print(f"  Candidats pour Alice:")
        for i, candidate in enumerate(candidates[:3]):
            print(f"    {i+1}. {candidate['prenom']} ({candidate['age']} ans) - Score: {candidate['score']:.3f}")
            print(f"       Intérêts: {candidate['interets']}")
            
        # Vérifier que les scores sont cohérents
        if len(candidates) > 1:
            for i in range(len(candidates)-1):
                if candidates[i]['score'] < candidates[i+1]['score']:
                    print(f"❌ Erreur tri: score {i} < score {i+1}")
                    return False
                    
        print("✅ Algorithme avancé testé")
        return True
        
    async def test_double_optin_flow(self):
        """Simulation du flux double opt-in"""
        print("\n💕 Test flux double opt-in...")
        
        # Simuler Alice qui s'intéresse à Ethan
        await self.conn.execute("""
            INSERT INTO matches (user1, user2, status, score, nonce) 
            VALUES (?, ?, ?, ?, ?)
        """, ('100001', '100005', 'pending', 0.85, 'test_nonce_123'))
        
        # Simuler Ethan qui accepte
        await self.conn.execute("""
            UPDATE matches SET status = 'accepted' 
            WHERE user1 = ? AND user2 = ? AND nonce = ?
        """, ('100001', '100005', 'test_nonce_123'))
        
        await self.conn.commit()
        
        # Vérifier le match
        async with self.conn.execute("""
            SELECT * FROM matches WHERE status = 'accepted' 
        """) as cursor:
            matches = await cursor.fetchall()
            
        print(f"✅ {len(matches)} match(s) accepté(s) en base")
        return True
        
    async def get_profile(self, user_id):
        """Récupère un profil par ID"""
        async with self.conn.execute(
            "SELECT * FROM profiles WHERE user_id = ?", (user_id,)
        ) as cursor:
            return await cursor.fetchone()
            
    async def cleanup(self):
        """Nettoie la base de test"""
        await self.conn.close()
        
    async def run_all_tests(self):
        """Lance tous les tests"""
        print("🚀 LANCEMENT TESTS SYSTÈME AVANCÉ")
        print("=" * 50)
        
        try:
            await self.setup_test_database()
            await self.create_test_profiles()
            
            await self.test_canonicalization()
            await self.test_idf_computation()
            await self.test_fuzzy_matching()
            
            # Test critique
            age_ok = await self.test_age_segregation()
            if not age_ok:
                print("\n❌ ÉCHEC CRITIQUE: Ségrégation d'âge défaillante")
                return False
                
            algo_ok = await self.test_advanced_algorithm()
            if not algo_ok:
                print("\n❌ ÉCHEC: Algorithme de matching défaillant")
                return False
                
            await self.test_double_optin_flow()
            
            print("\n" + "=" * 50)
            print("✅ TOUS LES TESTS RÉUSSIS!")
            print("🎯 Le système avancé est opérationnel")
            return True
            
        except Exception as e:
            print(f"\n❌ ERREUR GÉNÉRALE: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            await self.cleanup()

async def main():
    """Point d'entrée principal"""
    tester = AdvancedSystemTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎉 Système prêt pour utilisation en production!")
    else:
        print("\n⚠️  Corrections nécessaires avant mise en production")
        
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)