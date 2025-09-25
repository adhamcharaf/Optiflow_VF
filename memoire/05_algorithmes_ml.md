# Algorithmes de Machine Learning dans Optiflow

## 5.1 Introduction aux Modèles Prédictifs

Optiflow utilise Prophet, la librairie de prédiction de séries temporelles développée par Meta (Facebook), comme algorithme principal pour générer des prévisions de ventes. Ce choix s'appuie sur la capacité de Prophet à gérer automatiquement les tendances, saisonnalités et événements spéciaux tout en restant robuste face aux données manquantes.

## 5.2 Prophet : Cœur Prédictif du Système

### 5.2.1 Principe de Fonctionnement

Prophet décompose une série temporelle selon l'équation :

```
y(t) = g(t) + s(t) + h(t) + ε(t)
```

Où :
- **g(t)** : Tendance (croissance ou décroissance)
- **s(t)** : Saisonnalité (patterns périodiques)
- **h(t)** : Holidays/événements (impacts ponctuels)
- **ε(t)** : Terme d'erreur (bruit)

### 5.2.2 Configuration des Modèles

```python
class DailySalesPredictor:
    def _create_prophet_model(self, product_id):
        model = Prophet(
            daily_seasonality=True,    # Patterns journaliers
            weekly_seasonality=True,    # Patterns hebdomadaires
            yearly_seasonality=True,    # Patterns annuels
            holidays=self.holidays_df,  # Événements spéciaux
            seasonality_mode='multiplicative',  # Pour produits saisonniers
            changepoint_prior_scale=0.05,      # Sensibilité changements
            interval_width=0.95               # Intervalle confiance 95%
        )
        return model
```

### 5.2.3 Entraînement Individualisé

**Un modèle par produit** : Chaque produit a son propre modèle Prophet entraîné sur son historique spécifique.

```python
# Processus d'entraînement
def train_model(product_id, sales_history):
    # Préparation données format Prophet
    df = pd.DataFrame({
        'ds': sales_history['order_date'],
        'y': sales_history['quantity']
    })

    # Entraînement
    model = Prophet()
    model.fit(df)

    # Sauvegarde modèle
    with open(f'models/prophet_model_{product_id}.pkl', 'wb') as f:
        pickle.dump(model, f)
```

### 5.2.4 Gestion des Saisonnalités

**Saisonnalités Multiples Détectées** :

1. **Journalière** : Variations intra-journée (matin/soir)
2. **Hebdomadaire** : Pic weekend vs semaine
3. **Mensuelle** : Fin de mois (paies)
4. **Annuelle** : Saisons (été/hiver)

```python
# Ajout saisonnalité personnalisée
model.add_seasonality(
    name='monthly',
    period=30.5,
    fourier_order=5
)
```

## 5.3 Système de Calcul des Alertes

### 5.3.1 Algorithme de Classification

```python
class AlertCalculator:
    def calculate_alert(self, product_id, predictions):
        # 1. Récupération données
        stock_actuel = self.get_current_stock(product_id)
        lead_time = self.get_lead_time(product_id)

        # 2. Calcul ventes prévues pendant délai
        ventes_prevues_delai = sum([
            p['predicted_quantity']
            for p in predictions[:lead_time]
        ])

        # 3. Classification
        stock_fin_delai = stock_actuel - ventes_prevues_delai

        if stock_fin_delai < 0:
            return AlertStatus.CRITIQUE
        elif stock_fin_delai < self.get_3_days_sales(product_id):
            return AlertStatus.ATTENTION
        else:
            return AlertStatus.OK
```

### 5.3.2 Calcul de l'Impact Financier

```python
def calculate_potential_loss(product_id, rupture_days):
    """Calcule la perte potentielle en cas de rupture"""

    # Ventes moyennes journalières
    avg_daily_sales = self.get_average_sales(product_id)

    # Prix unitaire
    unit_price = self.get_unit_price(product_id)

    # Calcul perte
    potential_loss = rupture_days * avg_daily_sales * unit_price

    # Ajout coût client perdu (20% supplément)
    total_loss = potential_loss * 1.2

    return total_loss
```

### 5.3.3 Priorisation des Alertes

Algorithme de scoring multi-critères :

```python
def priority_score(alert):
    score = 0

    # Facteur sévérité
    if alert.severity == 'CRITIQUE':
        score += 100
    elif alert.severity == 'ATTENTION':
        score += 50

    # Facteur financier (normalisé 0-100)
    score += min(alert.potential_loss / 1000, 100)

    # Facteur rotation (produits fast-moving prioritaires)
    score += alert.rotation_rate * 10

    # Facteur délai (urgence temporelle)
    score += max(0, 50 - alert.days_to_rupture * 5)

    return score
```

## 5.4 Détection d'Anomalies

### 5.4.1 Algorithme Prophet pour Anomalies

