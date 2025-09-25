"""
Script d'initialisation pour détecter les anomalies historiques avec Prophet
Analyse les données de 2022-01-01 jusqu'à aujourd'hui - 30 jours
Peut être lancé manuellement à tout moment
"""

import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
import time

# Ajouter le chemin parent pour les imports
sys.path.append(str(Path(__file__).parent.parent))

from prophet_anomaly_detector import ProphetAnomalyDetector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def initialize_anomaly_detection(resume: bool = True):
    """
    Lance la détection d'anomalies sur l'historique complet

    Args:
        resume: Si True, reprend depuis la dernière exécution
    """
    print("=" * 60)
    print("INITIALISATION DE LA DÉTECTION D'ANOMALIES PROPHET")
    print("=" * 60)

    # Initialiser le détecteur
    detector = ProphetAnomalyDetector(
        db_path="../optiflow.db",
        models_dir="../models"
    )

    # Définir les dates
    start_date = "2022-01-01"
    end_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    print(f"\nPériode analysée: {start_date} → {end_date}")
    print(f"Analyse de tous les produits...")
    print("\n" + "-" * 60)

    try:
        # Enregistrer le MAPE de référence avant détection
        print("\nCalcul du MAPE de référence...")
        detector.track_improvement()

        # Lancer la détection
        start_time = time.time()
        print("\nDétection des anomalies en cours...")
        print("(Cela peut prendre quelques minutes...)\n")

        result = detector.detect_historical_anomalies(
            start_date=start_date,
            end_date=end_date
        )

        elapsed_time = time.time() - start_time

        # Afficher les résultats
        if result['success']:
            print("\n" + "=" * 60)
            print("DÉTECTION TERMINÉE AVEC SUCCÈS")
            print("=" * 60)
            print(f"\nSTATISTIQUES:")
            print(f"  • Période analysée: {result['period']}")
            print(f"  • Produits analysés: {result['products_analyzed']}")
            print(f"  • Prédictions générées: {result['total_predictions']}")
            print(f"  • Anomalies détectées: {result['anomalies_detected']}")
            print(f"  • Taux d'anomalie: {result['anomaly_rate']:.2f}%")
            print(f"  • Temps d'exécution: {elapsed_time:.1f} secondes")

            # Calculer le MAPE propre initial
            mape_stats = detector.calculate_clean_mape()
            print(f"\nMAPE PROPRE INITIAL:")
            print(f"  • MAPE: {mape_stats['clean_mape']}%")
            print(f"  • Prédictions utilisées: {mape_stats['predictions_used']}")

            print("\nProchaine étape:")
            print("   Accédez à la page Prédictions dans Streamlit")
            print("   pour valider ou ignorer les anomalies détectées.")

        else:
            print("\nERREUR lors de la détection:")
            print(f"   {result.get('error', 'Erreur inconnue')}")

    except KeyboardInterrupt:
        print("\n\nDétection interrompue par l'utilisateur")
        print("   Relancez le script pour reprendre")
    except Exception as e:
        print(f"\nErreur inattendue: {e}")
        logger.exception("Erreur détection anomalies")

    print("\n" + "=" * 60)

def main():
    """Point d'entrée principal"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Initialisation de la détection d'anomalies Prophet"
    )
    parser.add_argument(
        '--no-resume',
        action='store_true',
        help="Recommencer depuis le début (ignorer l'état précédent)"
    )
    parser.add_argument(
        '--start-date',
        type=str,
        default="2022-01-01",
        help="Date de début d'analyse (format: YYYY-MM-DD)"
    )

    args = parser.parse_args()

    # Confirmation utilisateur
    print("\nATTENTION:")
    print("Ce script va analyser TOUT l'historique des ventes")
    print("et détecter les anomalies basées sur les prédictions Prophet.\n")

    response = input("Voulez-vous continuer? (o/n): ")
    if response.lower() != 'o':
        print("Annulé.")
        return

    # Lancer l'initialisation
    initialize_anomaly_detection(resume=not args.no_resume)

if __name__ == "__main__":
    main()