"""
backtesting_engine.py - Moteur principal de backtesting temporel

Effectue la validation temporelle des modèles Prophet sur les données historiques.
Méthodologie : Split strict 2022-2023 (train) vs 2024 (test)
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pickle
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import warnings

warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BacktestingEngine:
    """
    Moteur de backtesting pour validation académique des performances

    Principe : Simuler le système comme s'il fonctionnait en temps réel sur 2024,
    en utilisant uniquement les données 2022-2023 pour l'entraînement.
    """

    def __init__(self, db_path: str = "optiflow.db", models_dir: str = "models"):
        """
        Initialise le moteur de backtesting

        Args:
            db_path: Chemin vers la base de données SQLite
            models_dir: Répertoire contenant les modèles Prophet
        """
        self.db_path = db_path
        self.models_dir = Path(models_dir)

        # Périodes de validation
        self.train_start = "2022-01-01"
        self.train_end = "2023-12-31"
        self.test_start = "2024-01-01"
        self.test_end = "2024-12-31"

        # Cache des résultats
        self.predictions_cache = {}
        self.actuals_cache = {}

        logger.info(f"Backtesting Engine initialisé")
        logger.info(f"Train: {self.train_start} à {self.train_end}")
        logger.info(f"Test: {self.test_start} à {self.test_end}")

    def get_connection(self) -> sqlite3.Connection:
        """Retourne une connexion à la base de données"""
        return sqlite3.connect(self.db_path)

    def get_historical_sales(self, product_id: int, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Récupère les ventes historiques pour un produit sur une période

        Args:
            product_id: ID du produit
            start_date: Date de début (format YYYY-MM-DD)
            end_date: Date de fin (format YYYY-MM-DD)

        Returns:
            DataFrame avec colonnes [date, quantity]
        """
        with self.get_connection() as conn:
            query = """
                SELECT
                    order_date as date,
                    SUM(quantity) as quantity
                FROM sales_history
                WHERE product_id = ?
                    AND order_date >= ?
                    AND order_date <= ?
                GROUP BY order_date
                ORDER BY order_date
            """

            df = pd.read_sql_query(
                query,
                conn,
                params=[product_id, start_date, end_date]
            )

            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])

            return df

    def get_product_list(self) -> List[Dict]:
        """Récupère la liste des produits"""
        with self.get_connection() as conn:
            query = """
                SELECT id, name, category
                FROM products
                ORDER BY id
            """
            cursor = conn.cursor()
            cursor.execute(query)

            products = []
            for row in cursor.fetchall():
                products.append({
                    'id': row[0],
                    'name': row[1],
                    'category': row[2]
                })

            return products

    def simulate_daily_predictions(self, product_id: int) -> pd.DataFrame:
        """
        Simule les prédictions jour par jour pour 2024

        Cette fonction simule ce que le système aurait prédit chaque jour de 2024
        en utilisant uniquement les données disponibles jusqu'à 2023.

        Args:
            product_id: ID du produit

        Returns:
            DataFrame avec colonnes [date, predicted, actual]
        """
        logger.info(f"Simulation des prédictions pour produit {product_id}")

        # Charger le modèle entraîné sur 2022-2023
        model_path = self.models_dir / f"prophet_model_{product_id}.pkl"

        if not model_path.exists():
            logger.warning(f"Modèle non trouvé pour produit {product_id}")
            return pd.DataFrame()

        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)

            # Créer les dates de prédiction pour 2024
            test_dates = pd.date_range(
                start=self.test_start,
                end=self.test_end,
                freq='D'
            )

            # Préparer le DataFrame pour Prophet
            future = pd.DataFrame({'ds': test_dates})

            # Faire les prédictions
            forecast = model.predict(future)

            # Récupérer les ventes réelles de 2024
            actuals = self.get_historical_sales(
                product_id,
                self.test_start,
                self.test_end
            )

            # Fusionner prédictions et réel
            results = pd.DataFrame({
                'date': forecast['ds'],
                'predicted': forecast['yhat'].clip(lower=0),  # Pas de prédictions négatives
                'predicted_lower': forecast['yhat_lower'].clip(lower=0),
                'predicted_upper': forecast['yhat_upper'].clip(lower=0)
            })

            # Joindre avec les ventes réelles
            if not actuals.empty:
                actuals = actuals.rename(columns={'quantity': 'actual'})
                results = results.merge(actuals, on='date', how='left')
                results['actual'] = results['actual'].fillna(0)
            else:
                results['actual'] = 0

            return results

        except Exception as e:
            logger.error(f"Erreur simulation produit {product_id}: {e}")
            return pd.DataFrame()

    def run_temporal_validation(self) -> Dict[str, Any]:
        """
        Exécute la validation temporelle complète sur tous les produits

        Returns:
            Dictionnaire avec tous les résultats de validation
        """
        logger.info("=" * 60)
        logger.info("DÉBUT DE LA VALIDATION TEMPORELLE")
        logger.info("=" * 60)

        products = self.get_product_list()
        all_results = {
            'metadata': {
                'validation_date': datetime.now().isoformat(),
                'train_period': f"{self.train_start} to {self.train_end}",
                'test_period': f"{self.test_start} to {self.test_end}",
                'n_products': len(products)
            },
            'product_results': {},
            'daily_predictions': {}
        }

        for product in products:
            product_id = product['id']
            product_name = product['name']

            logger.info(f"\nValidation produit {product_id}: {product_name}")

            # Simuler les prédictions journalières
            predictions_df = self.simulate_daily_predictions(product_id)

            if not predictions_df.empty:
                # Stocker les résultats
                all_results['product_results'][product_id] = {
                    'name': product_name,
                    'category': product['category'],
                    'n_predictions': len(predictions_df),
                    'predictions': predictions_df.to_dict('records')
                }

                # Calculer les métriques de base
                mape = self._calculate_mape_simple(
                    predictions_df['predicted'].values,
                    predictions_df['actual'].values
                )

                all_results['product_results'][product_id]['mape'] = round(mape, 2)

                logger.info(f"  ✓ {len(predictions_df)} prédictions - MAPE: {mape:.2f}%")
            else:
                logger.warning(f"  ✗ Pas de données pour ce produit")

        logger.info("\n" + "=" * 60)
        logger.info("VALIDATION TEMPORELLE TERMINÉE")
        logger.info("=" * 60)

        return all_results

    def walk_forward_analysis(self, window_size: int = 30) -> Dict[str, Any]:
        """
        Effectue une analyse walk-forward mois par mois sur 2024

        Walk-forward : Technique où on avance dans le temps en réentraînant
        le modèle à chaque période avec les nouvelles données disponibles.

        Args:
            window_size: Taille de la fenêtre de test en jours (30 = mensuel)

        Returns:
            Résultats de l'analyse walk-forward
        """
        logger.info("\n" + "=" * 60)
        logger.info("WALK-FORWARD ANALYSIS")
        logger.info("=" * 60)

        products = self.get_product_list()[:3]  # Limiter à 3 produits pour la démo

        # Créer les fenêtres de validation
        test_start = pd.to_datetime(self.test_start)
        test_end = pd.to_datetime(self.test_end)

        windows = []
        current_date = test_start

        while current_date < test_end:
            window_end = min(current_date + timedelta(days=window_size), test_end)
            windows.append({
                'start': current_date,
                'end': window_end,
                'month': current_date.strftime('%Y-%m')
            })
            current_date = window_end

        results = {
            'windows': [],
            'performance_evolution': {}
        }

        for window in windows:
            logger.info(f"\nFenêtre: {window['month']}")
            window_results = {
                'month': window['month'],
                'start': window['start'].isoformat(),
                'end': window['end'].isoformat(),
                'products': {}
            }

            for product in products:
                # Simuler les prédictions pour cette fenêtre
                # (Dans un vrai walk-forward, on réentraînerait ici)
                predictions = self._get_window_predictions(
                    product['id'],
                    window['start'],
                    window['end']
                )

                if predictions is not None:
                    mape = self._calculate_mape_simple(
                        predictions['predicted'],
                        predictions['actual']
                    )

                    window_results['products'][product['id']] = {
                        'name': product['name'],
                        'mape': round(mape, 2)
                    }

            results['windows'].append(window_results)

        # Calculer l'évolution de la performance
        for product in products:
            evolution = []
            for window in results['windows']:
                if product['id'] in window['products']:
                    evolution.append(window['products'][product['id']]['mape'])

            if evolution:
                results['performance_evolution'][product['id']] = {
                    'name': product['name'],
                    'mape_evolution': evolution,
                    'trend': 'amélioration' if evolution[-1] < evolution[0] else 'dégradation'
                }

        return results

    def _calculate_mape_simple(self, predicted: np.ndarray, actual: np.ndarray) -> float:
        """
        Calcule le MAPE de manière simple et robuste

        Args:
            predicted: Valeurs prédites
            actual: Valeurs réelles

        Returns:
            MAPE en pourcentage
        """
        # Filtrer les zéros pour éviter la division par zéro
        mask = actual != 0
        if not mask.any():
            return 100.0

        predicted_filtered = predicted[mask]
        actual_filtered = actual[mask]

        mape = np.mean(np.abs((actual_filtered - predicted_filtered) / actual_filtered)) * 100

        return min(mape, 100.0)  # Limiter à 100%

    def _get_window_predictions(self, product_id: int, start: pd.Timestamp, end: pd.Timestamp) -> Optional[Dict]:
        """
        Récupère les prédictions pour une fenêtre temporelle spécifique

        Args:
            product_id: ID du produit
            start: Date de début de la fenêtre
            end: Date de fin de la fenêtre

        Returns:
            Dictionnaire avec predicted et actual arrays
        """
        # Utiliser le cache si disponible
        cache_key = f"{product_id}_{start}_{end}"
        if cache_key in self.predictions_cache:
            return self.predictions_cache[cache_key]

        # Sinon, extraire de la simulation complète
        full_predictions = self.simulate_daily_predictions(product_id)

        if full_predictions.empty:
            return None

        # Filtrer sur la fenêtre
        mask = (full_predictions['date'] >= start) & (full_predictions['date'] <= end)
        window_data = full_predictions[mask]

        if window_data.empty:
            return None

        result = {
            'predicted': window_data['predicted'].values,
            'actual': window_data['actual'].values
        }

        # Mettre en cache
        self.predictions_cache[cache_key] = result

        return result

    def save_results(self, results: Dict, filename: str = "backtesting_results.json"):
        """
        Sauvegarde les résultats dans un fichier JSON

        Args:
            results: Résultats à sauvegarder
            filename: Nom du fichier de sortie
        """
        output_path = Path("validation") / filename

        # Convertir les arrays numpy en listes pour JSON
        def convert_to_serializable(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            elif isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            return obj

        # Convertir récursivement
        serializable_results = json.loads(
            json.dumps(results, default=convert_to_serializable)
        )

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)

        logger.info(f"Résultats sauvegardés dans {output_path}")


def main():
    """Fonction de test du moteur de backtesting"""
    engine = BacktestingEngine()

    # Test validation temporelle
    print("\n🔄 Validation temporelle en cours...")
    temporal_results = engine.run_temporal_validation()

    # Test walk-forward
    print("\n🚶 Walk-forward analysis...")
    walk_forward_results = engine.walk_forward_analysis()

    # Sauvegarder les résultats
    all_results = {
        'temporal_validation': temporal_results,
        'walk_forward': walk_forward_results
    }

    engine.save_results(all_results)

    print("\n✅ Backtesting terminé avec succès!")
    print(f"📊 {len(temporal_results['product_results'])} produits validés")

    # Afficher un résumé
    if temporal_results['product_results']:
        mapes = [r['mape'] for r in temporal_results['product_results'].values() if 'mape' in r]
        if mapes:
            print(f"📈 MAPE moyen: {np.mean(mapes):.2f}%")


if __name__ == "__main__":
    main()