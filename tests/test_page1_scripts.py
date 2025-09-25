"""
Tests unitaires pour les scripts ML de la Page 1
Tests des 5 scripts principaux avec TDD
"""

import unittest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json
import pandas as pd
import numpy as np

# Ajouter le chemin des scripts
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts_ml'))

from predict_daily_sales import DailySalesPredictor
from calculate_alerts import AlertCalculator, AlertStatus
from suggest_quantity import QuantitySuggester
from evaluate_events_impact import EventsImpactEvaluator
from monitor_ml_performance import MLPerformanceMonitor


class TestPredictDailySales(unittest.TestCase):
    """Tests pour predict_daily_sales.py"""
    
    def setUp(self):
        self.predictor = DailySalesPredictor()
        
    def test_predict_basic(self):
        """Test prédiction basique"""
        # Mock des prédictions
        test_predictions = [
            {"date": "2025-09-10", "quantity": 20},
            {"date": "2025-09-11", "quantity": 18},
            {"date": "2025-09-12", "quantity": 25}
        ]
        
        with patch.object(self.predictor, '_load_model') as mock_load:
            mock_model = Mock()
            mock_model.predict.return_value = pd.DataFrame({
                'ds': pd.date_range('2025-09-10', periods=3),
                'yhat': [20, 18, 25],
                'yhat_lower': [15, 14, 20],
                'yhat_upper': [25, 22, 30]
            })
            mock_load.return_value = mock_model
            
            result = self.predictor.predict(
                article_id=1,
                date_debut="2025-09-10",
                date_fin="2025-09-12"
            )
            
            self.assertEqual(result['article_id'], "1")
            self.assertEqual(len(result['predictions']), 3)
            self.assertIn('mape', result)
            
    def test_predict_with_events(self):
        """Test prédiction avec événements"""
        events = [
            {"name": "Black Friday", "date": "2025-09-11", "multiplier": 2.0}
        ]
        
        with patch.object(self.predictor, '_load_model') as mock_load:
            mock_model = Mock()
            base_forecast = pd.DataFrame({
                'ds': pd.date_range('2025-09-10', periods=3),
                'yhat': [20, 18, 25],
                'yhat_lower': [15, 14, 20],
                'yhat_upper': [25, 22, 30]
            })
            mock_model.predict.return_value = base_forecast
            mock_load.return_value = mock_model
            
            result = self.predictor.predict(
                article_id=1,
                date_debut="2025-09-10",
                date_fin="2025-09-12",
                events=events
            )
            
            # Vérifier que l'événement a été appliqué
            self.assertIsNotNone(result)
            self.assertEqual(len(result['predictions']), 3)
            
    def test_predict_max_30_days(self):
        """Test limite 30 jours"""
        with patch.object(self.predictor, '_load_model') as mock_load:
            mock_model = Mock()
            mock_load.return_value = mock_model
            
            # Tenter de prédire sur 60 jours
            result = self.predictor.predict(
                article_id=1,
                date_debut="2025-09-10",
                date_fin="2025-11-10"
            )
            
            # Vérifier que c'est limité à 30 jours
            mock_model.predict.assert_called_once()
            args = mock_model.predict.call_args[0][0]
            self.assertLessEqual(len(args), 31)
            
    def test_fallback_when_no_model(self):
        """Test fallback quand pas de modèle"""
        with patch.object(self.predictor, '_load_model') as mock_load:
            mock_load.return_value = None
            
            result = self.predictor.predict(
                article_id=999,
                date_debut="2025-09-10",
                date_fin="2025-09-12"
            )
            
            self.assertEqual(result['article_id'], "999")
            self.assertIn('fallback_mode', result)
            self.assertTrue(result.get('fallback_mode', False))


