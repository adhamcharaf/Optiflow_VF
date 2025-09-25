"""
Page 1 - Alertes et Gestion des Stocks
Navigation native Streamlit
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
import sqlite3
import plotly.graph_objects as go
import plotly.express as px

# Configuration de la page
st.set_page_config(
    page_title="Optiflow - Alertes",
    page_icon="📦",
    layout="wide"
)

# Ajouter les chemins nécessaires
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent / "scripts_ml"))

# Import des scripts ML fonctionnels
from scripts_ml.Page_alertes.predict_daily_sales import DailySalesPredictor
from scripts_ml.Page_alertes.calculate_alerts import AlertCalculator, AlertStatus
from scripts_ml.Page_alertes.suggest_quantity import QuantitySuggester

# Import des utilitaires
from utils.database import OptiflowDB
from utils.pdf_generator import generate_order_pdf
from utils.orders import OrderManager

# Couleurs exactes selon les specs
COLORS = {
    'CRITIQUE': '#dc3545',  # Rouge
    'ATTENTION': '#ffc107',  # Orange  
    'OK': '#28a745'  # Vert
}

# Fonctions locales pour la gestion des alertes

def get_last_update_timestamp():
    """Récupère le timestamp de dernière mise à jour depuis la DB"""
    try:
        conn = sqlite3.connect("optiflow.db")
        query = """
            SELECT MAX(created_at) as last_update 
            FROM forecasts 
            WHERE created_at IS NOT NULL
        """
        result = pd.read_sql_query(query, conn)
        conn.close()
        
        if not result.empty and result['last_update'].iloc[0]:
            # Convertir en datetime et formater
            last_update = pd.to_datetime(result['last_update'].iloc[0])
            return last_update.strftime("%d/%m/%Y à %H:%M")
        else:
            return "Pas de données"
    except Exception as e:
        return f"Erreur: {str(e)}"

def generate_all_alerts(db):
    """Génère les alertes pour tous les produits (sans cache)"""
    
    alerts = []
    
    # Initialiser les composants
    predictor = DailySalesPredictor(models_dir="models", db_path="optiflow.db")
    calculator = AlertCalculator(db_path="optiflow.db")
    
    # Récupérer tous les produits
    conn = db.get_connection()
    products = pd.read_sql_query("SELECT id, name FROM products", conn)
    
    for _, product in products.iterrows():
        try:
            # Générer les prédictions
            predictions_result = predictor.predict(
                article_id=product['id'],
                date_debut=datetime.now().strftime("%Y-%m-%d"),
                date_fin=(datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
            )
            
            if predictions_result and predictions_result.get('predictions'):
                # Calculer l'alerte
                alert_result = calculator.calculate_alert(
                    article_id=product['id'],
                    predictions=predictions_result['predictions']
                )
                
                if alert_result:
                    alert_result['article_nom'] = product['name']
                    alerts.append(alert_result)
        
        except Exception as e:
            # Log silencieux pour ne pas encombrer l'interface
            continue
    
    return alerts

# Style CSS optimisé pour le mode sombre
st.markdown("""
    <style>
    /* Support mode sombre */
    [data-testid="metric-container"] {
        background-color: rgba(240, 242, 246, 0.1);
        border: 1px solid rgba(250, 250, 250, 0.2);
        padding: 8px;
        border-radius: 5px;
        margin: 5px 0;
        min-width: 0;
        overflow: visible;
    }
    
    /* Forcer la visibilité des labels en mode sombre */
    [data-testid="metric-container"] label {
        color: rgba(250, 250, 250, 0.9) !important;
        font-size: 0.85rem !important;
        white-space: normal !important;
        line-height: 1.2 !important;
    }
    
    /* Métriques visibles */
    [data-testid="stMetricValue"] {
        color: white !important;
        font-size: 1.2rem !important;
        overflow: visible !important;
        white-space: nowrap !important;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.85rem;
        white-space: nowrap !important;
    }
    
    /* Alertes avec bon contraste pour mode sombre */
    .alert-critical {
        background-color: rgba(220, 53, 69, 0.15);
        border-left: 5px solid #dc3545;
        color: #ff6b7d;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
    }
    
    .alert-warning {
        background-color: rgba(255, 193, 7, 0.15);
        border-left: 5px solid #ffc107;
        color: #ffdd57;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
    }
    
    .alert-ok {
        background-color: rgba(40, 167, 69, 0.15);
        border-left: 5px solid #28a745;
        color: #5dd879;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
    }
    
    /* Sélecteurs et inputs visibles */
    .stSelectbox label,
    .stDateInput label,
    .stSlider label,
    .stNumberInput label,
    .stTextInput label {
        color: rgba(250, 250, 250, 0.9) !important;
    }
    
    .stSelectbox > div > div,
    .stDateInput > div > div,
    .stSlider > div > div {
        background-color: rgba(38, 39, 48, 0.5) !important;
    }
    
    /* Colonnes avec bordures subtiles */
    .stColumn {
        padding: 10px;
        border-radius: 8px;
    }
    
    /* Boutons */
    .stButton > button {
        background-color: #FF6B6B;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        background-color: #ff5252;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(255, 107, 107, 0.3);
    }
    
    /* Info boxes */
    .stAlert {
        background-color: rgba(255, 255, 255, 0.05);
        color: rgba(250, 250, 250, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: rgba(250, 250, 250, 0.9) !important;
        border-radius: 8px;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent;
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255, 255, 255, 0.05);
        color: rgba(250, 250, 250, 0.7);
        border-radius: 8px;
        padding: 8px 16px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #FF6B6B !important;
        color: white !important;
    }
    
    /* Responsive pour petits écrans */
    @media (max-width: 768px) {
        [data-testid="metric-container"] {
            padding: 5px;
            margin: 3px 0;
        }
        
        [data-testid="metric-container"] label {
            font-size: 0.75rem !important;
        }
        
        [data-testid="stMetricValue"] {
            font-size: 1rem !important;
        }
        
        [data-testid="stMetricDelta"] {
            font-size: 0.7rem !important;
        }
    }
    
    /* Amélioration de l'affichage des colonnes */
    [data-testid="column"] {
        padding: 0 5px;
    }
    </style>
