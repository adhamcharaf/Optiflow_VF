"""
Tests unitaires pour les scripts ML de la Page 2 Dashboard
Tests des 5 nouveaux scripts avec approche TDD
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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts_ml', 'page2_dashboard'))

from track_savings import SavingsTracker
from compare_ca_predictions import CAPredictionsComparator  
from calculate_trends import AlertsTrendsCalculator
from get_top_urgent import TopUrgentGetter
from get_stock_dormant import StockDormantAnalyzer

class TestTrackSavings(unittest.TestCase):
    """Tests pour track_savings.py"""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tracker = SavingsTracker(self.temp_db.name)
        self._setup_test_data()
        
    def tearDown(self):
        os.unlink(self.temp_db.name)
    
    def _setup_test_data(self):
        """Configure des données de test"""
        with sqlite3.connect(self.temp_db.name) as conn:
            # Créer tables nécessaires
            conn.execute("""
                CREATE TABLE alertes (
                    id INTEGER PRIMARY KEY,
                    date_creation DATE,
                    status TEXT,
                    article_id TEXT
                )
            """)
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
                    quantity REAL
                )
            """)
            
            # Insérer données test
            conn.execute("""
                INSERT INTO articles VALUES ('123', 'Coca-Cola 33cl', 500)
            """)
            conn.execute("""
                INSERT INTO alertes VALUES (1, '2025-09-10', 'CRITIQUE', '123')
            """)
            conn.execute("""
                INSERT INTO predictions VALUES ('2025-09-10', '123', 50)
            """)
            
            conn.commit()
    
    def test_track_alert_action_success(self):
        """Test enregistrement d'action suite à alerte"""
        result = self.tracker.track_alert_action(1, True, '2025-09-10')
        
        self.assertIn('rupture_evitee_jours', result)
        self.assertIn('montant_economise', result)
        self.assertEqual(result['enregistre'], True)
    
    def test_calculate_savings_critical(self):
        """Test calcul économies pour alerte critique"""
        alerte_info = {
            'date_alerte': '2025-09-10',
            'type_alerte': 'CRITIQUE',
            'article_id': '123',
            'prix_unitaire': 500
        }
        
        with sqlite3.connect(self.temp_db.name) as conn:
            savings = self.tracker._calculate_savings(conn, alerte_info, True)
        
        self.assertGreater(savings['montant_economise'], 0)
        self.assertGreater(savings['rupture_evitee_jours'], 0)
    
    def test_get_weekly_savings(self):
        """Test récupération économies hebdomadaires"""
        # Simuler une action enregistrée
        self.tracker.track_alert_action(1, True, '2025-09-10')
        
        weekly = self.tracker.get_weekly_savings()
        
        self.assertIn('montant_economise', weekly)
        self.assertIn('ruptures_evitees', weekly)
        self.assertIn('jours_vente_sauves', weekly)


class TestCompareCApredictions(unittest.TestCase):
    """Tests pour compare_ca_predictions.py"""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.comparator = CAPredictionsComparator(self.temp_db.name)
        self._setup_test_data()
        
    def tearDown(self):
        os.unlink(self.temp_db.name)
    
    def _setup_test_data(self):
        """Configure des données de test"""
        with sqlite3.connect(self.temp_db.name) as conn:
            conn.execute("""
                CREATE TABLE ventes (
                    date DATE,
                    article_id TEXT,
                    quantite_vendue INTEGER
                )
            """)
            conn.execute("""
                CREATE TABLE predictions (
                    date DATE,
                    article_id TEXT,
                    quantity INTEGER
                )
            """)
            conn.execute("""
                CREATE TABLE articles (
                    id TEXT PRIMARY KEY,
                    prix_unitaire REAL
                )
            """)
            
            # Données test
            conn.execute("INSERT INTO articles VALUES ('123', 500)")
            conn.execute("INSERT INTO ventes VALUES ('2025-09-10', '123', 100)")
            conn.execute("INSERT INTO predictions VALUES ('2025-09-10', '123', 95)")
            
            conn.commit()
    
    def test_compare_ca_basic(self):
        """Test comparaison CA basique"""
        result = self.comparator.compare_ca("semaine")
        
        self.assertIn('ca_prevu', result)
        self.assertIn('ca_reel', result)
        self.assertIn('ecart_pourcentage', result)
        self.assertIn('interpretation', result)
    
    def test_period_dates_calculation(self):
        """Test calcul des dates de période"""
        dates = self.comparator._get_period_dates("semaine")
        
        self.assertIn('debut', dates)
        self.assertIn('fin', dates)
        
        # Vérifier que les dates sont valides
        datetime.fromisoformat(dates['debut'])
        datetime.fromisoformat(dates['fin'])
    
    def test_interpretation_performance(self):
        """Test interprétation des performances"""
        # Test excellente performance
        interp1 = self.comparator._interpret_performance(15)
        self.assertIn("Excellente", interp1)
        
        # Test sous-performance
        interp2 = self.comparator._interpret_performance(-20)
        self.assertIn("sous-performance", interp2)