class TestCalculateAlerts(unittest.TestCase):
    """Tests pour calculate_alerts.py"""
    
    def setUp(self):
        self.calculator = AlertCalculator()
        
    def test_alert_critique(self):
        """Test statut CRITIQUE"""
        # Stock insuffisant pour couvrir le délai
        predictions = [
            {"quantity": 20},  # Jour 1
            {"quantity": 25},  # Jour 2
            {"quantity": 30},  # Jour 3
            {"quantity": 20},  # Jour 4
            {"quantity": 25},  # Jour 5 (délai)
        ]
        
        with patch.object(self.calculator, '_get_article_info') as mock_info:
            mock_info.return_value = {
                "id": 1,
                "nom": "Article Test",
                "prix_unitaire": 1000,
                "delai_reapprovisionnement": 5,
                "stock_actuel": 50,  # Stock < somme 5 jours (120)
                "stock_min": 10,
                "stock_max": 200
            }
            
            result = self.calculator.calculate_alert(
                article_id=1,
                predictions=predictions
            )
            
            self.assertEqual(result['status'], AlertStatus.CRITIQUE.value)
            self.assertIn('Commander immédiatement', result['action'])
            self.assertGreater(result['financial_impact']['amount'], 0)
            
    def test_alert_attention(self):
        """Test statut ATTENTION"""
        predictions = [
            {"quantity": 10},  # Jour 1
            {"quantity": 10},  # Jour 2
            {"quantity": 10},  # Jour 3
            {"quantity": 10},  # Jour 4
            {"quantity": 10},  # Jour 5 (délai)
            {"quantity": 15},  # Jour 6
            {"quantity": 15},  # Jour 7
            {"quantity": 15},  # Jour 8
        ]
        
        with patch.object(self.calculator, '_get_article_info') as mock_info:
            mock_info.return_value = {
                "id": 1,
                "nom": "Article Test",
                "prix_unitaire": 1000,
                "delai_reapprovisionnement": 5,
                "stock_actuel": 70,  # Stock OK pour délai mais pas pour délai+3j
                "stock_min": 10,
                "stock_max": 200
            }
            
            result = self.calculator.calculate_alert(
                article_id=1,
                predictions=predictions
            )
            
            self.assertEqual(result['status'], AlertStatus.ATTENTION.value)
            self.assertIn('Commander avant', result['action'])
            
    def test_alert_ok(self):
        """Test statut OK"""
        predictions = [{"quantity": 5} for _ in range(10)]
        
        with patch.object(self.calculator, '_get_article_info') as mock_info:
            mock_info.return_value = {
                "id": 1,
                "nom": "Article Test",
                "prix_unitaire": 1000,
                "delai_reapprovisionnement": 5,
                "stock_actuel": 200,  # Stock largement suffisant
                "stock_min": 10,
                "stock_max": 500
            }
            
            result = self.calculator.calculate_alert(
                article_id=1,
                predictions=predictions
            )
            
            self.assertEqual(result['status'], AlertStatus.OK.value)
            self.assertIn('Prochaine commande entre', result['action'])
            self.assertEqual(result['financial_impact']['amount'], 0)
            
    def test_calculate_financial_impact(self):
        """Test calcul impact financier"""
        predictions = [{"quantity": 30} for _ in range(5)]
        
        with patch.object(self.calculator, '_get_article_info') as mock_info:
            mock_info.return_value = {
                "id": 1,
                "nom": "Article Test",
                "prix_unitaire": 500,
                "delai_reapprovisionnement": 5,
                "stock_actuel": 50,
                "stock_min": 10,
                "stock_max": 200
            }
            
            result = self.calculator.calculate_alert(
                article_id=1,
                predictions=predictions
            )
            
            # Vérifier le calcul de perte
            self.assertIn('financial_impact', result)
            self.assertIn('ventes_perdues', result['financial_impact'])
            self.assertGreater(result['financial_impact']['amount'], 0)


class TestSuggestQuantity(unittest.TestCase):
    """Tests pour suggest_quantity.py"""
    
    def setUp(self):
        self.suggester = QuantitySuggester()
        
    def test_quantity_calculation_formula(self):
        """Test formule de calcul exacte"""
        predictions = [
            {"quantity": 10},
            {"quantity": 15},
            {"quantity": 20},
            {"quantity": 10},
            {"quantity": 15}
        ]
        
        with patch.object(self.suggester, '_get_stock_actuel') as mock_stock:
            with patch.object(self.suggester, '_get_article_info') as mock_info:
                mock_stock.return_value = 30
                mock_info.return_value = {
                    "id": 1,
                    "nom": "Article Test",
                    "prix_unitaire": 100,
                    "stock_min": 10,
                    "stock_max": 200,
                    "delai_reapprovisionnement": 5
                }
                
                result = self.suggester.calculate_quantity(
                    article_id=1,
                    predictions=predictions * 6,  # 30 jours
                    marge_securite=15.0
                )
                
                # Vérifier la formule
                # (Σ prédictions - stock_actuel) × (1 + marge)
                predictions_sum = sum(p['quantity'] for p in predictions * 6)
                besoin_net = predictions_sum - 30
                expected = besoin_net * 1.15
                
                self.assertAlmostEqual(
                    result['quantite_suggeree'],
                    round(expected),
                    delta=1
                )
                
    def test_margin_limits(self):
        """Test limites de marge 0-50%"""
        predictions = [{"quantity": 10} for _ in range(10)]
        
        with patch.object(self.suggester, '_get_stock_actuel') as mock_stock:
            with patch.object(self.suggester, '_get_article_info') as mock_info:
                mock_stock.return_value = 20
                mock_info.return_value = {
                    "id": 1,
                    "nom": "Test",
                    "prix_unitaire": 100,
                    "stock_min": 10,
                    "stock_max": 500,
                    "delai_reapprovisionnement": 5
                }
                
                # Test marge négative
                result = self.suggester.calculate_quantity(
                    article_id=1,
                    predictions=predictions,
                    marge_securite=-10
                )
                self.assertEqual(result['details']['marge_pourcentage'], 15.0)
                
                # Test marge > 50%
                result = self.suggester.calculate_quantity(
                    article_id=1,
                    predictions=predictions,
                    marge_securite=75
                )
                self.assertEqual(result['details']['marge_pourcentage'], 15.0)
                
    def test_budget_optimization(self):
        """Test optimisation avec budget"""
        predictions = [{"quantity": 20} for _ in range(30)]
        
        with patch.object(self.suggester, '_get_stock_actuel') as mock_stock:
            with patch.object(self.suggester, '_get_article_info') as mock_info:
                mock_stock.return_value = 50
                mock_info.return_value = {
                    "id": 1,
                    "nom": "Test",
                    "prix_unitaire": 1000,
                    "stock_min": 10,
                    "stock_max": 1000,
                    "delai_reapprovisionnement": 5
                }
                
                result = self.suggester.optimize_quantity_for_budget(
                    article_id=1,
                    predictions=predictions,
                    budget_max=100000
                )
                
                # Vérifier que la quantité respecte le budget
                cout_total = result['quantite_suggeree'] * 1000
                self.assertLessEqual(cout_total, 100000)