""", unsafe_allow_html=True)

# Titre de la page
st.title(":material/inventory_2: Gestion des Alertes et Stocks")

# Afficher le contenu de la page
# Initialisation
db = OptiflowDB()

# Afficher le timestamp de dernière mise à jour
col1, col2 = st.columns([3, 1])
with col2:
    last_update = get_last_update_timestamp()
    st.info(f":material/calendar_today: Dernière MAJ: {last_update}")
    if st.button(":material/refresh: Actualiser"):
        st.rerun()

# Sections principales
st.header("Alertes")

# Générer les alertes directement (sans cache)
with st.spinner("Calcul des alertes en cours..."):
    alerts_data = generate_all_alerts(db)

# Compter les alertes par statut
stats = {'CRITIQUE': [], 'ATTENTION': [], 'OK': []}
for alert in alerts_data:
    if alert['status'] in stats:
        stats[alert['status']].append(alert)

# Afficher les métriques en colonnes
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div style="background-color: {COLORS['CRITIQUE']}; color: white; padding: 1rem; border-radius: 0.5rem; text-align: center;">
        <h2>{len(stats['CRITIQUE'])}</h2>
        <p style="margin: 0;">CRITIQUES</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div style="background-color: {COLORS['ATTENTION']}; color: white; padding: 1rem; border-radius: 0.5rem; text-align: center;">
        <h2>{len(stats['ATTENTION'])}</h2>
        <p style="margin: 0;">ATTENTION</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div style="background-color: {COLORS['OK']}; color: white; padding: 1rem; border-radius: 0.5rem; text-align: center;">
        <h2>{len(stats['OK'])}</h2>
        <p style="margin: 0;">OK</p>
    </div>
    """, unsafe_allow_html=True)

