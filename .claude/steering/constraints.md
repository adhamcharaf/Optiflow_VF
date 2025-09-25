# Contraintes Optiflow MVP

## CONTRAINTES CRITIQUES - À RESPECTER ABSOLUMENT

### Base de données
- **INTERDICTION ABSOLUE** de modifier la structure d'optiflow.db
- **18 tables** avec 3 ans d'historique : structure intacte
- **Lecture seule** sauf pour les nouvelles tables (actions_alertes, historique_alertes, evenements_appris)
- **Backup obligatoire** avant toute intervention

### Workflow opérationnel
- **Batch nocturne obligatoire** : Génération des prédictions à 00:30
- **Cache 24h** : Toutes les données affichées avec timestamp de dernière mise à jour
- **Pas de calculs lourds en temps réel** : Utiliser les données pré-calculées
- **Timestamp visible** : L'utilisateur doit toujours savoir l'âge des données

### Interface utilisateur
- **Fidélité aux specs** : Respecter EXACTEMENT les formules et layouts des documents
- **Couleurs obligatoires** : 🔴 Rouge (Critique), 🟡 Jaune (Attention), 🟢 Vert (OK)
- **Formules exactes** : Pas d'approximation dans les calculs
- **Workflow 2 min/jour** : Interface rapide et intuitive

### Performance
- **Indexation requise** sur toutes les colonnes de dates
- **Requêtes asynchrones** pour l'interface Streamlit
- **Pas de calculs Prophet en temps réel** : Uniquement en batch
- **Cache intelligent** : Éviter les recalculs inutiles

## CONTRAINTES TECHNIQUES

### Stack imposée
```
Python 3.8+
Streamlit (interface web)
SQLite (base existante)
Prophet (ML predictions)
Pandas (manipulation données)
```

### Architecture
- **src/pages/** : 3 pages Streamlit uniquement
- **src/components/** : Composants réutilisables
- **src/utils/** : Base, cache, workflow
- **scripts_ml/** : 11 scripts organisés

### Sécurité
- **Pas de secrets** dans le code
- **Validation des inputs** utilisateur
- **Pas d'exécution SQL arbitraire**
- **Logs des actions critiques**

## CONTRAINTES FONCTIONNELLES

### Formules non négociables

#### Alertes
```python
# Statut CRITIQUE
stock_actuel - sum(ventes_prevues_delai) < 0

# Statut ATTENTION  
stock_actuel - sum(ventes_prevues_delai) >= 0 AND < 3_jours_ventes

# Quantité suggérée
(sum(predictions_jusqu_date) - stock_actuel) * (1 + marge_securite/100)
```

#### Taux de rotation
```python
taux_rotation = ventes_30j / stock_moyen_periode
```

#### Économies réalisées
```python
economies = jours_rupture_evites * ventes_predites_jour * prix_unitaire
```

### Workflow utilisateur imposé
1. **Matin (2 min max)** : Check alertes + commandes urgentes
2. **Soir (1 min, optionnel)** : Explication écarts prédiction
3. **Résultat** : Précision croissante (85% → 92% en 8 semaines)

## CONTRAINTES DE DÉVELOPPEMENT

### Tests obligatoires
- **Tests unitaires** pour tous les scripts ML
- **Tests d'intégration** pour le workflow batch
- **Validation des formules** avec données test
- **Tests de performance** pour les requêtes

### Documentation
- **Code documenté** avec docstrings
- **README.md** avec installation et usage
- **Architecture decision records** pour les choix techniques

### Maintenance
- **Code linting** avec ruff
- **Type hints** partout
- **Gestion d'erreurs** robuste
- **Logging** pour debugging

## CONTRAINTES D'EXPLOITATION

### Monitoring
- **Métriques de précision** ML suivies
- **Performance des requêtes** monitored
- **Taille de la base** surveillée
- **Erreurs batch** alertées

### Backup et récupération
- **Backup quotidien** automatique d'optiflow.db
- **Procédure de récupération** documentée
- **Tests de restauration** réguliers

### Évolutivité
- **Architecture modulaire** pour ajouts futurs
- **API potentielle** préparée
- **Migration** vers production facilitée

## POINTS DE CONTRÔLE

### Avant chaque développement
1. ✅ La spec exacte est-elle respectée ?
2. ✅ Le workflow batch est-il préservé ?
3. ✅ La base de données reste-t-elle intacte ?
4. ✅ Les performances sont-elles optimales ?

### Avant chaque commit
1. ✅ Tests unitaires passent
2. ✅ Linting OK
3. ✅ Documentation à jour
4. ✅ Pas de secrets exposés

### Avant chaque release
1. ✅ Tests d'intégration complets
2. ✅ Backup de sécurité créé
3. ✅ Performance validée
4. ✅ Documentation utilisateur OK