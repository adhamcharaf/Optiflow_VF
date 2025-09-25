# Guide d'Utilisation Optiflow

## 10.1 Installation et Configuration

### 10.1.1 Prérequis Système

#### Configuration Minimale

- **OS** : Windows 10/11, macOS 10.15+, Linux Ubuntu 20.04+
- **Python** : 3.8 ou supérieur
- **RAM** : 4 GB minimum
- **Disque** : 2 GB d'espace libre
- **Processeur** : Dual-core 2.0 GHz
- **Navigateur** : Chrome 90+, Firefox 88+, Safari 14+, Edge 90+

#### Configuration Recommandée

- **RAM** : 8 GB
- **Disque** : SSD avec 10 GB libre
- **Processeur** : Quad-core 2.5 GHz
- **Connexion** : Internet stable pour mises à jour

### 10.1.2 Installation

#### Étape 1 : Cloner le Repository

```bash
# Via Git
git clone https://github.com/entreprise/optiflow_mvp.git
cd optiflow_mvp

# Ou télécharger le ZIP et extraire
```

#### Étape 2 : Créer l'Environnement Python

```bash
# Créer environnement virtuel
python -m venv venv

# Activer environnement
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

#### Étape 3 : Installer les Dépendances

```bash
# Installation des packages
pip install -r requirements.txt

# Vérification installation
python -c "import streamlit; import prophet; print('Installation OK')"
```

#### Étape 4 : Vérifier la Base de Données

```bash
# Vérifier présence base de données
ls -la optiflow.db
# Devrait afficher ~10 MB

# Test connexion
python -c "import sqlite3; conn = sqlite3.connect('optiflow.db'); print('DB OK')"
```

### 10.1.3 Configuration Initiale

#### Configuration Streamlit

Créer le fichier `.streamlit/config.toml` :

```toml
[server]
port = 8501
address = "localhost"
headless = true

[browser]
serverAddress = "localhost"
serverPort = 8501
gatherUsageStats = false

[theme]
primaryColor = "#007bff"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f8f9fa"
textColor = "#262730"
```

#### Variables d'Environnement

Créer le fichier `.env` :

```bash
# Configuration Optiflow
OPTIFLOW_ENV=production
DATABASE_PATH=optiflow.db
MODELS_PATH=models/
LOG_LEVEL=INFO
CACHE_TTL=86400

# Paramètres ML
PROPHET_UNCERTAINTY_SAMPLES=1000
MAPE_THRESHOLD=15
ANOMALY_THRESHOLD=2.5

# Batch
BATCH_HOUR=0
BATCH_MINUTE=0
```

## 10.2 Démarrage de l'Application

### 10.2.1 Lancement Standard

```bash
# Démarrer Optiflow
streamlit run src/main.py

# Avec options
streamlit run src/main.py --server.port 8080 --server.address 0.0.0.0
```

### 10.2.2 Vérification du Démarrage

1. Attendre message : `You can now view your Streamlit app in your browser`
2. Ouvrir navigateur : http://localhost:8501
3. Vérifier chargement dashboard
4. Contrôler indicateurs sidebar

### 10.2.3 Mode Debug

```bash
# Lancement avec logs détaillés
streamlit run src/main.py --logger.level debug

