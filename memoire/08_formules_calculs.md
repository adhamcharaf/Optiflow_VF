# Formules et Calculs dans Optiflow

## 8.1 Introduction

Ce chapitre détaille l'ensemble des formules mathématiques et algorithmes de calcul utilisés dans Optiflow. Ces formules constituent le cœur logique du système et permettent la prise de décision automatisée en matière de gestion des stocks.

## 8.2 Calculs d'Alertes

### 8.2.1 Classification des Niveaux d'Alerte

#### Formule Générale

```
Niveau_Alerte = f(Stock_Actuel, Ventes_Prévues, Délai_Livraison)
```

#### Niveau CRITIQUE

**Condition** : Rupture inévitable dans le délai de livraison

```
SI (Stock_Actuel - Σ(Ventes_Prévues[J0 → J+Délai])) < 0
ALORS Alerte = CRITIQUE
```

**Exemple de calcul** :
- Stock actuel : 50 unités
- Délai livraison : 5 jours
- Ventes prévues J+1 à J+5 : [15, 12, 10, 8, 12] = 57 unités
- Résultat : 50 - 57 = -7 → **CRITIQUE**

#### Niveau ATTENTION

**Condition** : Rupture évitable si commande sous 3 jours

```
SI 0 ≤ (Stock_Actuel - Σ(Ventes_Prévues[J0 → J+Délai])) < Σ(Ventes_Prévues[J0 → J+3])
ALORS Alerte = ATTENTION
```

**Exemple de calcul** :
- Stock actuel : 50 unités
- Délai livraison : 5 jours
- Ventes prévues J+1 à J+5 : [10, 8, 7, 6, 5] = 36 unités
- Ventes prévues J+1 à J+3 : [10, 8, 7] = 25 unités
- Stock fin délai : 50 - 36 = 14
- Condition : 0 ≤ 14 < 25 → **ATTENTION**

#### Niveau OK

**Condition** : Stock suffisant

```
SI (Stock_Actuel - Σ(Ventes_Prévues[J0 → J+Délai])) ≥ Σ(Ventes_Prévues[J0 → J+3])
ALORS Alerte = OK
```

### 8.2.2 Calcul de l'Impact Financier

#### Perte Potentielle sur Rupture

```
Perte_Potentielle = Jours_Rupture × Ventes_Moyennes_Jour × Prix_Unitaire × Coefficient_Impact_Client
```

Où :
- **Jours_Rupture** = Nombre de jours sans stock
- **Ventes_Moyennes_Jour** = Moyenne des ventes sur 30 jours
- **Prix_Unitaire** = Prix de vente du produit
- **Coefficient_Impact_Client** = 1.2 (perte client + vente)

**Exemple** :
- Jours rupture estimés : 3
- Ventes moyennes/jour : 10 unités
- Prix unitaire : 25€
- Perte = 3 × 10 × 25 × 1.2 = **900€**

## 8.3 Calcul des Quantités Suggérées

### 8.3.1 Formule de Base

```
Quantité_Suggérée = (Besoins_Futurs - Stock_Actuel) × (1 + Marge_Sécurité)
```

Développée :

```
Q_suggérée = [Σ(Prédictions[J0 → J_cible]) - Stock_Actuel] × (1 + MS/100)
```

### 8.3.2 Calcul Détaillé avec Conditionnement

```python
def calculate_suggested_quantity(product_id, target_date, safety_margin_pct):
    # 1. Calcul des besoins bruts
    predictions_sum = sum(get_predictions(product_id, today, target_date))
    current_stock = get_current_stock(product_id)

    # 2. Besoin net
    net_requirement = predictions_sum - current_stock

    # 3. Application marge sécurité
    with_margin = net_requirement * (1 + safety_margin_pct/100)

    # 4. Arrondi au conditionnement
    packaging_unit = get_packaging_unit(product_id)
    final_quantity = ceil(with_margin / packaging_unit) * packaging_unit

    return final_quantity
```

**Exemple complet** :
- Prédictions 14 jours : 280 unités
- Stock actuel : 50 unités
- Besoin net : 280 - 50 = 230 unités
- Marge sécurité 20% : 230 × 1.2 = 276 unités
- Conditionnement par 25 : ⌈276/25⌉ × 25 = **300 unités**