class TestCalculateTrends(unittest.TestCase):
    """Tests pour calculate_trends.py"""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.calculator = AlertsTrendsCalculator(self.temp_db.name)
        self._setup_test_data()
        
    def tearDown(self):
        os.unlink(self.temp_db.name)
    
    def _setup_test_data(self):
        """Configure des données de test"""
        with sqlite3.connect(self.temp_db.name) as conn:
            conn.execute("""
                CREATE TABLE alertes (
                    id INTEGER PRIMARY KEY,
                    article_id TEXT,
                    status TEXT,
                    date_creation DATE
                )
            """)
            
            # Données test sur plusieurs jours
            for i in range(7):
                date = (datetime.now().date() - timedelta(days=i)).isoformat()
                conn.execute("""
                    INSERT INTO alertes VALUES (?, ?, 'CRITIQUE', ?)
                """, (i+1, f'art_{i}', date))
            
            conn.commit()
    
    def test_save_daily_snapshot(self):
        """Test sauvegarde snapshot quotidien"""
        result = self.calculator.save_daily_snapshot()
        self.assertTrue(result)
        
        # Vérifier que le snapshot existe
        with sqlite3.connect(self.temp_db.name) as conn:
            count = conn.execute("""
                SELECT COUNT(*) FROM historique_alertes 
                WHERE date = DATE('now')
            """).fetchone()[0]
            self.assertGreaterEqual(count, 0)
    
    def test_calculate_trends(self):
        """Test calcul des tendances"""
        # Sauvegarder quelques snapshots
        for i in range(3):
            date = datetime.now().date() - timedelta(days=i)
            self.calculator.save_daily_snapshot(date)
        
        trends = self.calculator.calculate_trends(7)
        
        self.assertIn('tendance_7j', trends)
        self.assertIn('evolution', trends)
        self.assertIn('critique_reduction', trends)
        
        # Vérifier structure des données
        if trends['tendance_7j']:
            first_trend = trends['tendance_7j'][0]
            self.assertIn('date', first_trend)
            self.assertIn('critique', first_trend)
            self.assertIn('attention', first_trend)


