"""
Orchestration du workflow batch nocturne selon les contraintes Optiflow
CONTRAINTE CRITIQUE: Batch nocturne obligatoire à minuit
"""

import asyncio
import logging
import subprocess
import sys
from datetime import datetime, time
from pathlib import Path
from typing import Dict, List, Optional
from .cache import set_cached_data, CACHE_KEYS
from .database import get_db_connection

logger = logging.getLogger(__name__)

class WorkflowOrchestrator:
    """Orchestrateur du workflow batch nocturne selon les spécifications"""
    
    def __init__(self, scripts_dir="scripts_ml"):
        """
        Initialise l'orchestrateur
        
        Args:
            scripts_dir: Dossier contenant les scripts ML
        """
        self.scripts_dir = Path(scripts_dir)
        self.batch_time = time(0, 30)  # 00:30 selon les specs
        self.is_running = False
        
        # Ordre d'exécution selon les specs (Page 1, section Notes d'implémentation)
        self.execution_order = [
            # 1. Génération des prédictions (base pour tout le reste)
            "predict_daily_sales.py",
            
            # 2. Enrichissement avec événements
            "evaluate_events_impact.py",
            
            # 3. Calcul des alertes basé sur les prédictions
            "calculate_alerts.py",
            
            # 4. Agrégation pour le dashboard
            "aggregate_dashboard_kpis.py",
            
            # 5. Monitoring des performances
            "monitor_ml_performance.py",
            
            # 6. Scripts dashboard complémentaires
            "compare_ca_predictions.py",
            "calculate_trends.py",
            "get_top_urgent.py",
            "get_stock_dormant.py",
            
            # 7. Scripts prédictions (Page 3)
            "generate_predictions.py",
            "calculate_accuracy.py"
        ]
    
    async def run_batch_process(self):
        """Exécute le processus batch complet selon l'orchestration des specs"""
        if self.is_running:
            logger.warning("Batch déjà en cours d'exécution")
            return False
        
        self.is_running = True
        start_time = datetime.now()
        
        logger.info("🚀 Début du processus batch nocturne")
        
        try:
            results = {}
            
            # Exécution séquentielle selon l'ordre défini
            for script_name in self.execution_order:
                script_path = self.scripts_dir / script_name
                
                if not script_path.exists():
                    logger.warning(f"⚠️ Script non trouvé: {script_name}")
                    continue
                
                logger.info(f"▶️ Exécution: {script_name}")
                result = await self._run_script(script_path)
                results[script_name] = result
                
                if not result['success']:
                    logger.error(f"❌ Échec: {script_name} - {result['error']}")
                    # Continuer malgré les erreurs selon les specs
                else:
                    logger.info(f"✅ Succès: {script_name}")
            
            # Mise à jour du cache avec les résultats
            await self._update_cache_with_results(results)
            
            # Enregistrement des métriques de performance
            duration = datetime.now() - start_time
            await self._log_batch_performance(duration, results)
            
            logger.info(f"🎉 Batch terminé en {duration.total_seconds():.1f}s")
            return True
            
        except Exception as e:
            logger.error(f"💥 Erreur batch: {e}")
            return False
        
        finally:
            self.is_running = False
    
    async def _run_script(self, script_path: Path) -> Dict:
        """
        Exécute un script ML de manière asynchrone
        
        Args:
            script_path: Chemin vers le script
            
        Returns:
            Dictionnaire avec résultat et métadonnées
        """
        try:
            # Exécution du script Python
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                'success': process.returncode == 0,
                'returncode': process.returncode,
                'stdout': stdout.decode() if stdout else '',
                'stderr': stderr.decode() if stderr else '',
                'script': script_path.name
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'script': script_path.name
            }
    
    async def _update_cache_with_results(self, results: Dict):
        """Met à jour le cache avec les résultats du batch"""
        try:
            # Simulation de mise à jour du cache avec les résultats
            # TODO: Implémenter la logique réelle de mise à jour selon les outputs des scripts
            
            # Exemple: Si predict_daily_sales.py a réussi, on met à jour le cache des prédictions
            if results.get('predict_daily_sales.py', {}).get('success'):
                # Charger les nouvelles prédictions et les mettre en cache
                pass
            
            # Mettre à jour le timestamp global du cache
            cache_update_time = datetime.now().isoformat()
            set_cached_data('last_batch_run', {
                'timestamp': cache_update_time,
                'success_count': sum(1 for r in results.values() if r.get('success')),
                'total_scripts': len(results)
            })
            
            logger.info("📦 Cache mis à jour avec les résultats du batch")
            
        except Exception as e:
            logger.error(f"Erreur mise à jour cache: {e}")
    
    async def _log_batch_performance(self, duration, results):
        """Enregistre les métriques de performance du batch"""
        try:
            performance_data = {
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': duration.total_seconds(),
                'scripts_executed': len(results),
                'scripts_success': sum(1 for r in results.values() if r.get('success')),
                'scripts_failed': sum(1 for r in results.values() if not r.get('success')),
                'details': results
            }
            
            # Enregistrement dans le cache pour monitoring
            set_cached_data('batch_performance', performance_data)
            
            logger.info(f"📊 Performance batch enregistrée: {performance_data['scripts_success']}/{performance_data['scripts_executed']} succès")
            
        except Exception as e:
            logger.error(f"Erreur logging performance: {e}")
    
    def schedule_batch(self):
        """Programme l'exécution du batch nocturne"""
        # TODO: Implémenter la planification réelle (cron, scheduler, etc.)
        logger.info(f"📅 Batch programmé pour {self.batch_time}")
    
    async def run_on_demand_script(self, script_name: str, params: Optional[Dict] = None):
        """
        Exécute un script ML à la demande (hors batch)
        
        Args:
            script_name: Nom du script à exécuter
            params: Paramètres optionnels
            
        Returns:
            Résultat de l'exécution
        """
        script_path = self.scripts_dir / script_name
        
        if not script_path.exists():
            return {'success': False, 'error': f'Script non trouvé: {script_name}'}
        
        logger.info(f"🔄 Exécution à la demande: {script_name}")
        result = await self._run_script(script_path)
        
        # Mise à jour partielle du cache si nécessaire
        if result['success']:
            await self._update_cache_for_script(script_name, result)
        
        return result
    
    async def _update_cache_for_script(self, script_name: str, result: Dict):
        """Met à jour le cache pour un script spécifique"""
        # Mapping script -> clé de cache selon les specs
        script_cache_mapping = {
            'calculate_alerts.py': CACHE_KEYS['alerts'],
            'aggregate_dashboard_kpis.py': CACHE_KEYS['dashboard_kpis'],
            'predict_daily_sales.py': 'predictions_data',
            # TODO: Compléter le mapping pour tous les scripts
        }
        
        cache_key = script_cache_mapping.get(script_name)
        if cache_key:
            # TODO: Parser le résultat du script et mettre à jour le cache approprié
            logger.info(f"📦 Cache mis à jour pour {script_name} -> {cache_key}")

# Instance globale pour l'application
workflow = WorkflowOrchestrator()

async def run_daily_batch():
    """Fonction utilitaire pour lancer le batch quotidien"""
    return await workflow.run_batch_process()

async def run_script_on_demand(script_name: str, params: Optional[Dict] = None):
    """Fonction utilitaire pour lancer un script à la demande"""
    return await workflow.run_on_demand_script(script_name, params)

def is_batch_running():
    """Vérifie si le batch est en cours d'exécution"""
    return workflow.is_running

# Configuration pour l'exécution en production
class BatchScheduler:
    """Planificateur pour le batch nocturne en production"""
    
    def __init__(self):
        self.is_scheduled = False
    
    def start_scheduler(self):
        """Démarre la planification du batch nocturne"""
        # TODO: Implémenter avec APScheduler ou cron
        logger.info("📅 Planificateur batch démarré")
        self.is_scheduled = True
    
    def stop_scheduler(self):
        """Arrête la planification"""
        logger.info("⏹️ Planificateur batch arrêté")
        self.is_scheduled = False