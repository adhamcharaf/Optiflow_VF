# Scripts d'Automatisation et Orchestration

## 6.1 Vue d'Ensemble de l'Automatisation

L'automatisation dans Optiflow repose sur un ensemble de scripts Python orchestrés pour s'exécuter de manière coordonnée. Le système utilise un orchestrateur principal qui gère l'exécution séquentielle et parallèle des différents scripts selon un workflow défini.

## 6.2 Orchestrateur Principal

### 6.2.1 Architecture de l'Orchestrateur

```python
class OptiflowOrchestrator:
    """Orchestrateur principal des scripts ML Optiflow"""

    def __init__(self):
        self.base_dir = Path(__file__).parent

        # Ordre d'exécution défini selon les dépendances
        self.execution_sequence = [
            # Phase 1: Prédictions
            "Page_alertes/predict_daily_sales.py",

            # Phase 2: Enrichissement
            "Page_alertes/evaluate_events_impact.py",

            # Phase 3: Alertes
            "Page_alertes/calculate_alerts.py",

            # Phase 4: Monitoring
            "Page_alertes/monitor_ml_performance.py",

            # Phase 5: Dashboard KPIs
            "page2_dashboard/aggregate_dashboard_kpis.py",
            "page2_dashboard/track_savings.py",
            "page2_dashboard/compare_ca_predictions.py",
            "page2_dashboard/calculate_trends.py",
            "page2_dashboard/get_top_urgent.py",
            "page2_dashboard/get_stock_dormant.py"
        ]
```

### 6.2.2 Exécution du Batch Nocturne

```python
async def run_batch_nocturne(self):
    """Exécute le batch nocturne complet à minuit"""

    logger.info("Début du batch nocturne Optiflow")
    start_time = datetime.now()

    results = {}

    # Phase 1: Scripts séquentiels (dépendances)
    for script in self.execution_sequence[:4]:
        result = await self._run_script(script)
        results[script] = result

        if not result['success']:
            logger.error(f"Échec {script}, arrêt batch")
            return False

    # Phase 2: Scripts parallèles (indépendants)
    parallel_scripts = self.execution_sequence[4:]
    parallel_results = await asyncio.gather(*[
        self._run_script(script) for script in parallel_scripts
    ])

    # Mise à jour cache global
    await self._update_global_cache()

    duration = (datetime.now() - start_time).total_seconds()
    logger.info(f"Batch terminé en {duration}s")

    return True
```

## 6.3 Scripts de la Page Alertes

### 6.3.1 Script 1 : predict_daily_sales.py

**Fonction** : Génère les prédictions de ventes pour tous les produits

```python
class DailySalesPredictor:
    def run_batch_predictions(self):
        """Génère prédictions pour tous les produits"""

        products = self.get_all_products()
        predictions_count = 0

        for product in products:
            try:
                # Chargement modèle Prophet
                model = self._load_model(product.id)

                if model:
                    # Génération prédictions 30 jours
                    future = model.make_future_dataframe(periods=30)
                    forecast = model.predict(future)

                    # Sauvegarde en base
                    self._save_predictions(product.id, forecast)
                    predictions_count += len(forecast)

            except Exception as e:
                logger.error(f"Erreur produit {product.id}: {e}")

        logger.info(f"{predictions_count} prédictions générées")
        return predictions_count
```

**Fréquence** : Quotidienne (minuit)
**Durée moyenne** : 3-5 minutes pour 250 produits
**Output** : Table `forecasts` mise à jour

### 6.3.2 Script 2 : calculate_alerts.py

**Fonction** : Calcule et classifie les alertes stocks

```python
class AlertCalculator:
    def run_batch_alerts(self):
        """Calcule toutes les alertes du système"""

        # Désactivation anciennes alertes
        self.deactivate_old_alerts()

        alerts_created = []

        for product_id in self.get_active_products():
            # Récupération prédictions
            predictions = self.get_predictions(product_id)

            # Calcul alerte
            alert = self.calculate_alert(product_id, predictions)

            if alert.severity in ['CRITIQUE', 'ATTENTION']:
                # Création alerte en base
                alert_id = self.create_alert(alert)
                alerts_created.append(alert_id)

                # Notification si critique
                if alert.severity == 'CRITIQUE':
                    self.send_notification(alert)

        logger.info(f"{len(alerts_created)} alertes créées")
        return alerts_created
```

**Dépendance** : Script 1 (prédictions)
**Fréquence** : Quotidienne après prédictions
**Durée** : 1-2 minutes

### 6.3.3 Script 3 : suggest_quantity.py

**Fonction** : Calcule les quantités optimales à commander

```python
class QuantitySuggester:
    def calculate_suggestion(self, product_id, params):
        """Calcul à la demande (pas batch)"""

        # Récupération paramètres utilisateur
        target_date = params['target_date']
        safety_margin = params['safety_margin']

        # Calcul suggestion
        suggestion = self.suggest_quantity(
            product_id,
            target_date,
            safety_margin
        )

        # Enrichissement avec données fournisseur
        suggestion['supplier_info'] = self.get_supplier_info(product_id)
        suggestion['best_price'] = self.calculate_best_price(suggestion['quantity'])

        return suggestion
```