# Monitoring logs
tail -f batch_optiflow.log
```

## 10.3 Workflow Utilisateur Quotidien

### 10.3.1 Routine Matinale (2 minutes)

#### 8h30 - Ouverture Dashboard

1. **Accéder à l'application**
   - URL : http://localhost:8501
   - Page par défaut : Dashboard

2. **Consulter les KPIs principaux**
   - Vérifier compteurs alertes (Rouge/Jaune/Vert)
   - Noter valeur stock totale
   - Observer taux de rotation

3. **Identifier les urgences**
   - Regarder section "Top 3 Urgences"
   - Noter les pertes potentielles

#### 8h31 - Traitement des Alertes

1. **Naviguer vers page Alertes**
   - Clic sur "Alertes" dans menu
   - Focus automatique sur critiques

2. **Analyser alertes critiques**
   ```
   Tableau affiché avec :
   - Produits en rouge = Action immédiate
   - Perte financière calculée
   - Quantité suggérée pré-remplie
   ```

3. **Sélectionner produits à commander**
   - Cocher cases des produits critiques
   - Vérifier quantités suggérées
   - Ajuster si nécessaire (rare)

#### 8h32 - Génération Commande

1. **Valider sélection**
   - Cliquer "Générer Commande"
   - Vérifier récapitulatif

2. **Télécharger PDF**
   - Clic sur "Télécharger PDF"
   - Fichier sauvé dans Downloads

3. **Envoyer fournisseur**
   - Email avec PDF attaché
   - Copie pour archivage

**✅ Fin routine : 8h32 (2 minutes)**

### 10.3.2 Actions Hebdomadaires

#### Lundi - Revue Performance

1. **Page Amélioration Système**
   - Consulter MAPE propre
   - Vérifier amélioration %

2. **Validation anomalies**
   - Réviser anomalies détectées
   - Valider événements exceptionnels
   - Marquer patterns récurrents

#### Mercredi - Analyse Tendances

1. **Page Dashboard**
   - Étudier graphique 7 jours
   - Identifier tendances émergentes

2. **Ajustements préventifs**
   - Anticiper pics d'activité
   - Planifier commandes futures

#### Vendredi - Planification

1. **Page Prédictions**
   - Sélectionner horizon 7 jours
   - Vérifier prédictions weekend
   - Ajuster stocks si nécessaire

## 10.4 Utilisation des Fonctionnalités

### 10.4.1 Page Dashboard

#### Lecture des KPIs

```
┌─────────────────┬─────────────────┬─────────────────┐
│   5 CRITIQUES   │  12 ATTENTION   │    233 OK       │
│     Rouge       │     Jaune       │     Vert        │
└─────────────────┴─────────────────┴─────────────────┘

Interprétation :
- Rouge = Action immédiate requise
- Jaune = Surveiller dans 48h
- Vert = Situation normale
```

#### Graphiques Interactifs

- **Zoom** : Clic + glisser sur zone
- **Reset** : Double-clic sur graphique
- **Export** : Icône appareil photo
- **Détails** : Survol pour tooltip

### 10.4.2 Page Alertes

#### Filtrage et Tri

1. **Filtrer par statut**
   ```python
   Sélecteur : [Tous] [Critique] [Attention] [OK]
   ```

2. **Trier colonnes**
   - Clic sur en-tête colonne
   - Flèche ↑ = Ascendant
   - Flèche ↓ = Descendant

#### Configuration Suggestions

```
╔══════════════════════════════════════╗
║  Configuration Quantité Suggérée     ║
╠══════════════════════════════════════╣
║  Date cible : [📅 Sélectionner]      ║
║  Marge sécurité : [====|====] 20%    ║
║  [✅ Calculer]                       ║
╚══════════════════════════════════════╝
```

**Paramètres** :
- Date cible : Jusqu'à quand couvrir
- Marge : Stock tampon (0-50%)

#### Actions Groupées

1. **Sélection multiple**
   - Case à cocher individuelle
   - "Sélectionner tout" en haut

2. **Actions disponibles**
   - Commander : Génère bon commande
   - Ignorer : Masque temporairement
   - Reporter : Décale à J+1

### 10.4.3 Page Prédictions

#### Sélection Produit et Période

```python
# Interface de sélection
Produit : [▼ Rechercher ou sélectionner]
Période : [1 jour ========|======== 30 jours]
Vue : (•) Graphique ( ) Tableau
```

#### Lecture du Graphique

```
      ↑
Ventes│     .-.     Légende:
      │    /   \    ── Prédiction
      │___/     \__ ░░ Intervalle 95%
      │░░░░░░░░░░░░ •• Ventes réelles
      │___|___|___→ -- Stock actuel
         J+1 J+7    Jours
