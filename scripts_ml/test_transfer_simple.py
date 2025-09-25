"""
Test simple du transfert des anomalies saisonnières
"""

import sqlite3
import json
from datetime import datetime

# Récupérer les anomalies saisonnières
conn = sqlite3.connect('optiflow.db')
cursor = conn.cursor()

# Récupérer les anomalies groupées
cursor.execute("""
    SELECT
        a.product_id,
        p.name as product_name,
        COUNT(*) as count,
        GROUP_CONCAT(a.detection_date) as dates,
        AVG(a.deviation_percent) as avg_deviation,
        a.anomaly_type
    FROM anomalies a
    JOIN products p ON a.product_id = p.id
    WHERE a.status = 'seasonal'
    GROUP BY a.product_id, a.anomaly_type
""")

groups = cursor.fetchall()
print(f"Groupes d'anomalies trouvés: {len(groups)}")

for group in groups:
    product_id, product_name, count, dates_str, avg_deviation, anomaly_type = group
    print(f"\nProduit: {product_name}")
    print(f"  Type: {anomaly_type}")
    print(f"  Nombre: {count}")
    print(f"  Déviation moyenne: {avg_deviation:.1f}%")

    # Créer un événement appris
    event_name = f"Pattern_{anomaly_type}_{product_id}"

    # Vérifier si l'événement existe déjà
    cursor.execute("SELECT id FROM learned_events WHERE name = ?", (event_name,))
    existing = cursor.fetchone()

    if existing:
        print(f"  -> Événement déjà existant (ID: {existing[0]})")
    else:
        # Créer l'événement
        typical_impact = {
            "type": "multiplicative" if anomaly_type == 'spike' else "additive",
            "value": 1 + (avg_deviation / 100) if anomaly_type == 'spike' else -avg_deviation,
            "severity": "high" if abs(avg_deviation) > 100 else "medium"
        }

        try:
            cursor.execute("""
                INSERT INTO learned_events (
                    name,
                    category,
                    recurrence_type,
                    recurrence_params,
                    next_occurrence,
                    typical_impact,
                    confidence_score,
                    observations_count,
                    created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_name,
                "seasonal_pattern",
                "weekly",  # Simplifié pour le test
                json.dumps({"day_of_week": 6}),  # Samedi
                datetime.now().strftime("%Y-%m-%d"),
                json.dumps(typical_impact),
                0.7,
                count,
                "seasonal_detector"
            ))

            event_id = cursor.lastrowid
            print(f"  -> Événement créé (ID: {event_id})")

            # Créer l'association avec le produit
            cursor.execute("""
                INSERT INTO event_product_impacts (
                    event_id,
                    product_id,
                    impact_type,
                    impact_value,
                    confidence
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                event_id,
                product_id,
                typical_impact['type'],
                typical_impact['value'],
                0.7
            ))

            conn.commit()
            print(f"  -> Association créée avec le produit")

        except Exception as e:
            print(f"  -> Erreur: {e}")
            conn.rollback()

# Vérifier le résultat
cursor.execute("SELECT COUNT(*) FROM learned_events")
total = cursor.fetchone()[0]
print(f"\n Total d'événements dans learned_events: {total}")

conn.close()