"""
Script 2: calculate_alerts.py
Détermine le statut d'alerte pour chaque article et calcule les impacts financiers
Logique exacte selon doc/Page1_Optiflow.md
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

import pandas as pd
import numpy as np
import sqlite3

from db_mapping import get_table_name, get_column_name, build_query

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AlertStatus(Enum):
    CRITIQUE = "CRITIQUE"
    ATTENTION = "ATTENTION"
    OK = "OK"

class AlertCalculator:
    def __init__(self, db_path: str = "optiflow.db"):
        self.db_path = db_path
        self.conn = None
        
    def _get_connection(self):
        """Obtient une connexion à la base de données"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
        return self.conn
        
    def _get_article_info(self, article_id: int) -> Dict[str, Any]:
        """Récupère les informations de l'article depuis la DB"""
        conn = self._get_connection()
        
        # Requête avec vrais noms de tables et colonnes
        query = """
            SELECT 
                p.id,
                p.name,
                p.unit_price,
                p.lead_time_days,
                s.quantity_on_hand as stock_actuel
            FROM products p
            LEFT JOIN (
                SELECT product_id, quantity_on_hand 
                FROM stock_levels 
                WHERE (product_id, recorded_at) IN (
                    SELECT product_id, MAX(recorded_at) 
                    FROM stock_levels 
                    GROUP BY product_id
                )
            ) s ON p.id = s.product_id
            WHERE p.id = ?
        """
        
        cursor = conn.cursor()
        cursor.execute(query, (article_id,))
        row = cursor.fetchone()
        
        if not row:
            raise ValueError(f"Article {article_id} non trouvé")
            
        return {
            "id": row[0],
            "nom": row[1],
            "prix_unitaire": row[2] or 1000,
            "delai_reapprovisionnement": row[3] or 5,
            "stock_actuel": row[4] or 0,
            "stock_min": 10,  # Valeur par défaut
            "stock_max": 100  # Valeur par défaut
        }
        
    def calculate_alert(
        self,
        article_id: int,
        predictions: List[Dict[str, Any]],
        custom_delai: Optional[int] = None,
        custom_prix: Optional[float] = None,
        date_cible: Optional[str] = None,
        marge_securite: float = 15.0
    ) -> Dict[str, Any]:
        """
        Calcule le statut d'alerte selon les règles exactes du document
        
        CRITIQUE: stock_actuel - ventes_prevues_delai < 0
        ATTENTION: stock_actuel - ventes_prevues_delai >= 0 ET < 3j_ventes
        OK: stock suffisant pour plus de 3 jours après le délai
        """
        try:
            # Récupérer les infos de l'article
            article_info = self._get_article_info(article_id)
            
            stock_actuel = article_info['stock_actuel']
            delai_reappro = custom_delai or article_info['delai_reapprovisionnement']
            prix_unitaire = custom_prix or article_info['prix_unitaire']
            
            # Calculer les ventes prévues pendant le délai
            ventes_delai = self._sum_predictions(predictions, 0, delai_reappro)
            
            # Calculer les ventes des 3 jours suivants
            ventes_3j_apres = self._sum_predictions(predictions, delai_reappro, delai_reappro + 3)
            
            # Déterminer le statut selon les règles exactes
            stock_apres_delai = stock_actuel - ventes_delai
            
            if stock_apres_delai < 0:
                # CRITIQUE : Rupture inévitable
                status = AlertStatus.CRITIQUE
                result = self._calculate_critique(
                    stock_actuel, predictions, delai_reappro, prix_unitaire
                )
                
            elif stock_apres_delai >= 0 and stock_apres_delai < ventes_3j_apres:
                # ATTENTION : Rupture évitable si commande avant 3j
                status = AlertStatus.ATTENTION
                result = self._calculate_attention(
                    stock_actuel, predictions, delai_reappro, prix_unitaire
                )
                
            else:
                # OK : Stock suffisant
                status = AlertStatus.OK
                result = self._calculate_ok(
                    stock_actuel, predictions, delai_reappro
                )
                
            # Calculer la quantité suggérée (30 jours par défaut)
            if not date_cible:
                # Par défaut, suggérer pour 30 jours
                date_cible_calc = self._get_date_plus_days(30)
            else:
                date_cible_calc = date_cible
                
            # Calculer les ventes prévues jusqu'à la date cible
            jours_a_couvrir = min(30, len(predictions))
            ventes_totales = self._sum_predictions(predictions, 0, jours_a_couvrir)
            besoin_net = max(0, ventes_totales - stock_actuel)
            quantite_suggeree = int(besoin_net * (1 + marge_securite / 100))
            
            # Ajouter les informations communes
            result.update({
                "article_id": article_id,
                "article_nom": article_info['nom'],
                "status": status.value,
                "stock_actuel": stock_actuel,
                "delai_reapprovisionnement": delai_reappro,
                "ventes_prevues_delai": ventes_delai,
                "stock_apres_delai": stock_apres_delai,
                "prix_unitaire": prix_unitaire,
                # Extraction des champs pour l'interface
                "perte_estimee": result.get('financial_impact', {}).get('amount', 0) if status == AlertStatus.CRITIQUE else 0,
                "benefice_si_commande": result.get('financial_impact', {}).get('amount', 0) if status == AlertStatus.ATTENTION else 0,
                "date_limite_commande": result.get('dates', {}).get('commande_limite') if status == AlertStatus.ATTENTION else None,
                "date_rupture_prevue": result.get('dates', {}).get('rupture_prevue') if status == AlertStatus.CRITIQUE else None,
                "date_commande_min": result.get('dates', {}).get('commande_minimum') if status == AlertStatus.OK else None,
                "date_commande_max": result.get('dates', {}).get('commande_maximum') if status == AlertStatus.OK else None,
                # Quantité suggérée
                "quantite_suggeree": quantite_suggeree,
                "quantite_details": {
                    "predictions_cumulees": ventes_totales,
                    "stock_actuel": stock_actuel,
                    "besoin_net": besoin_net,
                    "marge_appliquee": int(besoin_net * marge_securite / 100),
                    "couverture_jusqu_au": date_cible_calc
                }
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur calcul alerte article {article_id}: {e}")
            return {
                "article_id": article_id,
                "status": "ERROR",
                "error": str(e)
            }
            
    def _sum_predictions(self, predictions: List[Dict], start_day: int, end_day: int) -> int:
        """Somme les prédictions entre deux jours"""
        total = 0
        for i, pred in enumerate(predictions):
            if start_day <= i < end_day:
                total += pred.get('quantity', 0)
        return total
        
    def _calculate_critique(
        self, 
        stock_actuel: int,
        predictions: List[Dict],
        delai_reappro: int,
        prix_unitaire: float
    ) -> Dict[str, Any]:
        """
        Calcule les détails pour un statut CRITIQUE
        Formule perte: jours_rupture × ventes_predites × prix
        """
        # Identifier le jour de rupture
        stock_restant = stock_actuel
        jour_rupture = None
        
        for i, pred in enumerate(predictions[:delai_reappro]):
            stock_restant -= pred.get('quantity', 0)
            if stock_restant < 0 and jour_rupture is None:
                jour_rupture = i + 1
                break
                
        if jour_rupture is None:
            jour_rupture = delai_reappro
            
        # Calculer les jours de rupture
        jours_rupture = delai_reappro - jour_rupture + 1
        
        # Calculer les ventes perdues
        ventes_perdues = self._sum_predictions(
            predictions, 
            jour_rupture - 1, 
            delai_reappro
        )
        
        # Calculer la perte financière
        perte_financiere = ventes_perdues * prix_unitaire
        
        return {
            "action": "Commander immédiatement pour limiter les pertes",
            "financial_impact": {
                "type": "perte_si_pas_commande",
                "amount": round(perte_financiere),
                "details": f"{jours_rupture} jours × {ventes_perdues} articles × {prix_unitaire} FCFA",
                "ventes_perdues": ventes_perdues,
                "jours_rupture": jours_rupture
            },
            "dates": {
                "rupture_prevue": self._get_date_plus_days(jour_rupture),
                "commande_recommandee": "Immédiatement"
            },
            "urgence_level": "MAXIMALE"
        }
        
    def _calculate_attention(
        self,
        stock_actuel: int,
        predictions: List[Dict],
        delai_reappro: int,
        prix_unitaire: float
    ) -> Dict[str, Any]:
        """
        Calcule les détails pour un statut ATTENTION
        Bénéfice = delai × ventes_par_jour × prix
        """
        # Trouver la date limite de commande
        # C'est quand stock_actuel - ventes = 1 jour de ventes
        stock_restant = stock_actuel
        jour_limite = None
        
        for i in range(len(predictions)):
            ventes_jusqu_ici = self._sum_predictions(predictions, 0, i + delai_reappro)
            if stock_actuel - ventes_jusqu_ici <= predictions[i].get('quantity', 0):
                jour_limite = i
                break
                
        if jour_limite is None:
            jour_limite = 3  # Par défaut 3 jours
            
        # Calculer le bénéfice si commande avant la date limite
        ventes_moyennes = self._sum_predictions(predictions, 0, delai_reappro) / delai_reappro
        benefice = delai_reappro * ventes_moyennes * prix_unitaire
        
        return {
            "action": f"Commander avant le {self._get_date_plus_days(jour_limite)}",
            "financial_impact": {
                "type": "benefice_si_commande",
                "amount": round(benefice),
                "details": f"{delai_reappro} jours × {round(ventes_moyennes)} articles/jour × {prix_unitaire} FCFA",
                "ventes_sauvees": round(delai_reappro * ventes_moyennes)
            },
            "dates": {
                "rupture_si_pas_commande": self._get_date_plus_days(jour_limite + delai_reappro),
                "commande_limite": self._get_date_plus_days(jour_limite)
            },
            "jours_restants": jour_limite,
            "urgence_level": "HAUTE"
        }
        
    def _calculate_ok(
        self,
        stock_actuel: int,
        predictions: List[Dict],
        delai_reappro: int
    ) -> Dict[str, Any]:
        """
        Calcule les détails pour un statut OK
        DATE1 = quand stock couvre délai + 3 jours
        DATE2 = quand stock couvre délai + 1 jour
        """
        # Calculer DATE1 (peut attendre minimum)
        stock_temp = stock_actuel
        date1 = None
        
        for i in range(len(predictions)):
            ventes_total = self._sum_predictions(predictions, 0, i + delai_reappro + 3)
            if stock_actuel <= ventes_total:
                date1 = max(0, i - 1)
                break
                
        if date1 is None:
            date1 = 7  # Par défaut une semaine
            
        # Calculer DATE2 (doit commander maximum)
        date2 = None
        for i in range(len(predictions)):
            ventes_total = self._sum_predictions(predictions, 0, i + delai_reappro + 1)
            if stock_actuel <= ventes_total:
                date2 = max(0, i)
                break
                
        if date2 is None:
            date2 = min(14, date1 + 7)  # Par défaut date1 + 7 jours
            
        # Calculer le nombre de jours de stock restant
        jours_stock = 0
        stock_temp = stock_actuel
        
        for i, pred in enumerate(predictions):
            stock_temp -= pred.get('quantity', 0)
            if stock_temp < 0:
                jours_stock = i
                break
            jours_stock = i + 1
            
        return {
            "action": f"Prochaine commande entre le {self._get_date_plus_days(date1)} et le {self._get_date_plus_days(date2)}",
            "financial_impact": {
                "type": "aucun_risque",
                "amount": 0,
                "details": "Stock suffisant, pas de risque de rupture"
            },
            "dates": {
                "commande_minimum": self._get_date_plus_days(date1),
                "commande_maximum": self._get_date_plus_days(date2)
            },
            "jours_stock_restant": jours_stock,
            "urgence_level": "FAIBLE"
        }
        
    def _get_date_plus_days(self, days: int) -> str:
        """Retourne la date actuelle + n jours au format YYYY-MM-DD"""
        future_date = datetime.now() + timedelta(days=days)
        return future_date.strftime('%Y-%m-%d')
        
    def calculate_batch_alerts(
        self,
        articles_predictions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Calcule les alertes pour plusieurs articles
        
        Args:
            articles_predictions: Liste de dicts avec 'article_id' et 'predictions'
        """
        results = []
        
        stats = {
            AlertStatus.CRITIQUE: 0,
            AlertStatus.ATTENTION: 0,
            AlertStatus.OK: 0
        }
        
        for item in articles_predictions:
            article_id = item['article_id']
            predictions = item['predictions']
            
            logger.info(f"Calcul alerte pour article {article_id}")
            
            result = self.calculate_alert(article_id, predictions)
            results.append(result)
            
            # Mise à jour des stats
            if result['status'] in [s.value for s in AlertStatus]:
                stats[AlertStatus(result['status'])] += 1
                
        # Ajouter un résumé
        summary = {
            "total_articles": len(results),
            "critiques": stats[AlertStatus.CRITIQUE],
            "attention": stats[AlertStatus.ATTENTION],
            "ok": stats[AlertStatus.OK],
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Résumé alertes: {summary}")
        
        return {
            "alerts": results,
            "summary": summary
        }
        
    def save_alerts_to_db(self, alerts: List[Dict[str, Any]]):
        """Sauvegarde les alertes dans la base de données"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Créer la table si elle n'existe pas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alertes_calculees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER,
                status TEXT,
                action TEXT,
                impact_financier REAL,
                date_calcul TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details JSON,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            )
        """)
        
        # Insérer les nouvelles alertes
        for alert in alerts:
            if alert.get('status') != 'ERROR':
                cursor.execute("""
                    INSERT INTO alertes_calculees 
                    (article_id, status, action, impact_financier, details)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    alert['article_id'],
                    alert['status'],
                    alert.get('action', ''),
                    alert.get('financial_impact', {}).get('amount', 0),
                    json.dumps(alert)
                ))
                
        conn.commit()
        logger.info(f"Sauvegardé {len(alerts)} alertes dans la DB")
        
    def __del__(self):
        """Ferme la connexion à la destruction"""
        if self.conn:
            self.conn.close()


def main():
    """Fonction principale pour tests"""
    calculator = AlertCalculator()
    
    # Prédictions de test (simulées)
    test_predictions = [
        {"date": "2025-09-10", "quantity": 15},
        {"date": "2025-09-11", "quantity": 18},
        {"date": "2025-09-12", "quantity": 25},
        {"date": "2025-09-13", "quantity": 20},
        {"date": "2025-09-14", "quantity": 22},
        {"date": "2025-09-15", "quantity": 30},
        {"date": "2025-09-16", "quantity": 18},
        {"date": "2025-09-17", "quantity": 16},
        {"date": "2025-09-18", "quantity": 19},
        {"date": "2025-09-19", "quantity": 21},
    ]
    
    # Test sur un article
    result = calculator.calculate_alert(
        article_id=1,
        predictions=test_predictions
    )
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Test batch
    articles_data = [
        {"article_id": 1, "predictions": test_predictions},
        {"article_id": 2, "predictions": test_predictions},
        {"article_id": 3, "predictions": test_predictions}
    ]
    
    batch_results = calculator.calculate_batch_alerts(articles_data)
    print(f"\nRésumé batch: {batch_results['summary']}")


if __name__ == "__main__":
    main()