# Afficher le détail des alertes critiques et attention
st.subheader(":material/warning: Alertes Critiques")
if stats['CRITIQUE']:
    # Initialiser le gestionnaire de commandes
    order_manager = OrderManager()
    critical_data = []
    for alert in stats['CRITIQUE']:
        critical_data.append({
            'Article': alert['article_nom'],
            'Stock actuel': f"{alert.get('stock_actuel', 0):.0f}",
            'Ventes prévues': f"{alert.get('ventes_prevues_delai', 0):.0f}",
            'Rupture prévue': alert.get('date_rupture_prevue', 'N/A'),
            'Perte (FCFA)': f"{alert.get('perte_estimee', 0):,.0f}",
            'Qté suggérée': f"{alert.get('quantite_suggeree', 0)}",
            'Action': 'Commander immédiatement'
        })
    
    column_config = {
        "Qté suggérée": st.column_config.TextColumn(
            "Qté suggérée (!)",
            help="Basée sur les prédictions des 30 prochains jours"
        ),
        "Action": st.column_config.TextColumn(
            "Action",
            help="Action recommandée pour éviter la rupture"
        )
    }
    
    df_critical = pd.DataFrame(critical_data)
    st.dataframe(
        df_critical,
        column_config=column_config,
        use_container_width=True,
        hide_index=True
    )

    # Section pour passer commande
    st.markdown("### Passer commande")
    for idx, alert in enumerate(stats['CRITIQUE']):
        with st.expander(f"📦 Commander: {alert['article_nom']}"):
            col1, col2 = st.columns(2)

            with col1:
                # Input pour la quantité
                quantity = st.number_input(
                    "Quantité à commander",
                    min_value=1,
                    value=int(alert.get('quantite_suggeree', 100)),
                    step=10,
                    key=f"qty_crit_{alert['article_id']}_{idx}"
                )

                st.info(f"💡 Quantité suggérée: {alert.get('quantite_suggeree', 'N/A')} unités")

            with col2:
                # Récupérer le lead time du produit
                lead_time = order_manager.get_product_lead_time(str(alert['article_id']))

                # Afficher les informations
                st.metric("Stock actuel", f"{alert.get('stock_actuel', 0):.0f} unités")
                st.metric("Prix unitaire", f"{alert.get('prix_unitaire', 0):,.0f} FCFA")
                st.metric("Délai de livraison", f"{lead_time} jours")

            # Bouton pour générer le PDF et enregistrer la commande
            if st.button(f"📄 Passer commande (PDF)", key=f"order_crit_{alert['article_id']}_{idx}"):
                with st.spinner("Génération du bon de commande..."):
                    try:
                        # Générer le PDF
                        pdf_bytes = generate_order_pdf(
                            product_name=alert['article_nom'],
                            product_id=str(alert['article_id']),
                            stock_at_order=int(alert.get('stock_actuel', 0)),
                            alert_type=alert['status'],
                            quantity_ordered=quantity,
                            unit_price=alert.get('prix_unitaire', 0),
                            lead_time_days=lead_time
                        )

                        # Enregistrer dans la base de données
                        order_result = order_manager.save_order(
                            product_id=str(alert['article_id']),
                            quantity_ordered=quantity,
                            suggested_quantity=int(alert.get('quantite_suggeree', 0)),
                            alert_type=alert['status'],
                            stock_at_order=int(alert.get('stock_actuel', 0)),
                            unit_price=alert.get('prix_unitaire', 0),
                            lead_time_days=lead_time
                        )

                        if order_result['success']:
                            st.success(f"✅ Commande #{order_result['order_id']} enregistrée avec succès!")

                            # Bouton de téléchargement du PDF
                            st.download_button(
                                label="📥 Télécharger le bon de commande",
                                data=pdf_bytes,
                                file_name=f"bon_commande_{alert['article_id']}_{order_result['order_id']}.pdf",
                                mime="application/pdf",
                                key=f"download_crit_{alert['article_id']}_{idx}"
                            )

                            # Afficher les détails
                            st.info(f"""📋 **Détails de la commande:**
                            - Montant total: {order_result['total_amount']:,.0f} FCFA
                            - Livraison prévue: {order_result['expected_delivery'].strftime('%d/%m/%Y')}
                            """)
                        else:
                            st.error(f"❌ Erreur lors de l'enregistrement: {order_result.get('error', 'Erreur inconnue')}")

                    except Exception as e:
                        st.error(f"❌ Erreur lors de la génération du bon de commande: {str(e)}")
