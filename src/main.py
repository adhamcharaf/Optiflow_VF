"""
Optiflow MVP - Point d'entrée principal avec navigation native Streamlit
Système de gestion intelligente des stocks
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# Ajouter le chemin pour les imports
sys.path.append(str(Path(__file__).parent.parent))

# Import pour le timestamp
from pages.alertes import get_last_update_timestamp

# Définir les pages avec st.Page
page_dashboard = st.Page(
    "pages/dashboard.py",
    title="Dashboard",
    icon=":material/dashboard:",
    default=True
)

page_alertes = st.Page(
    "pages/alertes.py",
    title="Alertes",
    icon=":material/inventory:"
)

page_predictions = st.Page(
    "pages/predictions.py",
    title="Prédictions",
    icon=":material/trending_up:"
)

page_amelioration = st.Page(
    "pages/amelioration.py",
    title="Amélioration Système",
    icon=":material/engineering:"
)

# Configuration de la navigation native
pg = st.navigation(
    {
        "🎯 Optiflow": [page_dashboard, page_alertes, page_predictions, page_amelioration]
    }
)

# Information dans la sidebar
with st.sidebar:
    st.markdown("### :material/monitor_heart: État du Système")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("État", "● OK")
    with col2:
        st.metric("Version", "1.0")
    
    
    st.divider()
    
    # Indicateurs rapides
    st.markdown("### 🎯 Indicateurs Rapides")
    st.info("""
    **État:** Prêt pour test
    """)
    
    # Footer
    st.divider()
    st.caption("Version 1.0")
    st.caption("© 2025 Optiflow MVP")

# Lancer la page sélectionnée
pg.run()