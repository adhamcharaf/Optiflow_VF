# 🎯 Optiflow MVP - Système de Gestion Intelligente des Stocks

## Vue d'ensemble

Optiflow est un système MVP de gestion intelligente des stocks utilisant des algorithmes de Machine Learning (Prophet) pour prédire les ventes et optimiser les commandes. Le système respecte un workflow batch nocturne avec cache 24h et affichage en temps réel.

## 🚀 Caractéristiques principales

### Architecture conforme aux spécifications
- **3 pages Streamlit** : Alertes, Dashboard, Prédictions
- **Workflow batch nocturne** : Génération des prédictions à 00:30
- **Cache 24h obligatoire** : Avec timestamp visible utilisateur
- **Base SQLite existante** : 18 tables, 3 ans d'historique (structure préservée)

### Fonctionnalités métier
- **Alertes intelligentes** : 3 niveaux (Critique, Attention, OK)
- **Prédictions ML** : Prophet avec saisonnalité et événements
- **Calcul de quantités** : Formule personnalisable avec marge de sécurité
- **Dashboard KPIs** : Santé globale, tendances, performances
- **Amélioration continue** : Apprentissage par feedback utilisateur

## 📋 Prérequis

- Python 3.8+
- Base de données `optiflow.db` (existante, ne pas modifier)
- 2GB RAM minimum
- Accès en écriture pour le cache et les logs

## 🛠️ Installation

### 1. Clone du projet
```bash
git clone <repository>
cd optiflow_mvp
```

### 2. Environnement virtuel
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

### 3. Installation des dépendances
```bash
pip install -r requirements.txt
```

### 4. Vérification de la base de données
```bash
# Vérifier que optiflow.db existe à la racine
ls -la optiflow.db
```

## 🚀 Utilisation

### Lancement de l'application
```bash
# Depuis la racine du projet
streamlit run src/main.py
```

L'application sera accessible sur `http://localhost:8501`

### Batch nocturne
```bash
# Exécution manuelle du batch
python scripts_ml/orchestrator.py

# Exécution d'un script spécifique
python scripts_ml/orchestrator.py predict_daily_sales.py
```

## 📊 Structure du projet

```
optiflow_mvp/
├── .claude/                    # Configuration Claude Code
│   ├── CLAUDE.md              # Contexte complet du projet
│   ├── commands/              # Slash commands par fonctionnalité
│   └── steering/              # Contraintes et règles
├── src/                       # Code source principal
│   ├── main.py               # Point d'entrée Streamlit
│   ├── pages/                # 3 pages selon spécifications
│   │   ├── alertes.py        # Page 1 - Alertes & Stocks
│   │   ├── dashboard.py      # Page 2 - Dashboard
│   │   └── predictions.py    # Page 3 - Prédictions
│   ├── components/           # Composants UI réutilisables
│   │   ├── alerts_display.py
│   │   ├── kpi_cards.py
│   │   └── quantity_calculator.py
│   └── utils/                # Utilitaires
│       ├── database.py       # Gestion DB sécurisée
│       ├── cache.py          # Cache 24h obligatoire
│       └── workflow.py       # Orchestration batch
├── scripts_ml/               # Scripts Machine Learning
│   ├── orchestrator.py       # Orchestrateur principal
│   ├── page1_alerts/         # Scripts 1-5 (Page Alertes)
│   ├── page2_dashboard/      # Scripts 6-11 (Page Dashboard)
│   └── page3_predictions/    # Scripts A-C (Page Prédictions)
├── doc/                      # Documentation spécifications
│   ├── Page1_Optiflow.md
│   ├── Page2_optiflow.md
│   └── Page3_Prédiction.md
├── optiflow.db              # Base de données (18 tables)
└── requirements.txt         # Dépendances Python
```

## 🎯 Pages de l'application