### 8.3.3 Optimisation Multi-Contraintes

Pour optimiser une commande avec contraintes budget et stockage :

```
Minimiser : Σ(Prix_i × Quantité_i)

Sous contraintes :
- Σ(Prix_i × Quantité_i) ≤ Budget_Max
- Σ(Volume_i × Quantité_i) ≤ Capacité_Stockage
- Quantité_i ≥ Quantité_Min_i (sécurité)
- Quantité_i ≤ Quantité_Max_i (capacité)
```

## 8.4 Taux de Rotation des Stocks

### 8.4.1 Formule Standard

```
Taux_Rotation = Ventes_Période / Stock_Moyen_Période
```

### 8.4.2 Calcul sur 30 Jours

```
TR_30j = Σ(Ventes[J-29 → J0]) / ((Stock_Début + Stock_Fin) / 2)
```

**Interprétation** :
- TR > 12 : Rotation mensuelle excellente
- 6 < TR ≤ 12 : Bonne rotation
- 3 < TR ≤ 6 : Rotation moyenne
- TR ≤ 3 : Stock dormant

**Exemple** :
- Ventes 30j : 150 unités
- Stock début période : 20 unités
- Stock fin période : 10 unités
- Stock moyen : (20 + 10) / 2 = 15
- Taux rotation : 150 / 15 = **10** (Bonne rotation)

## 8.5 Métriques de Performance Machine Learning

### 8.5.1 MAPE (Mean Absolute Percentage Error)

#### Formule Standard

```
MAPE = (1/n) × Σ|((Réel_i - Prédit_i) / Réel_i)| × 100
```

#### Implémentation Python

```python
def calculate_mape(actual, predicted):
    # Éviter division par zéro
    mask = actual != 0

    mape = np.mean(
        np.abs((actual[mask] - predicted[mask]) / actual[mask])
    ) * 100

    return round(mape, 2)
```

### 8.5.2 MAPE Propre (Innovation Optiflow)

#### Concept

Exclut les anomalies validées comme exceptionnelles pour calculer la vraie performance du modèle.

```
MAPE_Propre = MAPE(Données - Anomalies_Exceptionnelles)
```

#### Formule Détaillée

```
MAPE_Propre = (1/m) × Σ|((Réel_j - Prédit_j) / Réel_j)| × 100
```

Où : j ∈ {Jours_Normaux} et m = |Jours_Normaux|

#### Calcul de l'Amélioration

```
Amélioration_% = ((MAPE_Standard - MAPE_Propre) / MAPE_Standard) × 100
```

**Exemple** :
- MAPE standard : 8.5%
- MAPE propre : 7.2%
- Amélioration : (8.5 - 7.2) / 8.5 × 100 = **15.3%**

### 8.5.3 RMSE (Root Mean Square Error)

```
RMSE = √((1/n) × Σ(Réel_i - Prédit_i)²)
```

Utilisé pour pénaliser davantage les grandes erreurs.

### 8.5.4 Coefficient de Détermination (R²)

```
R² = 1 - (Σ(Réel_i - Prédit_i)² / Σ(Réel_i - Moyenne_Réel)²)
```

Mesure la proportion de variance expliquée par le modèle.

## 8.6 Calculs Financiers

### 8.6.1 Valeur Totale du Stock

```
Valeur_Stock = Σ(Quantité_Produit_i × Prix_Unitaire_i)
```

### 8.6.2 Capital Immobilisé

```
Capital_Immobilisé = Valeur_Stock × (1 - Taux_Rotation/365)
```

### 8.6.3 Économies Réalisées

#### Par Évitement de Rupture

```
Économie_Rupture = Nb_Ruptures_Évitées × Perte_Moyenne_Rupture
```

#### Par Optimisation du Stock

```
Économie_Stock = (Stock_Moyen_Avant - Stock_Moyen_Après) × Prix_Moyen × Coût_Stockage_%
```

#### ROI du Système

```
ROI = (Économies_Totales - Coût_Système) / Coût_Système × 100
```

**Exemple de calcul ROI** :
- Économies ruptures : 15 000€/mois
- Économies stock : 3 000€/mois
- Coût système : 2 000€/mois
- ROI = (18 000 - 2 000) / 2 000 × 100 = **800%**

