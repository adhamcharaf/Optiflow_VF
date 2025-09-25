# /db - Gestion Base de Données

## Description
Commandes pour interagir avec la base de données optiflow.db de manière sécurisée.

## Utilisation
```
/db [action] [options]
```

## Actions disponibles

### /db schema
Affiche la structure des tables principales

### /db check
Vérifie l'intégrité de la base et affiche les statistiques

### /db query [table] [conditions]
Exécute une requête SELECT sécurisée

### /db backup
Crée une sauvegarde horodatée de la base

### /db stats
Affiche les statistiques : nombre d'articles, de ventes, période de données

## Exemples
```bash
# Voir la structure
/db schema

# Statistiques générales
/db stats

# Vérifier l'intégrité
/db check

# Sauvegarder
/db backup

# Requête sur les articles
/db query articles "WHERE categorie='Boissons'"
```

## Contraintes importantes
- **LECTURE SEULE** : Aucune modification de structure autorisée
- **18 tables** avec 3 ans d'historique à préserver
- **SQLite** : Base locale, pas de connexions externes
- **Backup automatique** avant toute intervention

## Tables principales
- articles : Catalogue produits
- ventes : Historique des ventes
- stock : Niveaux de stock actuels
- predictions : Prédictions ML
- alertes : Statuts d'alerte
- evenements : Événements impactants