```

#### Export Données

1. Format CSV : Données brutes
2. Format Excel : Mise en forme
3. Format PNG : Image graphique

### 10.4.4 Page Amélioration

#### Validation Anomalies

```
┌────────┬──────────┬────────┬─────────────┐
│  Date  │ Produit  │ Écart  │   Action    │
├────────┼──────────┼────────┼─────────────┤
│ 15/09  │ Prod A   │ +150%  │ [✓][✗][?]  │
└────────┴──────────┴────────┴─────────────┘

Boutons :
[✓] = Valider comme exceptionnel
[✗] = Ignorer (pattern normal)
[?] = Reporter décision
```

#### Déclenchement Réentraînement

```python
if MAPE > 15% or demande_utilisateur:
    [🔄 Réentraîner Modèles]
    # Lance réentraînement Prophet
    # Durée : ~30-45 minutes
    # Notification email à la fin
```

## 10.5 Administration Système

### 10.5.1 Batch Nocturne

#### Configuration Automatique

```bash
# Linux/macOS - Crontab
crontab -e
# Ajouter ligne :
0 0 * * * cd /opt/optiflow && python scripts_ml/orchestrator.py

# Windows - Planificateur de tâches
schtasks /create /tn "Optiflow Batch" /tr "python C:\optiflow\scripts_ml\orchestrator.py" /sc daily /st 00:00
```

#### Lancement Manuel

```bash
# Exécution immédiate
python scripts_ml/orchestrator.py

# Avec options
python scripts_ml/orchestrator.py --force --verbose
```

#### Monitoring Batch

```bash
# Suivre exécution temps réel
tail -f batch_optiflow.log

# Vérifier dernière exécution
grep "Batch terminé" batch_optiflow.log | tail -1
```

### 10.5.2 Maintenance Base de Données

#### Sauvegarde

```bash
# Backup quotidien
cp optiflow.db backups/optiflow_$(date +%Y%m%d).db

# Backup avant maintenance
sqlite3 optiflow.db ".backup backup_temp.db"
```

#### Optimisation

```bash
# Optimisation mensuelle
sqlite3 optiflow.db "VACUUM;"
sqlite3 optiflow.db "ANALYZE;"

# Vérifier intégrité
sqlite3 optiflow.db "PRAGMA integrity_check;"
```

#### Purge Données Anciennes

```sql
-- Purger prédictions > 90 jours
DELETE FROM forecasts WHERE created_at < date('now', '-90 days');

-- Archiver alertes résolues > 180 jours
INSERT INTO alerts_archive SELECT * FROM alerts
WHERE status = 'resolved' AND resolved_at < date('now', '-180 days');

DELETE FROM alerts
WHERE status = 'resolved' AND resolved_at < date('now', '-180 days');
```

### 10.5.3 Gestion des Modèles

#### Réentraînement Hebdomadaire

```bash
# Dimanche 2h du matin
python scripts_ml/training/train_models.py --all

# Produit spécifique
python scripts_ml/training/train_models.py --product_id 123
```

#### Validation Modèles

```bash
# Tester nouveaux modèles
python scripts_ml/training/validate_training.py