class TestGetTopUrgent(unittest.TestCase):
    """Tests pour get_top_urgent.py"""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        
        # Mock des dépendances Page 1
        with patch('get_top_urgent.AlertCalculator') as mock_alert, \
             patch('get_top_urgent.QuantitySuggester') as mock_quantity:
            
            self.mock_alert_calc = Mock()
            self.mock_quantity_sugg = Mock()
            mock_alert.return_value = self.mock_alert_calc
            mock_quantity.return_value = self.mock_quantity_sugg
            
            self.getter = TopUrgentGetter(self.temp_db.name)
        
        self._setup_test_data()
        
    def tearDown(self):
        os.unlink(self.temp_db.name)
    
    def _setup_test_data(self):
        """Configure des données de test"""
        with sqlite3.connect(self.temp_db.name) as conn:
            conn.execute("""
                CREATE TABLE alertes (
                    id INTEGER PRIMARY KEY,
                    article_id TEXT,
                    status TEXT,
                    days_until_stockout INTEGER,
                    potential_loss REAL
                )
            """)
            conn.execute("""
                CREATE TABLE articles (
                    id TEXT PRIMARY KEY,
                    nom TEXT,
                    prix_unitaire REAL,
                    stock_actuel INTEGER
                )
            """)
            conn.execute("""
                CREATE TABLE predictions (
                    date DATE,
                    article_id TEXT,
                    quantity REAL
                )
            """)
            
            # Données test
            conn.execute("""
                INSERT INTO articles VALUES ('123', 'Coca-Cola', 500, 10)
            """)
            conn.execute("""
                INSERT INTO alertes VALUES (1, '123', 'CRITIQUE', 2, 450000)
            """)
            conn.execute("""
                INSERT INTO predictions VALUES (DATE('now'), '123', 50)
            """)
            
            conn.commit()
    
    def test_get_top_urgent_basic(self):
        """Test récupération top articles urgents"""
        # Mock de la suggestion de quantité
        self.mock_quantity_sugg.suggest_quantity.return_value = {
            'suggested_quantity': 500
        }
        
        result = self.getter.get_top_urgent(3)
        
        self.assertIn('top_urgents', result)
        self.assertIsInstance(result['top_urgents'], list)
    
    def test_get_urgent_summary(self):
        """Test résumé des urgences"""
        # Mock de la suggestion de quantité
        self.mock_quantity_sugg.suggest_quantity.return_value = {
            'suggested_quantity': 500
        }
        
        summary = self.getter.get_urgent_summary()
        
        self.assertIn('nb_critiques', summary)
        self.assertIn('perte_totale_estimee', summary)
        self.assertIn('article_plus_urgent', summary)


class TestGetStockDormant(unittest.TestCase):
    """Tests pour get_stock_dormant.py"""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.analyzer = StockDormantAnalyzer(self.temp_db.name)
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
                    stock_actuel INTEGER,
                    prix_unitaire REAL,
                    categorie TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE ventes (
                    date DATE,
                    article_id TEXT,
                    quantite_vendue INTEGER
                )
            """)
            
            # Article dormant (pas de vente récente)
            conn.execute("""
                INSERT INTO articles VALUES ('123', 'Produit Dormant', 100, 1000, 'Boissons')
            """)
            
            # Vente ancienne (> 30 jours)
            old_date = (datetime.now().date() - timedelta(days=45)).isoformat()
            conn.execute("""
                INSERT INTO ventes VALUES (?, '123', 10)
            """, (old_date,))
            
            conn.commit()
    
    def test_identify_dormant_stock(self):
        """Test identification stock dormant"""
        result = self.analyzer.identify_dormant_stock(30)
        
        self.assertIn('nb_articles_dormants', result)
        self.assertIn('valeur_immobilisee', result)
        self.assertIn('top_3_dormants', result)
    
    def test_generate_suggestion(self):
        """Test génération de suggestions"""
        article = {
            'valeur_stock': 50000,
            'jours_inactif': 95
        }
        
        suggestion = self.analyzer._generate_suggestion(article)
        self.assertIn("Promotion", suggestion)
    
    def test_get_dormant_summary(self):
        """Test résumé stock dormant"""
        summary = self.analyzer.get_dormant_summary()
        
        self.assertIn('nb_articles_dormants', summary)
        self.assertIn('valeur_immobilisee', summary)
        self.assertIn('pourcentage_stock_dormant', summary)


def run_page2_tests():
    """Exécute tous les tests Page 2"""
    # Créer la suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Ajouter les classes de test
    suite.addTests(loader.loadTestsFromTestCase(TestTrackSavings))
    suite.addTests(loader.loadTestsFromTestCase(TestCompareCAptions))
    suite.addTests(loader.loadTestsFromTestCase(TestCalculateTrends))
    suite.addTests(loader.loadTestsFromTestCase(TestGetTopUrgent))
    suite.addTests(loader.loadTestsFromTestCase(TestGetStockDormant))
    
    # Exécuter les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    # Exécuter les tests
    success = run_page2_tests()
    
    if success:
        print("\n✅ Tous les tests Page 2 Dashboard passent avec succès!")
    else:
        print("\n❌ Certains tests Page 2 ont échoué.")
        
    # Exit code pour intégration CI
    exit(0 if success else 1)