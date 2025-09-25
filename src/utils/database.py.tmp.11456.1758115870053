"""
Utilitaire de gestion de la base de données optiflow.db
CONTRAINTE CRITIQUE: Structure existante à préserver absolument
"""

import sqlite3
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptiflowDB:
    """Gestionnaire de la base de données Optiflow avec contraintes de sécurité"""
    
    def __init__(self, db_path=None):
        """
        Initialise la connexion à la base de données
        
        Args:
            db_path: Chemin vers optiflow.db (par défaut à la racine du projet)
        """
        if db_path is None:
            # Chemin par défaut depuis n'importe quel répertoire du projet
            current_path = Path(__file__).parent
            project_root = current_path.parent.parent
            db_path = project_root / "optiflow.db"
        
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Base de données non trouvée: {db_path}")
        
        logger.info(f"Connexion à la base: {self.db_path}")
    
    def get_connection(self):
        """Retourne une connexion à la base de données"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Pour accès par nom de colonne
            return conn
        except sqlite3.Error as e:
            logger.error(f"Erreur connexion DB: {e}")
            raise
    
    def execute_query(self, query, params=None, fetch_all=True):
        """
        Exécute une requête SELECT de manière sécurisée
        
        Args:
            query: Requête SQL (SELECT uniquement)
            params: Paramètres de la requête
            fetch_all: True pour fetchall(), False pour fetchone()
        
        Returns:
            Résultat de la requête ou None en cas d'erreur
        """
        # Sécurité: Vérifier que c'est bien une requête SELECT ou WITH (CTE)
        query_upper = query.strip().upper()
        if not (query_upper.startswith('SELECT') or query_upper.startswith('WITH')):
            raise ValueError("Seules les requêtes SELECT sont autorisées")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or [])
                
                if fetch_all:
                    return cursor.fetchall()
                else:
                    return cursor.fetchone()
                    
        except sqlite3.Error as e:
            logger.error(f"Erreur requête: {e}")
            return None
    
    def get_dataframe(self, query, params=None):
        """
        Exécute une requête et retourne un DataFrame pandas
        
        Args:
            query: Requête SQL SELECT
            params: Paramètres de la requête
            
        Returns:
            DataFrame pandas ou None en cas d'erreur
        """
        try:
            with self.get_connection() as conn:
                return pd.read_sql_query(query, conn, params=params)
        except Exception as e:
            logger.error(f"Erreur DataFrame: {e}")
            return None
    
    def get_table_schema(self, table_name):
        """Retourne le schéma d'une table"""
        query = f"PRAGMA table_info({table_name})"
        return self.execute_query(query)
    
    def get_all_tables(self):
        """Retourne la liste de toutes les tables"""
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        result = self.execute_query(query)
        return [row[0] for row in result] if result else []
    
    def backup_database(self, backup_path=None):
        """
        Crée une sauvegarde de la base de données
        
        Args:
            backup_path: Chemin de sauvegarde (par défaut: backup_YYYYMMDD_HHMMSS.db)
        """
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backup_{timestamp}.db"
        
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Sauvegarde créée: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Erreur sauvegarde: {e}")
            return None
    
    def get_database_stats(self):
        """Retourne les statistiques de la base de données"""
        stats = {}
        
        try:
            # Nombre total de tables
            tables = self.get_all_tables()
            stats['nb_tables'] = len(tables)
            stats['tables'] = tables
            
            # Taille de la base
            stats['taille_mb'] = self.db_path.stat().st_size / (1024 * 1024)
            
            # Statistiques par table importante
            important_tables = ['articles', 'ventes', 'stock', 'predictions', 'alertes']
            
            for table in important_tables:
                if table in tables:
                    count_query = f"SELECT COUNT(*) as count FROM {table}"
                    result = self.execute_query(count_query, fetch_all=False)
                    stats[f'nb_{table}'] = result[0] if result else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur stats: {e}")
            return {}

# Instance globale pour l'application
db = OptiflowDB()

def check_db_connection():
    """Vérifie la connexion à la base de données"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Connexion impossible: {e}")
        return False

def get_db_connection():
    """Retourne l'instance de base de données"""
    return db

# Requêtes prédéfinies pour la sécurité
SAFE_QUERIES = {
    'articles_list': """
        SELECT id, nom, stock_actuel as stock, prix_unitaire, categorie 
        FROM articles 
        ORDER BY nom
    """,
    
    'alerts_summary': """
        SELECT status, COUNT(*) as count 
        FROM alertes 
        GROUP BY status
    """,
    
    'stock_value': """
        SELECT SUM(stock_actuel * prix_unitaire) as valeur_totale 
        FROM articles
    """,
    
    'sales_30_days': """
        SELECT SUM(quantite) as total_ventes 
        FROM ventes 
        WHERE date >= DATE('now', '-30 days')
    """,
    
    'predictions_today': """
        SELECT article_id, quantite_predite, confiance 
        FROM predictions 
        WHERE date = DATE('now')
    """
}

def get_safe_data(query_name, params=None):
    """
    Exécute une requête prédéfinie de manière sécurisée
    
    Args:
        query_name: Nom de la requête dans SAFE_QUERIES
        params: Paramètres optionnels
    
    Returns:
        Résultat de la requête ou None
    """
    if query_name not in SAFE_QUERIES:
        logger.error(f"Requête non autorisée: {query_name}")
        return None
    
    query = SAFE_QUERIES[query_name]
    return db.execute_query(query, params)