**Exécution** : À la demande utilisateur (temps réel)
**Durée** : < 500ms par produit

### 6.3.4 Script 4 : monitor_ml_performance.py

**Fonction** : Calcule les métriques de performance ML

```python
class MLPerformanceMonitor:
    def run_performance_check(self):
        """Évalue la performance des modèles"""

        metrics = {}

        for product_id in self.get_products_with_predictions():
            # Comparaison prédit vs réel
            comparison = self.compare_predictions_to_actuals(
                product_id,
                lookback_days=7
            )

            # Calcul métriques
            metrics[product_id] = {
                'mape': self.calculate_mape(comparison),
                'rmse': self.calculate_rmse(comparison),
                'bias': self.calculate_bias(comparison)
            }

            # Alerte si dégradation
            if metrics[product_id]['mape'] > 15:
                self.flag_for_retraining(product_id)

        # Agrégation globale
        global_metrics = self.aggregate_metrics(metrics)
        self.save_metrics_history(global_metrics)

        return global_metrics
```

**Fréquence** : Quotidienne
**Output** : Métriques de performance, flags réentraînement

## 6.4 Scripts du Dashboard

### 6.4.1 Script 6 : aggregate_dashboard_kpis.py

```python
def aggregate_kpis():
    """Agrège tous les KPIs du dashboard"""

    kpis = {
        'alerts_count': count_active_alerts_by_severity(),
        'stock_value': calculate_total_stock_value(),
        'rotation_rate': calculate_average_rotation_rate(),
        'critical_products': get_critical_products_count(),
        'savings_mtd': calculate_month_to_date_savings()
    }

    # Cache pour performance
    save_to_cache('dashboard_kpis', kpis, ttl=86400)

    return kpis
```

### 6.4.2 Script 7 : track_savings.py

```python
def track_savings():
    """Calcule les économies réalisées"""

    savings = {
        'avoided_stockouts': calculate_avoided_stockout_losses(),
        'reduced_overstock': calculate_overstock_reduction(),
        'optimized_orders': calculate_order_optimization_gains()
    }

    # Historisation
    save_savings_history(savings)

    return savings
```

### 6.4.3 Script 8 : compare_ca_predictions.py

```python
def compare_revenue_predictions():
    """Compare CA prévu vs réel"""

    comparison = []

    for day in get_last_30_days():
        predicted_ca = get_predicted_revenue(day)
        actual_ca = get_actual_revenue(day)

        comparison.append({
            'date': day,
            'predicted': predicted_ca,
            'actual': actual_ca,
            'variance': (actual_ca - predicted_ca) / predicted_ca * 100
        })

    return pd.DataFrame(comparison)
```

## 6.5 Scripts d'Entraînement

### 6.5.1 train_models.py

```python
class ModelTrainer:
    def train_all_models(self, force=False):
        """Entraîne tous les modèles Prophet"""

        trained_count = 0

        for product_id in self.get_products():
            # Vérification besoin réentraînement
            if force or self.needs_retraining(product_id):
                # Préparation données
                train_data = self.prepare_training_data(product_id)

                # Entraînement
                model = self.train_prophet_model(train_data)

                # Validation
                metrics = self.validate_model(model, product_id)

                if metrics['mape'] < 15:  # Seuil qualité
                    # Sauvegarde modèle
                    self.save_model(model, product_id)
                    trained_count += 1
                else:
                    logger.warning(f"Modèle {product_id} rejeté (MAPE={metrics['mape']})")

        return trained_count
```

**Fréquence** : Hebdomadaire (dimanche 2h)
**Durée** : 30-45 minutes pour tous les produits

### 6.5.2 validate_training.py

```python
def validate_training_results():
    """Valide la qualité des modèles entraînés"""

    validation_results = []

    for model_file in get_new_models():
        # Test sur données récentes
        test_metrics = test_model_on_recent_data(model_file)

        # Comparaison avec ancien modèle
        improvement = compare_with_previous_version(model_file)

        validation_results.append({
            'model': model_file,
            'mape': test_metrics['mape'],
            'improvement': improvement,
            'status': 'approved' if test_metrics['mape'] < 10 else 'rejected'
        })

    return validation_results
```

## 6.6 Gestion des Erreurs et Recovery

### 6.6.1 Mécanisme de Retry

```python
async def _run_script_with_retry(self, script_path, max_retries=3):
    """Exécute un script avec retry automatique"""

    for attempt in range(max_retries):
        try:
            result = await self._run_script(script_path)

            if result['success']:
                return result

            logger.warning(f"Tentative {attempt + 1} échouée pour {script_path}")

        except Exception as e:
            logger.error(f"Exception tentative {attempt + 1}: {e}")

        # Backoff exponentiel
        await asyncio.sleep(2 ** attempt)

    # Échec après tous les essais
    return {'success': False, 'error': 'Max retries exceeded'}
```

