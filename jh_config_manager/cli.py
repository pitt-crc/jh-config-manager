"""Command-line argument parser for the JupyterHub config manager service.

It defines the arguments accepted by the service entry point, falling back
to environment variables for each default so the service can be configured
either via the command line or through the process environment.
"""

import argparse
import os

__all__ = ['create_parser']


def create_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser for the config manager service.

    Returns:
        The configured argument parser.
    """

    default_venv_root = os.environ.get('VENV_ROOT', '/ihome/crc/install/jupyterhub/hub.5.2.1/envs')
    default_modules_config_file = os.environ.get('MODULES_CONFIG_FILE', '/ihome/crc/install/jupyterhub/modules_config.json')
    default_cache_file = os.environ.get('CACHE_FILE', '/ihome/crc/install/jupyterhub/config_cache.json')
    default_reload_interval = int(os.environ.get('RELOAD_INTERVAL', 30))

    parser = argparse.ArgumentParser(description="JupyterHub config manager service")

    parser.add_argument('--venv_root', default=default_venv_root)
    parser.add_argument('--modules_config_file', default=default_modules_config_file)
    parser.add_argument('--cache_file', default=default_cache_file)
    parser.add_argument('--reload_interval', type=int, default=default_reload_interval)

    return parser
