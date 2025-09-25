#!/usr/bin/env python3
"""
run_training_session.py - Orchestrateur de la session d'entraînement
Lance l'entraînement complet des modèles Prophet avec validation
"""

import asyncio
import subprocess
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrainingSessionOrchestrator:
    """Orchestrateur de session d'entraînement ML"""
    
    def __init__(self):
        self.scripts_dir = Path(__file__).parent
        self.models_dir = Path("models")
        self.models_dir.mkdir(exist_ok=True)
        
    async def run_script(self, script_name, description):
        """Exécute un script d'entraînement"""
        logger.info(f"▶ {description}")
        
        script_path = self.scripts_dir / script_name
        
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Parse du résultat JSON si disponible
            result = {'success': process.returncode == 0}
            
            try:
                if stdout:
                    json_output = json.loads(stdout.decode())
                    result.update(json_output)
            except json.JSONDecodeError:
                result['output'] = stdout.decode() if stdout else ''
            
            if stderr:
                result['error'] = stderr.decode()
            
            if result['success']:
                logger.info(f" {description} - Terminé avec succès")
            else:
                logger.error(f" {description} - Échec")
                if 'error' in result:
                    logger.error(f"   Erreur: {result['error']}")
            
            return result
            
        except Exception as e:
            logger.error(f"💥 Erreur exécution {script_name}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def run_training_session(self):
        """Exécute la session d'entraînement complète"""
        logger.info(" DÉBUT SESSION D'ENTRAÎNEMENT OPTIFLOW ML")
        logger.info("=" * 60)
        
        session_start = datetime.now()
        session_results = {
            'session_id': f"training_{session_start.strftime('%Y%m%d_%H%M%S')}",
            'started_at': session_start.isoformat(),
            'steps': []
        }
        
        # ÉTAPE 1: Préparation des événements
        events_result = await self.run_script(
            'prepare_events.py',
            'Préparation des événements Prophet'
        )
        session_results['steps'].append({
            'step': 1,
            'name': 'prepare_events',
            'result': events_result
        })
        
        if not events_result['success']:
            logger.error("🛑 Échec préparation événements - Arrêt de la session")
            return session_results
        
        # ÉTAPE 2: Vérification des dépendances
        deps_result = await self.check_dependencies()
        session_results['steps'].append({
            'step': 2,
            'name': 'check_dependencies',
            'result': deps_result
        })
        
        if not deps_result['success']:
            logger.error("🛑 Dépendances manquantes - Installation nécessaire")
            logger.info(" Exécutez: pip install prophet pandas numpy scikit-learn")
            return session_results
        
        # ÉTAPE 3: Entraînement des modèles
        training_result = await self.run_script(
            'train_models.py',
            'Entraînement des 12 modèles Prophet'
        )
        session_results['steps'].append({
            'step': 3,
            'name': 'train_models',
            'result': training_result
        })
        
        if not training_result['success']:
            logger.error("🛑 Échec entraînement des modèles")
            return session_results
        
        # ÉTAPE 4: Validation des modèles
        validation_result = await self.run_script(
            'validate_training.py',
            'Validation des modèles entraînés'
        )
        session_results['steps'].append({
            'step': 4,
            'name': 'validate_training',
            'result': validation_result
        })
        
        # ÉTAPE 5: Génération du rapport final
        final_report = self.generate_final_report(session_results)
        
        session_end = datetime.now()
        session_results['completed_at'] = session_end.isoformat()
        session_results['total_duration'] = (session_end - session_start).total_seconds()
        session_results['final_report'] = final_report
        
        # Sauvegarde de la session
        self.save_session_results(session_results)
        
        logger.info("=" * 60)
        logger.info("🏁 SESSION D'ENTRAÎNEMENT TERMINÉE")
        logger.info(f"⏱ Durée: {session_results['total_duration']:.1f}s")
        
        return session_results
    
    async def check_dependencies(self):
        """Vérifie les dépendances nécessaires"""
        try:
            # Test import Prophet
            import prophet
            import pandas as pd
            import numpy as np
            import sklearn
            
            return {
                'success': True,
                'prophet_version': prophet.__version__,
                'pandas_version': pd.__version__,
                'numpy_version': np.__version__
            }
            
        except ImportError as e:
            return {
                'success': False,
                'error': f'Dépendance manquante: {e}',
                'missing_packages': ['prophet', 'pandas', 'numpy', 'scikit-learn']
            }
    
    def generate_final_report(self, session_results):
        """Génère le rapport final de session"""
        
        # Extraction des métriques clés
        training_step = next((s for s in session_results['steps'] if s['name'] == 'train_models'), None)
        validation_step = next((s for s in session_results['steps'] if s['name'] == 'validate_training'), None)
        
        models_trained = training_step['result'].get('models_trained', 0) if training_step and training_step['result']['success'] else 0
        models_failed = training_step['result'].get('models_failed', 0) if training_step and training_step['result']['success'] else 0
        global_mape = training_step['result'].get('global_mape', 0) if training_step and training_step['result']['success'] else 0
        
        validation_passed = validation_step['result'].get('validation_passed', False) if validation_step and validation_step['result']['success'] else False
        
        report = {
            'session_success': all(step['result']['success'] for step in session_results['steps']),
            'models_trained': models_trained,
            'models_failed': models_failed,
            'success_rate': (models_trained / (models_trained + models_failed)) * 100 if (models_trained + models_failed) > 0 else 0,
            'global_mape': global_mape,
            'validation_passed': validation_passed,
            'performance_grade': self.calculate_performance_grade(global_mape, validation_passed),
            'next_steps': self.generate_next_steps(global_mape, validation_passed, models_trained)
        }
        
        # Affichage du rapport
        logger.info(" RAPPORT FINAL")
        logger.info("-" * 30)
        logger.info(f" Modèles entraînés: {models_trained}/12")
        logger.info(f" Échecs: {models_failed}")
        logger.info(f" MAPE global: {global_mape:.2f}%")
        logger.info(f" Validation: {'RÉUSSIE' if validation_passed else 'ÉCHOUÉE'}")
        logger.info(f"🏆 Note: {report['performance_grade']}")
        
        return report
    
    def calculate_performance_grade(self, mape, validation_passed):
        """Calcule la note de performance"""
        if not validation_passed:
            return 'F'
        elif mape < 10:
            return 'A+'
        elif mape < 12:
            return 'A'
        elif mape < 15:
            return 'B'
        elif mape < 20:
            return 'C'
        else:
            return 'D'
    
    def generate_next_steps(self, mape, validation_passed, models_trained):
        """Génère les prochaines étapes recommandées"""
        next_steps = []
        
        if models_trained < 10:
            next_steps.append("Réentraîner les modèles en échec")
        
        if mape > 15:
            next_steps.append("Optimiser les hyperparamètres Prophet")
            next_steps.append("Analyser les outliers dans les données")
        
        if not validation_passed:
            next_steps.append("Investiguer les incohérences de validation")
        
        if not next_steps:
            next_steps.append("Modèles prêts pour la production")
            next_steps.append("Intégrer dans le batch nocturne")
            next_steps.append("Tester les prédictions en temps réel")
        
        return next_steps
    
    def save_session_results(self, session_results):
        """Sauvegarde les résultats de session"""
        try:
            session_file = self.models_dir / f"training_session_{session_results['session_id']}.json"
            
            with open(session_file, 'w') as f:
                json.dump(session_results, f, indent=2)
            
            logger.info(f"📄 Session sauvée: {session_file}")
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde session: {e}")

async def main():
    """Point d'entrée principal"""
    orchestrator = TrainingSessionOrchestrator()
    session_results = await orchestrator.run_training_session()
    
    # Code de sortie selon le succès
    success = session_results['final_report']['session_success']
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())