else:
    st.success(":material/check_circle: Aucune alerte critique")

st.subheader(":material/report: Alertes Attention")
if stats['ATTENTION']:
    # Initialiser le gestionnaire de commandes si pas déjà fait
    if 'order_manager' not in locals():
        order_manager = OrderManager()
    attention_data = []
    for alert in stats['ATTENTION']:
        attention_data.append({
            'Article': alert['article_nom'],
            'Stock actuel': f"{alert.get('stock_actuel', 0):.0f}",
            'Stock après délai': f"{alert.get('stock_apres_delai', 0):.0f}",
            'Commander avant': alert.get('date_limite_commande', 'N/A'),
            'Jours restants': f"{alert.get('jours_restants', 3)}",
            'Bénéfice (FCFA)': f"{alert.get('benefice_si_commande', 0):,.0f}",
            'Qté suggérée': f"{alert.get('quantite_suggeree', 0)}",
        })
    
    column_config = {
        "Qté suggérée": st.column_config.TextColumn(
            "Qté suggérée (!)",
            help="Basée sur les prédictions des 30 prochains jours"
        ),
        "Commander avant": st.column_config.TextColumn(
            "Commander avant",
            help="Date limite pour éviter la rupture"
        )
    }
    
    df_attention = pd.DataFrame(attention_data)
    st.dataframe(
        df_attention,
        column_config=column_config,
        use_container_width=True,
        hide_index=True
    )

    # Section pour passer commande
    st.markdown("### Passer commande")
    for idx, alert in enumerate(stats['ATTENTION']):
        with st.expander(f"📦 Commander: {alert['article_nom']}"):
            col1, col2 = st.columns(2)

            with col1:
                # Input pour la quantité
                quantity = st.number_input(
                    "Quantité à commander",
                    min_value=1,
                    value=int(alert.get('quantite_suggeree', 100)),
                    step=10,
                    key=f"qty_att_{alert['article_id']}_{idx}"
                )

                st.info(f"💡 Quantité suggérée: {alert.get('quantite_suggeree', 'N/A')} unités")

            with col2:
                # Récupérer le lead time du produit
                lead_time = order_manager.get_product_lead_time(str(alert['article_id']))

                # Afficher les informations
                st.metric("Stock actuel", f"{alert.get('stock_actuel', 0):.0f} unités")
                st.metric("Prix unitaire", f"{alert.get('prix_unitaire', 0):,.0f} FCFA")
                st.metric("Délai de livraison", f"{lead_time} jours")

            # Bouton pour générer le PDF et enregistrer la commande
            if st.button(f"📄 Passer commande (PDF)", key=f"order_att_{alert['article_id']}_{idx}"):
                with st.spinner("Génération du bon de commande..."):
                    try:
                        # Générer le PDF
                        pdf_bytes = generate_order_pdf(
                            product_name=alert['article_nom'],
                            product_id=str(alert['article_id']),
                            stock_at_order=int(alert.get('stock_actuel', 0)),
                            alert_type=alert['status'],
                            quantity_ordered=quantity,
                            unit_price=alert.get('prix_unitaire', 0),
                            lead_time_days=lead_time
                        )

                        # Enregistrer dans la base de données
                        order_result = order_manager.save_order(
                            product_id=str(alert['article_id']),
                            quantity_ordered=quantity,
                            suggested_quantity=int(alert.get('quantite_suggeree', 0)),
                            alert_type=alert['status'],
                            stock_at_order=int(alert.get('stock_actuel', 0)),
                            unit_price=alert.get('prix_unitaire', 0),
                            lead_time_days=lead_time
                        )

                        if order_result['success']:
                            st.success(f"✅ Commande #{order_result['order_id']} enregistrée avec succès!")

                            # Bouton de téléchargement du PDF
                            st.download_button(
                                label="📥 Télécharger le bon de commande",
                                data=pdf_bytes,
                                file_name=f"bon_commande_{alert['article_id']}_{order_result['order_id']}.pdf",
                                mime="application/pdf",
                                key=f"download_att_{alert['article_id']}_{idx}"
                            )

                            # Afficher les détails
                            st.info(f"""📋 **Détails de la commande:**
                            - Montant total: {order_result['total_amount']:,.0f} FCFA
                            - Livraison prévue: {order_result['expected_delivery'].strftime('%d/%m/%Y')}
                            """)
                        else:
                            st.error(f"❌ Erreur lors de l'enregistrement: {order_result.get('error', 'Erreur inconnue')}")

                    except Exception as e:
                        st.error(f"❌ Erreur lors de la génération du bon de commande: {str(e)}")
