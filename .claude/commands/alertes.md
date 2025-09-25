# /alertes - Gestion des Alertes de Stock

## Description
Gérer les alertes de stock et calculer les quantités de commande selon les spécifications de la Page 1.

## Utilisation
```
/alertes [action] [options]
```

## Actions disponibles

### /alertes status
Affiche le statut de tous les articles avec leurs alertes

### /alertes critique
Liste uniquement les articles en statut CRITIQUE nécessitant une commande immédiate

### /alertes attention  
Liste les articles en statut ATTENTION avec les dates limites de commande

### /alertes calcul [article_id] [date_couverture] [marge_securite]
Calcule la quantité suggérée pour un article selon la formule :
`Quantité = (Σ prédictions - stock_actuel) × (1 + marge_sécurité)`

### /alertes events
Gère les événements et leur impact sur les prédictions

## Exemples
```bash
# Voir toutes les alertes
/alertes status

# Articles critiques uniquement
/alertes critique

# Calculer quantité pour Coca-Cola avec 30j de couverture et 15% de marge
/alertes calcul 123 30 15

# Gérer les événements
/alertes events
```

## Scripts ML utilisés
- calculate_alerts.py : Calcul des statuts d'alerte
- suggest_quantity.py : Calcul des quantités suggérées  
- evaluate_events_impact.py : Impact des événements

## Contraintes
- Respecter les seuils : Critique < 0j, Attention < 3j, OK >= 3j
- Calculs basés sur prédictions ML existantes
- Affichage avec couleurs : Rouge/Jaune/Vert