```python
class ProphetAnomalyDetector:
    def detect_anomalies(self, product_id, threshold=2.5):
        """Détecte les anomalies via résidus Prophet"""

        # Prédictions vs réel
        forecast = self.model.predict(self.historical_data)

        # Calcul des résidus standardisés
        residuals = (actual - forecast.yhat) / forecast.yhat_std

        # Détection outliers (Z-score > threshold)
        anomalies = abs(residuals) > threshold

        return self.historical_data[anomalies]
```

### 5.4.2 Classification des Anomalies

```python
def classify_anomaly(anomaly_point):
    """Classifie le type d'anomalie détectée"""

    deviation = anomaly_point.deviation_percentage

    if deviation > 100:
        # Pic important = probable promotion
        return 'PROMOTION'
    elif deviation < -50:
        # Chute brutale = probable rupture
        return 'STOCKOUT'
    elif is_recurring(anomaly_point.date):
        # Pattern récurrent = saisonnalité
        return 'SEASONAL'
    else:
        # Autre = outlier simple
        return 'OUTLIER'
```

### 5.4.3 Apprentissage des Patterns

```python
def learn_from_validated_anomaly(anomaly):
    """Intègre une anomalie validée dans le modèle"""

    if anomaly.is_exceptional:
        # Ajout comme événement spécial
        new_holiday = pd.DataFrame({
            'holiday': anomaly.event_name,
            'ds': anomaly.date,
            'lower_window': -1,
            'upper_window': 1
        })

        # Mise à jour modèle
        self.holidays_df = pd.concat([
            self.holidays_df,
            new_holiday
        ])

        # Réentraînement nécessaire
        self.retrain_flag = True
```

## 5.5 Optimisation des Quantités

### 5.5.1 Algorithme de Suggestion

```python
class QuantitySuggester:
    def suggest_quantity(
        self,
        product_id,
        target_date,
        safety_margin=0.2
    ):
        """Calcule la quantité optimale à commander"""

        # 1. Prédictions jusqu'à date cible
        predictions = self.get_predictions_until(
            product_id,
            target_date
        )

        # 2. Somme des ventes prévues
        total_predicted = sum([
            p.predicted_quantity
            for p in predictions
        ])

        # 3. Stock actuel
        current_stock = self.get_current_stock(product_id)

        # 4. Calcul besoin net
        net_requirement = total_predicted - current_stock

        # 5. Application marge sécurité
        suggested = net_requirement * (1 + safety_margin)

        # 6. Arrondi au conditionnement
        packaging_unit = self.get_packaging_unit(product_id)
        final_quantity = ceil(suggested / packaging_unit) * packaging_unit

        return final_quantity
```

### 5.5.2 Optimisation Multi-Objectifs

```python
def optimize_order(products_list, constraints):
    """Optimise une commande multi-produits"""

    from scipy.optimize import linprog

    # Fonction objectif : minimiser coût total
    costs = [p.unit_price * p.suggested_qty for p in products_list]

    # Contraintes
    # 1. Budget maximum
    A_budget = [p.unit_price for p in products_list]
    b_budget = constraints.max_budget

    # 2. Capacité stockage
    A_storage = [p.volume for p in products_list]
    b_storage = constraints.max_storage

    # 3. Quantités minimales (sécurité)
    bounds = [(p.min_qty, p.max_qty) for p in products_list]

    # Résolution
    result = linprog(
        c=costs,
        A_ub=[A_budget, A_storage],
        b_ub=[b_budget, b_storage],
        bounds=bounds,
        method='highs'
    )

    return result.x  # Quantités optimales
```

## 5.6 Calcul du MAPE et Métriques

### 5.6.1 MAPE Standard

```python
def calculate_mape(actual, predicted):
    """Mean Absolute Percentage Error"""

    # Éviter division par zéro
    mask = actual != 0

    # Calcul MAPE
    mape = np.mean(
        np.abs((actual[mask] - predicted[mask]) / actual[mask])
    ) * 100

    return round(mape, 2)
```

### 5.6.2 MAPE Propre (Innovation)

```python
def calculate_clean_mape(self):
    """MAPE excluant les anomalies validées"""

    # Récupération données
    all_data = self.get_predictions_with_actuals()

    # Exclusion anomalies exceptionnelles
    exceptional_dates = self.get_exceptional_anomalies()
    clean_data = all_data[~all_data.date.isin(exceptional_dates)]

    # Calcul MAPE propre
    clean_mape = calculate_mape(
        clean_data.actual,
        clean_data.predicted
    )

    # Calcul amélioration
    standard_mape = calculate_mape(all_data.actual, all_data.predicted)
    improvement = standard_mape - clean_mape

    return {
        'clean_mape': clean_mape,
        'standard_mape': standard_mape,
        'improvement': improvement,
        'improvement_percent': (improvement/standard_mape)*100
    }
```

