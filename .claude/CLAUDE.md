# Optiflow MVP - Système de Gestion Intelligente des Stocks

## CONTEXTE DU PROJET

Optiflow est un système MVP de gestion intelligente des stocks développé en Python/Streamlit avec une base SQLite (optiflow.db) contenant 18 tables et 3 ans de données historiques. Le système utilise des algorithmes de Machine Learning (Prophet) pour prédire les ventes et optimiser les commandes.

## ARCHITECTURE DU SYSTÈME

### Base de données existante
- **optiflow.db** : 18 tables, 3 ans d'historique
- **NE PAS MODIFIER** la structure existante
- Tables principales : articles, ventes, stock, predictions, alertes

### Workflow opérationnel
- **Batch nocturne** : Génération des prédictions à minuit
- **Cache 24h** : Affichage avec timestamp de dernière mise à jour
- **Interface temps réel** : Calcul des alertes à la demande

## PAGES DU SYSTÈME

### Page 1 - Alertes et Gestion des Stocks

**Sections principales :**
1. **Alertes** : 3 niveaux (Critique, Attention, OK)
   - Critique : Rupture inévitable, commande immédiate
   - Attention : Rupture évitable si commande sous 3 jours
   - OK : Stock suffisant pour 3+ jours

2. **Calcul de quantité suggérée**
   - Configuration utilisateur : date de couverture + marge sécurité
   - Formule : `(Σ prédictions - stock actuel) × (1 + marge)`

3. **Événements** : Liste et historique d'impact

4. **Performances Optiflow** : MAPE moyen et précision

**Scripts ML associés (5 scripts) :**
- predict_daily_sales.py
- calculate_alerts.py  
- suggest_quantity.py
- evaluate_events_impact.py
- monitor_ml_performance.py

### Page 2 - Dashboard

**KPIs en en-tête :**
- Alertes par statut, valeur stock total, taux de rotation
- `Taux rotation = Ventes 30j / Stock moyen`

**Sections :**
1. **Santé Financière** : CA prévu vs réel, économies réalisées
2. **Tendance 7 jours** : Évolution des alertes
3. **Événements à venir** : Impact prévu

**Scripts ML associés (6 scripts) :**
- aggregate_dashboard_kpis.py
- track_savings.py
- compare_ca_predictions.py
- calculate_trends.py
- get_top_urgent.py
- get_stock_dormant.py

### Page 3 - Prédictions

**Sections :**
1. **Prédictions futures** : Tableau par article/période
2. **Preuve de précision** : Comparaison prédit vs réel
3. **Amélioration continue** : Apprentissage des événements

**Scripts ML associés (3 scripts) :**
- generate_predictions.py
- calculate_accuracy.py
- learn_from_feedback.py

## CONTRAINTES TECHNIQUES

### Stack technologique
- Python 3.8+
- Streamlit pour l'interface
- SQLite (base existante)
- Prophet pour ML
- Pandas pour manipulation données

### Règles de développement
- Respecter FIDÈLEMENT les spécifications des documents
- Workflow batch nocturne obligatoire
- Cache 24h avec timestamp
- Interface responsive et intuitive
- Couleurs : Rouge (Critique), Jaune (Attention), Vert (OK)

### Performance
- Calculs asynchrones pour l'interface
- Indexation sur colonnes de dates
- Pas de requêtes lourdes en temps réel

## ORGANISATION DU CODE

### Structure src/
```
src/
├── pages/              # 3 pages Streamlit
│   ├── alertes.py     # Page 1
│   ├── dashboard.py   # Page 2
│   └── predictions.py # Page 3
├── components/         # Composants UI réutilisables
│   ├── alerts_display.py
│   ├── kpi_cards.py
│   └── charts.py
└── utils/             # Utilitaires
    ├── database.py    # Connexion DB
    ├── cache.py       # Gestion cache 24h
    └── workflow.py    # Orchestration batch
```

### Scripts ML (scripts_ml/)
11 scripts organisés par page :
- Page 1 : Scripts 1-5
- Page 2 : Scripts 6-11  
- Page 3 : Scripts A-C

## FORMULES ET CALCULS CLÉS

### Alertes
- **Critique** : `stock_actuel - ventes_prevues_delai < 0`
- **Attention** : `stock_actuel - ventes_prevues_delai >= 0 ET < 3j_ventes`
- **Perte** : `jours_rupture × ventes_predites × prix`

### Quantité suggérée
```
Quantité = (Σ prédictions_jusqu_date - stock_actuel) × (1 + marge_sécurité/100)
```

### Taux de rotation
```
Taux = Ventes_30j / Stock_moyen_periode
```

## WORKFLOW UTILISATEUR

### Matinée (2 min)
1. Consultation Page 1 pour alertes critiques
2. Commandes urgentes basées sur suggestions

### Soir (optionnel, 1 min)
1. Explication des écarts de prédiction
2. Ajout d'événements futurs

### Résultat
- Semaine 1 : 85% précision
- Semaine 4 : 89% précision  
- Semaine 8 : 92% précision

## COMMANDES UTILES

### Développement
```bash
# Lancer l'application
streamlit run src/main.py

# Tests
python -m pytest tests/

# Linting
ruff check src/
ruff format src/

# Scripts ML (batch nocturne)
python scripts_ml/orchestrator.py
```

### Base de données
```bash
# Vérifier structure
sqlite3 optiflow.db ".schema"

# Backup
cp optiflow.db optiflow_backup_$(date +%Y%m%d).db
```

## PROCHAINES ÉTAPES DE DÉVELOPPEMENT

1. Implémenter les 3 pages Streamlit selon specs exactes
2. Créer les 11 scripts ML avec orchestration
3. Configurer le cache et workflow batch
4. Tests unitaires et validation
5. Documentation utilisateur

## RÉFÉRENCES

- Documents specs : doc/Page1_Optiflow.md, doc/Page2_optiflow.md, doc/Page3_Prédiction.md
- Base de données : optiflow.db (structure existante)
- Scripts ML : scripts_ml/ (à organiser selon spécifications)