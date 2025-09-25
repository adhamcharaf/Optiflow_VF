"""
Script 1: predict_daily_sales.py
Génère des prédictions de ventes journalières avec modèles Prophet pré-entraînés
"""

import json
import pickle
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd
import numpy as np
from prophet import Prophet
import sqlite3

from db_mapping import get_table_name, get_column_name, build_query

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DailySalesPredictor:
    def __init__(self, models_dir: str = "models", db_path: str = "optiflow.db"):
        self.models_dir = Path(models_dir)
        self.db_path = db_path
        self.models_cache = {}
        self.metadata_cache = {}
        self.holidays_df = None
        self._load_holidays()
        
    def _load_holidays(self):
        """Charge la configuration des événements/holidays"""
        try:
            holidays_path = self.models_dir / "prophet_holidays.csv"
            if holidays_path.exists():
                self.holidays_df = pd.read_csv(holidays_path)
                self.holidays_df['ds'] = pd.to_datetime(self.holidays_df['ds'])
                logger.info(f"Chargé {len(self.holidays_df)} événements")
            
            # Charger aussi la config JSON pour les multiplicateurs
            config_path = self.models_dir / "holidays_config.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    self.holidays_config = json.load(f)
            else:
                self.holidays_config = {}
                
        except Exception as e:
            logger.error(f"Erreur chargement holidays: {e}")
            self.holidays_df = pd.DataFrame()
            
    def _load_model(self, article_id: int) -> Optional[Prophet]:
        """Charge un modèle Prophet pré-entraîné depuis le cache ou disque"""
        if article_id in self.models_cache:
            return self.models_cache[article_id]
            
        model_path = self.models_dir / f"prophet_model_{article_id}.pkl"
        metadata_path = self.models_dir / f"model_metadata_{article_id}.json"
        
        if not model_path.exists():
            logger.warning(f"Modèle non trouvé pour article {article_id}")
            return None
            
        try:
            # Charger le modèle
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            self.models_cache[article_id] = model
            
            # Charger les métadonnées
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    self.metadata_cache[article_id] = json.load(f)
                    
            logger.info(f"Modèle chargé pour article {article_id}")
            return model
            
        except Exception as e:
            logger.error(f"Erreur chargement modèle {article_id}: {e}")
            return None
            
    def _check_cached_forecast(self, article_id: int, date_debut: str, date_fin: str) -> Optional[pd.DataFrame]:
        """Vérifie si des prédictions sont déjà en cache"""
        forecast_path = self.models_dir / f"forecast_{article_id}.csv"
        
        if not forecast_path.exists():
            return None
            
        try:
            forecast = pd.read_csv(forecast_path)
            forecast['ds'] = pd.to_datetime(forecast['ds'])
            
            # Filtrer sur la période demandée
            mask = (forecast['ds'] >= pd.to_datetime(date_debut)) & \
                   (forecast['ds'] <= pd.to_datetime(date_fin))
            
            filtered = forecast[mask]
            
            if len(filtered) > 0:
                logger.info(f"Utilisation du cache pour article {article_id}")
                return filtered
                
        except Exception as e:
            logger.warning(f"Erreur lecture cache: {e}")
            
        return None
        
    def predict(
        self, 
        article_id: int,
        date_debut: str,
        date_fin: str,
        events: Optional[List[Dict]] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Génère des prédictions journalières pour un article
        
        Args:
            article_id: ID de l'article
            date_debut: Date début format YYYY-MM-DD
            date_fin: Date fin (max 30 jours)
            events: Liste optionnelle d'événements supplémentaires
            use_cache: Utiliser les prédictions cachées si disponibles
            
        Returns:
            Dict avec prédictions et métriques
        """
        try:
            start_date = pd.to_datetime(date_debut)
            end_date = pd.to_datetime(date_fin)
            
            # Vérifier limite 30 jours
            if (end_date - start_date).days > 30:
                end_date = start_date + timedelta(days=30)
                logger.warning(f"Période limitée à 30 jours jusqu'au {end_date}")
                
            # Vérifier le cache
            if use_cache:
                cached = self._check_cached_forecast(article_id, date_debut, str(end_date.date()))
                if cached is not None:
                    return self._format_predictions(cached, article_id)
                    
            # Charger le modèle
            model = self._load_model(article_id)
            if model is None:
                return self._fallback_prediction(article_id, start_date, end_date)
                
            # Créer le dataframe pour les prédictions
            future = pd.DataFrame({
                'ds': pd.date_range(start=start_date, end=end_date, freq='D')
            })
            
            # Ajouter les événements si fournis
            if events or self.holidays_df is not None:
                future = self._add_events_to_future(future, events)
                
            # Faire les prédictions
            forecast = model.predict(future)
            
            # Appliquer les multiplicateurs d'événements
            forecast = self._apply_event_multipliers(forecast, events)
            
            # Formater et retourner
            return self._format_predictions(forecast, article_id)
            
        except Exception as e:
            logger.error(f"Erreur prédiction article {article_id}: {e}")
            return {
                "article_id": str(article_id),
                "error": str(e),
                "predictions": []
            }
            
    def _add_events_to_future(self, future: pd.DataFrame, custom_events: Optional[List[Dict]]) -> pd.DataFrame:
        """Ajoute les colonnes d'événements au dataframe future"""
        if self.holidays_df is not None and not self.holidays_df.empty:
            # Extraire les noms uniques d'événements
            event_names = self.holidays_df['holiday'].unique()
            
            for event in event_names:
                future[event] = 0
                event_dates = self.holidays_df[self.holidays_df['holiday'] == event]['ds'].values
                future.loc[future['ds'].isin(event_dates), event] = 1
                
        # Ajouter événements custom si fournis
        if custom_events:
            for event in custom_events:
                event_name = event.get('name', 'custom_event')
                event_date = pd.to_datetime(event.get('date'))
                
                if event_name not in future.columns:
                    future[event_name] = 0
                    
                if event_date in future['ds'].values:
                    future.loc[future['ds'] == event_date, event_name] = 1
                    
        return future
        
    def _apply_event_multipliers(self, forecast: pd.DataFrame, events: Optional[List[Dict]]) -> pd.DataFrame:
        """Applique les multiplicateurs d'événements aux prédictions"""
        if not events and not self.holidays_config:
            return forecast
            
        forecast = forecast.copy()
        
        # Appliquer multiplicateurs depuis config
        if self.holidays_config:
            for _, row in forecast.iterrows():
                multiplier = 1.0
                
                # Vérifier chaque événement dans la config
                for event_name, config in self.holidays_config.items():
                    if event_name in forecast.columns and row.get(event_name, 0) == 1:
                        event_mult = config.get('impact_multiplier', 1.0)
                        multiplier *= event_mult
                        
                # Appliquer le multiplicateur
                if multiplier != 1.0:
                    idx = row.name
                    forecast.loc[idx, 'yhat'] *= multiplier
                    forecast.loc[idx, 'yhat_lower'] *= multiplier
                    forecast.loc[idx, 'yhat_upper'] *= multiplier
                    
        # Appliquer multiplicateurs custom
        if events:
            for event in events:
                event_date = pd.to_datetime(event.get('date'))
                multiplier = event.get('multiplier', 1.0)
                
                mask = forecast['ds'] == event_date
                if mask.any():
                    forecast.loc[mask, 'yhat'] *= multiplier
                    forecast.loc[mask, 'yhat_lower'] *= multiplier
                    forecast.loc[mask, 'yhat_upper'] *= multiplier
                    
        return forecast
        
    def _format_predictions(self, forecast: pd.DataFrame, article_id: int) -> Dict[str, Any]:
        """Formate les prédictions selon le format de sortie spécifié"""
        predictions = []
        
        for _, row in forecast.iterrows():
            # S'assurer que les valeurs sont positives
            quantity = max(0, round(row['yhat']))
            
            # Calculer l'intervalle de confiance
            lower = max(0, round(row.get('yhat_lower', quantity * 0.8)))
            upper = max(0, round(row.get('yhat_upper', quantity * 1.2)))
            
            # Calculer le score de confiance (basé sur l'écart de l'intervalle)
            if upper > lower and upper > 0:
                confidence = 1 - (upper - lower) / (upper + lower)
            else:
                confidence = 0.85  # Valeur par défaut
                
            predictions.append({
                "date": row['ds'].strftime('%Y-%m-%d'),
                "quantity": int(quantity),
                "confidence": round(confidence, 2),
                "lower_bound": int(lower),
                "upper_bound": int(upper)
            })
            
        # Récupérer le MAPE depuis les métadonnées
        mape = 12.62  # Valeur par défaut
        if article_id in self.metadata_cache:
            mape = self.metadata_cache[article_id].get('mape', mape)
            
        return {
            "article_id": str(article_id),
            "predictions": predictions,
            "mape": round(mape, 1),
            "model_last_trained": self.metadata_cache.get(article_id, {}).get('training_date', 'Unknown'),
            "seasonality_detected": self._get_seasonality_info(article_id)
        }
        
    def _get_seasonality_info(self, article_id: int) -> Dict[str, Any]:
        """Récupère les infos de saisonnalité depuis les métadonnées"""
        if article_id not in self.metadata_cache:
            return {"weekly": True, "monthly": False, "yearly": False}
            
        metadata = self.metadata_cache[article_id]
        return {
            "weekly": metadata.get('weekly_seasonality', True),
            "monthly": metadata.get('monthly_seasonality', False),
            "yearly": metadata.get('yearly_seasonality', False),
            "peak_day": metadata.get('peak_day', 'Samedi')
        }
        
    def _fallback_prediction(self, article_id: int, start_date: pd.Timestamp, end_date: pd.Timestamp) -> Dict[str, Any]:
        """Prédiction de secours basée sur moyennes historiques"""
        logger.warning(f"Utilisation du fallback pour article {article_id}")
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Récupérer les ventes moyennes des 30 derniers jours avec vrais noms
            query = f"""
                SELECT AVG(quantity) as avg_sales
                FROM sales_history
                WHERE product_id = ?
                AND order_date >= date('now', '-30 days')
            """
            
            result = pd.read_sql_query(query, conn, params=[article_id])
            avg_sales = result['avg_sales'].iloc[0] if not result.empty and result['avg_sales'].iloc[0] is not None else 10
            
            conn.close()
            
            # Générer prédictions constantes
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            predictions = []
            
            for date in dates:
                # Ajouter variation pour le samedi (pic observé)
                multiplier = 1.3 if date.weekday() == 5 else 1.0
                quantity = int(avg_sales * multiplier)
                
                predictions.append({
                    "date": date.strftime('%Y-%m-%d'),
                    "quantity": quantity,
                    "confidence": 0.65,
                    "lower_bound": int(quantity * 0.8),
                    "upper_bound": int(quantity * 1.2)
                })
                
            return {
                "article_id": str(article_id),
                "predictions": predictions,
                "mape": 25.0,  # MAPE élevé pour fallback
                "model_last_trained": "Fallback",
                "fallback_mode": True
            }
            
        except Exception as e:
            logger.error(f"Erreur fallback: {e}")
            return {
                "article_id": str(article_id),
                "predictions": [],
                "error": "Aucun modèle disponible",
                "fallback_mode": True
            }
            
    def predict_batch(self, articles: List[int], date_debut: str, date_fin: str) -> List[Dict]:
        """Génère des prédictions pour plusieurs articles"""
        results = []
        
        for article_id in articles:
            logger.info(f"Prédiction pour article {article_id}")
            result = self.predict(article_id, date_debut, date_fin)
            results.append(result)
            
        return results


def main():
    """Fonction principale pour tests"""
    predictor = DailySalesPredictor()
    
    # Test sur article 1
    result = predictor.predict(
        article_id=1,
        date_debut="2025-09-10",
        date_fin="2025-09-20",
        events=[
            {"name": "Black Friday", "date": "2025-09-15", "multiplier": 2.0}
        ]
    )
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Test batch
    batch_results = predictor.predict_batch(
        articles=[1, 2, 3],
        date_debut="2025-09-10",
        date_fin="2025-09-15"
    )
    
    print(f"\nPrédictions pour {len(batch_results)} articles générées")


if __name__ == "__main__":
    main()