### 6.6.2 Checkpointing

```python
class BatchCheckpoint:
    """Système de checkpoint pour reprendre après échec"""

    def save_checkpoint(self, step, data):
        checkpoint = {
            'step': step,
            'timestamp': datetime.now(),
            'data': data
        }

        with open('batch_checkpoint.json', 'w') as f:
            json.dump(checkpoint, f)

    def resume_from_checkpoint(self):
        if os.path.exists('batch_checkpoint.json'):
            with open('batch_checkpoint.json', 'r') as f:
                checkpoint = json.load(f)

            logger.info(f"Reprise depuis étape {checkpoint['step']}")
            return checkpoint

        return None
```

## 6.7 Monitoring et Alerting

### 6.7.1 Système de Logs

```python
# Configuration centralisée des logs
logging.config.dictConfig({
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'batch_optiflow.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'detailed'
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        }
    },
    'formatters': {
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'simple': {
            'format': '%(levelname)s - %(message)s'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file', 'console']
    }
})
```

### 6.7.2 Métriques de Performance

```python
class BatchMetrics:
    """Collecte métriques d'exécution batch"""

    def collect_metrics(self, batch_result):
        metrics = {
            'duration_seconds': batch_result['duration'],
            'scripts_executed': len(batch_result['scripts']),
            'scripts_failed': len([s for s in batch_result['scripts'] if not s['success']]),
            'predictions_generated': batch_result['predictions_count'],
            'alerts_created': batch_result['alerts_count'],
            'memory_peak_mb': batch_result['memory_peak'] / 1024 / 1024
        }

        # Envoi vers système monitoring (optionnel)
        self.send_to_monitoring(metrics)

        # Sauvegarde locale
        self.save_metrics_history(metrics)

        return metrics
```

## 6.8 Planification et Scheduling

### 6.8.1 Configuration Crontab

```bash
# Batch nocturne principal - tous les jours à minuit
0 0 * * * cd /opt/optiflow && python scripts_ml/orchestrator.py >> logs/batch.log 2>&1

# Réentraînement hebdomadaire - dimanche 2h
0 2 * * 0 cd /opt/optiflow && python scripts_ml/training/train_models.py >> logs/training.log 2>&1

# Nettoyage mensuel - 1er du mois 3h
0 3 1 * * cd /opt/optiflow && python scripts_ml/maintenance/cleanup.py >> logs/cleanup.log 2>&1

# Health check - toutes les heures
0 * * * * cd /opt/optiflow && python scripts_ml/monitoring/health_check.py
```

### 6.8.2 Gestion des Dépendances

```python
class DependencyManager:
    """Gère les dépendances entre scripts"""

    dependencies = {
        'calculate_alerts.py': ['predict_daily_sales.py'],
        'track_savings.py': ['calculate_alerts.py'],
        'compare_ca_predictions.py': ['predict_daily_sales.py']
    }

    def can_run(self, script):
        """Vérifie si un script peut s'exécuter"""

        if script not in self.dependencies:
            return True

        for dependency in self.dependencies[script]:
            if not self.is_completed(dependency):
                return False

        return True

    def get_execution_order(self):
        """Calcule l'ordre optimal d'exécution"""
        # Algorithme de tri topologique
        return topological_sort(self.dependencies)
```

## 6.9 Optimisations de Performance

### 6.9.1 Parallélisation

```python
async def run_parallel_scripts(scripts):
    """Exécute plusieurs scripts en parallèle"""

    # Limitation concurrence
    semaphore = asyncio.Semaphore(4)  # Max 4 scripts simultanés

    async def run_with_semaphore(script):
        async with semaphore:
            return await run_script(script)

    # Exécution parallèle
    results = await asyncio.gather(*[
        run_with_semaphore(script) for script in scripts
    ])

    return results
```

### 6.9.2 Cache Warming

```python
def warm_cache_after_batch():
    """Précharge le cache avec données fréquentes"""

    # Dashboard KPIs
    cache.set('dashboard_kpis', calculate_dashboard_kpis(), ttl=86400)

    # Top alertes
    cache.set('top_alerts', get_top_alerts(limit=10), ttl=86400)

    # Prédictions jour courant
    for product_id in get_high_rotation_products():
        cache.set(
            f'prediction_{product_id}_today',
            get_today_prediction(product_id),
            ttl=86400
        )

    logger.info("Cache préchauffé avec succès")
```

## 6.10 Conclusion

Le système d'automatisation d'Optiflow assure une exécution fiable et performante des processus de Machine Learning et de calcul des métriques. L'architecture modulaire permet une maintenance aisée et une évolution progressive, tandis que les mécanismes de recovery garantissent la continuité de service même en cas d'erreur.