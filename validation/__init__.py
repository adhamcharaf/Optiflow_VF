"""
Module de validation par backtesting pour Optiflow
===================================================

Ce module fournit des outils de validation scientifique et académique
pour évaluer les performances du système de prédiction Optiflow.

Méthodologie :
- Split temporel strict (2022-2023 train, 2024 test)
- Walk-forward validation mensuelle
- Métriques standards académiquement acceptées
- Aucune modification du système existant

Utilisation :
    python validation/run_validation.py

Génère automatiquement :
- validation_report.pdf : Rapport complet pour mémoire
- validation_results.json : Résultats détaillés
- performance_metrics.csv : Métriques tabulaires
"""

__version__ = "1.0.0"
__author__ = "Optiflow Validation System"

from .backtesting_engine import BacktestingEngine
from .metrics_calculator import MetricsCalculator
from .time_series_validator import TimeSeriesValidator
from .report_generator import ValidationReport

__all__ = [
    'BacktestingEngine',
    'MetricsCalculator',
    'TimeSeriesValidator',
    'ValidationReport'
]