class TestEventsImpact(unittest.TestCase):
    """Tests pour evaluate_events_impact.py"""
    
    def setUp(self):
        self.evaluator = EventsImpactEvaluator()
        
    def test_known_event_impact(self):
        """Test événement connu (Tabaski)"""
        result = self.evaluator.evaluate_event_impact(
            event_type="Tabaski",
            article_category="boissons"
        )
        
        self.assertEqual(result['event'], "Tabaski")
        self.assertGreater(result['impact_multiplier'], 2.0)
        self.assertIn('confidence', result)
        self.assertIn('affected_days', result)
        
    def test_unknown_event_estimation(self):
        """Test événement inconnu"""
        result = self.evaluator.evaluate_event_impact(
            event_type="Festival de musique",
            article_category="boissons"
        )
        
        self.assertEqual(result['event'], "Festival de musique")
        self.assertGreaterEqual(result['impact_multiplier'], 1.0)
        self.assertIn('recommendations', result)
        
    def test_temporal_impact_calculation(self):
        """Test calcul impact temporel"""
        future_date = (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d')
        
        result = self.evaluator.evaluate_event_impact(
            event_type="Black Friday",
            date_event=future_date
        )
        
        self.assertIn('temporal_impact', result)
        self.assertIn('days_until_event', result['temporal_impact'])
        self.assertIn('impact_period', result['temporal_impact'])
        
    def test_category_specific_multiplier(self):
        """Test multiplicateur par catégorie"""
        # Test différentes catégories pour Tabaski
        result_boissons = self.evaluator.evaluate_event_impact(
            event_type="Tabaski",
            article_category="boissons"
        )
        
        result_autres = self.evaluator.evaluate_event_impact(
            event_type="Tabaski",
            article_category="autres"
        )
        
        # Les boissons devraient avoir un multiplicateur plus élevé
        self.assertGreater(
            result_boissons['impact_multiplier'],
            result_autres['impact_multiplier']
        )


class TestMLPerformance(unittest.TestCase):
    """Tests pour monitor_ml_performance.py"""
    
    def setUp(self):
        self.monitor = MLPerformanceMonitor()
        
    def test_mape_calculation(self):
        """Test calcul MAPE"""
        predictions = [100, 120, 80, 90, 110]
        actuals = [95, 115, 85, 92, 108]
        
        mape = self.monitor.calculate_mape(predictions, actuals)
        
        # MAPE devrait être autour de 3-5%
        self.assertGreater(mape, 0)
        self.assertLess(mape, 10)
        
    def test_mape_with_zero_actuals(self):
        """Test MAPE avec valeurs nulles"""
        predictions = [10, 20, 30]
        actuals = [0, 20, 30]
        
        mape = self.monitor.calculate_mape(predictions, actuals)
        
        # Ne devrait pas crasher avec des zéros
        self.assertIsNotNone(mape)
        
    def test_error_pattern_identification(self):
        """Test identification patterns d'erreur"""
        # Créer un DataFrame avec sur-estimation systématique
        df = pd.DataFrame({
            'date': pd.date_range('2025-09-01', periods=10),
            'weekday': ['Monday'] * 10,
            'quantite_predite': [120] * 10,
            'quantity_sold': [100] * 10
        })
        
        pattern = self.monitor._identify_error_pattern(df)
        self.assertEqual(pattern, "sur_estimation_systematique")
        
        # Test sous-estimation
        df['quantite_predite'] = [80] * 10
        pattern = self.monitor._identify_error_pattern(df)
        self.assertEqual(pattern, "sous_estimation_systematique")
        
    def test_performance_classification(self):
        """Test classification de performance"""
        self.assertEqual(self.monitor._classify_performance(8), "Excellent")
        self.assertEqual(self.monitor._classify_performance(12), "Bon")
        self.assertEqual(self.monitor._classify_performance(20), "Moyen")
        self.assertEqual(self.monitor._classify_performance(30), "Faible")
        
    def test_recommendations_generation(self):
        """Test génération de recommandations"""
        recommendations = self.monitor._generate_recommendations(
            mape_global=25,
            mape_par_jour={'Lundi': 20, 'Samedi': 35},
            error_pattern="sous_estimation_weekends",
            metrics={'bias': 10, 'std_error': 5, 'mae': 8}
        )
        
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)
        self.assertIn("Augmenter le poids de la saisonnalité hebdomadaire", recommendations)


