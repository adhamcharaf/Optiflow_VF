"""
Script de migration pour corriger la table anomalies
Remplace les contraintes CHECK pour accepter les nouvelles valeurs de status
"""

import sqlite3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_anomalies_table():
    """Migre la table anomalies avec les nouvelles contraintes"""

    conn = sqlite3.connect('../optiflow.db')
    cursor = conn.cursor()

    try:
        logger.info(" Début de la migration de la table anomalies...")

        # 1. Sauvegarder les données existantes
        cursor.execute("""
            SELECT * FROM anomalies
        """)
        existing_data = cursor.fetchall()
        logger.info(f" {len(existing_data)} enregistrements sauvegardés")

        # 2. Renommer l'ancienne table
        cursor.execute("ALTER TABLE anomalies RENAME TO anomalies_old")
        logger.info(" Table originale renommée en anomalies_old")

        # 3. Créer la nouvelle table avec les bonnes contraintes
        cursor.execute("""
            CREATE TABLE anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                detection_date DATE,
                actual_value REAL,
                predicted_value REAL,
                deviation_percent REAL,
                anomaly_type TEXT CHECK(anomaly_type IN ('spike', 'drop', 'structural_change')),
                severity TEXT CHECK(severity IN ('low', 'medium', 'high', 'critical')),
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'validated', 'ignored', 'seasonal')),
                group_id INTEGER,
                confidence_score REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        logger.info(" Nouvelle table créée avec les contraintes correctes")

        # 4. Restaurer les données avec mapping des anciennes valeurs
        if existing_data:
            for row in existing_data:
                # Mapper les anciennes valeurs de status
                status = row[8]  # Index de la colonne status
                if status == 'qualified':
                    status = 'validated'
                elif status == 'dismissed':
                    status = 'ignored'
                elif status == 'resolved':
                    status = 'seasonal'

                # Insérer dans la nouvelle table
                cursor.execute("""
                    INSERT INTO anomalies
                    (id, product_id, detection_date, actual_value, predicted_value,
                     deviation_percent, anomaly_type, severity, status, group_id,
                     confidence_score, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row[0], row[1], row[2], row[3], row[4], row[5],
                    row[6], row[7], status, row[9], row[10], row[11]
                ))

            logger.info(f" {len(existing_data)} enregistrements restaurés avec succès")

        # 5. Supprimer l'ancienne table
        cursor.execute("DROP TABLE anomalies_old")
        logger.info(" Ancienne table supprimée")

        # 6. Créer un index sur les colonnes fréquemment utilisées
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_anomalies_status
            ON anomalies(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_anomalies_product_date
            ON anomalies(product_id, detection_date)
        """)
        logger.info(" Index créés pour optimiser les performances")

        conn.commit()
        logger.info(" Migration terminée avec succès !")

        # Vérifier les contraintes
        cursor.execute("""
            SELECT sql FROM sqlite_master
            WHERE name='anomalies' AND type='table'
        """)
        result = cursor.fetchone()
        logger.info("\n📋 Nouvelle structure de la table:")
        print(result[0])

        return True

    except Exception as e:
        logger.error(f" Erreur lors de la migration: {e}")
        conn.rollback()

        # Essayer de restaurer l'ancienne table si elle existe
        try:
            cursor.execute("DROP TABLE IF EXISTS anomalies")
            cursor.execute("ALTER TABLE anomalies_old RENAME TO anomalies")
            logger.info(" Table originale restaurée")
        except:
            pass

        return False

    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("MIGRATION DE LA TABLE ANOMALIES")
    print("=" * 60)
    print("\nCe script va:")
    print("1. Sauvegarder les donnees existantes")
    print("2. Recreer la table avec les bonnes contraintes")
    print("3. Restaurer les donnees avec mapping des valeurs")
    print("\nValeurs de status:")
    print("  - pending -> pending")
    print("  - qualified -> validated")
    print("  - dismissed -> ignored")
    print("  - resolved -> seasonal")

    response = input("\nVoulez-vous continuer? (o/n): ")
    if response.lower() == 'o':
        if migrate_anomalies_table():
            print("\nMigration reussie !")
        else:
            print("\nMigration echouee. Consultez les logs.")
    else:
        print("Migration annulée.")