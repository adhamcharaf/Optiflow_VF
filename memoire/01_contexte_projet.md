# Contexte et Présentation du Projet Optiflow

## 1.1 Introduction

Optiflow est un système de gestion intelligente des stocks développé comme projet de fin d'études. Il s'agit d'un MVP (Minimum Viable Product) conçu pour répondre aux défis critiques de la gestion des stocks dans le commerce de détail, en utilisant des techniques avancées de Machine Learning pour optimiser les approvisionnements et minimiser les ruptures de stock.

## 1.2 Problématique Adressée

### Contexte économique
Les entreprises de distribution font face à des défis majeurs dans la gestion de leurs stocks :
- **Ruptures de stock** : Perte de ventes et insatisfaction client
- **Sur-stockage** : Capital immobilisé et coûts de stockage élevés
- **Prévisions imprécises** : Difficulté à anticiper la demande future
- **Réactivité insuffisante** : Délais dans la détection des problèmes

### Impact financier
- Coût moyen d'une rupture de stock : perte directe de chiffre d'affaires
- Coût du sur-stockage : 15-30% de la valeur du stock par an
- Temps de gestion manuelle : 2-3 heures par jour pour un gestionnaire

## 1.3 Objectifs du Projet

### Objectif principal
Créer un système intelligent capable de prédire les ventes futures et d'optimiser automatiquement les commandes de réapprovisionnement, réduisant ainsi les ruptures de stock tout en minimisant le capital immobilisé.

### Objectifs spécifiques

#### 1. Prédiction précise des ventes
- Utilisation de modèles Prophet pour prévoir les ventes sur 30 jours
- Prise en compte des tendances, saisonnalités et événements
- Précision cible : MAPE < 10%

#### 2. Système d'alertes proactif
- Détection anticipée des ruptures potentielles
- Classification en 3 niveaux : Critique, Attention, OK
- Calcul automatique des pertes potentielles

#### 3. Optimisation des commandes
- Suggestions de quantités basées sur les prédictions
- Prise en compte des délais de livraison
- Intégration d'une marge de sécurité paramétrable

#### 4. Amélioration continue
- Apprentissage des anomalies et événements
- Ajustement automatique des modèles
- Feedback utilisateur pour affiner les prédictions

## 1.4 Périmètre Fonctionnel

### Fonctionnalités incluses dans le MVP

1. **Gestion des alertes stocks**
   - Monitoring en temps réel des niveaux de stock
   - Calcul automatique des alertes
   - Priorisation par criticité et impact financier

2. **Prédictions de ventes**
   - Modèles Prophet individuels par produit
   - Horizon de prédiction : 1 à 30 jours
   - Intervalles de confiance à 95%

3. **Dashboard analytique**
   - KPIs essentiels (valeur stock, taux rotation, alertes)
   - Visualisations interactives
   - Suivi des économies réalisées

4. **Système de commandes**
   - Génération de suggestions d'achat
   - Export PDF des bons de commande
   - Historique des commandes passées

5. **Amélioration du système**
   - Détection d'anomalies dans les ventes
   - Validation des événements exceptionnels
   - Calcul du MAPE propre (excluant anomalies)

### Limitations du MVP

1. **Base de données**
   - Limitée à SQLite (mono-utilisateur)
   - Pas de réplication ou sauvegarde automatique

2. **Scalabilité**
   - Conçu pour < 1000 produits
   - Batch nocturne unique
   - Pas de traitement distribué

3. **Intégrations**
   - Pas de connexion ERP
   - Import manuel des données
   - Export limité à PDF et CSV

## 1.5 Utilisateurs Cibles

### Profil principal : Gestionnaire de stock
- **Temps disponible** : 2-3 minutes le matin
- **Compétences** : Utilisation basique d'applications web
- **Besoins** : Décisions rapides et fiables

### Workflow utilisateur type

#### Matin (2 minutes)
1. Consultation du dashboard général
2. Revue des alertes critiques
3. Validation des commandes urgentes

#### Soir (optionnel, 1 minute)
1. Validation des anomalies détectées
2. Ajout d'événements futurs connus

### Bénéfices attendus
- **Gain de temps** : 90% de réduction du temps de gestion
- **Réduction des ruptures** : -70% en 8 semaines
- **Amélioration de la précision** : 85% → 92% en 2 mois
- **ROI** : Économies significatives dès le premier mois

## 1.6 Contexte Technique

### Environnement de développement
- **Langage** : Python 3.8+
- **Base de données** : SQLite avec 3 ans d'historique
- **Framework UI** : Streamlit
- **Machine Learning** : Prophet (Meta/Facebook)

### Données disponibles
- **Historique** : 3 ans de ventes quotidiennes
- **Produits** : Catalogue complet avec caractéristiques
- **Stock** : Niveaux temps réel
- **Événements** : Promotions, jours fériés, etc.

## 1.7 Innovation et Valeur Ajoutée

### Aspects innovants

1. **Intelligence adaptative**
   - Apprentissage continu des patterns de vente
   - Adaptation automatique aux changements

2. **Approche holistique**
   - Vision 360° du stock
   - Prise en compte multi-critères

3. **Simplicité d'usage**
   - Interface intuitive
   - Workflow optimisé (2 min/jour)

4. **Transparence**
   - Explications des recommandations
   - Traçabilité des décisions

### Valeur ajoutée mesurable
- **Économies directes** : Réduction des pertes sur rupture
- **Optimisation du BFR** : Diminution du stock dormant
- **Productivité** : Libération du temps gestionnaire
- **Satisfaction client** : Disponibilité produits améliorée

## 1.8 Conclusion

Optiflow représente une solution pragmatique et efficace aux défis de la gestion des stocks moderne. En combinant l'intelligence artificielle avec une interface utilisateur simplifiée, le système permet d'obtenir des résultats mesurables rapidement tout en s'améliorant continuellement grâce à l'apprentissage automatique.