## 8.7 Détection d'Anomalies

### 8.7.1 Z-Score pour Outliers

```
Z_Score = (Valeur_Observée - Moyenne) / Écart_Type
```

**Seuil d'anomalie** : |Z_Score| > 2.5

### 8.7.2 Écart Relatif

```
Écart_% = ((Réel - Prédit) / Prédit) × 100
```

**Classification** :
- |Écart| > 100% : Promotion probable
- |Écart| > 50% : Anomalie significative
- |Écart| < 50% : Variation normale

### 8.7.3 Score de Confiance Anomalie

```
Score_Confiance = 1 - e^(-|Z_Score|/2)
```

Plus le score est proche de 1, plus l'anomalie est certaine.

## 8.8 Prédictions Prophet

### 8.8.1 Décomposition de la Série Temporelle

```
y(t) = g(t) + s(t) + h(t) + ε(t)
```

Où :
- **g(t)** : Tendance (linéaire ou logistique)
- **s(t)** : Saisonnalité (Fourier series)
- **h(t)** : Événements/Holidays
- **ε(t)** : Erreur résiduelle

### 8.8.2 Calcul de la Tendance

#### Croissance Linéaire

```
g(t) = (k + a(t)ᵀδ) × t + (m + a(t)ᵀγ)
```

#### Croissance Logistique

```
g(t) = C(t) / (1 + e^(-(k + a(t)ᵀδ)(t - (m + a(t)ᵀγ))))
```

### 8.8.3 Modélisation de la Saisonnalité

```
s(t) = Σ[aₙcos(2πnt/P) + bₙsin(2πnt/P)]
```

Où P est la période (365.25 pour annuelle, 7 pour hebdomadaire)

### 8.8.4 Impact des Événements

```
h(t) = Z(t)κ
```

Où :
- Z(t) : Matrice indicatrice d'événements
- κ : Vecteur des impacts d'événements

## 8.9 Algorithmes d'Optimisation

### 8.9.1 Niveau de Réapprovisionnement Optimal

```
Point_Commande = Demande_Moyenne_Délai + Stock_Sécurité
```

Où :

```
Stock_Sécurité = Z_α × σ_demande × √Délai_Livraison
```

- Z_α : Score Z pour niveau de service (1.65 pour 95%)
- σ_demande : Écart-type de la demande

### 8.9.2 Quantité Économique de Commande (EOQ)

```
EOQ = √((2 × Demande_Annuelle × Coût_Commande) / Coût_Stockage_Unitaire)
```

**Exemple** :
- Demande annuelle : 1200 unités
- Coût commande : 50€
- Coût stockage/unité/an : 5€
- EOQ = √((2 × 1200 × 50) / 5) = **155 unités**

## 8.10 Indicateurs Composites

### 8.10.1 Score de Criticité Produit

```
Score_Criticité = w₁×Impact_Financier + w₂×Fréquence_Rupture + w₃×Délai_Livraison_Normalisé
```

Avec w₁ + w₂ + w₃ = 1 (poids configurables)

### 8.10.2 Indice de Performance Globale

```
IPG = (Précision_Prédictions × 0.4) + (Taux_Service × 0.3) + (Rotation_Stock × 0.3)
```

Normalisation sur une échelle 0-100.

## 8.11 Validation et Limites

### 8.11.1 Intervalles de Confiance

Pour les prédictions Prophet :

```
IC_95% = Prédiction ± 1.96 × σ_prédiction
```

### 8.11.2 Seuils de Décision

| Métrique | Seuil Critique | Seuil Attention | Seuil OK |
|----------|----------------|-----------------|----------|
| MAPE | > 15% | 10-15% | < 10% |
| Stock/Ventes | < 3 jours | 3-7 jours | > 7 jours |
| Taux Rotation | < 3 | 3-6 | > 6 |
| Score Criticité | > 80 | 50-80 | < 50 |

## 8.12 Conclusion

Les formules et calculs présentés dans ce chapitre constituent le moteur décisionnel d'Optiflow. Leur combinaison permet une gestion optimisée des stocks basée sur des critères objectifs et mesurables, garantissant ainsi des décisions cohérentes et performantes.