### Page 1 - Alertes & Stocks
- **Alertes en temps réel** : Critique, Attention, OK
- **Calcul de quantités** : Interface personnalisable
- **Gestion d'événements** : Impact sur les prédictions
- **Performances ML** : Précision et MAPE

### Page 2 - Dashboard
- **KPIs de santé** : Alertes, valeur stock, taux rotation
- **Santé financière** : CA prévu vs réel, économies
- **Tendances** : Évolution des alertes sur 7 jours
- **Urgences** : Top 3 articles critiques

### Page 3 - Prédictions
- **Prédictions futures** : Tableau détaillé par article
- **Preuve de précision** : Comparaison prédit vs réel
- **Amélioration continue** : Apprentissage des événements

## 🔧 Configuration

### Variables d'environnement
```bash
# .env (optionnel)
OPTIFLOW_DB_PATH=optiflow.db
CACHE_DURATION_HOURS=24
BATCH_TIME=00:30
LOG_LEVEL=INFO
```

### Configuration cache
Le cache est configuré pour 24h selon les contraintes. Timestamp visible dans l'interface.

### Workflow batch
- **Heure d'exécution** : 00:30 (configurable)
- **Ordre des scripts** : Selon spécifications Page 1
- **Gestion d'erreurs** : Continue malgré les échecs
- **Logging complet** : batch_optiflow.log

## ⚡ Commandes utiles

```bash
# Lancer l'application
streamlit run src/main.py

# Batch nocturne complet
python scripts_ml/orchestrator.py

# Tests (si configurés)
pytest tests/

# Linting
ruff check src/
ruff format src/

# Vérifier la base de données
python -c "from src.utils.database import check_db_connection; print(check_db_connection())"

# Nettoyer le cache
python -c "from src.utils.cache import clear_cache; clear_cache()"

# Statistiques de la base
python -c "from src.utils.database import get_db_connection; print(get_db_connection().get_database_stats())"
```

## 📈 Formules clés

### Alertes
```
Critique: stock_actuel - ventes_prévues_délai < 0
Attention: stock_actuel - ventes_prévues_délai >= 0 ET < 3j_ventes
```

### Quantité suggérée
```
Quantité = (Σ prédictions_jusqu_date - stock_actuel) × (1 + marge_sécurité%)
```

### Taux de rotation
```
Taux = Ventes_30j / Stock_moyen_période
```

## 🚨 Contraintes critiques

### ⚠️ RESPECTER ABSOLUMENT
- **NE JAMAIS MODIFIER** la structure d'optiflow.db
- **Batch nocturne obligatoire** pour les prédictions
- **Cache 24h** avec timestamp visible utilisateur
- **Formules exactes** selon les spécifications
- **Workflow utilisateur** : 2 min/jour maximum

### Sécurité
- Pas de secrets dans le code
- Base de données en lecture seule (sauf nouvelles tables)
- Validation des inputs utilisateur
- Backup automatique avant modifications

## 📞 Support et développement

### Claude Code Commands
```bash
# Gestion des alertes
/alertes status
/alertes critique
/alertes calcul [article_id] [date] [marge]

# Dashboard
/dashboard kpis
/dashboard sante
/dashboard tendances

# Prédictions
/predictions generate [article_id] [jours]
/predictions accuracy
/predictions batch

# Machine Learning
/ml batch                    # Batch nocturne complet
/ml predict-sales [id]       # Script 1
/ml calc-alerts             # Script 2

# Base de données
/db schema
/db stats
/db backup
```

### Architecture decisions
- **Streamlit** : Interface simple et rapide
- **SQLite** : Base locale selon contraintes
- **Prophet** : ML pour séries temporelles
- **Cache local** : Performance et contraintes

## 📝 Licence

Projet MVP Optiflow - Usage interne

---

🎯 **Objectif** : Transformer la gestion des stocks avec l'IA tout en respectant les contraintes métier existantes.

📊 **Résultat attendu** : Précision 85% → 92% en 8 semaines avec workflow 2min/jour.