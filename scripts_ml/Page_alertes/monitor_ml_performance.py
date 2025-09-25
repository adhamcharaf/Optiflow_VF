"""
Script 5: monitor_ml_performance.py
Suivi et amélioration de la performance des prédictions ML
Calcul MAPE, identification patterns d'erreur, recommandations
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import statistics

import pandas as pd
import numpy as np
import sqlite3

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MLPerformanceMonitor:
    def __init__(self, db_path: str = "optiflow.db", models_dir: str = "models"):
        self.db_path = db_path
        self.models_dir = models_dir
        self.conn = None
        self.performance_cache = {}
        
    def _get_connection(self):
        """Obtient une connexion à la base de données"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
        return self.conn
        
    def calculate_mape(
        self,
        predictions: List[float],
        actuals: List[float]
    ) -> float:
        """
        Calcule le Mean Absolute Percentage Error (MAPE)
        MAPE = (1/n) * Σ(|actual - predicted| / |actual|) * 100
        """
        if len(predictions) != len(actuals):
            raise ValueError("Les listes doivent avoir la même longueur")
            
        if not predictions or not actuals:
            return float('inf')
            
        mape_values = []
        for pred, actual in zip(predictions, actuals):
            if actual != 0:
                mape_values.append(abs(actual - pred) / abs(actual))
                
        if not mape_values:
            return float('inf')
            
        return statistics.mean(mape_values) * 100
        
    def monitor_article_performance(
        self,
        article_id: int,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Analyse la performance des prédictions pour un article
        
        Args:
            article_id: ID de l'article
            days_back: Nombre de jours à analyser
        """
        try:
            conn = self._get_connection()
            
            # Récupérer les prédictions passées
            query_predictions = """
                SELECT 
                    date_prediction,
                    quantite_predite,
                    confidence
                FROM predictions
                WHERE article_id = ?
                AND date_prediction >= date('now', '-{} days')
                AND date_prediction < date('now')
                ORDER BY date_prediction
            """.format(days_back)
            
            predictions_df = pd.read_sql_query(
                query_predictions,
                conn,
                params=[article_id]
            )
            
            if predictions_df.empty:
                return self._no_data_response(article_id)
                
            # Récupérer les ventes réelles
            query_actuals = """
                SELECT 
                    date,
                    SUM(quantity) as quantity_sold
                FROM ventes
                WHERE article_id = ?
                AND date >= date('now', '-{} days')
                AND date < date('now')
                GROUP BY date
                ORDER BY date
            """.format(days_back)
            
            actuals_df = pd.read_sql_query(
                query_actuals,
                conn,
                params=[article_id]
            )
            
            # Fusionner les données
            predictions_df['date_prediction'] = pd.to_datetime(predictions_df['date_prediction'])
            actuals_df['date'] = pd.to_datetime(actuals_df['date'])
            
            merged = pd.merge(
                predictions_df,
                actuals_df,
                left_on='date_prediction',
                right_on='date',
                how='inner'
            )
            
            if merged.empty:
                return self._no_data_response(article_id)
                
            # Calculer les métriques
            mape_global = self.calculate_mape(
                merged['quantite_predite'].tolist(),
                merged['quantity_sold'].tolist()
            )
            
            # Analyser par jour de la semaine
            merged['weekday'] = merged['date'].dt.day_name()
            mape_par_jour = self._calculate_mape_by_weekday(merged)
            
            # Identifier les patterns d'erreur
            error_pattern = self._identify_error_pattern(merged)
            
            # Calculer d'autres métriques
            metrics = self._calculate_additional_metrics(merged)
            
            # Générer les recommandations
            recommendations = self._generate_recommendations(
                mape_global,
                mape_par_jour,
                error_pattern,
                metrics
            )
            
            # Charger les métadonnées du modèle
            model_metadata = self._load_model_metadata(article_id)
            
            return {
                "article_id": article_id,
                "period_analyzed": f"{days_back} derniers jours",
                "mape_global": round(mape_global, 1),
                "mape_par_jour": mape_par_jour,
                "tendance_erreur": error_pattern,
                "metrics": metrics,
                "model_info": model_metadata,
                "recommendations": recommendations,
                "performance_trend": self._calculate_performance_trend(article_id),
                "data_points": len(merged),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur monitoring article {article_id}: {e}")
            return {
                "article_id": article_id,
                "error": str(e)
            }
            
    def _calculate_mape_by_weekday(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calcule le MAPE par jour de la semaine"""
        mape_by_day = {}
        
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
            day_data = df[df['weekday'] == day]
            
            if not day_data.empty:
                mape = self.calculate_mape(
                    day_data['quantite_predite'].tolist(),
                    day_data['quantity_sold'].tolist()
                )
                # Traduire en français
                day_fr = {
                    'Monday': 'Lundi',
                    'Tuesday': 'Mardi',
                    'Wednesday': 'Mercredi',
                    'Thursday': 'Jeudi',
                    'Friday': 'Vendredi',
                    'Saturday': 'Samedi',
                    'Sunday': 'Dimanche'
                }[day]
                mape_by_day[day_fr] = round(mape, 1)
                
        return mape_by_day
        
    def _identify_error_pattern(self, df: pd.DataFrame) -> str:
        """Identifie le pattern d'erreur dominant"""
        df['error'] = df['quantite_predite'] - df['quantity_sold']
        df['error_pct'] = (df['error'] / df['quantity_sold']) * 100
        
        # Analyser la distribution des erreurs
        mean_error = df['error'].mean()
        median_error = df['error'].median()
        
        # Identifier les patterns
        if mean_error > 5:
            pattern = "sur_estimation_systematique"
        elif mean_error < -5:
            pattern = "sous_estimation_systematique"
        else:
            # Analyser par jour de semaine
            weekend_error = df[df['weekday'].isin(['Saturday', 'Sunday'])]['error'].mean()
            weekday_error = df[~df['weekday'].isin(['Saturday', 'Sunday'])]['error'].mean()
            
            if abs(weekend_error) > abs(weekday_error) * 1.5:
                if weekend_error > 0:
                    pattern = "sur_estimation_weekends"
                else:
                    pattern = "sous_estimation_weekends"
            else:
                pattern = "equilibre"
                
        return pattern
        
    def _calculate_additional_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calcule des métriques supplémentaires"""
        df['error'] = df['quantite_predite'] - df['quantity_sold']
        df['abs_error'] = abs(df['error'])
        df['squared_error'] = df['error'] ** 2
        
        return {
            "mae": round(df['abs_error'].mean(), 2),  # Mean Absolute Error
            "rmse": round(np.sqrt(df['squared_error'].mean()), 2),  # Root Mean Square Error
            "bias": round(df['error'].mean(), 2),  # Biais moyen
            "std_error": round(df['error'].std(), 2),  # Écart-type des erreurs
            "accuracy_rate": round((1 - df['abs_error'].mean() / df['quantity_sold'].mean()) * 100, 1),
            "overestimation_rate": round((df['error'] > 0).mean() * 100, 1),
            "perfect_predictions": int((df['abs_error'] <= 1).sum()),
            "worst_prediction": {
                "date": df.loc[df['abs_error'].idxmax(), 'date'].strftime('%Y-%m-%d'),
                "predicted": float(df.loc[df['abs_error'].idxmax(), 'quantite_predite']),
                "actual": float(df.loc[df['abs_error'].idxmax(), 'quantity_sold']),
                "error": float(df.loc[df['abs_error'].idxmax(), 'abs_error'])
            }
        }
        
    def _generate_recommendations(
        self,
        mape_global: float,
        mape_par_jour: Dict,
        error_pattern: str,
        metrics: Dict
    ) -> List[str]:
        """Génère des recommandations d'amélioration"""
        recommendations = []
        
        # Recommandations basées sur le MAPE global
        if mape_global < 10:
            recommendations.append("✓ Excellente performance - Maintenir le modèle actuel")
        elif mape_global < 15:
            recommendations.append("✓ Bonne performance - Optimisations mineures possibles")
        elif mape_global < 25:
            recommendations.append(" Performance moyenne - Envisager réentraînement")
        else:
            recommendations.append(" Performance faible - Réentraînement urgent recommandé")
            
        # Recommandations basées sur les patterns
        pattern_recommendations = {
            "sur_estimation_systematique": "Ajuster le modèle pour réduire les prédictions",
            "sous_estimation_systematique": "Augmenter les prédictions ou ajuster la tendance",
            "sur_estimation_weekends": "Réduire le poids de la saisonnalité hebdomadaire",
            "sous_estimation_weekends": "Augmenter le poids de la saisonnalité hebdomadaire",
            "equilibre": "Modèle équilibré - Maintenir les paramètres actuels"
        }
        
        if error_pattern in pattern_recommendations:
            recommendations.append(pattern_recommendations[error_pattern])
            
        # Recommandations basées sur les jours spécifiques
        if mape_par_jour:
            worst_day = max(mape_par_jour, key=mape_par_jour.get)
            if mape_par_jour[worst_day] > mape_global * 1.5:
                recommendations.append(f"Améliorer les prédictions pour {worst_day}")
                
        # Recommandations basées sur le biais
        if abs(metrics['bias']) > 5:
            if metrics['bias'] > 0:
                recommendations.append("Réduire le biais positif du modèle")
            else:
                recommendations.append("Corriger le biais négatif du modèle")
                
        # Recommandations sur la variance
        if metrics['std_error'] > metrics['mae'] * 1.5:
            recommendations.append("Forte variance - Stabiliser les prédictions")
            
        return recommendations
        
    def _load_model_metadata(self, article_id: int) -> Dict[str, Any]:
        """Charge les métadonnées du modèle depuis les fichiers"""
        try:
            metadata_path = f"{self.models_dir}/model_metadata_{article_id}.json"
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                
            # Charger aussi les résultats de test
            test_path = f"{self.models_dir}/test_results_{article_id}.json"
            if pd.io.common.file_exists(test_path):
                with open(test_path, 'r') as f:
                    test_results = json.load(f)
                    metadata['test_performance'] = test_results
                    
            return metadata
            
        except FileNotFoundError:
            logger.warning(f"Métadonnées non trouvées pour article {article_id}")
            return {
                "status": "Métadonnées non disponibles",
                "training_date": "Unknown"
            }
        except Exception as e:
            logger.error(f"Erreur chargement métadonnées: {e}")
            return {"error": str(e)}
            
    def _calculate_performance_trend(self, article_id: int) -> str:
        """Calcule la tendance de performance sur plusieurs périodes"""
        try:
            # Calculer MAPE sur plusieurs fenêtres temporelles
            mape_7d = self._calculate_mape_for_period(article_id, 7)
            mape_14d = self._calculate_mape_for_period(article_id, 14)
            mape_30d = self._calculate_mape_for_period(article_id, 30)
            
            if mape_7d < mape_14d < mape_30d:
                return "amélioration"
            elif mape_7d > mape_14d > mape_30d:
                return "dégradation"
            else:
                return "stable"
                
        except Exception:
            return "indéterminée"
            
    def _calculate_mape_for_period(self, article_id: int, days: int) -> float:
        """Calcule le MAPE pour une période spécifique"""
        # Version simplifiée, devrait utiliser la même logique que monitor_article_performance
        # mais avec la période spécifiée
        return 15.0  # Placeholder
        
    def _no_data_response(self, article_id: int) -> Dict:
        """Réponse quand pas de données disponibles"""
        return {
            "article_id": article_id,
            "status": "no_data",
            "message": "Aucune donnée de performance disponible",
            "recommendations": [
                "Attendre l'accumulation de données",
                "Vérifier que les prédictions sont enregistrées"
            ]
        }
        
    def compare_models_performance(
        self,
        article_ids: List[int],
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Compare la performance entre plusieurs modèles/articles"""
        results = []
        
        for article_id in article_ids:
            perf = self.monitor_article_performance(article_id, days_back)
            if 'error' not in perf:
                results.append({
                    "article_id": article_id,
                    "mape": perf.get('mape_global', float('inf')),
                    "accuracy": perf.get('metrics', {}).get('accuracy_rate', 0),
                    "trend": perf.get('performance_trend', 'unknown')
                })
                
        # Trier par MAPE
        results.sort(key=lambda x: x['mape'])
        
        # Calculer les statistiques
        if results:
            mapes = [r['mape'] for r in results if r['mape'] != float('inf')]
            
            stats = {
                "best_model": results[0] if results else None,
                "worst_model": results[-1] if results else None,
                "average_mape": statistics.mean(mapes) if mapes else None,
                "median_mape": statistics.median(mapes) if mapes else None,
                "models_analyzed": len(results),
                "models_improving": sum(1 for r in results if r['trend'] == 'amélioration'),
                "models_degrading": sum(1 for r in results if r['trend'] == 'dégradation')
            }
        else:
            stats = {"message": "Aucun modèle analysé"}
            
        return {
            "comparison": results,
            "statistics": stats,
            "period": f"{days_back} derniers jours",
            "timestamp": datetime.now().isoformat()
        }
        
    def generate_performance_report(self) -> Dict[str, Any]:
        """Génère un rapport de performance global"""
        conn = self._get_connection()
        
        try:
            # Récupérer tous les articles actifs
            query = """
                SELECT DISTINCT article_id
                FROM predictions
                WHERE date_prediction >= date('now', '-30 days')
            """
            
            cursor = conn.cursor()
            cursor.execute(query)
            article_ids = [row[0] for row in cursor.fetchall()]
            
            if not article_ids:
                return {"status": "Aucune prédiction récente"}
                
            # Analyser chaque article
            performances = []
            for article_id in article_ids[:10]:  # Limiter à 10 pour performance
                perf = self.monitor_article_performance(article_id, 30)
                if 'error' not in perf:
                    performances.append(perf)
                    
            # Agréger les résultats
            if performances:
                avg_mape = statistics.mean([p['mape_global'] for p in performances])
                
                report = {
                    "summary": {
                        "total_models": len(article_ids),
                        "models_analyzed": len(performances),
                        "average_mape": round(avg_mape, 1),
                        "performance_level": self._classify_performance(avg_mape)
                    },
                    "top_performers": sorted(performances, key=lambda x: x['mape_global'])[:3],
                    "needs_improvement": sorted(performances, key=lambda x: x['mape_global'], reverse=True)[:3],
                    "global_recommendations": self._generate_global_recommendations(performances),
                    "report_date": datetime.now().isoformat()
                }
            else:
                report = {"status": "Aucune donnée de performance"}
                
            return report
            
        except Exception as e:
            logger.error(f"Erreur génération rapport: {e}")
            return {"error": str(e)}
            
    def _classify_performance(self, mape: float) -> str:
        """Classifie le niveau de performance"""
        if mape < 10:
            return "Excellent"
        elif mape < 15:
            return "Bon"
        elif mape < 25:
            return "Moyen"
        else:
            return "Faible"
            
    def _generate_global_recommendations(self, performances: List[Dict]) -> List[str]:
        """Génère des recommandations globales"""
        recommendations = []
        
        # Analyser les tendances communes
        patterns = [p.get('tendance_erreur', '') for p in performances]
        
        if patterns.count('sous_estimation_systematique') > len(patterns) / 2:
            recommendations.append("Tendance générale à la sous-estimation - Ajuster les modèles")
        elif patterns.count('sur_estimation_systematique') > len(patterns) / 2:
            recommendations.append("Tendance générale à la sur-estimation - Réduire les prédictions")
            
        # Analyser les MAPE
        mapes = [p['mape_global'] for p in performances]
        if statistics.stdev(mapes) > 10:
            recommendations.append("Grande variance entre modèles - Standardiser l'approche")
            
        # Vérifier les données récentes
        recommendations.append("Effectuer un réentraînement mensuel pour maintenir la précision")
        
        return recommendations
        
    def __del__(self):
        """Ferme la connexion à la destruction"""
        if self.conn:
            self.conn.close()


def main():
    """Fonction principale pour tests"""
    monitor = MLPerformanceMonitor()
    
    # Test monitoring d'un article
    print("=== Monitoring Article 1 ===")
    result = monitor.monitor_article_performance(article_id=1, days_back=30)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Test comparaison de modèles
    print("\n=== Comparaison Modèles ===")
    comparison = monitor.compare_models_performance(
        article_ids=[1, 2, 3, 4, 5],
        days_back=30
    )
    print(f"Meilleur modèle: Article {comparison['statistics']['best_model']['article_id']}")
    print(f"MAPE moyen: {comparison['statistics']['average_mape']}")
    
    # Test rapport global
    print("\n=== Rapport Global ===")
    report = monitor.generate_performance_report()
    if 'summary' in report:
        print(f"Performance globale: {report['summary']['performance_level']}")
        print(f"MAPE moyen: {report['summary']['average_mape']}%")


if __name__ == "__main__":
    main()