#!/usr/bin/env python3
"""
Version simplifiée du script de mise à jour du cache des alertes
Utilise une logique simple pour générer les alertes basées sur le stock actuel
"""

import sqlite3
import random
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleAlertsCacheUpdater:
    """Version simplifiée pour mise à jour rapide des alertes"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / 'optiflow.db'
        self.db_path = db_path
    
    def update_all_alerts(self):
        """Met à jour toutes les alertes avec une logique simple"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 1. Marquer toutes les alertes actuelles comme résolues
            cursor.execute("""
                UPDATE alerts 
                SET status = 'resolved', 
                    resolved_at = datetime('now')
                WHERE status = 'active'
            """)
            
            # 2. Récupérer stock actuel et lead time pour chaque produit
            query = """
            WITH latest_stock AS (
                SELECT product_id, MAX(recorded_at) as max_date
                FROM stock_levels
                GROUP BY product_id
            )
            SELECT DISTINCT
                p.id,
                p.name,
                sl.quantity_on_hand as stock,
                p.lead_time_days,
                p.unit_price
            FROM products p
            LEFT JOIN stock_levels sl ON p.id = sl.product_id
            LEFT JOIN latest_stock ls ON sl.product_id = ls.product_id 
                AND sl.recorded_at = ls.max_date
            WHERE ls.max_date IS NOT NULL OR sl.product_id IS NULL
            """
            
            cursor.execute(query)
            products = cursor.fetchall()
            
            logger.info(f"Mise à jour des alertes pour {len(products)} produits")
            alerts_created = 0
            
            # 3. Créer les alertes basées sur des seuils simples
            for product_id, name, stock, lead_time, price in products:
                if stock is None:
                    stock = 0
                
                # Estimation simple : ventes moyennes = 10 unités/jour
                avg_daily_sales = 10
                days_of_stock = stock / avg_daily_sales if avg_daily_sales > 0 else 999
                
                # Déterminer le niveau d'alerte
                severity = None
                message = None
                
                if days_of_stock <= lead_time:
                    # CRITIQUE : rupture avant réapprovisionnement
                    severity = 'critical'
                    message = f"Rupture dans {int(days_of_stock)} jours"
                elif days_of_stock <= lead_time + 3:
                    # ATTENTION : rupture possible
                    severity = 'warning'
                    message = f"Stock faible, rupture possible dans {int(days_of_stock)} jours"
                elif days_of_stock <= lead_time + 7:
                    # INFO : stock à surveiller
                    severity = 'info'
                    message = f"Stock suffisant pour {int(days_of_stock)} jours"
                
                # Créer l'alerte si nécessaire
                if severity:
                    cursor.execute("""
                        INSERT INTO alerts (
                            product_id, alert_type, severity, title, 
                            message, status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                    """, (
                        product_id,
                        'stockout',
                        severity,
                        f"Alerte stock {name[:30]}",
                        message,
                        'active'
                    ))
                    alerts_created += 1
            
            # 4. Mettre à jour le timestamp
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                INSERT OR REPLACE INTO system_metadata (key, value, updated_at)
                VALUES ('alerts_last_update', datetime('now'), datetime('now'))
            """)
            
            conn.commit()
            conn.close()
            
            logger.info(f"OK: {alerts_created} alertes créées")
            return True
            
        except Exception as e:
            logger.error(f"Erreur: {e}")
            return False
    
    def get_last_update(self):
        """Récupère le timestamp de dernière mise à jour"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT value FROM system_metadata 
                WHERE key = 'alerts_last_update'
            """)
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except:
            return None

def main():
    print("=" * 50)
    print("MISE À JOUR SIMPLIFIÉE DU CACHE DES ALERTES")
    print("=" * 50)
    
    updater = SimpleAlertsCacheUpdater()
    
    # Afficher dernière MAJ
    last = updater.get_last_update()
    if last:
        print(f"Dernière MAJ: {last}")
    
    # Lancer mise à jour
    print("Mise à jour en cours...")
    if updater.update_all_alerts():
        print("OK: Mise à jour terminée")
        new_time = updater.get_last_update()
        if new_time:
            print(f"Nouvelle MAJ: {new_time}")
    else:
        print("ERREUR lors de la mise à jour")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())