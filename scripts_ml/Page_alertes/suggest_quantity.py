"""
Script 3: suggest_quantity.py
Calcule la quantité optimale à commander selon la formule exacte du document
Formule: (Σ prédictions jusqu'à date_cible - stock_actuel) × (1 + marge_sécurité)
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import pandas as pd
import sqlite3

from db_mapping import get_table_name, get_column_name, build_query

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuantitySuggester:
    def __init__(self, db_path: str = "optiflow.db"):
        self.db_path = db_path
        self.conn = None
        
    def _get_connection(self):
        """Obtient une connexion à la base de données"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
        return self.conn
        
    def _get_stock_actuel(self, article_id: int) -> int:
        """Récupère le stock actuel d'un article"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT quantity_on_hand 
            FROM stock_levels 
            WHERE product_id = ?
            ORDER BY recorded_at DESC
            LIMIT 1
        """, (article_id,))
        
        result = cursor.fetchone()
        return result[0] if result else 0
        
    def _get_article_info(self, article_id: int) -> Dict[str, Any]:
        """Récupère les informations détaillées de l'article"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                p.id,
                p.name,
                p.unit_price,
                p.lead_time_days
            FROM products p
            WHERE p.id = ?
        """, (article_id,))
        
        result = cursor.fetchone()
        if not result:
            raise ValueError(f"Article {article_id} non trouvé")
            
        return {
            "id": result[0],
            "nom": result[1],
            "prix_unitaire": result[2] or 1000,
            "delai_reapprovisionnement": result[3] or 5
        }
        
    def calculate_quantity(
        self,
        article_id: int,
        predictions: List[Dict[str, Any]],
        date_cible: Optional[str] = None,
        marge_securite: float = 15.0,
        stock_actuel_override: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calcule la quantité suggérée selon la formule du document
        
        Args:
            article_id: ID de l'article
            predictions: Liste des prédictions journalières
            date_cible: Date jusqu'à laquelle couvrir (défaut: 30 jours)
            marge_securite: Pourcentage de marge (0-50%, défaut: 15%)
            stock_actuel_override: Stock actuel si différent de la DB
            
        Returns:
            Dict avec quantité suggérée et détails du calcul
        """
        try:
            # Validation de la marge de sécurité
            if not 0 <= marge_securite <= 50:
                logger.warning(f"Marge {marge_securite}% hors limites, ajustée à 15%")
                marge_securite = 15.0
                
            # Récupérer le stock actuel
            stock_actuel = stock_actuel_override or self._get_stock_actuel(article_id)
            
            # Récupérer les infos de l'article
            article_info = self._get_article_info(article_id)
            
            # Déterminer la date cible
            if date_cible:
                date_cible_dt = pd.to_datetime(date_cible)
                date_debut = pd.to_datetime(datetime.now().date())
                jours_couverture = (date_cible_dt - date_debut).days
                
                # Limiter à 90 jours maximum
                if jours_couverture > 90:
                    jours_couverture = 90
                    date_cible_dt = date_debut + timedelta(days=90)
                    logger.warning("Date cible limitée à 90 jours")
                elif jours_couverture < 1:
                    jours_couverture = 30
                    date_cible_dt = date_debut + timedelta(days=30)
                    logger.warning("Date cible invalide, défaut à 30 jours")
            else:
                # Par défaut: 30 jours
                jours_couverture = 30
                date_cible_dt = datetime.now() + timedelta(days=30)
                
            # Calculer les prédictions cumulées jusqu'à la date cible
            predictions_cumulees = self._sum_predictions_until_date(
                predictions, 
                jours_couverture
            )
            
            # Appliquer la formule exacte du document
            besoin_net = predictions_cumulees - stock_actuel
            
            # S'assurer que le besoin net n'est pas négatif
            if besoin_net < 0:
                besoin_net = 0
                logger.info(f"Stock suffisant pour article {article_id}, besoin net = 0")
                
            # Calculer la marge de sécurité
            marge_articles = besoin_net * (marge_securite / 100)
            
            # Quantité finale
            quantite_suggeree = besoin_net + marge_articles
            
            # Arrondir à l'entier supérieur
            quantite_finale = int(round(quantite_suggeree))
            
            # Application STRICTE de la formule selon specs (pas de limitation stock_max)
            quantite_ajustee = quantite_finale
            
            # Pas de limitation stock_max selon les specs
            # On garde la formule exacte selon les spécifications
                
            # Calculer le coût estimé
            cout_total = quantite_ajustee * article_info['prix_unitaire']
            
            return {
                "quantite_suggeree": quantite_ajustee,
                "details": {
                    "predictions_cumulees": predictions_cumulees,
                    "stock_actuel": stock_actuel,
                    "besoin_net": besoin_net,
                    "marge_appliquee": round(marge_articles),
                    "marge_pourcentage": marge_securite,
                    "couverture_jusqu_au": date_cible_dt.strftime('%Y-%m-%d'),
                    "jours_couverture": jours_couverture
                },
                "calcul_detaille": {
                    "formule": f"({predictions_cumulees} - {stock_actuel}) × (1 + {marge_securite}%)",
                    "etape1": f"Prédictions sur {jours_couverture}j = {predictions_cumulees} articles",
                    "etape2": f"Stock actuel = -{stock_actuel} articles",
                    "etape3": f"Besoin net = {besoin_net} articles",
                    "etape4": f"Marge {marge_securite}% = +{round(marge_articles)} articles",
                    "resultat": f"Quantité finale = {quantite_ajustee} articles"
                },
                "article_info": {
                    "id": article_id,
                    "nom": article_info['nom'],
                    "stock_apres_commande": stock_actuel + quantite_ajustee
                },
                "cout_estime": {
                    "prix_unitaire": article_info['prix_unitaire'],
                    "cout_total": cout_total,
                    "devise": "FCFA"
                },
                "recommandations": self._generate_recommandations(
                    besoin_net,
                    stock_actuel,
                    article_info,
                    marge_securite
                )
            }
            
        except Exception as e:
            logger.error(f"Erreur calcul quantité article {article_id}: {e}")
            return {
                "quantite_suggeree": 0,
                "error": str(e),
                "article_id": article_id
            }
            
    def _sum_predictions_until_date(
        self, 
        predictions: List[Dict[str, Any]], 
        jours: int
    ) -> int:
        """Somme les prédictions jusqu'au nombre de jours spécifié"""
        total = 0
        for i, pred in enumerate(predictions):
            if i >= jours:
                break
            total += pred.get('quantity', 0)
        return total
        
    def _generate_recommandations(
        self,
        besoin_net: int,
        stock_actuel: int,
        article_info: Dict,
        marge_securite: float
    ) -> List[str]:
        """Génère des recommandations contextuelles"""
        recommandations = []
        
        # Analyse du stock actuel
        taux_stock = 50.0  # Valeur par défaut sans stock_max
        
        if taux_stock < 20:
            recommandations.append(" Stock critique - Commander rapidement")
        elif taux_stock > 80:
            recommandations.append("✓ Stock élevé - Commande non urgente")
            
        # Analyse de la marge
        if marge_securite < 10:
            recommandations.append(" Marge faible - Augmenter pour plus de sécurité")
        elif marge_securite > 30:
            recommandations.append("💰 Marge élevée - Possible surstockage")
            
        # Analyse du besoin
        if besoin_net == 0:
            recommandations.append("✓ Stock suffisant pour la période")
        elif besoin_net > 500:  # Seuil fixe sans stock_max
            recommandations.append(" Forte demande prévue - Surveiller attentivement")
            
        return recommandations
        
    def calculate_batch_quantities(
        self,
        articles: List[Dict[str, Any]],
        date_cible: Optional[str] = None,
        marge_securite: float = 15.0
    ) -> Dict[str, Any]:
        """
        Calcule les quantités suggérées pour plusieurs articles
        
        Args:
            articles: Liste de dicts avec 'article_id' et 'predictions'
            date_cible: Date cible commune (optionnel)
            marge_securite: Marge commune (optionnel)
        """
        results = []
        total_cout = 0
        total_articles = 0
        
        for item in articles:
            article_id = item['article_id']
            predictions = item['predictions']
            
            # Permettre des paramètres individuels
            date_cible_article = item.get('date_cible', date_cible)
            marge_article = item.get('marge_securite', marge_securite)
            
            logger.info(f"Calcul quantité pour article {article_id}")
            
            result = self.calculate_quantity(
                article_id=article_id,
                predictions=predictions,
                date_cible=date_cible_article,
                marge_securite=marge_article
            )
            
            results.append(result)
            
            if 'error' not in result:
                total_cout += result['cout_estime']['cout_total']
                total_articles += result['quantite_suggeree']
                
        return {
            "suggestions": results,
            "summary": {
                "nombre_articles": len(results),
                "quantite_totale": total_articles,
                "cout_total_estime": total_cout,
                "date_calcul": datetime.now().isoformat(),
                "parametres": {
                    "date_cible_defaut": date_cible or "30 jours",
                    "marge_securite_defaut": marge_securite
                }
            }
        }
        
    def optimize_quantity_for_budget(
        self,
        article_id: int,
        predictions: List[Dict[str, Any]],
        budget_max: float,
        marge_securite: float = 15.0
    ) -> Dict[str, Any]:
        """
        Optimise la quantité en fonction d'un budget maximum
        """
        article_info = self._get_article_info(article_id)
        prix_unitaire = article_info['prix_unitaire']
        
        # Quantité max selon budget
        quantite_max_budget = int(budget_max / prix_unitaire)
        
        # Calcul normal
        result_normal = self.calculate_quantity(
            article_id=article_id,
            predictions=predictions,
            marge_securite=marge_securite
        )
        
        quantite_ideale = result_normal['quantite_suggeree']
        
        if quantite_ideale <= quantite_max_budget:
            result_normal['budget_status'] = "OK - Budget suffisant"
            return result_normal
        else:
            # Ajuster la quantité au budget
            stock_actuel = self._get_stock_actuel(article_id)
            
            # Calculer la couverture avec la quantité limitée
            jours_couverts = 0
            cumul = 0
            for i, pred in enumerate(predictions):
                cumul += pred.get('quantity', 0)
                if cumul > stock_actuel + quantite_max_budget:
                    jours_couverts = i
                    break
                    
            return {
                "quantite_suggeree": quantite_max_budget,
                "quantite_ideale": quantite_ideale,
                "budget_status": "Limité par le budget",
                "details": {
                    "budget_max": budget_max,
                    "cout_ajuste": quantite_max_budget * prix_unitaire,
                    "jours_couverts": jours_couverts,
                    "deficit": quantite_ideale - quantite_max_budget
                },
                "article_info": {
                    "id": article_id,
                    "nom": article_info['nom'],
                    "prix_unitaire": prix_unitaire
                },
                "recommandations": [
                    f" Budget insuffisant - Manque {quantite_ideale - quantite_max_budget} articles",
                    f" Couverture limitée à {jours_couverts} jours",
                    " Envisager une commande complémentaire prochainement"
                ]
            }
            
    def __del__(self):
        """Ferme la connexion à la destruction"""
        if self.conn:
            self.conn.close()


def main():
    """Fonction principale pour tests"""
    suggester = QuantitySuggester()
    
    # Prédictions de test
    test_predictions = [
        {"date": "2025-09-10", "quantity": 20},
        {"date": "2025-09-11", "quantity": 18},
        {"date": "2025-09-12", "quantity": 25},
        {"date": "2025-09-13", "quantity": 22},
        {"date": "2025-09-14", "quantity": 30},
        {"date": "2025-09-15", "quantity": 35},
        {"date": "2025-09-16", "quantity": 20},
    ] + [{"date": f"2025-09-{17+i}", "quantity": 20} for i in range(23)]
    
    # Test calcul simple
    print("=== Test calcul quantité standard ===")
    result = suggester.calculate_quantity(
        article_id=1,
        predictions=test_predictions,
        date_cible="2025-09-30",
        marge_securite=15.0
    )
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Test avec budget limité
    print("\n=== Test avec budget limité ===")
    result_budget = suggester.optimize_quantity_for_budget(
        article_id=1,
        predictions=test_predictions,
        budget_max=100000,
        marge_securite=15.0
    )
    
    print(json.dumps(result_budget, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()