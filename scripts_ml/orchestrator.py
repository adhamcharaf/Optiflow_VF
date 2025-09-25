#!/usr/bin/env python3
"""
Orchestrateur principal des scripts ML Optiflow
Exécution selon l'ordre défini dans les spécifications
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_optiflow.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class OptiflowOrchestrator:
    """Orchestrateur principal selon les spécifications"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        
        # Ordre d'exécution selon les specs (Notes d'implémentation Page 1)
        self.execution_sequence = [
            # 1. Script 1 s'exécute en premier pour générer les prédictions
            "Page_alertes/predict_daily_sales.py",
            
            # 2. Script 4 enrichit les prédictions avec l'impact des événements  
            "Page_alertes/evaluate_events_impact.py",
            
            # 3. Script 2 utilise les prédictions pour calculer les alertes
            "Page_alertes/calculate_alerts.py",
            
            # 4. Script 3 calcule les quantités sur demande utilisateur (pas batch)
            # "Page_alertes/suggest_quantity.py",  # Exécution à la demande uniquement
            
            # 5. Script 5 s'exécute périodiquement pour améliorer le système
            "Page_alertes/monitor_ml_performance.py",
            
            # Scripts Dashboard (Page 2) - Nouveaux scripts intégrés
            "page2_dashboard/aggregate_dashboard_kpis.py",
            "page2_dashboard/track_savings.py",  # Script 7: Économies alertes
            "page2_dashboard/compare_ca_predictions.py",  # Script 8: CA prévu vs réel
            "page2_dashboard/calculate_trends.py",  # Script 9: Tendances 7j
            "page2_dashboard/get_top_urgent.py",  # Script 10: Top 3 critiques
            "page2_dashboard/get_stock_dormant.py",  # Script 11: Stock dormant
            
            # Scripts Prédictions (Page 3) - Nouveaux scripts intégrés
            "page3_predictions/generate_predictions.py",  # Script A: Tableau prédictions
            "page3_predictions/calculate_accuracy.py"  # Script B: Précision
            # learn_from_feedback.py (Script C) s'exécute à la demande uniquement
        ]

    async def _run_weekly_predictions_update(self):
        """Exécute la mise à jour hebdomadaire des prédictions (30 jours)"""
        try:
            script_path = self.base_dir / "weekly_predictions_update.py"

            if not script_path.exists():
                logger.error(f"Script weekly_predictions_update.py non trouvé")
                return {'success': False, 'error': 'Script not found'}

            # Exécuter avec le flag --force pour s'assurer qu'il s'exécute
            result = await asyncio.create_subprocess_exec(
                sys.executable,
                str(script_path),
                '--force',
                '--days=30',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                logger.info("Mise à jour hebdomadaire des prédictions réussie")
                return {'success': True, 'output': stdout.decode()}
            else:
                logger.error(f"Erreur mise à jour hebdomadaire: {stderr.decode()}")
                return {'success': False, 'error': stderr.decode()}

        except Exception as e:
            logger.error(f"Exception lors de la mise à jour hebdomadaire: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def run_batch_nocturne(self):
        """
        Exécute le batch nocturne complet selon les specs
        Fréquence: 1 fois par jour à minuit selon Page 1
        """
        logger.info("Début du batch nocturne Optiflow")
        start_time = datetime.now()

        # Vérifier si c'est dimanche pour la mise à jour hebdomadaire
        if start_time.weekday() == 6:
            logger.info("DIMANCHE: Exécution de la mise à jour hebdomadaire des prédictions")
            await self._run_weekly_predictions_update()

        logger.info("Exécution du batch quotidien")
        start_time = datetime.now()
        
        results = {
            'start_time': start_time.isoformat(),
            'scripts_executed': [],
            'scripts_failed': [],
            'total_duration': 0
        }
        
        # Étape préalable: Sauvegarder les snapshots quotidiens pour les tendances
        await self._save_daily_snapshots()
        
        for script_path in self.execution_sequence:
            full_path = self.base_dir / script_path
            
            if not full_path.exists():
                logger.warning(f" Script non trouvé: {script_path}")
                results['scripts_failed'].append({
                    'script': script_path,
                    'error': 'Script file not found'
                })
                continue
            
            logger.info(f"Exécution: {script_path}")
            
            try:
                # Exécution du script
                result = await self._execute_script(full_path)
                
                if result['success']:
                    logger.info(f" Succès: {script_path}")
                    results['scripts_executed'].append({
                        'script': script_path,
                        'duration': result['duration'],
                        'output': result.get('output', '')
                    })
                else:
                    logger.error(f" Échec: {script_path} - {result['error']}")
                    results['scripts_failed'].append({
                        'script': script_path,
                        'error': result['error']
                    })
                    
            except Exception as e:
                logger.error(f"💥 Erreur inattendue: {script_path} - {e}")
                results['scripts_failed'].append({
                    'script': script_path,
                    'error': str(e)
                })
        
        # Finalisation
        end_time = datetime.now()
        results['end_time'] = end_time.isoformat()
        results['total_duration'] = (end_time - start_time).total_seconds()
        
        logger.info(f" Batch terminé en {results['total_duration']:.1f}s")
        logger.info(f" Résultats: {len(results['scripts_executed'])} succès, {len(results['scripts_failed'])} échecs")
        
        return results
    
    async def _execute_script(self, script_path):
        """Exécute un script Python de manière asynchrone"""
        script_start = datetime.now()
        
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(script_path.parent)
            )
            
            stdout, stderr = await process.communicate()
            
            duration = (datetime.now() - script_start).total_seconds()
            
            return {
                'success': process.returncode == 0,
                'duration': duration,
                'returncode': process.returncode,
                'output': stdout.decode() if stdout else '',
                'error': stderr.decode() if stderr else ''
            }
            
        except Exception as e:
            duration = (datetime.now() - script_start).total_seconds()
            return {
                'success': False,
                'duration': duration,
                'error': str(e)
            }
    
    async def run_single_script(self, script_name):
        """Exécute un script spécifique à la demande"""
        # Recherche du script dans tous les dossiers
        for subdir in ['Page_alertes', 'page2_dashboard', 'page3_predictions', 'utils']:
            script_path = self.base_dir / subdir / script_name
            if script_path.exists():
                logger.info(f" Exécution à la demande: {script_name}")
                return await self._execute_script(script_path)
        
        return {
            'success': False,
            'error': f'Script non trouvé: {script_name}'
        }
    
    async def _save_daily_snapshots(self):
        """
        Sauvegarde les snapshots quotidiens nécessaires aux analyses de tendances
        Appelé avant le batch principal
        """
        try:
            logger.info("📸 Sauvegarde des snapshots quotidiens...")
            
            # Importer et exécuter le snapshot des alertes
            import sys
            sys.path.insert(0, str(self.base_dir / 'page2_dashboard'))
            
            from calculate_trends import AlertsTrendsCalculator
            
            calculator = AlertsTrendsCalculator()
            success = calculator.save_daily_snapshot()
            
            if success:
                logger.info(" Snapshots sauvegardés avec succès")
            else:
                logger.warning(" Problème lors de la sauvegarde des snapshots")
                
        except Exception as e:
            logger.error(f" Erreur sauvegarde snapshots: {e}")
    
    async def run_on_demand_scripts(self, script_list):
        """
        Exécute des scripts à la demande (ex: suggest_quantity, learn_from_feedback)
        
        Args:
            script_list: Liste des noms de scripts à exécuter
            
        Returns:
            Dict avec résultats de chaque script
        """
        logger.info(f" Exécution à la demande: {', '.join(script_list)}")
        results = {}
        
        for script_name in script_list:
            result = await self.run_single_script(script_name)
            results[script_name] = result
            
            if result['success']:
                logger.info(f" {script_name} terminé avec succès")
            else:
                logger.error(f" {script_name} a échoué: {result.get('error', 'Erreur inconnue')}")
        
        return results

async def main():
    """Point d'entrée principal"""
    orchestrator = OptiflowOrchestrator()
    
    if len(sys.argv) > 1:
        # Exécution d'un script spécifique
        script_name = sys.argv[1]
        result = await orchestrator.run_single_script(script_name)
        
        if result['success']:
            print(f" Script {script_name} exécuté avec succès")
            sys.exit(0)
        else:
            print(f" Échec du script {script_name}: {result['error']}")
            sys.exit(1)
    else:
        # Batch nocturne complet
        result = await orchestrator.run_batch_nocturne()
        
        if len(result['scripts_failed']) == 0:
            print(" Batch nocturne terminé avec succès")
            sys.exit(0)
        else:
            print(f" Batch terminé avec {len(result['scripts_failed'])} erreurs")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())