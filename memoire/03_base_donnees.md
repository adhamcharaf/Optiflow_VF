# Base de Données Optiflow

## 3.1 Vue d'Ensemble

La base de données Optiflow utilise SQLite 3 comme système de gestion. Elle contient 23 tables interconnectées stockant 3 ans d'historique de données commerciales, soit environ 10 MB de données structurées représentant plus de 500 000 enregistrements.

### Caractéristiques principales
- **Type** : SQLite 3 (base embarquée)
- **Taille** : ~10 MB
- **Tables** : 23 tables actives
- **Historique** : 3 ans de données (2022-2025)
- **Volume** : ~500 000 enregistrements totaux

## 3.2 Schéma de la Base de Données

### 3.2.1 Tables Principales

#### Table `products` (Produits)
Catalogue des produits avec leurs caractéristiques.

| Colonne | Type | Description |
|---------|------|-------------|
| id | INTEGER PRIMARY KEY | Identifiant unique |
| name | TEXT NOT NULL | Nom du produit |
| category | TEXT | Catégorie produit |
| supplier | TEXT | Fournisseur |
| unit_price | REAL | Prix unitaire |
| lead_time_days | INTEGER | Délai réapprovisionnement (jours) |
| min_stock_level | INTEGER | Stock minimum |
| max_stock_level | INTEGER | Stock maximum |

**Volume** : ~250 produits actifs

#### Table `sales_history` (Historique des ventes)
Enregistrement de toutes les transactions de vente.

| Colonne | Type | Description |
|---------|------|-------------|
| id | INTEGER PRIMARY KEY | Identifiant transaction |
| product_id | INTEGER FK | Référence produit |
| order_date | DATE | Date de vente |
| quantity | INTEGER | Quantité vendue |
| unit_price | REAL | Prix unitaire appliqué |
| discount_applied | REAL | Remise appliquée (%) |
| customer_id | INTEGER | ID client (optionnel) |

**Volume** : ~350 000 enregistrements (3 ans)

#### Table `stock_levels` (Niveaux de stock)
État actuel et historique des stocks.

| Colonne | Type | Description |
|---------|------|-------------|
| id | INTEGER PRIMARY KEY | Identifiant |
| product_id | INTEGER FK | Référence produit |
| quantity_on_hand | INTEGER | Stock physique |
| quantity_available | INTEGER | Stock disponible |
| recorded_at | TIMESTAMP | Date/heure enregistrement |
| location | TEXT | Emplacement stock |

**Volume** : ~90 000 enregistrements

### 3.2.2 Tables de Machine Learning

#### Table `forecasts` (Prédictions)
Stockage des prédictions générées par Prophet.

| Colonne | Type | Description |
|---------|------|-------------|
| id | INTEGER PRIMARY KEY | Identifiant |
| product_id | INTEGER FK | Référence produit |
| forecast_date | DATE | Date de prédiction |
| predicted_quantity | REAL | Quantité prédite |
| lower_bound | REAL | Borne inférieure (IC 95%) |
| upper_bound | REAL | Borne supérieure (IC 95%) |
| confidence_interval | REAL | Niveau de confiance |
| created_at | TIMESTAMP | Date génération |
| model_version | TEXT | Version du modèle |

**Volume** : ~75 000 prédictions actives

#### Table `alerts` (Alertes)
Système d'alertes générées automatiquement.

| Colonne | Type | Description |
|---------|------|-------------|
| id | INTEGER PRIMARY KEY | Identifiant |
| product_id | INTEGER FK | Référence produit |
| alert_type | TEXT | Type (rupture/surstock) |
| severity | TEXT | Sévérité (critical/warning/info) |
| title | TEXT | Titre de l'alerte |
| message | TEXT | Description détaillée |
| status | TEXT | Statut (active/resolved) |
| created_at | TIMESTAMP | Date création |
| resolved_at | TIMESTAMP | Date résolution |

**Volume** : ~5 000 alertes historiques

#### Table `anomalies` (Anomalies détectées)
Détection automatique d'anomalies dans les ventes.

