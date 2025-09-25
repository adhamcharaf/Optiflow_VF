"""
Tests unitaires pour les scripts ML de la Page 3 Prédictions
Tests des 3 scripts selon approche TDD
"""

import unittest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json
import sqlite3
import tempfile

# Ajouter le chemin des scripts
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts_ml', 'page3_predictions'))

from generate_predictions import SimplePredictionsGenerator
from calculate_accuracy import AccuracyCalculator
from learn_from_feedback import UserFeedbackLearner

class TestGeneratePredictions(unittest.TestCase):
    """Tests pour generate_predictions.py"""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        
        # Mock du prédicteur Page 1
        with patch('generate_predictions.DailySalesPredictor'):
            self.generator = SimplePredictionsGenerator(self.temp_db.name)
        
        self._setup_test_data()
        
    def tearDown(self):
        os.unlink(self.temp_db.name)
    
    def _setup_test_data(self):
        """Configure des données de test"""
        with sqlite3.connect(self.temp_db.name) as conn:
            conn.execute("""
                CREATE TABLE articles (
                    id TEXT PRIMARY KEY,
                    nom TEXT,
                    prix_unitaire REAL
                )
            """)
            conn.execute("""
                CREATE TABLE predictions (
                    date DATE,
                    article_id TEXT,
                    quantity REAL,
                    confidence_level REAL
                )
            """)
            conn.execute("""
                CREATE TABLE ventes (
                    date DATE,
                    article_id TEXT,
                    quantite_vendue INTEGER
                )
            """)
            
            # Données test
            conn.execute("""
                INSERT INTO articles VALUES ('123', 'Coca-Cola 33cl', 500)
            """)
            
            # Prédictions pour les 7 prochains jours
            for i in range(7):
                date = (datetime.now().date() + timedelta(days=i)).isoformat()
                conn.execute("""
                    INSERT INTO predictions VALUES (?, '123', ?, 0.85)
                """, (date, 40 + i*2))
            
            # Ventes historiques pour fallback
            for i in range(30):
                date = (datetime.now().date() - timedelta(days=i)).isoformat()
                conn.execute("""
                    INSERT INTO ventes VALUES (?, '123', ?)
                """, (date, 35 + (i % 10)))
            
            conn.commit()
    
    def test_generate_predictions_table_basic(self):
        """Test génération tableau prédictions basique"""
        result = self.generator.generate_predictions_table('123', 7)
        
        self.assertIn('article', result)
        self.assertIn('tableau', result)
        self.assertIn('total_periode', result)
        self.assertEqual(result['article'], 'Coca-Cola 33cl')
        
        # Vérifier structure du tableau
        if result['tableau']:
            first_pred = result['tableau'][0]
            self.assertIn('date', first_pred)
            self.assertIn('jour', first_pred)
            self.assertIn('prediction', first_pred)
            self.assertIn('confiance', first_pred)
    
    def test_generate_predictions_different_periods(self):
        """Test génération pour différentes périodes"""
        for periode in [7, 14, 30]:
            result = self.generator.generate_predictions_table('123', periode)
            
            self.assertIn('periode', result)
            self.assertIn(str(periode), result['periode'])
    
    def test_get_existing_predictions(self):
        """Test récupération prédictions existantes"""
        with sqlite3.connect(self.temp_db.name) as conn:
            predictions = self.generator._get_existing_predictions(conn, '123', 7)
        
        self.assertIsInstance(predictions, list)
        
        if predictions:
            first_pred = predictions[0]
            self.assertIn('date', first_pred)
            self.assertIn('quantity', first_pred)
            self.assertIn('confidence', first_pred)
    
    def test_generate_fallback_predictions(self):
        """Test génération prédictions de secours"""
        with sqlite3.connect(self.temp_db.name) as conn:
            predictions = self.generator._generate_fallback_predictions(conn, '123', 7)
        
        self.assertEqual(len(predictions), 7)
        
        for pred in predictions:
            self.assertIn('date', pred)
            self.assertIn('quantity', pred)
            self.assertIn('confidence', pred)
            self.assertGreater(pred['quantity'], 0)
    
    def test_get_available_articles(self):
        """Test récupération articles disponibles"""
        articles = self.generator.get_available_articles()
        
        self.assertIsInstance(articles, list)
        
        if articles:
            first_article = articles[0]
            self.assertIn('id', first_article)
            self.assertIn('nom', first_article)


