# Page 1 Optiflow

# SECTION 1 : ALERTES

## **Critique**

**Condition** : Le stock actuel ne peut pas couvrir les ventes prédites pendant le temps d'attente de la commande. 
**En pratique** : On additionne les prédictions de vente jour par jour jusqu'au jour où la commande arrivera. Si le total dépasse le stock actuel → CRITIQUE

 rupture inévitable → stock actuel - ventes prévues durant le délai de réapprovisionnement < 0 

**Calcul de la perte** :

- On identifie à partir de quel jour on sera en rupture
- On compte combien d'articles on aurait pu vendre d’après les prédictions pendant les jours de rupture
- On multiplie par le prix pour avoir la perte en argent

**Perte si commande aujourd’hui :** nombre de jour de rupture X nombre de ventes prédite pour les jours de rupture X prix de l’article

**Action recommandée** : "Commander immédiatement pour limiter les pertes"

**Suggestion de quantité :**  Quantité optimale basée sur les prédictions des 30 prochains jours = [nombre d’articles]

## **Attention**

**Condition** : Le stock actuel peut couvrir le délai de livraison si on commande maintenant, MAIS ne tiendra pas si on attend 3 jours de plus

**En pratique** :

- Si on commande aujourd'hui → pas de rupture
- Si on attend 3 jours pour commander → rupture avant l'arrivée de la nouvelle commande

Rupture évitable si commande avant 3j → stock actuel - vente prévues durant le délai de réapprovisionnement ≥ 3 jours de ventes

**Bénéfice si commande avant date recommandée** : délai de réapprovisionnement X nombre de ventes prévue par jour X prix de l’article  

**Action recommandée** : "Commander avant le [DATE]*”

**Suggestion de quantité :**  Quantité optimale basée sur les prédictions des 30 prochains jours = [nombre d’articles]

*[DATE] = stock actuel - vente prévues durant le délai de réapprovisionnement = 1 jours de ventes

## **OK** - Stock suffisant

**Condition** : On peut attendre au moins 3 jours avant de commander sans risquer de rupture

**En pratique** : Même en attendant 3 jours pour passer commande, le stock tiendra jusqu'à l'arrivée de la livraison

**Action recommandée** : "Prochaine commande entre le [DATE1]* et le [DATE2]*”

*[DATE1] = stock actuel - vente prévues durant le délai de réapprovisionnement = 3 jours de ventes

*[DATE2] = stock actuel - vente prévues durant le délai de réapprovisionnement = 1 jours de ventes

## **Calcul de quantité suggérée**

### **Configuration par l'utilisateur**

**Interface de calcul personnalisable :**

- **Date de couverture souhaitée** : Sélecteur de date (par défaut : 30 jours)
- **Marge de sécurité** : Menu déroulant de 0% à 50% (par défaut : 15%)

### **Formule de calcul**

```
Quantité suggérée = (Σ prédictions jusqu'à la date choisie - stock actuel) × (1 + marge de sécurité)
```

**Détail affiché à l'utilisateur :**

- Prédictions cumulées : [X] articles
- Stock actuel : -[Y] articles
- Besoin net : [X-Y] articles
- Marge de sécurité (+[%]) : +[Z] articles
- **Quantité finale recommandée : [TOTAL] articles**

### **Exemple de calcul**

- Date choisie : 30 septembre (21 jours)
- Prédictions sur 21 jours : 420 articles
- Stock actuel : 100 articles
- Besoin net : 320 articles
- Marge 15% : 48 articles
- **Quantité suggérée : 368 articles**

### **Notes importantes**

- Le calcul se base sur les **prédictions journalières spécifiques** (pas des moyennes)
- La marge permet de compenser l'incertitude des prédictions ML
- Recalcul automatique quand l'utilisateur modifie la date ou la marge
- Cette quantité est suggérée pour tous les statuts CRITIQUE et ATTENTION

# SECTION 2 : EVENEMENTS

- Liste des évènements connu sur les 30 prochains jours
- Historique d'impact
- Ajouter un évènement

# SECTION 3 : PERFOMANCES OPTIFLOW

- **Précisions IA** : MAPE moyen
- **Précision vérifier** :  correspondance entre prédiction et résultats réel

# SECTION 4 : SCRIPTS ML

## **Script 1 : predict_daily_[sales.py](http://sales.py)**

### **Objectif**

Générer des prédictions de ventes journalières pour chaque article sur une période donnée

### **Inputs**

- `article_id` : Identifiant de l'article
- `date_debut` : Date de début des prédictions
- `date_fin` : Date de fin des prédictions (max 30 jours)
- `events` : Liste des événements sur la période (optionnel)

### **Modèle utilisé**

- **Prophet** avec composantes :
    - Tendance historique
    - Saisonnalité hebdomadaire (pic samedi)
    - Saisonnalité mensuelle
    - Impact des événements spéciaux