### 5.6.3 Autres Métriques de Performance

```python
def calculate_metrics_suite(actual, predicted):
    """Ensemble complet de métriques"""

    metrics = {
        'mape': calculate_mape(actual, predicted),
        'rmse': np.sqrt(mean_squared_error(actual, predicted)),
        'mae': mean_absolute_error(actual, predicted),
        'r2': r2_score(actual, predicted),
        'accuracy_threshold': np.mean(
            np.abs((actual - predicted) / actual) < 0.1
        ) * 100  # % prédictions < 10% erreur
    }

    return metrics
```

## 5.7 Apprentissage Continu

### 5.7.1 Feedback Loop

```python
class LearningSystem:
    def integrate_feedback(self, feedback):
        """Intègre le feedback utilisateur"""

        if feedback.type == 'WRONG_PREDICTION':
            # Ajustement des hyperparamètres
            self.adjust_changepoint_prior_scale(
                feedback.product_id,
                direction='increase'  # Plus sensible
            )

        elif feedback.type == 'EVENT_MISSED':
            # Ajout événement manqué
            self.add_holiday_event(
                date=feedback.date,
                impact=feedback.estimated_impact
            )

        elif feedback.type == 'PATTERN_CHANGE':
            # Réentraînement complet
            self.schedule_full_retrain(feedback.product_id)
```

### 5.7.2 Auto-Tuning des Hyperparamètres

```python
def auto_tune_prophet(product_id, param_grid):
    """Optimisation bayésienne des hyperparamètres"""

    from skopt import BayesSearchCV

    # Grille de recherche
    param_distributions = {
        'changepoint_prior_scale': (0.001, 0.5, 'log-uniform'),
        'seasonality_prior_scale': (0.01, 10, 'log-uniform'),
        'holidays_prior_scale': (0.01, 10, 'log-uniform'),
        'seasonality_mode': ['additive', 'multiplicative']
    }

    # Cross-validation temporelle
    tscv = TimeSeriesSplit(n_splits=3)

    # Recherche bayésienne
    search = BayesSearchCV(
        ProphetWrapper(),
        param_distributions,
        cv=tscv,
        n_iter=30,
        scoring='neg_mean_absolute_percentage_error'
    )

    # Entraînement
    search.fit(train_data)

    return search.best_params_
```

## 5.8 Gestion des Événements Spéciaux

### 5.8.1 Modélisation des Impacts

```python
def model_event_impact(event_type, historical_impacts):
    """Modélise l'impact d'un type d'événement"""

    if event_type == 'PROMOTION':
        # Distribution log-normale pour promotions
        impact = np.random.lognormal(
            mean=np.log(1.5),  # +50% en moyenne
            sigma=0.3
        )

    elif event_type == 'HOLIDAY':
        # Impact basé sur historique
        impact = np.mean(historical_impacts) * 1.1

    elif event_type == 'WEATHER':
        # Modèle polynomial pour météo
        impact = weather_polynomial(
            temperature,
            precipitation
        )

    return impact
```

### 5.8.2 Propagation des Effets

```python
def propagate_event_effects(event, affected_products):
    """Propage l'effet d'un événement sur plusieurs produits"""

    # Matrice de corrélation produits
    correlation_matrix = calculate_product_correlations()

    for product in affected_products:
        # Impact direct
        direct_impact = event.base_impact

        # Impacts indirects (produits liés)
        for other_product in all_products:
            if other_product != product:
                correlation = correlation_matrix[product][other_product]
                indirect_impact = direct_impact * correlation * 0.5

                apply_impact(other_product, indirect_impact)
```

## 5.9 Optimisations et Performance

### 5.9.1 Parallélisation des Calculs

```python
def parallel_train_all_models():
    """Entraînement parallèle de tous les modèles"""

    from multiprocessing import Pool

    with Pool(processes=4) as pool:
        results = pool.map(
            train_single_model,
            product_ids
        )

    return results
```

### 5.9.2 Cache Intelligent

```python
class PredictionCache:
    def __init__(self, ttl=86400):  # 24h
        self.cache = {}
        self.ttl = ttl

    def get_or_compute(self, key, compute_func):
        """Pattern cache-aside"""

        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['timestamp'] < self.ttl:
                return entry['value']

        # Calcul si absent ou expiré
        value = compute_func()

        self.cache[key] = {
            'value': value,
            'timestamp': time.time()
        }

        return value
```

## 5.10 Conclusion

Les algorithmes de Machine Learning implémentés dans Optiflow combinent robustesse et sophistication. L'utilisation de Prophet comme base, enrichie par des algorithmes de détection d'anomalies et d'optimisation, permet d'atteindre une précision élevée (MAPE < 10%) tout en s'améliorant continuellement grâce aux mécanismes d'apprentissage intégrés.