class TestCalculateAccuracy(unittest.TestCase):
    """Tests pour calculate_accuracy.py"""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.calculator = AccuracyCalculator(self.temp_db.name)
        self._setup_test_data()
        
    def tearDown(self):
        os.unlink(self.temp_db.name)
    
    def _setup_test_data(self):
        """Configure des données de test"""
        with sqlite3.connect(self.temp_db.name) as conn:
            conn.execute("""
                CREATE TABLE articles (
                    id TEXT PRIMARY KEY,
                    nom TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE predictions (
                    date DATE,
                    article_id TEXT,
                    quantity REAL
                )
            """)
            conn.execute("""
                CREATE TABLE ventes (
                    date DATE,
                    article_id TEXT,
                    quantite_vendue INTEGER
                )
            """)
            
            # Données test
            conn.execute("""
                INSERT INTO articles VALUES ('123', 'Coca-Cola 33cl')
            """)
            
            # Comparaisons sur 7 derniers jours
            for i in range(7):
                date = (datetime.now().date() - timedelta(days=i+1)).isoformat()
                predicted = 40 + i*2
                actual = predicted + (5 if i % 2 else -5)  # Écarts alternés
                
                conn.execute("""
                    INSERT INTO predictions VALUES (?, '123', ?)
                """, (date, predicted))
                
                conn.execute("""
                    INSERT INTO ventes VALUES (?, '123', ?)
                """, (date, actual))
            
            conn.commit()
    
    def test_calculate_accuracy_basic(self):
        """Test calcul précision basique"""
        result = self.calculator.calculate_accuracy('123', 7)
        
        self.assertIn('article', result)
        self.assertIn('comparaisons', result)
        self.assertIn('precision_moyenne', result)
        self.assertIn('meilleur_jour', result)
        self.assertIn('a_ameliorer', result)
        
        # Vérifier structure des comparaisons
        if result['comparaisons']:
            first_comp = result['comparaisons'][0]
            self.assertIn('date', first_comp)
            self.assertIn('jour', first_comp)
            self.assertIn('predit', first_comp)
            self.assertIn('reel', first_comp)
            self.assertIn('ecart', first_comp)
            self.assertIn('statut', first_comp)
    
    def test_calculate_percentage_error(self):
        """Test calcul pourcentage d'erreur"""
        # Erreur normale
        error1 = self.calculator._calculate_percentage_error(40, 45)
        self.assertEqual(error1, 12.5)
        
        # Erreur avec valeur réelle 0
        error2 = self.calculator._calculate_percentage_error(40, 0)
        self.assertEqual(error2, 100)
        
        # Pas d'erreur
        error3 = self.calculator._calculate_percentage_error(40, 40)
        self.assertEqual(error3, 0)
    
    def test_evaluate_prediction_quality(self):
        """Test évaluation qualité prédiction"""
        # Bonne prédiction (≤15%)
        status1 = self.calculator._evaluate_prediction_quality(10)
        self.assertEqual(status1, "✅")
        
        # Prédiction moyenne (≤30%)
        status2 = self.calculator._evaluate_prediction_quality(25)
        self.assertEqual(status2, "⚠️")
        
        # Mauvaise prédiction (>30%)
        status3 = self.calculator._evaluate_prediction_quality(50)
        self.assertEqual(status3, "❌")
    
    def test_get_global_accuracy_stats(self):
        """Test statistiques globales de précision"""
        stats = self.calculator.get_global_accuracy_stats()
        
        self.assertIn('precision_semaine', stats)
        self.assertIn('tendance', stats)
        self.assertIn('precision_numerique', stats)
        
        # Vérifier format
        self.assertTrue(stats['precision_semaine'].endswith('%'))
        self.assertIsInstance(stats['precision_numerique'], int)
    
    def test_identify_significant_gaps(self):
        """Test identification écarts significatifs"""
        # Créer des comparaisons avec écarts significatifs
        comparaisons = [
            {'date': '10/09', 'jour': 'Mardi', 'ecart': '+45%', 'statut': '❌'},
            {'date': '11/09', 'jour': 'Mercredi', 'ecart': '+10%', 'statut': '✅'},
            {'date': '12/09', 'jour': 'Jeudi', 'ecart': '-35%', 'statut': '❌'}
        ]
        
        gaps = self.calculator._identify_significant_gaps(comparaisons)
        
        # Doit retourner les 2 écarts > 30%
        self.assertEqual(len(gaps), 2)
        
        for gap in gaps:
            self.assertIn('date', gap)
            self.assertIn('message', gap)