else:
    st.info(":material/info: Aucune alerte d'attention")

# Section pour les alertes OK
st.subheader(":material/check_circle: Articles OK - Stock suffisant")
if stats['OK']:
    # Afficher sous forme de tableau pour les OK
    ok_data = []
    for alert in stats['OK']:
        ok_data.append({
            'Article': alert['article_nom'],
            'Stock actuel': f"{alert.get('stock_actuel', 0):.0f}",
            'Jours de stock': alert.get('jours_stock_restant', 'N/A'),
            'Commander entre': f"{alert.get('date_commande_min', 'N/A')} et {alert.get('date_commande_max', 'N/A')}",
        })
    
    df_ok = pd.DataFrame(ok_data)
    st.dataframe(df_ok, use_container_width=True, hide_index=True)
else:
    st.warning(":material/report: Aucun article avec un stock suffisant")

st.markdown("---")
st.header(":material/calculate: Quantité Suggérée par article")

# Sélection de l'article
conn = db.get_connection()
products_df = pd.read_sql_query("SELECT id, name FROM products ORDER BY name", conn)

col1, col2 = st.columns(2)

with col1:
    selected_product = st.selectbox(
        "Sélectionner un article",
        options=products_df['id'].tolist(),
        format_func=lambda x: products_df[products_df['id']==x]['name'].values[0]
    )
    
    # Date de couverture souhaitée (jusqu'à 30 jours dans le futur)
    max_date = datetime.now().date() + timedelta(days=30)
    target_date = st.date_input(
        "Date de couverture souhaitée",
        value=datetime.now().date() + timedelta(days=7),  # Défaut à 7 jours
        min_value=datetime.now().date() + timedelta(days=1),  # Demain minimum
        max_value=max_date,
        help="Sélectionnez une date future pour la couverture de stock (entre demain et 30 jours)"
    )

with col2:
    # Marge de sécurité
    security_margin = st.slider(
        "Marge de sécurité (%)",
        min_value=0,
        max_value=50,
        value=15,
        step=5
    )
    
    # Bouton de calcul
    if st.button(":material/analytics: Calculer la quantité", key="calc_qty"):
        # Calcul de quantité suggérée
        with st.spinner("Calcul en cours..."):
            # Générer les prédictions
            predictor = DailySalesPredictor(models_dir="models", db_path="optiflow.db")
            
            predictions_result = predictor.predict(
                article_id=selected_product,
                date_debut=datetime.now().date().strftime("%Y-%m-%d"),
                date_fin=target_date.strftime("%Y-%m-%d")
            )
            
            if predictions_result and predictions_result.get('predictions'):
                # Utiliser le script suggest_quantity
                suggester = QuantitySuggester(db_path="optiflow.db")
                
                result = suggester.calculate_quantity(
                    article_id=selected_product,
                    predictions=predictions_result['predictions'],
                    date_cible=target_date.strftime("%Y-%m-%d"),
                    marge_securite=security_margin
                )
                
                # Afficher le détail du calcul
                st.success(":material/check_circle: Calcul effectué avec succès")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Prédictions cumulées", f"{result['details']['predictions_cumulees']:.0f} unités")
                    st.metric("Stock actuel", f"{result['details']['stock_actuel']:.0f} unités")
                
                with col2:
                    st.metric("Besoin net", f"{result['details']['besoin_net']:.0f} unités")
                    st.metric("Marge appliquée", f"+{result['details']['marge_appliquee']:.0f} unités")
                
                with col3:
                    st.metric(
                        ":material/shopping_cart: QUANTITÉ FINALE",
                        f"{result['quantite_suggeree']:.0f} unités",
                        delta=f"+{security_margin}% de sécurité"
                    )
            else:
                st.error("Impossible de générer les prédictions")