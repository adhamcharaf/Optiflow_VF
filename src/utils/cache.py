"""
Système de cache 24h selon les contraintes Optiflow
CONTRAINTE CRITIQUE: Cache obligatoire avec timestamp visible
"""

import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class OptiflowCache:
    """Gestionnaire de cache 24h pour Optiflow MVP"""
    
    def __init__(self, cache_dir=".cache"):
        """
        Initialise le système de cache
        
        Args:
            cache_dir: Dossier de cache (créé si inexistant)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Fichier de métadonnées du cache
        self.meta_file = self.cache_dir / "cache_meta.json"
        self.cache_duration = timedelta(hours=24)  # Cache 24h selon specs
        
        logger.info(f"Cache initialisé: {self.cache_dir}")
    
    def _get_cache_file(self, key):
        """Retourne le chemin du fichier de cache pour une clé"""
        safe_key = "".join(c for c in key if c.isalnum() or c in ['_', '-'])
        return self.cache_dir / f"{safe_key}.pkl"
    
    def _load_meta(self):
        """Charge les métadonnées du cache"""
        if self.meta_file.exists():
            try:
                with open(self.meta_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erreur lecture meta: {e}")
        
        return {}
    
    def _save_meta(self, meta):
        """Sauvegarde les métadonnées du cache"""
        try:
            with open(self.meta_file, 'w') as f:
                json.dump(meta, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Erreur sauvegarde meta: {e}")
    
    def set(self, key, data, custom_duration=None):
        """
        Met en cache des données avec timestamp
        
        Args:
            key: Clé unique pour les données
            data: Données à mettre en cache
            custom_duration: Durée personnalisée (par défaut 24h)
        """
        try:
            # Calcul de l'expiration
            duration = custom_duration or self.cache_duration
            expires_at = datetime.now() + duration
            
            # Préparation des données avec métadonnées
            cache_data = {
                'data': data,
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat(),
                'key': key
            }
            
            # Sauvegarde des données
            cache_file = self._get_cache_file(key)
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            
            # Mise à jour des métadonnées
            meta = self._load_meta()
            meta[key] = {
                'created_at': cache_data['created_at'],
                'expires_at': cache_data['expires_at'],
                'file': str(cache_file)
            }
            self._save_meta(meta)
            
            logger.info(f"Cache mis à jour: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur mise en cache {key}: {e}")
            return False
    
    def get(self, key):
        """
        Récupère des données du cache si valides
        
        Args:
            key: Clé des données
            
        Returns:
            Données si valides, None si expirées ou inexistantes
        """
        try:
            cache_file = self._get_cache_file(key)
            
            if not cache_file.exists():
                return None
            
            # Chargement des données
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Vérification de l'expiration
            expires_at = datetime.fromisoformat(cache_data['expires_at'])
            if datetime.now() > expires_at:
                logger.info(f"Cache expiré: {key}")
                self.delete(key)
                return None
            
            logger.info(f"Cache hit: {key}")
            return cache_data['data']
            
        except Exception as e:
            logger.error(f"Erreur lecture cache {key}: {e}")
            return None
    
    def delete(self, key):
        """Supprime une entrée du cache"""
        try:
            cache_file = self._get_cache_file(key)
            if cache_file.exists():
                cache_file.unlink()
            
            # Mise à jour métadonnées
            meta = self._load_meta()
            if key in meta:
                del meta[key]
                self._save_meta(meta)
            
            logger.info(f"Cache supprimé: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur suppression cache {key}: {e}")
            return False
    
    def get_last_update_timestamp(self, key=None):
        """
        Retourne le timestamp de dernière mise à jour pour affichage
        
        Args:
            key: Clé spécifique (si None, prend la plus récente)
            
        Returns:
            Chaîne formatée avec date/heure ou None
        """
        try:
            meta = self._load_meta()
            
            if not meta:
                return None
            
            if key:
                if key in meta:
                    created_at = datetime.fromisoformat(meta[key]['created_at'])
                    return created_at.strftime("%d/%m/%Y à %H:%M")
                return None
            else:
                # Prendre la plus récente si pas de clé spécifiée
                latest = max(meta.values(), key=lambda x: x['created_at'])
                created_at = datetime.fromisoformat(latest['created_at'])
                return created_at.strftime("%d/%m/%Y à %H:%M")
                
        except Exception as e:
            logger.error(f"Erreur timestamp: {e}")
            return None
    
    def clear_expired(self):
        """Nettoie les entrées expirées du cache"""
        cleaned = 0
        try:
            meta = self._load_meta()
            now = datetime.now()
            
            for key, info in list(meta.items()):
                expires_at = datetime.fromisoformat(info['expires_at'])
                if now > expires_at:
                    self.delete(key)
                    cleaned += 1
            
            logger.info(f"Cache nettoyé: {cleaned} entrées supprimées")
            return cleaned
            
        except Exception as e:
            logger.error(f"Erreur nettoyage cache: {e}")
            return 0
    
    def get_cache_status(self):
        """Retourne le statut du cache pour monitoring"""
        try:
            meta = self._load_meta()
            now = datetime.now()
            
            total = len(meta)
            valid = 0
            expired = 0
            
            for info in meta.values():
                expires_at = datetime.fromisoformat(info['expires_at'])
                if now <= expires_at:
                    valid += 1
                else:
                    expired += 1
            
            return {
                'total_entries': total,
                'valid_entries': valid,
                'expired_entries': expired,
                'cache_dir_size_mb': sum(f.stat().st_size for f in self.cache_dir.glob('*')) / (1024*1024)
            }
            
        except Exception as e:
            logger.error(f"Erreur statut cache: {e}")
            return {}

# Instance globale pour l'application
cache = OptiflowCache()

def get_cached_data(key):
    """
    Fonction utilitaire pour récupérer des données du cache
    
    Args:
        key: Clé des données
        
    Returns:
        Données du cache ou None
    """
    return cache.get(key)

def set_cached_data(key, data, duration_hours=24):
    """
    Fonction utilitaire pour mettre en cache des données
    
    Args:
        key: Clé unique
        data: Données à cacher
        duration_hours: Durée en heures (défaut 24h)
    """
    duration = timedelta(hours=duration_hours)
    return cache.set(key, data, duration)

def get_last_update_timestamp(key=None):
    """
    Retourne le timestamp de dernière mise à jour pour l'interface
    CONTRAINTE: Timestamp obligatoire selon les specs
    
    Args:
        key: Clé spécifique ou None pour la plus récente
        
    Returns:
        Chaîne formatée pour affichage dans l'interface
    """
    return cache.get_last_update_timestamp(key)

def clear_cache():
    """Vide complètement le cache"""
    try:
        import shutil
        if cache.cache_dir.exists():
            shutil.rmtree(cache.cache_dir)
            cache.cache_dir.mkdir(exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Erreur vidage cache: {e}")
        return False

# Clés de cache standardisées pour l'application
CACHE_KEYS = {
    'alerts': 'dashboard_alerts',
    'articles_list': 'articles_list',
    'dashboard_kpis': 'dashboard_kpis',
    'ca_comparison': 'ca_comparison',
    'savings_data': 'savings_data',
    'trends_7days': 'trends_7days',
    'next_event': 'next_event',
    'top_urgent': 'top_urgent',
    'stock_dormant': 'stock_dormant',
    'confidence_score': 'confidence_score',
    'events': 'events_data',
    'events_impact_history': 'events_impact_history',
    'ml_performance': 'ml_performance',
    'ecarts_a_expliquer': 'ecarts_a_expliquer',
    'future_events': 'future_events',
    'learning_score': 'learning_score'
}