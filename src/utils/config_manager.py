import os
import yaml
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging


class ConfigManager:
    """Centralized configuration management"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.logger = logging.getLogger(__name__)
        self._config_cache = {}
    
    def load_config(self, config_name: str = "platforms") -> Dict[str, Any]:
        """Load configuration from YAML file with environment variable substitution"""
        if config_name in self._config_cache:
            return self._config_cache[config_name]
        
        config_file = self.config_dir / f"{config_name}.yaml"
        
        if not config_file.exists():
            self.logger.warning(f"Config file {config_file} not found, using default config")
            return self._get_default_config()
        
        try:
            with open(config_file, 'r') as f:
                config_content = f.read()
            
            # Substitute environment variables
            config_content = self._substitute_env_vars(config_content)
            
            config = yaml.safe_load(config_content)
            self._config_cache[config_name] = config
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load config {config_name}: {e}")
            return self._get_default_config()
    
    def _substitute_env_vars(self, content: str) -> str:
        """Substitute environment variables in config content"""
        import re
        
        # Pattern to match ${VAR_NAME} or ${VAR_NAME:default_value}
        pattern = r'\$\{([^}]+)\}'
        
        def replacer(match):
            var_spec = match.group(1)
            
            if ':' in var_spec:
                var_name, default_value = var_spec.split(':', 1)
                return os.environ.get(var_name, default_value)
            else:
                var_name = var_spec
                value = os.environ.get(var_name)
                if value is None:
                    self.logger.warning(f"Environment variable {var_name} not set")
                    return match.group(0)  # Return original if not found
                return value
        
        return re.sub(pattern, replacer, content)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'platforms': {
                'mercari': {
                    'enabled': False,
                    'sandbox': True,
                    'rate_limit': {
                        'requests_per_minute': 100,
                        'burst_limit': 10
                    },
                    'retry_config': {
                        'max_retries': 3,
                        'backoff_factor': 2,
                        'retry_on_status': [429, 500, 502, 503, 504]
                    }
                },
                'vinted': {
                    'enabled': False,
                    'rate_limit': {
                        'requests_per_minute': 60,
                        'burst_limit': 5
                    },
                    'retry_config': {
                        'max_retries': 3,
                        'backoff_factor': 2,
                        'retry_on_status': [429, 500, 502, 503, 504]
                    }
                },
                'facebook_marketplace': {
                    'enabled': False,
                    'rate_limit': {
                        'requests_per_minute': 200,
                        'burst_limit': 20
                    },
                    'retry_config': {
                        'max_retries': 3,
                        'backoff_factor': 2,
                        'retry_on_status': [429, 500, 502, 503, 504]
                    }
                }
            },
            'global': {
                'default_currency': 'USD',
                'max_photos_per_listing': 10,
                'photo_upload_timeout': 30,
                'sync_interval_minutes': 60,
                'batch_size': 50
            }
        }
    
    def get_platform_config(self, platform_name: str) -> Dict[str, Any]:
        """Get configuration for a specific platform"""
        config = self.load_config()
        platforms = config.get('platforms', {})
        
        if platform_name not in platforms:
            self.logger.warning(f"Platform {platform_name} not found in config")
            return {}
        
        return platforms[platform_name]
    
    def is_platform_enabled(self, platform_name: str) -> bool:
        """Check if a platform is enabled"""
        platform_config = self.get_platform_config(platform_name)
        return platform_config.get('enabled', False)
    
    def get_global_config(self) -> Dict[str, Any]:
        """Get global configuration"""
        config = self.load_config()
        return config.get('global', {})
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration and return validation results"""
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        config = self.load_config()
        
        # Validate platform configs
        for platform_name, platform_config in config.get('platforms', {}).items():
            if not isinstance(platform_config, dict):
                results['errors'].append(f"Platform {platform_name} config must be a dictionary")
                results['valid'] = False
                continue
            
            if platform_config.get('enabled', False):
                # Check required fields based on platform
                required_fields = self._get_required_fields(platform_name)
                
                for field in required_fields:
                    if field not in platform_config:
                        results['errors'].append(f"Missing required field '{field}' for platform {platform_name}")
                        results['valid'] = False
                    elif not platform_config[field]:
                        results['warnings'].append(f"Empty value for field '{field}' in platform {platform_name}")
        
        return results
    
    def _get_required_fields(self, platform_name: str) -> List[str]:
        """Get required configuration fields for a platform"""
        required_fields = {
            'mercari': ['api_key', 'secret', 'access_token'],
            'vinted': ['client_id', 'client_secret', 'access_token', 'refresh_token'],
            'facebook_marketplace': ['app_id', 'app_secret', 'access_token', 'page_id']
        }
        
        return required_fields.get(platform_name, [])
    
    def save_config(self, config: Dict[str, Any], config_name: str = "platforms") -> bool:
        """Save configuration to file"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            config_file = self.config_dir / f"{config_name}.yaml"
            
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            # Clear cache
            if config_name in self._config_cache:
                del self._config_cache[config_name]
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save config {config_name}: {e}")
            return False