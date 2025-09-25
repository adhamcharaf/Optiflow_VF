"""
Page Amélioration Système - Optiflow MVP
Système de validation des anomalies et calcul du MAPE propre
"""

import streamlit as st
import pandas as pd
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import plotly.graph_objects as go
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ajouter les chemins nécessaires
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent / "scripts_ml"))

# Import du détecteur d'anomalies Prophet
from scripts_ml.prophet_anomaly_detector import ProphetAnomalyDetector

# Configuration de la page
st.set_page_config(
    page_title="Optiflow - Amélioration Système",
    page_icon=":material/engineering:",
    layout="wide"
)

# Titre principal
st.title(":material/engineering: Amélioration du Système")
st.markdown("---")

# Initialiser le détecteur avec le BON chemin de DB
def get_detector():
    # Chemin absolu vers la DB depuis la page Streamlit
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'optiflow.db'))
    models_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'models'))

    # Debug : afficher les chemins
    logger.info(f"DB Path: {db_path}")
    logger.info(f"DB Exists: {os.path.exists(db_path)}")

    return ProphetAnomalyDetector(db_path=db_path, models_dir=models_path)

detector = get_detector()

# Section principale : Métriques MAPE
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    # Calculer le MAPE propre
    mape_stats = detector.calculate_clean_mape()

    # Afficher la métrique principale
    st.metric(
        label=":material/target: MAPE Propre",
        value=f"{mape_stats['clean_mape']}%",
        delta=f"-{mape_stats['improvement']}%" if mape_stats['improvement'] > 0 else None,
        help="Mesure de précision excluant les anomalies validées comme exceptionnelles"
    )

    # Description du MAPE
    st.caption("""
    :material/bar_chart: **MAPE (Mean Absolute Percentage Error)** : Mesure la précision moyenne
    des prédictions. Plus le % est bas, plus les prédictions sont précises.
    """)

with col2:
    if mape_stats['improvement_percent'] > 0:
        st.metric(
            label=":material/show_chart: Amélioration",
            value=f"+{mape_stats['improvement_percent']}%",
            delta="depuis dernière action",
            help="Amélioration du MAPE après exclusion des anomalies"
        )
    else:
        st.info("Validez des anomalies pour voir l'amélioration")

with col3:
    st.metric(
        label=":material/search: Anomalies exclues",
        value=mape_stats['anomalies_excluded'],
        help="Nombre d'anomalies marquées comme exceptionnelles"
    )

st.markdown("---")

# Section principale de détection
st.subheader(":material/refresh: Détection des Anomalies")

# Sous-section de validation
st.markdown("### :material/target: Anomalies à Valider")

# Récupérer les anomalies en attente
pending_anomalies = detector.get_pending_anomalies(limit=20)

