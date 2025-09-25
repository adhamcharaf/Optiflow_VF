"""
Setup de base de données de test pour validation du cycle d'apprentissage
Créé les tables et données minimales pour tester user_learning_system.py
"""

import sqlite3
import logging
from datetime import datetime, timedelta
import random
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_test_database(db_path: str = "../optiflow.db"):
    """Créé les tables et données de test nécessaires"""
    logger.info("🏗 Setup base de données de test...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Créer table sales_history (nécessaire pour spike detection)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            order_date TIMESTAMP,
            quantity INTEGER,
            unit_price REAL
        )
    """)
    
    # 2. Créer table products (pour les détails produits)  
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT
        )
    """)
    
    # 3. Créer table learned_events (pour stocker événements appris)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS learned_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT,
            next_occurrence TIMESTAMP,
            typical_impact TEXT,
            confidence_score REAL DEFAULT 0.5,
            is_active BOOLEAN DEFAULT 1,
            created_by TEXT DEFAULT 'user_learning',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            observations_count INTEGER DEFAULT 1,
            recurrence_type TEXT DEFAULT 'annual',
            base_multiplier REAL DEFAULT 1.0
        )
    """)
    
    # 4. Créer table event_product_impacts (pour liens événement-produit)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_product_impacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            product_id INTEGER,
            category TEXT,
            impact_multiplier REAL,
            impact_percent REAL,
            confidence_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            observations_count INTEGER DEFAULT 1,
            FOREIGN KEY (event_id) REFERENCES learned_events(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    
    # 5. Générer données de test
    logger.info(" Génération données de vente de test...")
    
    # Produits de test
    test_products = [
        (1, "Produit A", "electronique"),
        (2, "Produit B", "vêtement"),
        (3, "Produit C", "alimentation"),
        (4, "Produit D", "electronique"),
        (5, "Produit E", "vêtement")
    ]
    
    cursor.executemany("INSERT OR IGNORE INTO products (id, name, category) VALUES (?, ?, ?)", test_products)
    
    # Générer ventes sur 3 ans avec quelques spikes
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2024, 12, 31)
    
    sales_data = []
    current_date = start_date
    
    while current_date <= end_date:
        # Ventes normales (5-15 par produit par jour)
        for product_id in range(1, 6):
            base_quantity = random.randint(5, 15)
            
            # Créer quelques spikes artificiels (dates spécifiques)
            spike_dates = [
                datetime(2022, 6, 15),  # Tabaski potentiel
                datetime(2022, 11, 25), # Black Friday potentiel
                datetime(2023, 6, 28),  # Tabaski potentiel  
                datetime(2023, 11, 24), # Black Friday potentiel
                datetime(2024, 6, 16),  # Tabaski potentiel
                datetime(2024, 11, 29)  # Black Friday potentiel
            ]
            
            # Si c'est une date de spike, multiplier par 2-4
            if current_date.date() in [d.date() for d in spike_dates]:
                quantity = base_quantity * random.randint(2, 4)
            else:
                quantity = base_quantity
                
            # Prix unitaire
            unit_price = round(random.uniform(10.0, 100.0), 2)
            
            sales_data.append((product_id, current_date, quantity, unit_price))
        
        current_date += timedelta(days=1)
    
    # Insérer données de vente
    cursor.executemany("""
        INSERT INTO sales_history (product_id, order_date, quantity, unit_price)
        VALUES (?, ?, ?, ?)
    """, sales_data)
    
    conn.commit()
    
    # Statistiques finales
    cursor.execute("SELECT COUNT(*) FROM sales_history")
    sales_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM products")  
    products_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT MIN(DATE(order_date)), MAX(DATE(order_date)) FROM sales_history")
    date_range = cursor.fetchone()
    
    conn.close()
    
    logger.info(f" Base créée avec {sales_count} ventes, {products_count} produits")
    logger.info(f" Période: {date_range[0]} → {date_range[1]}")
    
    return {
        "sales_count": sales_count,
        "products_count": products_count,
        "date_range": date_range,
        "spike_dates_included": 6
    }

def verify_database_ready(db_path: str = "../optiflow.db"):
    """Vérifie que la DB est prête pour les tests"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    required_tables = ['sales_history', 'products', 'learned_events', 'event_product_impacts']
    
    verification = {}
    
    for table in required_tables:
        cursor.execute(f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='{table}'")
        exists = cursor.fetchone()[0] > 0
        verification[f"table_{table}"] = exists
        
        if exists:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            verification[f"count_{table}"] = count
    
    conn.close()
    
    all_ready = all(verification[f"table_{table}"] for table in required_tables)
    verification['database_ready'] = all_ready
    
    return verification

if __name__ == "__main__":
    print("=" * 60)
    print("SETUP BASE DE DONNÉES DE TEST")
    print("=" * 60)
    
    # Setup  
    result = setup_test_database()
    
    print("\nRÉSULTAT SETUP:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    
    # Vérification
    print("\n" + "=" * 60) 
    verification = verify_database_ready()
    
    print("VÉRIFICATION:")
    for key, value in verification.items():
        print(f"  {key}: {value}")
    
    if verification['database_ready']:
        print("\n BASE PRÊTE POUR TESTS D'APPRENTISSAGE")
    else:
        print("\n Setup incomplet")