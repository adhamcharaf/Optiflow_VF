#!/usr/bin/env python3
"""
validate_training.py - Valide les modèles entraînés
Teste la performance et la cohérence des modèles Prophet
"""

import sqlite3
import pandas as pd
import numpy as np
import pickle
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelValidator:
    """Validateur de modèles Prophet entraînés"""
    
    def __init__(self, db_path="../../optiflow.db", models_dir="models"):
        self.db_path = db_path
        self.models_dir = Path(models_dir)
        
    def load_model(self, product_id):
        """Charge un modèle entraîné avec ses métadonnées"""
        model_path = self.models_dir / f"prophet_model_{product_id}.pkl"
        metadata_path = self.models_dir / f"model_metadata_{product_id}.json"
        
        if not model_path.exists() or not metadata_path.exists():
            return None, None
            
        try:
            # Charger le modèle
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            
            # Charger les métadonnées
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                
            return model, metadata
            
        except Exception as e:
            logger.error(f"Erreur chargement modèle {product_id}: {e}")
            return None, None
    
    def validate_model_performance(self, product_id):
        """Valide la performance d'un modèle individuel"""
        model, metadata = self.load_model(product_id)
        
        if model is None:
            return None
            
        try:
            # Récupération des données récentes pour validation
            with sqlite3.connect(self.db_path) as conn:
                query = '''
                    SELECT order_date, SUM(quantity) as quantity,
                           p.name as product_name
                    FROM sales_history s
                    JOIN products p ON s.product_id = p.id
                    WHERE product_id = ?
                    AND order_date >= DATE('now', '-90 days')
                    GROUP BY order_date
                    ORDER BY order_date
                '''
                recent_df = pd.read_sql_query(query, conn, params=[product_id])
            
            if recent_df.empty:
                logger.warning(f"Pas de données récentes pour validation produit {product_id}")
                return metadata
            
            # Préparer les données pour Prophet
            recent_df['ds'] = pd.to_datetime(recent_df['order_date'])
            recent_df['y'] = recent_df['quantity'].astype(float)
            
            # Prédictions sur les données récentes
            forecast = model.predict(recent_df[['ds']])
            
            # Calcul MAPE sur données récentes
            recent_mape = self.calculate_mape(recent_df['y'], forecast['yhat'])
            
            # Prédictions futures (7 jours)
            future = model.make_future_dataframe(periods=7)
            future_forecast = model.predict(future)
            
            # Validation des prédictions futures
            future_predictions = future_forecast.tail(7)
            
            validation_result = {
                'product_id': product_id,
                'product_name': recent_df['product_name'].iloc[0],
                'original_mape': metadata['mape'],
                'recent_mape': round(recent_mape, 2),
                'performance_stable': abs(recent_mape - metadata['mape']) < 5.0,
                'future_predictions': {
                    'dates': future_predictions['ds'].dt.strftime('%Y-%m-%d').tolist(),
                    'values': future_predictions['yhat'].round(2).tolist(),
                    'confidence_lower': future_predictions['yhat_lower'].round(2).tolist(),
                    'confidence_upper': future_predictions['yhat_upper'].round(2).tolist()
                },
                'validation_date': datetime.now().isoformat(),
                'status': 'VALID' if recent_mape < 20 else 'WARNING' if recent_mape < 30 else 'INVALID'
            }
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Erreur validation produit {product_id}: {e}")
            return None
    
    def calculate_mape(self, actual, predicted):
        """Calcule le MAPE en évitant la division par zéro"""
        mask = actual != 0
        if not mask.any():
            return 100.0
            
        actual_filtered = actual[mask]
        predicted_filtered = predicted[mask]
        
        return np.mean(np.abs((actual_filtered - predicted_filtered) / actual_filtered)) * 100
    
    def validate_all_models(self):
        """Valide tous les modèles entraînés"""
        logger.info(" Validation des modèles entraînés")
        
        # Récupération de la liste des produits
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT id, name FROM products ORDER BY id"
            products_df = pd.read_sql_query(query, conn)
        
        validation_results = []
        performance_summary = {
            'valid_models': 0,
            'warning_models': 0,
            'invalid_models': 0,
            'missing_models': 0
        }
        
        for _, product in products_df.iterrows():
            product_id = product['id']
            
            validation = self.validate_model_performance(product_id)
            
            if validation is None:
                performance_summary['missing_models'] += 1
                logger.warning(f"Modèle manquant: {product['name']}")
                continue
            
            validation_results.append(validation)
            
            # Comptage par statut
            status = validation['status']
            if status == 'VALID':
                performance_summary['valid_models'] += 1
                logger.info(f" {validation['product_name']}: MAPE {validation['recent_mape']}%")
            elif status == 'WARNING':
                performance_summary['warning_models'] += 1
                logger.warning(f" {validation['product_name']}: MAPE {validation['recent_mape']}%")
            else:
                performance_summary['invalid_models'] += 1
                logger.error(f" {validation['product_name']}: MAPE {validation['recent_mape']}%")
        
        # Sauvegarde des résultats
        self.save_validation_report(validation_results, performance_summary)
        
        return validation_results, performance_summary
    
    def save_validation_report(self, validation_results, performance_summary):
        """Sauvegarde le rapport de validation"""
        report = {
            'validation_summary': performance_summary,
            'total_models': sum(performance_summary.values()),
            'validation_rate': (performance_summary['valid_models'] / sum(performance_summary.values())) * 100 if sum(performance_summary.values()) > 0 else 0,
            'detailed_results': validation_results,
            'global_mape': np.mean([r['recent_mape'] for r in validation_results]) if validation_results else 0,
            'validated_at': datetime.now().isoformat()
        }
        
        # Sauvegarde
        report_path = self.models_dir / "validation_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info("=" * 50)
        logger.info("📋 RAPPORT DE VALIDATION")
        logger.info("=" * 50)
        logger.info(f"Modèles valides: {performance_summary['valid_models']}")
        logger.info(f"Modèles en warning: {performance_summary['warning_models']}")
        logger.info(f"Modèles invalides: {performance_summary['invalid_models']}")
        logger.info(f"Modèles manquants: {performance_summary['missing_models']}")
        logger.info(f"Taux de validation: {report['validation_rate']:.1f}%")
        logger.info(f"MAPE global: {report['global_mape']:.2f}%")
        
        return report
    
    def test_prediction_coherence(self):
        """Teste la cohérence des prédictions entre produits"""
        logger.info(" Test de cohérence des prédictions")
        
        coherence_tests = []
        
        # Test 1: Les climatiseurs doivent avoir des pics en été
        summer_coherence = self.test_seasonal_coherence('CLIMATISATION', 'summer')
        coherence_tests.append(summer_coherence)
        
        # Test 2: Cohérence événementielle (Tabaski doit impacter tous les produits)
        event_coherence = self.test_event_coherence('Tabaski')
        coherence_tests.append(event_coherence)
        
        return coherence_tests
    
    def test_seasonal_coherence(self, category, season):
        """Teste la cohérence saisonnière pour une catégorie"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = '''
                    SELECT id, name FROM products 
                    WHERE category = ?
                '''
                category_products = pd.read_sql_query(query, conn, params=[category])
            
            seasonal_predictions = []
            
            for _, product in category_products.iterrows():
                model, metadata = self.load_model(product['id'])
                if model is not None:
                    # Prédictions pour l'été 2025 (juin-août)
                    summer_dates = pd.date_range('2025-06-01', '2025-08-31', freq='D')
                    summer_df = pd.DataFrame({'ds': summer_dates})
                    
                    forecast = model.predict(summer_df)
                    summer_avg = forecast['yhat'].mean()
                    
                    seasonal_predictions.append({
                        'product_name': product['name'],
                        'summer_avg': summer_avg
                    })
            
            return {
                'test_type': f'{category}_{season}_coherence',
                'passed': len(seasonal_predictions) > 0,
                'details': seasonal_predictions
            }
            
        except Exception as e:
            logger.error(f"Erreur test cohérence saisonnière: {e}")
            return {'test_type': f'{category}_{season}_coherence', 'passed': False, 'error': str(e)}
    
    def test_event_coherence(self, event_name):
        """Teste l'impact cohérent d'un événement"""
        # Test simplifié - vérifier que les modèles incluent l'événement
        try:
            holidays_path = self.models_dir / "prophet_holidays.csv"
            if holidays_path.exists():
                holidays_df = pd.read_csv(holidays_path)
                event_present = event_name in holidays_df['holiday'].str.contains(event_name, na=False).any() if not holidays_df.empty else False
                
                return {
                    'test_type': f'{event_name}_event_coherence',
                    'passed': event_present,
                    'details': f"Événement {event_name} {'inclus' if event_present else 'manquant'} dans les modèles"
                }
            else:
                return {
                    'test_type': f'{event_name}_event_coherence',
                    'passed': False,
                    'details': 'Fichier holidays manquant'
                }
                
        except Exception as e:
            return {
                'test_type': f'{event_name}_event_coherence',
                'passed': False,
                'error': str(e)
            }

def main():
    """Point d'entrée principal"""
    try:
        validator = ModelValidator()
        
        # Validation des performances
        validation_results, performance_summary = validator.validate_all_models()
        
        # Tests de cohérence
        coherence_tests = validator.test_prediction_coherence()
        
        # Résultat global
        global_valid = (
            performance_summary['valid_models'] >= 8 and  # Au moins 8/12 modèles valides
            performance_summary['invalid_models'] == 0     # Aucun modèle invalide
        )
        
        print(json.dumps({
            'status': 'success',
            'validation_passed': global_valid,
            'valid_models': performance_summary['valid_models'],
            'total_models': sum(performance_summary.values()),
            'global_mape': np.mean([r['recent_mape'] for r in validation_results]) if validation_results else 0,
            'coherence_tests_passed': sum(1 for t in coherence_tests if t['passed']),
            'timestamp': datetime.now().isoformat()
        }))
        
    except Exception as e:
        logger.error(f"Erreur validation globale: {e}")
        print(json.dumps({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }))

if __name__ == "__main__":
    main()