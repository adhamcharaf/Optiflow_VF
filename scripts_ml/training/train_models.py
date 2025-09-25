#!/usr/bin/env python3
"""
train_models.py - Entraîne les modèles Prophet pour les 12 produits
Script principal d'entraînement avec validation et sauvegarde
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pickle
import json
import logging
from pathlib import Path
import warnings

# Suppression des warnings Prophet
warnings.filterwarnings("ignore")

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    print("ERREUR: Prophet n'est pas installé. Installez avec: pip install prophet")
    PROPHET_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptiflowModelTrainer:
    """Entraîneur de modèles Prophet pour Optiflow"""
    
    def __init__(self, db_path="../../optiflow.db", models_dir="../../models"):
        self.db_path = db_path
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        
        # Chargement des événements
        self.holidays_df = self.load_holidays()
        
    def load_holidays(self):
        """Charge les événements préparés"""
        holidays_path = Path("../../models/prophet_holidays.csv")
        
        if holidays_path.exists():
            holidays_df = pd.read_csv(holidays_path)
            holidays_df['ds'] = pd.to_datetime(holidays_df['ds'])
            logger.info(f"Événements chargés: {len(holidays_df)} occurrences")
            return holidays_df
        else:
            logger.warning("Pas d'événements trouvés, continuons sans")
            return pd.DataFrame()
    
    def get_product_data(self, product_id):
        """Récupère les données d'entraînement pour un produit"""
        with sqlite3.connect(self.db_path) as conn:
            query = '''
                SELECT order_date, SUM(quantity) as quantity
                FROM sales_history 
                WHERE product_id = ?
                GROUP BY order_date
                ORDER BY order_date
            '''
            df = pd.read_sql_query(query, conn, params=[product_id])
            
            if df.empty:
                return None
                
            # Format Prophet (ds, y)
            df['ds'] = pd.to_datetime(df['order_date'])
            df['y'] = df['quantity'].astype(float)
            df = df[['ds', 'y']].copy()
            
            # Compléter les dates manquantes avec 0
            df = self.fill_missing_dates(df)
            
            return df
    
    def fill_missing_dates(self, df):
        """Complète les dates manquantes avec des ventes de 0"""
        df = df.sort_values('ds')
        
        # Créer une plage complète de dates
        full_date_range = pd.date_range(
            start=df['ds'].min(),
            end=df['ds'].max(),
            freq='D'
        )
        
        # DataFrame complet
        full_df = pd.DataFrame({'ds': full_date_range})
        
        # Merger et remplir les valeurs manquantes avec 0
        df = full_df.merge(df, on='ds', how='left')
        df['y'] = df['y'].fillna(0)
        
        return df
    
    def create_prophet_model(self, product_name):
        """Crée un modèle Prophet configuré selon les specs"""
        
        # Configuration selon les spécifications Optiflow
        model = Prophet(
            yearly_seasonality=True,        # Tendances annuelles
            weekly_seasonality=True,        # Pics samedi selon specs
            daily_seasonality=False,        # Données quotidiennes, pas besoin
            holidays=self.holidays_df if not self.holidays_df.empty else None,
            seasonality_mode='multiplicative',  # Pour les événements
            interval_width=0.8,             # Intervalle de confiance 80%
            changepoint_prior_scale=0.05,   # Flexibilité modérée
            holidays_prior_scale=10.0       # Impact fort des événements
        )
        
        # Saisonnalité personnalisée pour les produits saisonniers
        if 'Climatiseur' in product_name or 'Ventilateur' in product_name:
            # Forte saisonnalité pour climatisation (été)
            model.add_seasonality(
                name='monthly', 
                period=30.5, 
                fourier_order=5
            )
        elif 'Réfrigérateur' in product_name or 'Congélateur' in product_name:
            # Saisonnalité modérée pour le froid
            model.add_seasonality(
                name='monthly', 
                period=30.5, 
                fourier_order=3
            )
            
        return model
    
    def train_single_model(self, product_id, product_name):
        """Entraîne un modèle pour un produit spécifique"""
        logger.info(f"Entraînement modèle: {product_name}")
        
        # Récupération des données
        df = self.get_product_data(product_id)
        if df is None or len(df) < 100:  # Minimum 100 jours de données
            logger.warning(f"Données insuffisantes pour {product_name}")
            return None
            
        # Split train/test (80/20)
        split_date = df['ds'].quantile(0.8)
        train_df = df[df['ds'] <= split_date].copy()
        test_df = df[df['ds'] > split_date].copy()
        
        logger.info(f"  - Données train: {len(train_df)} jours")
        logger.info(f"  - Données test: {len(test_df)} jours")
        
        try:
            # Création et entraînement du modèle
            model = self.create_prophet_model(product_name)
            model.fit(train_df)
            
            # Prédictions sur les données test
            test_forecast = model.predict(test_df[['ds']])
            
            # Calcul de la performance (MAPE)
            mape = self.calculate_mape(test_df['y'], test_forecast['yhat'])
            
            # Prédictions futures (30 jours)
            future = model.make_future_dataframe(periods=30)
            forecast = model.predict(future)
            
            # Métadonnées du modèle
            model_metadata = {
                'product_id': product_id,
                'product_name': product_name,
                'train_size': len(train_df),
                'test_size': len(test_df),
                'mape': round(mape, 2),
                'trained_at': datetime.now().isoformat(),
                'data_range': {
                    'start': train_df['ds'].min().strftime('%Y-%m-%d'),
                    'end': train_df['ds'].max().strftime('%Y-%m-%d')
                },
                'has_events': len(self.holidays_df) > 0,
                'performance_grade': 'A' if mape < 10 else 'B' if mape < 15 else 'C'
            }
            
            logger.info(f"  - MAPE: {mape:.2f}% ({model_metadata['performance_grade']})")
            
            return {
                'model': model,
                'forecast': forecast,
                'metadata': model_metadata,
                'test_results': {
                    'actual': test_df['y'].tolist(),
                    'predicted': test_forecast['yhat'].tolist(),
                    'dates': test_df['ds'].dt.strftime('%Y-%m-%d').tolist()
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur entraînement {product_name}: {e}")
            return None
    
    def calculate_mape(self, actual, predicted):
        """Calcule le MAPE (Mean Absolute Percentage Error)"""
        # Éviter la division par zéro et aligner les séries
        actual = actual.reset_index(drop=True)
        predicted = predicted.reset_index(drop=True)
        
        # Assurer même longueur
        min_len = min(len(actual), len(predicted))
        actual = actual[:min_len]
        predicted = predicted[:min_len]
        
        mask = actual != 0
        if not mask.any():
            return 100.0
            
        actual_filtered = actual[mask]
        predicted_filtered = predicted[mask]
        
        mape = np.mean(np.abs((actual_filtered - predicted_filtered) / actual_filtered)) * 100
        return mape
    
    def save_model(self, model_result, product_id):
        """Sauvegarde un modèle entraîné"""
        if model_result is None:
            return False
            
        try:
            # Sauvegarde du modèle Prophet
            model_path = self.models_dir / f"prophet_model_{product_id}.pkl"
            with open(model_path, 'wb') as f:
                pickle.dump(model_result['model'], f)
            
            # Sauvegarde des métadonnées
            metadata_path = self.models_dir / f"model_metadata_{product_id}.json"
            with open(metadata_path, 'w') as f:
                json.dump(model_result['metadata'], f, indent=2)
            
            # Sauvegarde des prédictions de test
            test_path = self.models_dir / f"test_results_{product_id}.json"
            with open(test_path, 'w') as f:
                json.dump(model_result['test_results'], f, indent=2)
                
            # Sauvegarde du forecast
            forecast_path = self.models_dir / f"forecast_{product_id}.csv"
            model_result['forecast'].to_csv(forecast_path, index=False)
            
            logger.info(f"  - Modèle sauvé: {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde modèle {product_id}: {e}")
            return False
    
    def train_all_models(self):
        """Entraîne tous les modèles pour les 12 produits"""
        
        if not PROPHET_AVAILABLE:
            raise ImportError("Prophet non disponible")
            
        logger.info("🚀 Début de l'entraînement des modèles Prophet")
        
        # Récupération de la liste des produits
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT id, name, category FROM products ORDER BY id"
            products_df = pd.read_sql_query(query, conn)
        
        results = {
            'trained_models': [],
            'failed_models': [],
            'performance_summary': []
        }
        
        for _, product in products_df.iterrows():
            product_id = product['id']
            product_name = product['name']
            
            # Entraînement du modèle
            model_result = self.train_single_model(product_id, product_name)
            
            if model_result:
                # Sauvegarde
                if self.save_model(model_result, product_id):
                    results['trained_models'].append(product_id)
                    results['performance_summary'].append({
                        'product_id': product_id,
                        'product_name': product_name,
                        'mape': model_result['metadata']['mape'],
                        'grade': model_result['metadata']['performance_grade']
                    })
                else:
                    results['failed_models'].append(product_id)
            else:
                results['failed_models'].append(product_id)
        
        # Rapport final
        self.generate_training_report(results)
        
        return results
    
    def generate_training_report(self, results):
        """Génère un rapport d'entraînement"""
        report = {
            'training_summary': {
                'total_products': len(results['trained_models']) + len(results['failed_models']),
                'successful_trainings': len(results['trained_models']),
                'failed_trainings': len(results['failed_models']),
                'success_rate': len(results['trained_models']) / (len(results['trained_models']) + len(results['failed_models'])) * 100
            },
            'performance_stats': results['performance_summary'],
            'global_mape': np.mean([p['mape'] for p in results['performance_summary']]) if results['performance_summary'] else 0,
            'trained_at': datetime.now().isoformat()
        }
        
        # Sauvegarde du rapport
        report_path = self.models_dir / "training_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Log du rapport
        logger.info("=" * 50)
        logger.info("📊 RAPPORT D'ENTRAÎNEMENT")
        logger.info("=" * 50)
        logger.info(f"Produits traités: {report['training_summary']['total_products']}")
        logger.info(f"Entraînements réussis: {report['training_summary']['successful_trainings']}")
        logger.info(f"Échecs: {report['training_summary']['failed_trainings']}")
        logger.info(f"Taux de succès: {report['training_summary']['success_rate']:.1f}%")
        logger.info(f"MAPE global: {report['global_mape']:.2f}%")
        
        if results['performance_summary']:
            logger.info("\\nPerformances par produit:")
            for perf in results['performance_summary']:
                logger.info(f"  - {perf['product_name']}: {perf['mape']:.2f}% ({perf['grade']})")

def main():
    """Point d'entrée principal"""
    try:
        trainer = OptiflowModelTrainer()
        results = trainer.train_all_models()
        
        # Output pour orchestrateur
        print(json.dumps({
            'status': 'success',
            'models_trained': len(results['trained_models']),
            'models_failed': len(results['failed_models']),
            'global_mape': np.mean([p['mape'] for p in results['performance_summary']]) if results['performance_summary'] else 0,
            'timestamp': datetime.now().isoformat()
        }))
        
    except Exception as e:
        logger.error(f"Erreur entraînement global: {e}")
        print(json.dumps({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }))

if __name__ == "__main__":
    main()