| Colonne | Type | Description |
|---------|------|-------------|
| id | INTEGER PRIMARY KEY | Identifiant |
| product_id | INTEGER FK | Référence produit |
| anomaly_date | DATE | Date de l'anomalie |
| actual_value | REAL | Valeur réelle observée |
| expected_value | REAL | Valeur attendue |
| deviation_percentage | REAL | % d'écart |
| anomaly_type | TEXT | Type (outlier/promotion/stockout) |
| is_exceptional | BOOLEAN | Validé comme exceptionnel |
| validation_date | TIMESTAMP | Date validation |
| validated_by | TEXT | Utilisateur validateur |

### 3.2.3 Tables d'Événements et Apprentissage

#### Table `learned_events` (Événements appris)
Stockage des événements impactant les ventes.

| Colonne | Type | Description |
|---------|------|-------------|
| id | INTEGER PRIMARY KEY | Identifiant |
| event_name | TEXT | Nom de l'événement |
| event_type | TEXT | Type (promotion/holiday/special) |
| start_date | DATE | Date début |
| end_date | DATE | Date fin |
| impact_multiplier | REAL | Multiplicateur d'impact |
| description | TEXT | Description |
| created_at | TIMESTAMP | Date création |

#### Table `event_product_impacts` (Impact par produit)
Impact spécifique des événements sur chaque produit.

| Colonne | Type | Description |
|---------|------|-------------|
| id | INTEGER PRIMARY KEY | Identifiant |
| event_id | INTEGER FK | Référence événement |
| product_id | INTEGER FK | Référence produit |
| impact_percentage | REAL | % d'impact sur ventes |
| confidence_score | REAL | Score de confiance |

### 3.2.4 Tables de Gestion

#### Table `orders` (Commandes)
Historique des commandes passées.

| Colonne | Type | Description |
|---------|------|-------------|
| id | INTEGER PRIMARY KEY | Identifiant |
| product_id | INTEGER FK | Référence produit |
| order_date | TIMESTAMP | Date commande |
| quantity_ordered | INTEGER | Quantité commandée |
| suggested_quantity | INTEGER | Quantité suggérée système |
| alert_type | TEXT | Type alerte associée |
| stock_at_order | INTEGER | Stock au moment commande |
| unit_price | REAL | Prix unitaire |
| lead_time_days | INTEGER | Délai livraison |
| expected_delivery | DATE | Date livraison prévue |
| actual_delivery | DATE | Date livraison réelle |
| status | TEXT | Statut commande |

#### Table `system_metadata` (Métadonnées système)
Configuration et paramètres système.

| Colonne | Type | Description |
|---------|------|-------------|
| key | TEXT PRIMARY KEY | Clé paramètre |
| value | TEXT | Valeur |
| updated_at | TIMESTAMP | Dernière modification |

## 3.3 Système de Mapping Logique/Physique

Pour maintenir la compatibilité avec l'existant, un système de mapping traduit les noms logiques en noms physiques :

```python
TABLE_MAPPING = {
    "articles": "products",
    "ventes": "sales_history",
    "stock": "stock_levels",
    "evenements": "learned_events",
    "predictions": "forecasts",
    "alertes": "alerts"
}

COLUMN_MAPPING = {
    "products": {
        "nom": "name",
        "prix_unitaire": "unit_price",
        "delai_reapprovisionnement": "lead_time_days"
    },
    # ...
}
```

## 3.4 Relations et Intégrité

### 3.4.1 Diagramme Entité-Relation Simplifié

```
products (1) ──────> (N) sales_history
    │                         │
    │                         │
    └──> (N) stock_levels     │
    │                         │
    └──> (N) forecasts        │
    │                         │
    └──> (N) alerts           │
    │                         │
    └──> (N) anomalies ←──────┘
    │
    └──> (N) event_product_impacts
              │
              └──> (1) learned_events
```

### 3.4.2 Contraintes d'Intégrité

1. **Clés étrangères** : Toutes les références produit_id
2. **Contraintes NOT NULL** : Champs obligatoires définis
3. **Index** : Sur toutes les colonnes de dates et FK
4. **Triggers** : Mise à jour automatique timestamps

