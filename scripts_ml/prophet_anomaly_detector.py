"""
Détecteur d'anomalies basé sur les écarts entre prédictions Prophet et ventes réelles
Remplace l'ancien automatic_spike_detector.py basé sur moyennes mobiles
"""

import sqlite3
import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
from prophet import Prophet
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProphetAnomalyDetector:
    def __init__(self, db_path: str = "optiflow.db", models_dir: str = "models"):
        self.db_path = db_path
        self.models_dir = Path(models_dir)
        self.anomaly_threshold = 0.5  # 50% d'écart pour détecter une anomalie
        self.models_cache = {}
        self.last_improvement_mape = None

    def detect_historical_anomalies(self,
                                   start_date: str = "2022-01-01",
                                   end_date: Optional[str] = None,
                                   product_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Détecte les anomalies en comparant prédictions Prophet vs ventes réelles

        Args:
            start_date: Date de début d'analyse
            end_date: Date de fin (par défaut: aujourd'hui - 30 jours)
            product_ids: Liste des produits à analyser (None = tous)

        Returns:
            Dict avec statistiques et anomalies détectées
        """
        if end_date is None:
            # Par défaut: aujourd'hui moins 30 jours
            end_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        logger.info(f"Détection d'anomalies Prophet: {start_date} → {end_date}")

        conn = sqlite3.connect(self.db_path)

        try:
            # Récupérer la liste des produits
            if product_ids is None:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM products")
                product_ids = [row[0] for row in cursor.fetchall()]

            total_anomalies = []
            total_predictions = 0

            for product_id in product_ids:
                logger.info(f"Analyse produit {product_id}...")

                # Charger le modèle Prophet pour ce produit
                model = self._load_prophet_model(product_id)
                if model is None:
                    logger.warning(f"Pas de modèle pour produit {product_id}")
                    continue

                # Récupérer les ventes historiques
                sales_df = self._get_historical_sales(conn, product_id, start_date, end_date)
                if sales_df.empty:
                    continue

                # Générer les prédictions rétroactives
                predictions = self._generate_retroactive_predictions(
                    model, sales_df, product_id
                )

                # Détecter les anomalies
                anomalies = self._detect_anomalies_in_predictions(
                    predictions, sales_df, product_id
                )

                total_anomalies.extend(anomalies)
                total_predictions += len(predictions)

                # Sauvegarder dans prediction_feedback
                self._save_prediction_feedback(conn, predictions, sales_df, product_id)

            # Sauvegarder les anomalies dans la DB
            if total_anomalies:
                self._save_anomalies_to_db(conn, total_anomalies)

            conn.commit()

            return {
                "success": True,
                "period": f"{start_date} → {end_date}",
                "products_analyzed": len(product_ids),
                "total_predictions": total_predictions,
                "anomalies_detected": len(total_anomalies),
                "anomaly_rate": (len(total_anomalies) / total_predictions * 100) if total_predictions > 0 else 0
            }

        except Exception as e:
            logger.error(f"Erreur détection anomalies: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    def _load_prophet_model(self, product_id: int) -> Optional[Prophet]:
        """Charge le modèle Prophet pré-entraîné pour un produit"""
        if product_id in self.models_cache:
            return self.models_cache[product_id]

        model_path = self.models_dir / f"prophet_model_{product_id}.pkl"
        if not model_path.exists():
            return None

        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            self.models_cache[product_id] = model
            return model
        except Exception as e:
            logger.error(f"Erreur chargement modèle {product_id}: {e}")
            return None

    def _get_historical_sales(self, conn: sqlite3.Connection,
                             product_id: int,
                             start_date: str,
                             end_date: str) -> pd.DataFrame:
        """Récupère les ventes historiques d'un produit"""
        query = """
        SELECT
            order_date as ds,
            SUM(quantity) as y
        FROM sales_history
        WHERE product_id = ?
            AND order_date BETWEEN ? AND ?
        GROUP BY order_date
        ORDER BY order_date
        """

        df = pd.read_sql_query(query, conn, params=(product_id, start_date, end_date))
        df['ds'] = pd.to_datetime(df['ds'])
        return df

    def _generate_retroactive_predictions(self,
                                         model: Prophet,
                                         sales_df: pd.DataFrame,
                                         product_id: int) -> pd.DataFrame:
        """Génère des prédictions rétroactives pour comparer avec les ventes réelles"""
        # Créer un dataframe pour les dates à prédire
        future = pd.DataFrame({'ds': sales_df['ds'].values})

        # Faire les prédictions
        forecast = model.predict(future)

        # Garder seulement les colonnes nécessaires
        predictions = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
        predictions['product_id'] = product_id

        return predictions

    def _detect_anomalies_in_predictions(self,
                                        predictions: pd.DataFrame,
                                        sales_df: pd.DataFrame,
                                        product_id: int) -> List[Dict]:
        """Détecte les anomalies basées sur l'écart prédiction vs réel"""
        anomalies = []

        # Fusionner prédictions et ventes réelles
        merged = pd.merge(predictions, sales_df, on='ds', how='inner')

        for _, row in merged.iterrows():
            predicted = row['yhat']
            actual = row['y']

            # Éviter division par zéro
            if predicted == 0:
                if actual > 5:  # Vente significative non prédite
                    deviation_percent = 1.0
                else:
                    continue
            else:
                deviation_percent = abs(actual - predicted) / predicted

            # Détecter anomalie si écart > seuil
            if deviation_percent > self.anomaly_threshold:
                anomaly_type = 'spike' if actual > predicted else 'drop'
                severity = self._calculate_severity(deviation_percent)

                anomalies.append({
                    'product_id': product_id,
                    'detection_date': row['ds'].strftime('%Y-%m-%d'),
                    'actual_value': float(actual),
                    'predicted_value': float(predicted),
                    'deviation_percent': float(deviation_percent * 100),
                    'anomaly_type': anomaly_type,
                    'severity': severity,
                    'status': 'pending'
                })

        return anomalies

    def _calculate_severity(self, deviation_percent: float) -> str:
        """Calcule la sévérité de l'anomalie"""
        if deviation_percent > 2.0:  # > 200%
            return 'critical'
        elif deviation_percent > 1.0:  # > 100%
            return 'high'
        elif deviation_percent > 0.75:  # > 75%
            return 'medium'
        else:
            return 'low'

    def _save_prediction_feedback(self, conn: sqlite3.Connection,
                                 predictions: pd.DataFrame,
                                 sales_df: pd.DataFrame,
                                 product_id: int):
        """Sauvegarde les comparaisons prédiction/réel dans prediction_feedback"""
        cursor = conn.cursor()

        # Fusionner prédictions et ventes
        merged = pd.merge(predictions, sales_df, on='ds', how='inner')

        for _, row in merged.iterrows():
            predicted = row['yhat']
            actual = row['y']
            date_str = row['ds'].strftime('%Y-%m-%d')

            # Calculer MAPE pour cette prédiction
            if actual != 0:
                mape = abs(actual - predicted) / actual * 100
            else:
                mape = 100 if predicted > 0 else 0

            # Chercher si une anomalie existe pour cette date et ce produit
            cursor.execute("""
                SELECT id FROM anomalies
                WHERE product_id = ? AND detection_date = ?
            """, (product_id, date_str))
            anomaly_result = cursor.fetchone()
            anomaly_id = anomaly_result[0] if anomaly_result else None

            cursor.execute("""
                INSERT OR REPLACE INTO prediction_feedback
                (date, product_id, predicted_value, actual_value, mape, anomaly_id, included_in_training)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (
                date_str,
                product_id,
                float(predicted),
                float(actual),
                float(mape),
                anomaly_id
            ))

    def _save_anomalies_to_db(self, conn: sqlite3.Connection, anomalies: List[Dict]):
        """Sauvegarde les anomalies détectées dans la DB"""
        cursor = conn.cursor()

        for anomaly in anomalies:
            # Vérifier si l'anomalie existe déjà
            cursor.execute("""
                SELECT id FROM anomalies
                WHERE product_id = ? AND detection_date = ?
            """, (anomaly['product_id'], anomaly['detection_date']))

            existing = cursor.fetchone()

            if existing:
                # Mettre à jour l'anomalie existante
                cursor.execute("""
                    UPDATE anomalies
                    SET predicted_value = ?, actual_value = ?,
                        deviation_percent = ?, anomaly_type = ?,
                        severity = ?, status = 'pending'
                    WHERE id = ?
                """, (
                    anomaly['predicted_value'],
                    anomaly['actual_value'],
                    anomaly['deviation_percent'],
                    anomaly['anomaly_type'],
                    anomaly['severity'],
                    existing[0]
                ))
            else:
                # Créer nouvelle anomalie
                cursor.execute("""
                    INSERT INTO anomalies
                    (product_id, detection_date, actual_value, predicted_value,
                     deviation_percent, anomaly_type, severity, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
                """, (
                    anomaly['product_id'],
                    anomaly['detection_date'],
                    anomaly['actual_value'],
                    anomaly['predicted_value'],
                    anomaly['deviation_percent'],
                    anomaly['anomaly_type'],
                    anomaly['severity']
                ))

    def calculate_clean_mape(self,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> Dict[str, float]:
        """
        Calcule le MAPE en excluant les anomalies marquées comme 'ignored'

        Returns:
            Dict avec MAPE propre et amélioration
        """
        conn = sqlite3.connect(self.db_path)

        try:
            # Requête pour calculer MAPE propre
            query = """
            SELECT
                AVG(pf.mape) as clean_mape,
                COUNT(*) as predictions_count,
                SUM(CASE WHEN a.status = 'ignored' THEN 1 ELSE 0 END) as ignored_count
            FROM prediction_feedback pf
            LEFT JOIN anomalies a
                ON pf.product_id = a.product_id
                AND pf.date = a.detection_date
            WHERE (a.status IS NULL OR a.status != 'ignored')
            """

            params = []
            if start_date:
                query += " AND pf.date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND pf.date <= ?"
                params.append(end_date)

            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchone()

            clean_mape = result[0] if result[0] else 0
            predictions_count = result[1] if result[1] else 0
            ignored_count = result[2] if result[2] else 0

            # Calculer l'amélioration si on a un MAPE précédent
            improvement = 0
            if self.last_improvement_mape is not None:
                improvement = self.last_improvement_mape - clean_mape

            return {
                "clean_mape": round(clean_mape, 2),
                "predictions_used": predictions_count - ignored_count,
                "anomalies_excluded": ignored_count,
                "improvement": round(improvement, 2),
                "improvement_percent": round(improvement / self.last_improvement_mape * 100, 1) if self.last_improvement_mape else 0
            }

        finally:
            conn.close()

    def track_improvement(self) -> None:
        """Enregistre le MAPE actuel pour mesurer l'amélioration future"""
        result = self.calculate_clean_mape()
        self.last_improvement_mape = result['clean_mape']
        logger.info(f"MAPE de référence enregistré: {self.last_improvement_mape}%")

    def update_anomaly_status(self, anomaly_id: int, new_status: str) -> bool:
        """
        Met à jour le statut d'une anomalie

        Args:
            anomaly_id: ID de l'anomalie
            new_status: 'validated', 'ignored', ou 'seasonal'
        """
        logger.info(f"UPDATE: Tentative de mise à jour anomalie {anomaly_id} vers {new_status}")
        logger.info(f"DB Path utilisé: {self.db_path}")

        conn = sqlite3.connect(self.db_path)

        try:
            cursor = conn.cursor()

            # Vérifier que l'anomalie existe
            cursor.execute("SELECT id, status FROM anomalies WHERE id = ?", (anomaly_id,))
            result = cursor.fetchone()
            if not result:
                logger.error(f"Anomalie {anomaly_id} introuvable dans la DB")
                return False

            logger.info(f"Anomalie trouvée: ID={result[0]}, Status actuel={result[1]}")

            # Mettre à jour le statut
            cursor.execute("""
                UPDATE anomalies
                SET status = ?
                WHERE id = ?
            """, (new_status, anomaly_id))

            rows_affected = cursor.rowcount
            logger.info(f"Lignes affectées par UPDATE: {rows_affected}")

            # Si ignoré, mettre à jour prediction_feedback
            if new_status == 'ignored':
                cursor.execute("""
                    UPDATE prediction_feedback
                    SET included_in_training = 0
                    WHERE anomaly_id = ?
                """, (anomaly_id,))
                logger.info(f"Prediction_feedback mis à jour pour anomalie {anomaly_id}")

            # Si saisonnier, logger l'action
            if new_status == 'seasonal':
                logger.info(f"Anomalie {anomaly_id} marquée comme saisonnière")

            conn.commit()
            logger.info(f"COMMIT effectué avec succès pour anomalie {anomaly_id}")

            # Recalculer l'amélioration après chaque changement
            if self.last_improvement_mape is None:
                self.track_improvement()

            return True

        except Exception as e:
            logger.error(f"ERREUR mise à jour anomalie {anomaly_id}: {e}")
            logger.error(f"Type d'erreur: {type(e).__name__}")
            conn.rollback()
            return False
        finally:
            conn.close()
            logger.info(f"Connexion DB fermée pour anomalie {anomaly_id}")

    def detect_new_anomalies_only(self,
                                  start_date: str,
                                  end_date: str,
                                  product_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Détecte UNIQUEMENT les nouvelles anomalies sans toucher aux statuts existants

        Args:
            start_date: Date de début d'analyse
            end_date: Date de fin d'analyse
            product_ids: Liste des produits à analyser (None = tous)

        Returns:
            Dict avec le nombre de nouvelles anomalies détectées
        """
        logger.info(f"Détection de NOUVELLES anomalies uniquement: {start_date} → {end_date}")

        conn = sqlite3.connect(self.db_path)

        try:
            # Récupérer la liste des produits
            if product_ids is None:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM products")
                product_ids = [row[0] for row in cursor.fetchall()]

            new_anomalies_count = 0
            total_predictions = 0

            for product_id in product_ids:
                logger.info(f"Analyse produit {product_id} (nouvelles anomalies seulement)...")

                # Charger le modèle Prophet pour ce produit
                model = self._load_prophet_model(product_id)
                if model is None:
                    logger.warning(f"Pas de modèle pour produit {product_id}")
                    continue

                # Récupérer les ventes historiques
                sales_df = self._get_historical_sales(conn, product_id, start_date, end_date)
                if sales_df.empty:
                    continue

                # Générer les prédictions rétroactives
                predictions = self._generate_retroactive_predictions(
                    model, sales_df, product_id
                )

                # Détecter les anomalies
                anomalies = self._detect_anomalies_in_predictions(
                    predictions, sales_df, product_id
                )

                # Sauvegarder SEULEMENT les nouvelles anomalies
                new_count = self._save_new_anomalies_only(conn, anomalies)
                new_anomalies_count += new_count
                total_predictions += len(predictions)

                # Toujours sauvegarder dans prediction_feedback
                self._save_prediction_feedback(conn, predictions, sales_df, product_id)

            conn.commit()

            return {
                "success": True,
                "period": f"{start_date} → {end_date}",
                "products_analyzed": len(product_ids),
                "total_predictions": total_predictions,
                "new_anomalies": new_anomalies_count,
                "message": f"{new_anomalies_count} nouvelles anomalies détectées"
            }

        except Exception as e:
            logger.error(f"Erreur détection nouvelles anomalies: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    def _save_new_anomalies_only(self, conn: sqlite3.Connection, anomalies: List[Dict]) -> int:
        """
        Sauvegarde SEULEMENT les nouvelles anomalies, sans toucher aux existantes

        Returns:
            Nombre de nouvelles anomalies ajoutées
        """
        cursor = conn.cursor()
        new_count = 0

        for anomaly in anomalies:
            # Vérifier si l'anomalie existe déjà
            cursor.execute("""
                SELECT id, status FROM anomalies
                WHERE product_id = ? AND detection_date = ?
            """, (anomaly['product_id'], anomaly['detection_date']))

            existing = cursor.fetchone()

            if existing:
                # Si elle existe ET qu'elle est déjà validée, on ne touche pas
                if existing[1] in ['seasonal', 'ignored', 'validated']:
                    logger.info(f"Anomalie existante préservée: ID={existing[0]}, status={existing[1]}")
                    continue
                # Si elle est pending, on peut mettre à jour les valeurs
                elif existing[1] == 'pending':
                    cursor.execute("""
                        UPDATE anomalies
                        SET predicted_value = ?, actual_value = ?,
                            deviation_percent = ?, anomaly_type = ?,
                            severity = ?
                        WHERE id = ?
                    """, (
                        anomaly['predicted_value'],
                        anomaly['actual_value'],
                        anomaly['deviation_percent'],
                        anomaly['anomaly_type'],
                        anomaly['severity'],
                        existing[0]
                    ))
            else:
                # Nouvelle anomalie - la créer
                cursor.execute("""
                    INSERT INTO anomalies
                    (product_id, detection_date, actual_value, predicted_value,
                     deviation_percent, anomaly_type, severity, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
                """, (
                    anomaly['product_id'],
                    anomaly['detection_date'],
                    anomaly['actual_value'],
                    anomaly['predicted_value'],
                    anomaly['deviation_percent'],
                    anomaly['anomaly_type'],
                    anomaly['severity']
                ))
                new_count += 1
                logger.info(f"Nouvelle anomalie créée: produit={anomaly['product_id']}, date={anomaly['detection_date']}")

        return new_count

    def get_pending_anomalies(self, limit: int = 50) -> List[Dict]:
        """Récupère les anomalies en attente de validation"""
        conn = sqlite3.connect(self.db_path)

        try:
            query = """
            SELECT
                a.id,
                a.detection_date,
                p.name as product_name,
                a.predicted_value,
                a.actual_value,
                a.deviation_percent,
                a.anomaly_type,
                a.severity
            FROM anomalies a
            JOIN products p ON a.product_id = p.id
            WHERE a.status = 'pending'
            ORDER BY a.deviation_percent DESC
            LIMIT ?
            """

            df = pd.read_sql_query(query, conn, params=(limit,))
            return df.to_dict('records')

        finally:
            conn.close()