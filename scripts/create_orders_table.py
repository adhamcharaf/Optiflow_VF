"""
Script pour créer la table orders dans la base de données optiflow.db
"""

import sqlite3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_orders_table():
    """Crée la table orders si elle n'existe pas déjà"""
    try:
        conn = sqlite3.connect('optiflow.db')
        cursor = conn.cursor()

        # Créer la table orders
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                quantity_ordered INTEGER NOT NULL,
                suggested_quantity INTEGER,
                alert_type TEXT,
                stock_at_order INTEGER,
                unit_price REAL,
                lead_time_days INTEGER,
                expected_delivery DATE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)

        # Créer un index sur product_id pour améliorer les performances
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_product_id
            ON orders(product_id)
        """)

        # Créer un index sur order_date pour les requêtes temporelles
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_date
            ON orders(order_date)
        """)

        conn.commit()
        logger.info("Table 'orders' créée avec succès")

        # Vérifier que la table a bien été créée
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='orders'
        """)

        if cursor.fetchone():
            logger.info("✓ Table 'orders' vérifiée dans la base de données")

            # Afficher la structure de la table
            cursor.execute("PRAGMA table_info(orders)")
            columns = cursor.fetchall()
            logger.info("Colonnes de la table orders:")
            for col in columns:
                logger.info(f"  - {col[1]} ({col[2]})")
        else:
            logger.error("Erreur: La table 'orders' n'a pas été créée")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Erreur lors de la création de la table orders: {e}")
        return False

if __name__ == "__main__":
    success = create_orders_table()
    if success:
        print("Table 'orders' créée avec succès dans optiflow.db")
    else:
        print("Échec de la création de la table 'orders'")