class TestLearnFromFeedback(unittest.TestCase):
    """Tests pour learn_from_feedback.py"""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        
        # Mock des systèmes d'apprentissage Page 1
        with patch('learn_from_feedback.IntelligentEventsLearner'), \
             patch('learn_from_feedback.UserLearningSystem'):
            self.learner = UserFeedbackLearner(self.temp_db.name)
        
        self._setup_test_data()
        
    def tearDown(self):
        os.unlink(self.temp_db.name)
    
    def _setup_test_data(self):
        """Configure des données de test"""
        with sqlite3.connect(self.temp_db.name) as conn:
            conn.execute("""
                CREATE TABLE articles (
                    id TEXT PRIMARY KEY,
                    nom TEXT
                )
            """)
            
            # Table créée par le script
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comparaisons_predictions (
                    date DATE,
                    article_id TEXT,
                    predit REAL,
                    reel REAL,
                    ecart_pct REAL,
                    mape REAL,
                    PRIMARY KEY (date, article_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE learned_events (
                    event_name TEXT PRIMARY KEY,
                    learned_impact REAL,
                    confidence_score REAL,
                    usage_count INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE event_product_impacts (
                    event_name TEXT,
                    product_id TEXT,
                    impact_factor REAL
                )
            """)
            
            conn.execute("""
                CREATE TABLE future_events (
                    event_date DATE,
                    event_type TEXT
                )
            """)
            
            # Données test
            conn.execute("""
                INSERT INTO articles VALUES ('123', 'Coca-Cola 33cl')
            """)
            
            # Écarts significatifs à expliquer
            conn.execute("""
                INSERT INTO comparaisons_predictions VALUES 
                ('2025-09-10', '123', 40, 60, 50, 50)
            """)
            
            # Événements appris existants
            conn.execute("""
                INSERT INTO learned_events VALUES 
                ('Match de foot', 0.3, 0.8, 3)
            """)
            
            # Événements futurs
            conn.execute("""
                INSERT INTO future_events VALUES 
                ('2025-09-15', 'Match de foot')
            """)
            
            conn.commit()
    
    def test_detect_significant_gaps(self):
        """Test détection écarts significatifs"""
        gaps = self.learner.detect_significant_gaps()
        
        self.assertIsInstance(gaps, list)
        
        if gaps:
            first_gap = gaps[0]
            self.assertIn('date', first_gap)
            self.assertIn('article_id', first_gap)
            self.assertIn('ecart_pct', first_gap)
            self.assertIn('message', first_gap)
    
    def test_learn_from_feedback_basic(self):
        """Test apprentissage feedback basique"""
        result = self.learner.learn_from_feedback(
            '2025-09-10', '123', 'Match de foot', 'CAN finale'
        )
        
        self.assertIn('success', result)
        self.assertTrue(result.get('success', False))
        self.assertIn('impact_calcule', result)
        self.assertIn('apprentissage', result)
    
    def test_calculate_event_impact(self):
        """Test calcul impact événement"""
        # Impact positif
        impact1 = self.learner._calculate_event_impact(60, 40)
        self.assertEqual(impact1, 50.0)
        
        # Impact négatif
        impact2 = self.learner._calculate_event_impact(30, 40)
        self.assertEqual(impact2, -25.0)
        
        # Pas d'impact
        impact3 = self.learner._calculate_event_impact(40, 40)
        self.assertEqual(impact3, 0.0)
    
    def test_get_learning_score(self):
        """Test récupération score d'apprentissage"""
        score = self.learner.get_learning_score()
        
        self.assertIn('nb_evenements_appris', score)
        self.assertIn('precision_amelioration', score)
        self.assertIn('patterns_maitrise', score)
        self.assertIn('types_apprentissage', score)
        
        # Vérifier types
        self.assertIsInstance(score['nb_evenements_appris'], int)
        self.assertIsInstance(score['patterns_maitrise'], list)
        self.assertIsInstance(score['types_apprentissage'], list)
    
    def test_get_upcoming_events(self):
        """Test récupération événements futurs"""
        events = self.learner.get_upcoming_events()
        
        self.assertIsInstance(events, list)
        
        # Vérifier format des événements
        for event in events:
            self.assertIsInstance(event, str)
            self.assertIn(':', event)  # Format "date : événement"
    
    def test_analyze_day_patterns(self):
        """Test analyse patterns de jour"""
        patterns = self.learner._analyze_day_patterns()
        
        self.assertIsInstance(patterns, list)
        
        # Au moins un pattern par défaut
        self.assertGreaterEqual(len(patterns), 1)
    
    def test_integration_with_learning_system(self):
        """Test intégration système apprentissage"""
        # Mode autonome (sans système existant)
        self.learner.events_learner = None
        
        result = self.learner._integrate_with_learning_system(
            '2025-09-10', '123', 'Promotion', 20.0
        )
        
        self.assertIsInstance(result, str)
        self.assertIn('enregistré', result.lower())


def run_page3_tests():
    """Exécute tous les tests Page 3"""
    # Créer la suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Ajouter les classes de test
    suite.addTests(loader.loadTestsFromTestCase(TestGeneratePredictions))
    suite.addTests(loader.loadTestsFromTestCase(TestCalculateAccuracy))
    suite.addTests(loader.loadTestsFromTestCase(TestLearnFromFeedback))
    
    # Exécuter les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_all_tests():
    """Exécute tous les tests Page 3 avec rapport détaillé"""
    print("🧪 Lancement des tests Page 3 Prédictions...")
    print("=" * 60)
    
    success = run_page3_tests()
    
    print("=" * 60)
    
    if success:
        print("✅ Tous les tests Page 3 Prédictions passent avec succès!")
        print("\n📊 Couverture des fonctionnalités:")
        print("  ✓ Génération tableau prédictions")
        print("  ✓ Calcul précision (prédit vs réel)")
        print("  ✓ Système apprentissage utilisateur")
        print("  ✓ Détection écarts significatifs")
        print("  ✓ Score d'apprentissage")
    else:
        print("❌ Certains tests Page 3 ont échoué.")
        print("Consultez les détails ci-dessus pour corriger.")
    
    return success


if __name__ == '__main__':
    # Exécuter les tests
    success = run_all_tests()
    
    # Exit code pour intégration CI
    exit(0 if success else 1)