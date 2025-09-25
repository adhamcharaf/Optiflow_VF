#!/usr/bin/env python3
"""
Système de mise à jour hebdomadaire des prédictions
Régénère les prédictions sur 30 jours en intégrant les anomalies classifiées
Amélioration continue basée sur le feedback utilisateur
"""

import sqlite3
import logging
import pickle
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from prophet import Prophet

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WeeklyPredictionsUpdater:
    """Mise à jour hebdomadaire intelligente des prédictions"""

    def __init__(self, db_path: str = "optiflow.db", models_dir: str = "models"):
        self.db_path = db_path
        self.models_dir = Path(models_dir)
        self.prediction_horizon = 30  # Toujours 30 jours de prédictions
        self.generation_date = datetime.now()

    def run_weekly_update(self, force: bool = False) -> Dict:
        """
        Exécute la mise à jour hebdomadaire complète

        Args:
            force: Forcer l'exécution même si ce n'est pas dimanche

        Returns:
            Dict avec résultats de la mise à jour
        """
        # Vérifier si c'est dimanche ou si forcé
        if not force and datetime.now().weekday() != 6:
            logger.info("Mise à jour hebdomadaire planifiée pour dimanche. Utilisez --force pour exécuter maintenant.")
            return {"status": "skipped", "reason": "not_sunday"}

        logger.info("=" * 50)
        logger.info("MISE À JOUR HEBDOMADAIRE DES PRÉDICTIONS")
        logger.info(f"Date: {self.generation_date.strftime('%Y-%m-%d %H:%M')}")
        logger.info("=" * 50)

        results = {
            "start_time": self.generation_date.isoformat(),
            "products_updated": 0,
            "predictions_generated": 0,
            "anomalies_integrated": 0,
            "mape_improvement": 0,
            "errors": []
        }

        try:
            # Étape 1: Analyser les anomalies de la semaine
            anomalies_stats = self._analyze_weekly_anomalies()
            results["anomalies_integrated"] = anomalies_stats["total_classified"]

            # Étape 2: Récupérer la liste des produits
            products = self._get_all_products()

            # Étape 3: Pour chaque produit, générer 30 jours de prédictions
            for product in products:
                try:
                    logger.info(f"\nTraitement produit {product['id']}: {product['name']}")

                    # Générer les prédictions
                    predictions = self._generate_predictions_for_product(
                        product['id'],
                        anomalies_stats["by_product"].get(product['id'], {})
                    )

                    if predictions:
                        # Sauvegarder dans la base de données
                        self._save_predictions_to_db(product['id'], predictions)
                        results["products_updated"] += 1
                        results["predictions_generated"] += len(predictions)

                except Exception as e:
                    logger.error(f"Erreur produit {product['id']}: {str(e)}")
                    results["errors"].append(f"Product {product['id']}: {str(e)}")

            # Étape 4: Calculer l'amélioration du MAPE
            mape_stats = self._calculate_mape_improvement()
            results["mape_improvement"] = mape_stats.get("improvement_percent", 0)

            # Étape 5: Nettoyer les anciennes prédictions
            self._clean_old_predictions()

            # Étape 6: Mettre à jour les métadonnées système
            self._update_system_metadata(results)

            results["status"] = "success"
            results["end_time"] = datetime.now().isoformat()

            logger.info("\n" + "=" * 50)
            logger.info("RÉSUMÉ DE LA MISE À JOUR")
            logger.info(f"Produits mis à jour: {results['products_updated']}")
            logger.info(f"Prédictions générées: {results['predictions_generated']}")
            logger.info(f"Anomalies intégrées: {results['anomalies_integrated']}")
            logger.info(f"Amélioration MAPE: {results['mape_improvement']:.2f}%")
            logger.info("=" * 50)

        except Exception as e:
            logger.error(f"Erreur critique: {str(e)}")
            results["status"] = "error"
            results["error"] = str(e)

        return results

    def _analyze_weekly_anomalies(self) -> Dict:
        """Analyse les anomalies classifiées cette semaine"""
        conn = sqlite3.connect(self.db_path)

        # Récupérer les anomalies classifiées
        query = """
            SELECT
                product_id,
                status,
                COUNT(*) as count,
                AVG(deviation_percent) as avg_deviation
            FROM anomalies
            WHERE status IN ('seasonal', 'validated', 'exceptional')
                AND created_at >= date('now', '-7 days')
            GROUP BY product_id, status
        """

        df = pd.read_sql_query(query, conn)

        stats = {
            "total_classified": len(df),
            "by_product": {}
        }

        for _, row in df.iterrows():
            product_id = int(row['product_id'])
            if product_id not in stats["by_product"]:
                stats["by_product"][product_id] = {}

            stats["by_product"][product_id][row['status']] = {
                "count": int(row['count']),
                "avg_deviation": float(row['avg_deviation'])
            }

        conn.close()
        logger.info(f"Anomalies analysées: {stats['total_classified']} classifications")
        return stats

    def _get_all_products(self) -> List[Dict]:
        """Récupère tous les produits actifs"""
        conn = sqlite3.connect(self.db_path)
        query = "SELECT id, name FROM products ORDER BY id"
        cursor = conn.cursor()
        cursor.execute(query)

        products = []
        for row in cursor.fetchall():
            products.append({
                "id": row[0],
                "name": row[1]
            })

        conn.close()
        return products

    def _generate_predictions_for_product(self, product_id: int, anomaly_info: Dict) -> List[Dict]:
        """
        Génère 30 jours de prédictions pour un produit
        Intègre les informations d'anomalies pour amélioration
        """
        predictions = []

        try:
            # Charger le modèle Prophet
            model_path = self.models_dir / f"prophet_model_{product_id}.pkl"

            if not model_path.exists():
                logger.warning(f"Modèle non trouvé pour produit {product_id}, utilisation de moyennes")
                return self._generate_fallback_predictions(product_id)

            with open(model_path, 'rb') as f:
                model = pickle.load(f)

            # Obtenir les données historiques pour le modèle
            conn = sqlite3.connect(self.db_path)
            hist_query = """
                SELECT order_date as ds, quantity as y
                FROM sales_history
                WHERE product_id = ?
                ORDER BY order_date
            """
            historical = pd.read_sql_query(hist_query, conn, params=[product_id])
            conn.close()

            if historical.empty:
                logger.warning(f"Pas de données historiques pour produit {product_id}")
                return self._generate_fallback_predictions(product_id)

            historical['ds'] = pd.to_datetime(historical['ds'])

            # Créer le dataframe de dates futures à partir de demain
            last_date = historical['ds'].max()
            future_dates = pd.date_range(
                start=datetime.now().date() + timedelta(days=1),
                periods=self.prediction_horizon,
                freq='D'
            )
            future = pd.DataFrame({'ds': future_dates})

            # Faire les prédictions
            forecast = model.predict(future)

            # Ajuster selon les anomalies saisonnières détectées
            if 'seasonal' in anomaly_info:
                seasonal_adj = 1 + (anomaly_info['seasonal']['avg_deviation'] / 100 * 0.3)
                forecast['yhat'] *= seasonal_adj
                forecast['yhat_lower'] *= seasonal_adj
                forecast['yhat_upper'] *= seasonal_adj
                logger.info(f"  Ajustement saisonnier appliqué: {seasonal_adj:.2f}x")

            # Convertir en format pour la DB
            for _, row in forecast.iterrows():
                predictions.append({
                    'product_id': product_id,
                    'forecast_date': row['ds'].strftime('%Y-%m-%d'),
                    'predicted_quantity': max(0, row['yhat']),  # Pas de valeurs négatives
                    'lower_bound': max(0, row['yhat_lower']),
                    'upper_bound': max(0, row['yhat_upper']),
                    'confidence_interval': 0.95,
                    'model_version': f"weekly_v{self.generation_date.strftime('%Y%m%d')}",
                    'includes_anomalies': 1 if anomaly_info else 0
                })

            logger.info(f"  {len(predictions)} prédictions générées")

        except Exception as e:
            logger.error(f"Erreur génération prédictions produit {product_id}: {e}")
            return self._generate_fallback_predictions(product_id)

        return predictions

    def _generate_fallback_predictions(self, product_id: int) -> List[Dict]:
        """Génère des prédictions basiques basées sur les moyennes historiques"""
        conn = sqlite3.connect(self.db_path)

        # Calculer la moyenne des ventes sur les 30 derniers jours
        query = """
            SELECT AVG(quantity) as avg_sales
            FROM sales_history
            WHERE product_id = ?
                AND order_date >= date('now', '-30 days')
        """

        cursor = conn.cursor()
        cursor.execute(query, [product_id])
        result = cursor.fetchone()
        avg_sales = result[0] if result and result[0] else 10.0

        predictions = []
        base_date = datetime.now()

        for i in range(self.prediction_horizon):
            forecast_date = base_date + timedelta(days=i+1)

            # Variation simple selon le jour de la semaine
            day_factor = 1.1 if forecast_date.weekday() < 5 else 0.8

            predictions.append({
                'product_id': product_id,
                'forecast_date': forecast_date.strftime('%Y-%m-%d'),
                'predicted_quantity': avg_sales * day_factor,
                'lower_bound': avg_sales * day_factor * 0.8,
                'upper_bound': avg_sales * day_factor * 1.2,
                'confidence_interval': 0.8,
                'model_version': f"fallback_v{self.generation_date.strftime('%Y%m%d')}",
                'includes_anomalies': 0
            })

        conn.close()
        return predictions

    def _save_predictions_to_db(self, product_id: int, predictions: List[Dict]):
        """Sauvegarde les nouvelles prédictions dans la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Supprimer les anciennes prédictions pour ce produit
        cursor.execute(
            "DELETE FROM forecasts WHERE product_id = ? AND forecast_date >= date('now')",
            [product_id]
        )

        # Insérer les nouvelles prédictions
        for pred in predictions:
            cursor.execute("""
                INSERT INTO forecasts (
                    product_id, forecast_date, predicted_quantity,
                    lower_bound, upper_bound, confidence_interval,
                    model_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pred['product_id'],
                pred['forecast_date'],
                pred['predicted_quantity'],
                pred['lower_bound'],
                pred['upper_bound'],
                pred['confidence_interval'],
                pred['model_version'],
                datetime.now()
            ))

        conn.commit()
        conn.close()

    def _calculate_mape_improvement(self) -> Dict:
        """Calcule l'amélioration du MAPE après intégration des anomalies"""
        conn = sqlite3.connect(self.db_path)

        # MAPE de la semaine dernière vs cette semaine
        query = """
            SELECT
                AVG(ABS(actual_value - predicted_value) / NULLIF(actual_value, 0)) * 100 as mape
            FROM anomalies
            WHERE status != 'exceptional'
                AND created_at >= date('now', '-7 days')
        """

        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        current_mape = result[0] if result and result[0] else 15.0

        # Récupérer l'ancien MAPE depuis les métadonnées
        cursor.execute(
            "SELECT value FROM system_metadata WHERE key = 'last_weekly_mape'"
        )
        result = cursor.fetchone()
        last_mape = float(result[0]) if result else 20.0

        improvement = last_mape - current_mape
        improvement_percent = (improvement / last_mape * 100) if last_mape > 0 else 0

        # Mettre à jour le MAPE actuel
        cursor.execute("""
            INSERT OR REPLACE INTO system_metadata (key, value, updated_at)
            VALUES ('last_weekly_mape', ?, ?)
        """, (str(current_mape), datetime.now()))

        conn.commit()
        conn.close()

        return {
            "current_mape": current_mape,
            "last_mape": last_mape,
            "improvement": improvement,
            "improvement_percent": improvement_percent
        }

    def _clean_old_predictions(self):
        """Nettoie les prédictions obsolètes (plus de 30 jours dans le passé)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM forecasts
            WHERE forecast_date < date('now', '-30 days')
        """)

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted > 0:
            logger.info(f"Nettoyage: {deleted} prédictions obsolètes supprimées")

    def _update_system_metadata(self, results: Dict):
        """Met à jour les métadonnées système"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        metadata = {
            'last_weekly_update': self.generation_date.isoformat(),
            'weekly_products_updated': str(results['products_updated']),
            'weekly_predictions_generated': str(results['predictions_generated']),
            'weekly_anomalies_integrated': str(results['anomalies_integrated']),
            'weekly_mape_improvement': str(results['mape_improvement'])
        }

        for key, value in metadata.items():
            cursor.execute("""
                INSERT OR REPLACE INTO system_metadata (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, datetime.now()))

        conn.commit()
        conn.close()

def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description="Mise à jour hebdomadaire des prédictions Optiflow")
    parser.add_argument('--force', action='store_true', help="Forcer l'exécution même si ce n'est pas dimanche")
    parser.add_argument('--days', type=int, default=30, help="Nombre de jours de prédictions (défaut: 30)")
    parser.add_argument('--db', default='optiflow.db', help="Chemin vers la base de données")
    parser.add_argument('--models', default='models', help="Dossier des modèles Prophet")

    args = parser.parse_args()

    # Créer et exécuter l'updater
    updater = WeeklyPredictionsUpdater(db_path=args.db, models_dir=args.models)
    updater.prediction_horizon = args.days

    results = updater.run_weekly_update(force=args.force)

    # Retourner le code de sortie approprié
    if results.get("status") == "success":
        return 0
    elif results.get("status") == "skipped":
        return 2
    else:
        return 1

if __name__ == "__main__":
    exit(main())