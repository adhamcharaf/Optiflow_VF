# /predictions - Gestion des Prédictions ML

## Description
Gérer les prédictions de ventes et l'amélioration continue du modèle selon Page 3.

## Utilisation
```
/predictions [action] [options]
```

## Actions disponibles

### /predictions generate [article_id] [jours]
Génère les prédictions pour un article sur X jours (max 30)

### /predictions accuracy [article_id] [periode]
Calcule la précision des prédictions vs ventes réelles

### /predictions compare [article_id] [date_debut] [date_fin]
Compare prédictions vs réel sur une période avec détails jour par jour

### /predictions events add [date] [type] [impact]
Ajoute un événement futur pour améliorer les prédictions

### /predictions events learn [date] [explication]
Explique un écart important pour que le système apprenne

### /predictions confidence
Affiche le score de confiance global et par article

### /predictions batch
Lance le processus de génération batch (normalement nocturne)

## Exemples
```bash
# Prédictions Coca-Cola sur 7 jours
/predictions generate 123 7

# Précision de la semaine dernière
/predictions accuracy 123 semaine

# Comparer prédit vs réel
/predictions compare 123 2025-09-03 2025-09-09

# Ajouter événement futur
/predictions events add 2025-09-15 "Tabaski" 2.5

# Expliquer un écart
/predictions events learn 2025-09-05 "Match de foot"
```

## Scripts ML utilisés
- generate_predictions.py : Génération des prédictions
- calculate_accuracy.py : Calcul de précision
- learn_from_feedback.py : Apprentissage continu

## Algorithme
- **Prophet** avec composantes :
  - Tendance historique
  - Saisonnalité hebdomadaire/mensuelle  
  - Impact événements spéciaux
- **Amélioration continue** via feedback utilisateur

## Métriques
- **MAPE** : Mean Absolute Percentage Error
- **Confiance** : Score par prédiction (0-100%)
- **Évolution** : Progression de la précision dans le temps