if pending_anomalies:
    # Créer un DataFrame pour l'affichage
    df_anomalies = pd.DataFrame(pending_anomalies)

    # Formater les colonnes
    df_anomalies['deviation_percent'] = df_anomalies['deviation_percent'].round(1)
    df_anomalies['predicted_value'] = df_anomalies['predicted_value'].round(1)
    df_anomalies['actual_value'] = df_anomalies['actual_value'].round(1)

    # Convertir les dates et ajouter le jour de la semaine
    df_anomalies['detection_date'] = pd.to_datetime(df_anomalies['detection_date'])

    # Dictionnaire des jours en français
    jours_fr = {0: 'Lun', 1: 'Mar', 2: 'Mer', 3: 'Jeu', 4: 'Ven', 5: 'Sam', 6: 'Dim'}

    # Créer une colonne avec date + jour
    df_anomalies['Date_Jour'] = df_anomalies['detection_date'].apply(
        lambda x: f"{x.strftime('%Y-%m-%d')} ({jours_fr[x.weekday()]})"
    )

    # Ajouter une colonne d'écart visuel avec symboles Unicode
    df_anomalies['Écart'] = df_anomalies.apply(
        lambda x: f"{'▲' if x['anomaly_type'] == 'spike' else '▼'} {x['deviation_percent']}%",
        axis=1
    )

    # Gérer les sélections avec session_state
    if 'anomaly_selections' not in st.session_state:
        st.session_state.anomaly_selections = {}

    # Ajouter une colonne de sélection pour le tableau interactif
    df_anomalies['Sélection'] = False

    # Appliquer les sélections sauvegardées dans session_state
    for idx in df_anomalies.index:
        if idx in st.session_state.anomaly_selections:
            df_anomalies.loc[idx, 'Sélection'] = st.session_state.anomaly_selections[idx]

    # Colonnes à afficher
    display_columns = ['Date_Jour', 'product_name', 'predicted_value',
                      'actual_value', 'Écart', 'severity']

    # Renommer les colonnes pour l'affichage
    column_names = {
        'Date_Jour': 'Date',
        'product_name': 'Produit',
        'predicted_value': 'Prédit',
        'actual_value': 'Réel',
        'severity': 'Sévérité'
    }

    # Afficher le nombre d'anomalies
    st.info(f":material/bar_chart: {len(pending_anomalies)} anomalies en attente de validation")

    # Filtres de sévérité
    severity_filter = st.multiselect(
        "Filtrer par sévérité:",
        options=['low', 'medium', 'high', 'critical'],
        default=['high', 'critical']
    )

    # Appliquer le filtre
    if severity_filter:
        filtered_df = df_anomalies[df_anomalies['severity'].isin(severity_filter)].copy()
    else:
        filtered_df = df_anomalies.copy()

    # Boutons pour tout cocher/décocher
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("☑ Tout cocher", help="Cocher toutes les anomalies visibles"):
            # Cocher toutes les anomalies filtrées dans session_state
            for idx in filtered_df.index:
                st.session_state.anomaly_selections[idx] = True
            st.rerun()

    with col2:
        if st.button("☐ Tout décocher", help="Décocher toutes les anomalies"):
            # Vider les sélections
            st.session_state.anomaly_selections = {}
            st.rerun()

    # Colonnes à afficher dans l'ordre souhaité
    display_columns = ['Sélection', 'Date_Jour', 'product_name', 'predicted_value',
                      'actual_value', 'Écart', 'severity']

    # Configuration des colonnes pour st.data_editor
    column_config = {
        "Sélection": st.column_config.CheckboxColumn(
            "☑",
            help="Sélectionner pour action groupée",
            default=False,
        ),
        "Date_Jour": st.column_config.TextColumn(
            "Date",
            help="Date de détection de l'anomalie",
            disabled=True,
        ),
        "product_name": st.column_config.TextColumn(
            "Produit",
            disabled=True,
        ),
        "predicted_value": st.column_config.NumberColumn(
            "Prédit",
            format="%.1f",
            disabled=True,
        ),
        "actual_value": st.column_config.NumberColumn(
            "Réel",
            format="%.1f",
            disabled=True,
        ),
        "Écart": st.column_config.TextColumn(
            "Écart",
            disabled=True,
        ),
        "severity": st.column_config.TextColumn(
            "Sévérité",
            disabled=True,
        ),
    }

    # Afficher le tableau éditable
    edited_df = st.data_editor(
        filtered_df[display_columns],
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        key="anomalies_editor"
    )

    # Sauvegarder les changements dans session_state
    for idx, row in edited_df.iterrows():
        if row['Sélection']:
            st.session_state.anomaly_selections[idx] = True
        elif idx in st.session_state.anomaly_selections:
            del st.session_state.anomaly_selections[idx]

    # Compter les sélections
    selected_count = int(edited_df['Sélection'].sum())
    if selected_count > 0:
        st.caption(f"**{selected_count} anomalie(s) sélectionnée(s)** sur {len(filtered_df)} affichée(s)")

        # Actions sur la sélection
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button(":material/check_circle: Valider sélection", type="primary",
                        disabled=bool(selected_count == 0)):
                try:
                    count = 0
                    errors = 0
                    # Traiter uniquement les lignes sélectionnées
                    for idx, row in edited_df[edited_df['Sélection'] == True].iterrows():
                        try:
                            # Récupérer l'ID depuis le DataFrame original
                            anomaly_id = int(df_anomalies.loc[idx, 'id'])
                            if detector.update_anomaly_status(anomaly_id, 'validated'):
                                count += 1
                        except Exception as e:
                            errors += 1
                            logger.error(f"Erreur validation ID {anomaly_id}: {e}")

                    if count > 0:
                        st.success(f"{count} anomalie(s) validée(s)")
                    if errors > 0:
                        st.warning(f"{errors} erreur(s) rencontrée(s)")

                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur: {str(e)}")

        with col2:
            if st.button(":material/cancel: Ignorer sélection",
                        help="Marquer comme événements exceptionnels (exclus du MAPE)",
                        disabled=bool(selected_count == 0)):
                try:
                    count = 0
                    errors = 0
                    for idx, row in edited_df[edited_df['Sélection'] == True].iterrows():
                        try:
                            anomaly_id = int(df_anomalies.loc[idx, 'id'])
                            if detector.update_anomaly_status(anomaly_id, 'ignored'):
                                count += 1
                        except Exception as e:
                            errors += 1
                            logger.error(f"Erreur ignorance ID {anomaly_id}: {e}")

                    if count > 0:
                        st.success(f"{count} anomalie(s) ignorée(s)")
                    if errors > 0:
                        st.warning(f"{errors} erreur(s) rencontrée(s)")

                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur: {str(e)}")

        with col3:
            if st.button(":material/refresh: Marquer saisonnier",
                        help="Marquer comme patterns récurrents",
                        disabled=bool(selected_count == 0)):
                try:
                    count = 0
                    errors = 0
                    for idx, row in edited_df[edited_df['Sélection'] == True].iterrows():
                        try:
                            anomaly_id = int(df_anomalies.loc[idx, 'id'])
                            if detector.update_anomaly_status(anomaly_id, 'seasonal'):
                                count += 1
                        except Exception as e:
                            errors += 1
                            logger.error(f"Erreur saisonnier ID {anomaly_id}: {e}")

                    if count > 0:
                        st.success(f"{count} anomalie(s) marquée(s) saisonnière(s)")
                    if errors > 0:
                        st.warning(f"{errors} erreur(s) rencontrée(s)")

                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur: {str(e)}")