# Rollback si problème
cp models/backup/* models/
```

## 10.6 Résolution des Problèmes

### 10.6.1 Problèmes Courants

#### Application ne démarre pas

```bash
# Vérifier port
lsof -i :8501  # Linux/macOS
netstat -an | findstr :8501  # Windows

# Changer port si occupé
streamlit run src/main.py --server.port 8502
```

#### Erreur base de données

```bash
# Vérifier permissions
ls -la optiflow.db
chmod 664 optiflow.db  # Si nécessaire

# Réparer si corrompu
sqlite3 optiflow.db ".recover" | sqlite3 optiflow_recovered.db
```

#### Prédictions incorrectes

1. Vérifier données historiques
2. Valider anomalies récentes
3. Forcer réentraînement modèle
4. Contrôler logs pour erreurs

### 10.6.2 Messages d'Erreur

| Erreur | Cause | Solution |
|--------|-------|----------|
| "No module named 'prophet'" | Package manquant | `pip install prophet` |
| "Database is locked" | Accès concurrent | Fermer autres connexions |
| "MAPE > threshold" | Modèle dégradé | Réentraîner modèle |
| "Cache expired" | Cache obsolète | Relancer batch ou attendre |

### 10.6.3 Logs et Debug

```bash
# Localisation des logs
logs/
├── batch_optiflow.log      # Batch nocturne
├── training.log            # Entraînement ML
├── app.log                 # Application Streamlit
└── error.log              # Erreurs critiques

# Analyser erreurs
grep ERROR batch_optiflow.log | tail -20

# Mode debug complet
LOG_LEVEL=DEBUG streamlit run src/main.py
```

## 10.7 Optimisation Performances

### 10.7.1 Améliorer Temps de Réponse

```python
# Augmenter cache Streamlit
st.set_page_config(
    page_title="Optiflow",
    layout="wide",
    initial_sidebar_state="collapsed"  # Réduit chargement initial
)

# Cache agressif
@st.cache_data(ttl=3600, max_entries=1000)
def load_heavy_data():
    return fetch_from_db()
```

### 10.7.2 Réduire Utilisation Mémoire

```bash
# Limiter historique Prophet
export PROPHET_STAN_BACKEND=CMDSTANPY
export CMDSTAN_NUM_THREADS=2

# Purger cache régulièrement
find .cache -mtime +7 -delete
```

## 10.8 Intégrations Externes

### 10.8.1 Export Automatique

```python
# Configuration export journalier
EXPORT_CONFIG = {
    'format': 'csv',
    'destination': '/shared/exports/',
    'frequency': 'daily',
    'time': '06:00'
}
```

### 10.8.2 API REST (Future)

```python
# Endpoints prévus
GET  /api/alerts          # Liste alertes actives
GET  /api/predictions/{id} # Prédictions produit
POST /api/orders          # Créer commande
GET  /api/metrics         # Métriques système
```

## 10.9 Bonnes Pratiques

### 10.9.1 Usage Quotidien

✅ **À FAIRE** :
- Consulter chaque matin à heure fixe
- Valider anomalies hebdomadairement
- Sauvegarder PDFs commandes
- Vérifier logs après batch

❌ **À ÉVITER** :
- Modifier manuellement la BD
- Ignorer alertes critiques > 24h
- Réentraîner trop fréquemment
- Désactiver le batch nocturne

### 10.9.2 Maintenance Préventive

**Quotidien** :
- Vérifier exécution batch
- Contrôler espace disque

**Hebdomadaire** :
- Valider anomalies
- Backup base données
- Revue logs erreurs

**Mensuel** :
- Optimiser base données
- Purger données anciennes
- Analyser tendances performance

## 10.10 Support et Aide

### 10.10.1 Resources

- **Documentation** : `/doc/` dans le projet
- **Logs** : `/logs/` pour historique
- **Scripts** : `/scripts_ml/` pour automation

### 10.10.2 Contact Support

```
Support Technique Optiflow
Email : support@optiflow.com
Horaires : Lun-Ven 9h-18h
Délai réponse : < 24h

Urgences (rupture système) :
Hotline : +33 1 23 45 67 89
```

### 10.10.3 FAQ

**Q : Combien de temps pour voir les résultats ?**
R : Amélioration dès semaine 1, optimal après 4 semaines

**Q : Puis-je modifier les seuils d'alerte ?**
R : Oui, dans `.env` : ALERT_THRESHOLD_DAYS

**Q : Comment ajouter un nouvel utilisateur ?**
R : Version actuelle mono-utilisateur, multi-user prévu v2.0

**Q : Backup automatique possible ?**
R : Oui, via cron/scheduler système

## 10.11 Conclusion

Ce guide couvre l'ensemble des aspects d'utilisation d'Optiflow, de l'installation à l'usage quotidien. Le système est conçu pour être autonome après configuration initiale, ne nécessitant que 2 minutes d'attention quotidienne pour des résultats optimaux.