### **Output**

```json
{
  "article_id": "123",
  "predictions": [
    {"date": "2025-09-10", "quantity": 15, "confidence": 0.92},
    {"date": "2025-09-11", "quantity": 18, "confidence": 0.91},
    {"date": "2025-09-12", "quantity": 25, "confidence": 0.85}
  ],
  "mape": 8.5
}
```

---

## **Script 2 : calculate_[alerts.py](http://alerts.py)**

### **Objectif**

Déterminer le statut d'alerte pour chaque article et calculer les impacts financiers

### **Inputs**

- `stock_actuel` : Quantité en stock
- `predictions` : Prédictions journalières (du script 1)
- `delai_reappro` : Délai de réapprovisionnement en jours
- `prix_unitaire` : Prix de vente de l'article

### **Logique de calcul**

1. **Calculer la demande pendant le délai** : Somme des prédictions J à J+délai
2. **Déterminer le statut** :
    - Si stock < demande_delai → CRITIQUE
    - Si stock < demande_delai+3j → ATTENTION
    - Sinon → OK
3. **Calculer l'impact financier** selon le statut

### **Output**

```json
{
  "status": "ATTENTION",
  "action": "Commander avant le 12/09/2025",
  "financial_impact": {
    "type": "benefice_si_commande",
    "amount": 45000,
    "details": "5 jours x 10 articles x 900 FCFA"
  },
  "dates": {
    "rupture_si_pas_commande": "2025-09-15",
    "commande_limite": "2025-09-12"
  }
}
```

---

## **Script 3 : suggest_[quantity.py](http://quantity.py)**

### **Objectif**

Calculer la quantité optimale à commander selon les besoins de l'utilisateur

### **Inputs**

- `predictions` : Prédictions journalières (du script 1)
- `stock_actuel` : Quantité en stock
- `date_cible` : Jusqu'à quelle date couvrir le stock
- `marge_securite` : Pourcentage de marge (0-50%)

### **Formule**

```python
besoin_net = sum(predictions[jusqu_a_date_cible]) - stock_actuel
quantite_suggeree = besoin_net * (1 + marge_securite/100)
```

### **Output**

```json
{
  "quantite_suggeree": 368,
  "details": {
    "predictions_cumulees": 420,
    "stock_actuel": 100,
    "besoin_net": 320,
    "marge_appliquee": 48,
    "couverture_jusqu_au": "2025-09-30"
  }
}
```

---

## **Script 4 : evaluate_events_[impact.py](http://impact.py)**

### **Objectif**

Evaluer l'impact des événements sur les prédictions de ventes

### **Inputs**

- `event_type` : Type d'événement (religieux, sportif, commercial...)
- `historical_data` : Données historiques des mêmes événements
- `article_category` : Catégorie de l'article

### **Logique**

1. Analyser l'impact historique de l'événement sur cette catégorie
2. Calculer le multiplicateur moyen (ex: Tabaski = x2.5 pour boissons)
3. Ajuster selon la tendance récente

### **Output**

```json
{
  "event": "Tabaski",
  "impact_multiplier": 2.5,
  "confidence": 0.85,
  "historical_impacts": [2.3, 2.6, 2.5],
  "affected_days": 3
}
```

---

## **Script 5 : monitor_ml_[performance.py](http://performance.py)**

### **Objectif**

Suivre et améliorer la performance des prédictions ML

### **Inputs**

- `predictions_passees` : Prédictions faites précédemment
- `ventes_reelles` : Ventes réellement réalisées
- `article_id` : Article à analyser

### **Calculs**

1. **MAPE** (Mean Absolute Percentage Error)
2. **Identification des patterns d'erreur** (sous/sur-estimation)
3. **Recommandations d'amélioration**

### **Output**

```json
{
  "mape_global": 8.5,
  "mape_par_jour": {
    "lundi": 7.2,
    "samedi": 12.1
  },
  "tendance_erreur": "sous_estimation_weekends",
  "recommendation": "Augmenter le poids de la saisonnalité hebdomadaire"
}
```

---

## **Notes d'implémentation**

### **Orchestration des scripts**

1. **Script 1** s'exécute en premier pour générer les prédictions
2. **Script 4** enrichit les prédictions avec l'impact des événements
3. **Script 2** utilise les prédictions pour calculer les alertes
4. **Script 3** calcule les quantités sur demande utilisateur
5. **Script 5** s'exécute périodiquement pour améliorer le système

### **Fréquence d'exécution**

- **Prédictions** : 1 fois par jour à minuit
- **Alertes** : Temps réel à chaque consultation
- **Performance** : 1 fois par semaine

### **Stack technique minimal :**

- **SQLite** : Base de données locale
- **Python** : Scripts ML + backend
- **Streamlit** : Interface web simple (ou Flask si tu préfères)
- **Prophet** : Prédictions
- **Pandas** : Manipulation des données