class TestIntegration(unittest.TestCase):
    """Tests d'intégration entre scripts"""
    
    def test_prediction_to_alert_flow(self):
        """Test flux prédiction -> alerte"""
        predictor = DailySalesPredictor()
        calculator = AlertCalculator()
        
        # Mock prédictions
        with patch.object(predictor, 'predict') as mock_predict:
            mock_predict.return_value = {
                "article_id": "1",
                "predictions": [
                    {"date": "2025-09-10", "quantity": 20},
                    {"date": "2025-09-11", "quantity": 25},
                    {"date": "2025-09-12", "quantity": 30},
                    {"date": "2025-09-13", "quantity": 20},
                    {"date": "2025-09-14", "quantity": 25}
                ]
            }
            
            # Obtenir prédictions
            pred_result = predictor.predict(1, "2025-09-10", "2025-09-14")
            
            # Calculer alertes avec ces prédictions
            with patch.object(calculator, '_get_article_info') as mock_info:
                mock_info.return_value = {
                    "id": 1,
                    "nom": "Test",
                    "prix_unitaire": 1000,
                    "delai_reapprovisionnement": 5,
                    "stock_actuel": 50,
                    "stock_min": 10,
                    "stock_max": 200
                }
                
                alert_result = calculator.calculate_alert(
                    article_id=1,
                    predictions=pred_result['predictions']
                )
                
                self.assertIn('status', alert_result)
                self.assertIn('action', alert_result)
                
    def test_alert_to_quantity_flow(self):
        """Test flux alerte -> quantité suggérée"""
        calculator = AlertCalculator()
        suggester = QuantitySuggester()
        
        predictions = [{"quantity": 20} for _ in range(30)]
        
        # Calculer alerte
        with patch.object(calculator, '_get_article_info') as mock_info:
            mock_info.return_value = {
                "id": 1,
                "nom": "Test",
                "prix_unitaire": 1000,
                "delai_reapprovisionnement": 5,
                "stock_actuel": 100,
                "stock_min": 50,
                "stock_max": 500
            }
            
            alert = calculator.calculate_alert(1, predictions)
            
            # Si alerte CRITIQUE ou ATTENTION, suggérer quantité
            if alert['status'] in [AlertStatus.CRITIQUE.value, AlertStatus.ATTENTION.value]:
                with patch.object(suggester, '_get_stock_actuel') as mock_stock:
                    with patch.object(suggester, '_get_article_info') as mock_info2:
                        mock_stock.return_value = 100
                        mock_info2.return_value = mock_info.return_value
                        
                        quantity = suggester.calculate_quantity(
                            article_id=1,
                            predictions=predictions
                        )
                        
                        self.assertGreater(quantity['quantite_suggeree'], 0)


def run_tests():
    """Fonction pour exécuter tous les tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Ajouter tous les tests
    suite.addTests(loader.loadTestsFromTestCase(TestPredictDailySales))
    suite.addTests(loader.loadTestsFromTestCase(TestCalculateAlerts))
    suite.addTests(loader.loadTestsFromTestCase(TestSuggestQuantity))
    suite.addTests(loader.loadTestsFromTestCase(TestEventsImpact))
    suite.addTests(loader.loadTestsFromTestCase(TestMLPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Exécuter avec verbosité
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Résumé
    print("\n" + "="*70)
    print(f"Tests exécutés: {result.testsRun}")
    print(f"Succès: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Échecs: {len(result.failures)}")
    print(f"Erreurs: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)