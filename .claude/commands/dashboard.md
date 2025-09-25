# /dashboard - Tableau de Bord Optiflow

## Description
Génère et affiche les KPIs du dashboard selon les spécifications de la Page 2.

## Utilisation
```
/dashboard [section] [options]
```

## Sections disponibles

### /dashboard kpis
Affiche les KPIs de l'en-tête :
- Alertes par statut (Critique/Attention/OK)
- Valeur stock total
- Taux de rotation mensuel

### /dashboard sante
Section Santé Financière :
- CA prévu vs CA réel de la semaine
- Économies réalisées grâce aux alertes

### /dashboard tendances
Graphique d'évolution des alertes sur 7 jours

### /dashboard urgents
Top 3 des articles les plus urgents (status CRITIQUE)

### /dashboard dormant
Articles sans mouvement > 30 jours et valeur immobilisée

### /dashboard savings [alerte_id] [commande_passee]
Enregistre une action suite à une alerte pour calculer les économies

## Exemples
```bash
# Vue d'ensemble complète
/dashboard

# KPIs uniquement
/dashboard kpis

# Santé financière
/dashboard sante

# Enregistrer qu'une commande a été passée suite à une alerte
/dashboard savings 123 true
```

## Scripts ML utilisés
- aggregate_dashboard_kpis.py : KPIs globaux
- track_savings.py : Suivi des économies
- compare_ca_predictions.py : CA prévu vs réel
- calculate_trends.py : Tendances 7 jours
- get_top_urgent.py : Top urgents
- get_stock_dormant.py : Stock dormant

## Formules clés
- **Taux rotation** : `Ventes_30j / Stock_moyen`
- **Économies** : `Jours_rupture_évités × Ventes_prédites × Prix`
- **Interprétation taux** : >4 Excellent, 2-4 Correct, <2 Faible