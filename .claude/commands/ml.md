# /ml - Scripts Machine Learning

## Description
Gestion et exécution des scripts ML selon l'orchestration définie dans les specs.

## Utilisation
```
/ml [script] [options]
```

## Scripts disponibles

### Scripts Page 1 (Alertes)
```bash
/ml predict-sales [article_id] [jours]     # Script 1
/ml calc-alerts [article_id]               # Script 2  
/ml suggest-qty [article_id] [couverture]  # Script 3
/ml eval-events [event_type]               # Script 4
/ml monitor-perf [article_id]              # Script 5
```

### Scripts Page 2 (Dashboard)  
```bash
/ml agg-kpis                              # Script 6
/ml track-savings [alerte_id]             # Script 7
/ml compare-ca [periode]                  # Script 8
/ml calc-trends [nb_jours]                # Script 9
/ml top-urgent [limite]                   # Script 10
/ml stock-dormant [seuil_jours]           # Script 11
```

### Scripts Page 3 (Prédictions)
```bash
/ml generate-pred [article_id]            # Script A
/ml calc-accuracy [periode]               # Script B  
/ml learn-feedback [date] [explication]   # Script C
```

### Orchestration
```bash
/ml batch                                 # Processus batch nocturne complet
/ml validate                             # Validation de tous les scripts
/ml performance                          # Benchmark des performances
```

## Exemples
```bash
# Batch nocturne complet
/ml batch

# Prédictions pour un article
/ml predict-sales 123 30

# KPIs dashboard
/ml agg-kpis

# Validation des scripts
/ml validate
```

## Workflow batch nocturne
1. **00:30** : generate-pred (tous articles, 30j)
2. **01:00** : eval-events (enrichissement)  
3. **01:15** : calc-alerts (statuts)
4. **01:30** : agg-kpis (dashboard)
5. **01:45** : monitor-perf (amélioration)

## Technologies
- **Prophet** : Prédictions temporelles
- **Pandas** : Manipulation données
- **SQLite** : Persistance
- **JSON** : Format de sortie standardisé