## 3.5 Optimisations et Performance

### 3.5.1 Index Créés

```sql
CREATE INDEX idx_sales_date ON sales_history(order_date);
CREATE INDEX idx_sales_product ON sales_history(product_id);
CREATE INDEX idx_forecast_date ON forecasts(forecast_date);
CREATE INDEX idx_forecast_product ON forecasts(product_id);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_stock_product ON stock_levels(product_id);
```

### 3.5.2 Vues Matérialisées (Simulées)

Pour améliorer les performances, certaines agrégations sont pré-calculées :

```sql
-- Vue des ventes moyennes par produit (30 jours)
CREATE VIEW v_avg_sales_30d AS
SELECT
    product_id,
    AVG(quantity) as avg_daily_sales,
    COUNT(*) as days_with_sales
FROM sales_history
WHERE order_date >= date('now', '-30 days')
GROUP BY product_id;
```

## 3.6 Volume et Croissance des Données

### 3.6.1 Volumétrie Actuelle

| Table | Nombre d'enregistrements | Taille estimée |
|-------|-------------------------|----------------|
| products | 250 | 50 KB |
| sales_history | 350 000 | 7 MB |
| stock_levels | 90 000 | 1.5 MB |
| forecasts | 75 000 | 1 MB |
| alerts | 5 000 | 200 KB |
| anomalies | 2 000 | 100 KB |
| **Total** | **~522 000** | **~10 MB** |

### 3.6.2 Croissance Estimée

- **Ventes** : +300 enregistrements/jour
- **Stock** : +250 enregistrements/jour
- **Prédictions** : +7 500/mois (batch nocturne)
- **Croissance annuelle** : ~30% (3 MB/an)

## 3.7 Stratégie de Maintenance

### 3.7.1 Purge des Données

```sql
-- Purge des anciennes prédictions (> 90 jours)
DELETE FROM forecasts
WHERE created_at < date('now', '-90 days');

-- Archive des alertes résolues (> 180 jours)
INSERT INTO alerts_archive
SELECT * FROM alerts
WHERE status = 'resolved'
AND resolved_at < date('now', '-180 days');
```

### 3.7.2 Vacuum et Optimisation

```bash
# Optimisation mensuelle
sqlite3 optiflow.db "VACUUM;"
sqlite3 optiflow.db "ANALYZE;"
```

## 3.8 Sécurité et Sauvegarde

### 3.8.1 Contraintes de Sécurité

1. **Lecture seule** pour l'application (sauf tables spécifiques)
2. **Requêtes paramétrées** contre injection SQL
3. **Validation des types** avant insertion
4. **Audit trail** sur modifications critiques

### 3.8.2 Stratégie de Sauvegarde

```bash
# Sauvegarde quotidienne
cp optiflow.db backups/optiflow_$(date +%Y%m%d).db

# Sauvegarde incrémentale (WAL mode)
sqlite3 optiflow.db "PRAGMA wal_checkpoint;"
```

## 3.9 Migration et Évolution

### 3.9.1 Vers PostgreSQL

La structure est compatible avec une migration vers PostgreSQL :

```sql
-- Conversion des types SQLite → PostgreSQL
-- INTEGER → BIGINT
-- REAL → DECIMAL(10,2)
-- TEXT → VARCHAR/TEXT
-- TIMESTAMP → TIMESTAMP WITH TIME ZONE
```

### 3.9.2 Versioning du Schéma

Table `schema_migrations` pour tracer les évolutions :

| Version | Applied_at | Description |
|---------|-----------|-------------|
| 1.0.0 | 2024-01-01 | Schéma initial |
| 1.1.0 | 2024-06-01 | Ajout table orders |
| 1.2.0 | 2024-09-01 | Ajout table anomalies |

## 3.10 Conclusion

La base de données Optiflow représente le cœur du système avec une structure optimisée pour les opérations de lecture fréquentes tout en maintenant l'intégrité des données. Son architecture permet une évolution progressive vers des systèmes plus robustes sans rupture de compatibilité.