else:
    st.success(":material/check_circle: Aucune anomalie en attente de validation")
    st.info("""
    :material/lightbulb: **Pour détecter de nouvelles anomalies:**
    Cliquez sur le bouton "Détecter nouvelles (30j)" ci-dessous
    """)

# Bouton de détection placé avant l'historique
st.markdown("")
if st.button(":material/search: Détecter nouvelles (30j)",
             help="Détecte uniquement les nouvelles anomalies sans toucher aux validations",
             use_container_width=False):
    with st.spinner("Détection des nouvelles anomalies..."):
        # Période des 30 derniers jours
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        # Appeler la nouvelle méthode qui préserve les statuts
        result = detector.detect_new_anomalies_only(
            start_date=start_date,
            end_date=end_date
        )

        if result['success']:
            if result['new_anomalies'] > 0:
                st.success(f":material/check_circle: {result['new_anomalies']} nouvelles anomalies détectées")
            else:
                st.info("Aucune nouvelle anomalie détectée")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(f":material/error: Erreur : {result.get('error', 'Erreur inconnue')}")

st.markdown("")

# Section d'historique
with st.expander(":material/bar_chart: Historique des validations"):
    import sqlite3

    conn = sqlite3.connect("optiflow.db")

    # Récupérer l'historique des anomalies traitées
    query = """
    SELECT
        detection_date,
        p.name as product_name,
        predicted_value,
        actual_value,
        deviation_percent,
        anomaly_type,
        status,
        a.created_at
    FROM anomalies a
    JOIN products p ON a.product_id = p.id
    WHERE status != 'pending'
    ORDER BY a.created_at DESC
    LIMIT 50
    """

    df_history = pd.read_sql_query(query, conn)
    conn.close()

    if not df_history.empty:
        # Convertir les dates et ajouter le jour de la semaine
        df_history['detection_date'] = pd.to_datetime(df_history['detection_date'])

        # Dictionnaire des jours en français (même que ci-dessus)
        jours_fr = {0: 'Lun', 1: 'Mar', 2: 'Mer', 3: 'Jeu', 4: 'Ven', 5: 'Sam', 6: 'Dim'}

        # Créer une colonne avec date + jour
        df_history['Date_Jour'] = df_history['detection_date'].apply(
            lambda x: f"{x.strftime('%Y-%m-%d')} ({jours_fr[x.weekday()]})"
        )

        # Formater les colonnes
        df_history['deviation_percent'] = df_history['deviation_percent'].round(1)

        # Garder le status sans icônes dans le DataFrame
        st.dataframe(
            df_history[['Date_Jour', 'product_name', 'predicted_value',
                       'actual_value', 'deviation_percent', 'status']].rename(columns={
                           'Date_Jour': 'Date',
                           'status': 'Statut'
                       }),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Aucun historique de validation")

# Footer avec informations
st.markdown("---")

# Créer deux colonnes pour la légende et le bouton
col_legend, col_button = st.columns([3, 1])

with col_legend:
    st.caption("""
    **Légende des actions:**
    - :material/check_circle: **Valider** : L'anomalie est normale, la garder pour l'entraînement
    - :material/cancel: **Ignorer** : Événement exceptionnel, exclure du calcul MAPE
    - :material/refresh: **Saisonnier** : Pattern récurrent (Noël, soldes, etc.)
    """)

with col_button:
    # Initialiser l'état si nécessaire
    if 'show_detection_warning' not in st.session_state:
        st.session_state.show_detection_warning = False

    # Bouton dangereux placé en bas à droite
    if st.button(":material/refresh: Relancer détection complète",
                 type="secondary",
                 help="ATTENTION: Réinitialise TOUTES les validations",
                 key="bottom_full_detection"):
        st.session_state.show_detection_warning = True

    # Afficher le popup de confirmation si nécessaire
    if st.session_state.show_detection_warning:
        # Afficher l'avertissement
        st.warning("""
        :material/warning: **ATTENTION : Cette action va :**
        - Analyser tout l'historique (2022 → aujourd'hui)
        - **Réinitialiser TOUTES vos validations** (seasonal, ignored, validated)
        - Remettre toutes les anomalies en statut 'pending'

        **Toutes vos décisions précédentes seront perdues !**
        """)

        # Boutons de confirmation
        conf_col1, conf_col2 = st.columns(2)
        with conf_col1:
            if st.button(":material/check_circle: Confirmer", key="confirm_bottom_full_detection"):
                with st.spinner("Détection complète en cours... (cela peut prendre quelques minutes)"):
                    # Enregistrer le MAPE actuel comme référence
                    detector.track_improvement()

                    # Lancer la détection jusqu'à aujourd'hui
                    end_date = datetime.now().strftime("%Y-%m-%d")
                    result = detector.detect_historical_anomalies(
                        start_date="2022-01-01",
                        end_date=end_date
                    )

                    if result['success']:
                        st.success(f":material/check_circle: Détection complète terminée : {result['anomalies_detected']} anomalies trouvées")
                        st.session_state.show_detection_warning = False
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f":material/error: Erreur : {result.get('error', 'Erreur inconnue')}")
                        st.session_state.show_detection_warning = False

        with conf_col2:
            if st.button(":material/cancel: Annuler", key="cancel_bottom_full_detection"):
                st.session_state.show_detection_warning = False
                st.info("Détection annulée")
                st.rerun()