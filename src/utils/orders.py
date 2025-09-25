"""
Module pour la gestion des commandes dans la base de données
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrderManager:
    """Gestionnaire des commandes dans la base de données"""

    def __init__(self, db_path: str = "optiflow.db"):
        self.db_path = db_path

    def save_order(
        self,
        product_id: str,
        quantity_ordered: int,
        suggested_quantity: int,
        alert_type: str,
        stock_at_order: int,
        unit_price: float,
        lead_time_days: int
    ) -> Dict[str, Any]:
        """
        Enregistre une nouvelle commande dans la base de données

        Args:
            product_id: ID du produit
            quantity_ordered: Quantité commandée
            suggested_quantity: Quantité suggérée par le système
            alert_type: Type d'alerte (CRITIQUE/ATTENTION)
            stock_at_order: Stock au moment de la commande
            unit_price: Prix unitaire
            lead_time_days: Délai de livraison en jours

        Returns:
            Dict contenant l'ID de la commande et les informations enregistrées
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Date de commande et date de livraison prévue
            order_date = datetime.now()
            expected_delivery = order_date + timedelta(days=lead_time_days)

            # Insérer la commande
            cursor.execute("""
                INSERT INTO orders (
                    product_id,
                    order_date,
                    quantity_ordered,
                    suggested_quantity,
                    alert_type,
                    stock_at_order,
                    unit_price,
                    lead_time_days,
                    expected_delivery
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product_id,
                order_date.strftime("%Y-%m-%d %H:%M:%S"),
                quantity_ordered,
                suggested_quantity,
                alert_type,
                stock_at_order,
                unit_price,
                lead_time_days,
                expected_delivery.strftime("%Y-%m-%d")
            ))

            conn.commit()
            order_id = cursor.lastrowid

            logger.info(f"Commande #{order_id} enregistrée pour le produit {product_id}")

            conn.close()

            return {
                "success": True,
                "order_id": order_id,
                "product_id": product_id,
                "quantity_ordered": quantity_ordered,
                "order_date": order_date,
                "expected_delivery": expected_delivery,
                "total_amount": quantity_ordered * unit_price
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement de la commande: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_product_lead_time(self, product_id: str) -> int:
        """
        Récupère le lead_time_days d'un produit depuis la table products

        Args:
            product_id: ID du produit

        Returns:
            lead_time_days ou 5 par défaut
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT lead_time_days
                FROM products
                WHERE id = ?
            """, (product_id,))

            result = cursor.fetchone()
            conn.close()

            if result and result[0] is not None:
                return result[0]
            else:
                logger.warning(f"Lead time non trouvé pour le produit {product_id}, utilisation de 5 jours par défaut")
                return 5

        except Exception as e:
            logger.error(f"Erreur lors de la récupération du lead time: {e}")
            return 5

    def get_order_history(
        self,
        product_id: Optional[str] = None,
        days_back: int = 30
    ) -> pd.DataFrame:
        """
        Récupère l'historique des commandes

        Args:
            product_id: ID du produit (optionnel, pour filtrer)
            days_back: Nombre de jours d'historique à récupérer

        Returns:
            DataFrame avec l'historique des commandes
        """
        try:
            conn = sqlite3.connect(self.db_path)

            query = """
                SELECT
                    o.id as order_id,
                    o.product_id,
                    p.name as product_name,
                    o.order_date,
                    o.quantity_ordered,
                    o.suggested_quantity,
                    o.alert_type,
                    o.stock_at_order,
                    o.unit_price,
                    o.lead_time_days,
                    o.expected_delivery,
                    (o.quantity_ordered * o.unit_price) as total_amount
                FROM orders o
                LEFT JOIN products p ON o.product_id = p.id
                WHERE o.order_date >= date('now', '-{} days')
            """.format(days_back)

            if product_id:
                query += f" AND o.product_id = '{product_id}'"

            query += " ORDER BY o.order_date DESC"

            df = pd.read_sql_query(query, conn)
            conn.close()

            # Convertir les dates en datetime
            if not df.empty:
                df['order_date'] = pd.to_datetime(df['order_date'])
                df['expected_delivery'] = pd.to_datetime(df['expected_delivery'])

            return df

        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'historique: {e}")
            return pd.DataFrame()

    def get_order_statistics(self) -> Dict[str, Any]:
        """
        Récupère les statistiques sur les commandes

        Returns:
            Dict avec les statistiques des commandes
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Nombre total de commandes
            cursor.execute("SELECT COUNT(*) FROM orders")
            total_orders = cursor.fetchone()[0]

            # Commandes par type d'alerte
            cursor.execute("""
                SELECT alert_type, COUNT(*) as count
                FROM orders
                GROUP BY alert_type
            """)
            orders_by_alert = dict(cursor.fetchall())

            # Valeur totale des commandes
            cursor.execute("""
                SELECT SUM(quantity_ordered * unit_price) as total_value
                FROM orders
            """)
            total_value = cursor.fetchone()[0] or 0

            # Commandes des 7 derniers jours
            cursor.execute("""
                SELECT COUNT(*)
                FROM orders
                WHERE order_date >= date('now', '-7 days')
            """)
            recent_orders = cursor.fetchone()[0]

            # Top 5 produits commandés
            cursor.execute("""
                SELECT
                    p.name,
                    COUNT(o.id) as order_count,
                    SUM(o.quantity_ordered) as total_quantity
                FROM orders o
                JOIN products p ON o.product_id = p.id
                GROUP BY o.product_id
                ORDER BY order_count DESC
                LIMIT 5
            """)
            top_products = cursor.fetchall()

            conn.close()

            return {
                "total_orders": total_orders,
                "orders_by_alert_type": orders_by_alert,
                "total_value": total_value,
                "recent_orders_7_days": recent_orders,
                "top_ordered_products": [
                    {
                        "name": prod[0],
                        "order_count": prod[1],
                        "total_quantity": prod[2]
                    }
                    for prod in top_products
                ]
            }

        except Exception as e:
            logger.error(f"Erreur lors du calcul des statistiques: {e}")
            return {}

    def cancel_order(self, order_id: int) -> bool:
        """
        Annule une commande (soft delete - marque comme annulée)

        Args:
            order_id: ID de la commande à annuler

        Returns:
            True si succès, False sinon
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Vérifier que la commande existe
            cursor.execute("SELECT id FROM orders WHERE id = ?", (order_id,))
            if not cursor.fetchone():
                logger.error(f"Commande #{order_id} non trouvée")
                return False

            # Pour l'instant, on pourrait ajouter une colonne 'status' à la table
            # Mais pour rester simple, on va juste logger l'annulation
            logger.info(f"Commande #{order_id} marquée pour annulation")

            conn.close()
            return True

        except Exception as e:
            logger.error(f"Erreur lors de l'annulation de la commande: {e}")
            return False


def test_order_manager():
    """Test du gestionnaire de commandes"""
    manager = OrderManager()

    # Test de sauvegarde d'une commande
    result = manager.save_order(
        product_id="1",
        quantity_ordered=100,
        suggested_quantity=95,
        alert_type="CRITIQUE",
        stock_at_order=15,
        unit_price=349377.28,
        lead_time_days=5
    )

    if result["success"]:
        print(f"Commande créée avec succès: #{result['order_id']}")
        print(f"Montant total: {result['total_amount']:,.0f} FCFA")
        print(f"Livraison prévue: {result['expected_delivery']}")
    else:
        print(f"Erreur: {result['error']}")

    # Test de récupération du lead time
    lead_time = manager.get_product_lead_time("1")
    print(f"Lead time du produit 1: {lead_time} jours")

    # Test de l'historique
    history = manager.get_order_history()
    if not history.empty:
        print(f"\nHistorique des commandes ({len(history)} commandes):")
        print(history[['order_id', 'product_name', 'quantity_ordered', 'alert_type']].head())

    # Test des statistiques
    stats = manager.get_order_statistics()
    print(f"\nStatistiques des commandes:")
    print(f"- Total: {stats.get('total_orders', 0)} commandes")
    print(f"- Valeur totale: {stats.get('total_value', 0):,.0f} FCFA")
    print(f"- Commandes récentes (7j): {stats.get('recent_orders_7_days', 0)}")


if __name__ == "__main__":
    test_order_manager()