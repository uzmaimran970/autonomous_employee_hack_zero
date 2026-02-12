"""
Configuration loader for Silver Tier Foundation.

Loads environment variables from .env file and provides
type-safe access to configuration values.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Module-level configuration cache
_config: Optional[dict] = None


def load_config(env_path: Optional[Path] = None) -> dict:
    """
    Load configuration from .env file.

    Args:
        env_path: Optional path to .env file. If not provided,
                  searches in current directory and parent directories.

    Returns:
        Dictionary containing all configuration values.
    """
    global _config

    # Load .env file
    if env_path:
        load_dotenv(env_path)
    else:
        load_dotenv()

    # Build configuration dictionary
    _config = {
        'vault_path': Path(os.getenv('VAULT_PATH', './autonomous_employee')),
        'watch_dir': Path(os.getenv('WATCH_DIR', './inbox')),
        'check_interval_seconds': int(os.getenv('CHECK_INTERVAL_SECONDS', '30')),
        'log_level': os.getenv('LOG_LEVEL', 'INFO').upper(),

        # Silver Tier configuration
        'operations_log_path': Path(os.getenv('OPERATIONS_LOG_PATH', './operations.log')),
        'auto_execute_simple': os.getenv('AUTO_EXECUTE_SIMPLE', 'false').lower() == 'true',
        'credential_scan_enabled': os.getenv('CREDENTIAL_SCAN_ENABLED', 'true').lower() == 'true',

        # Gold Tier configuration
        'auto_execute_complex': os.getenv('AUTO_EXECUTE_COMPLEX', 'false').lower() == 'true',
        'allowed_external_services': [
            s.strip() for s in os.getenv('ALLOWED_EXTERNAL_SERVICES', '').split(',')
            if s.strip()
        ],
        'sla_simple_minutes': int(os.getenv('SLA_SIMPLE_MINUTES', '2')),
        'sla_complex_minutes': int(os.getenv('SLA_COMPLEX_MINUTES', '10')),
        'notification_channel': os.getenv('NOTIFICATION_CHANNEL', ''),
        'notification_endpoint': os.getenv('NOTIFICATION_ENDPOINT', ''),
        'rollback_retention_days': int(os.getenv('ROLLBACK_RETENTION_DAYS', '7')),

        # Platinum Tier configuration
        'prediction_threshold': float(os.getenv('PREDICTION_THRESHOLD', '0.7')),
        'max_parallel_tasks': int(os.getenv('MAX_PARALLEL_TASKS', '3')),
        'learning_window_days': int(os.getenv('LEARNING_WINDOW_DAYS', '30')),
        'max_recovery_attempts': int(os.getenv('MAX_RECOVERY_ATTEMPTS', '3')),
        'task_timeout_minutes': int(os.getenv('TASK_TIMEOUT_MINUTES', '15')),
        'enable_predictive_sla': os.getenv('ENABLE_PREDICTIVE_SLA', 'true').lower() == 'true',
        'enable_self_healing': os.getenv('ENABLE_SELF_HEALING', 'true').lower() == 'true',
        'enable_risk_scoring': os.getenv('ENABLE_RISK_SCORING', 'true').lower() == 'true',
        'risk_weight_sla': float(os.getenv('RISK_WEIGHT_SLA', '0.3')),
        'risk_weight_complexity': float(os.getenv('RISK_WEIGHT_COMPLEXITY', '0.2')),
        'risk_weight_impact': float(os.getenv('RISK_WEIGHT_IMPACT', '0.3')),
        'risk_weight_failure': float(os.getenv('RISK_WEIGHT_FAILURE', '0.2')),

        # Gmail configuration (optional)
        'gmail_client_id': os.getenv('GMAIL_CLIENT_ID'),
        'gmail_client_secret': os.getenv('GMAIL_CLIENT_SECRET'),
        'gmail_token_path': os.getenv('GMAIL_TOKEN_PATH'),
    }

    # Configure logging based on LOG_LEVEL
    logging.basicConfig(
        level=getattr(logging, _config['log_level'], logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    return _config


def get_config() -> dict:
    """
    Get the current configuration.

    Returns:
        Configuration dictionary. Loads from .env if not already loaded.
    """
    global _config
    if _config is None:
        load_config()
    return _config


def get_vault_path() -> Path:
    """Get the vault path from configuration."""
    return get_config()['vault_path']


def get_watch_dir() -> Path:
    """Get the watch directory from configuration."""
    return get_config()['watch_dir']


def get_check_interval() -> int:
    """Get the check interval in seconds."""
    return get_config()['check_interval_seconds']


def is_gmail_configured() -> bool:
    """Check if Gmail watcher is configured."""
    config = get_config()
    return bool(config['gmail_client_id'] and config['gmail_client_secret'])
