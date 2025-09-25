"""
Mapping entre les noms de tables attendus et les vraies tables de optiflow.db
Centralise la correspondance pour tous les scripts ML
"""

# Mapping des tables
TABLE_MAPPING = {
    # Noms attendus → Vraies tables
    "articles": "products",
    "ventes": "sales_history", 
    "stock": "stock_levels",
    "evenements": "learned_events",
    "event_product_impacts": "event_product_impacts",
    "predictions": "forecasts",
    "alertes": "alerts"
}

# Mapping des colonnes - CORRIGÉ avec les vrais noms
COLUMN_MAPPING = {
    "products": {
        "id": "id",
        "nom": "name",
        "prix_unitaire": "unit_price",
        "delai_reapprovisionnement": "lead_time_days",
        "categorie": "category",
        "fournisseur": "supplier"
    },
    "sales_history": {
        "article_id": "product_id",
        "date": "order_date",
        "quantity": "quantity",
        "prix": "unit_price",
        "remise": "discount_applied"
    },
    "stock_levels": {
        "article_id": "product_id",
        "quantite_actuelle": "quantity_on_hand",
        "quantite_disponible": "quantity_available",
        "date_maj": "recorded_at",
        "current_level": "quantity_on_hand"  # Alias pour compatibilité
    },
    "forecasts": {
        "article_id": "product_id",
        "date_prevision": "forecast_date",
        "quantite_prevue": "predicted_quantity",
        "borne_inf": "lower_bound",
        "borne_sup": "upper_bound",
        "intervalle_confiance": "confidence_interval"
    },
    "alerts": {
        "article_id": "product_id",
        "type_alerte": "alert_type",
        "severite": "severity",
        "titre": "title",
        "message": "message",
        "statut": "status"
    }
}

def get_table_name(logical_name: str) -> str:
    """Retourne le vrai nom de table pour un nom logique"""
    return TABLE_MAPPING.get(logical_name, logical_name)

def get_column_name(table: str, logical_column: str) -> str:
    """Retourne le vrai nom de colonne pour une table et colonne logique"""
    if table in COLUMN_MAPPING:
        return COLUMN_MAPPING[table].get(logical_column, logical_column)
    return logical_column

def build_query(query_template: str) -> str:
    """
    Transforme une requête SQL avec noms logiques en requête avec vrais noms
    Exemple: SELECT * FROM articles → SELECT * FROM products
    """
    query = query_template
    for logical, real in TABLE_MAPPING.items():
        query = query.replace(f" {logical} ", f" {real} ")
        query = query.replace(f" {logical}.", f" {real}.")
        query = query.replace(f"FROM {logical}", f"FROM {real}")
        query = query.replace(f"JOIN {logical}", f"JOIN {real}")
        query = query.replace(f"INTO {logical}", f"INTO {real}")
    return query