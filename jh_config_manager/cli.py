"""Command-line argument parser for the JupyterHub config manager service.

It defines the arguments accepted by the service entry point, falling back
to environment variables for each default so the service can be configured
either via the command line or through the process environment.
"""

import argparse
import os

__all__ = [
    'DEFAULT_VENV_ROOT',
    'DEFAULT_MODULES_CONFIG_FILE',
    'DEFAULT_CACHE_FILE',
    'DEFAULT_RELOAD_INTERVAL',
    'create_parser'
]

DEFAULT_VENV_ROOT = '/ihome/crc/install/jupyterhub/hub.5.2.1/envs'
DEFAULT_MODULES_CONFIG_FILE = '/ihome/crc/install/jupyterhub/modules_config.json'
DEFAULT_CACHE_FILE = '/ihome/crc/install/jupyterhub/config_cache.json'
DEFAULT_RELOAD_INTERVAL = 30


def create_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser for the config manager service.

    Returns:
        The configured argument parser.
    """

    default_venv_root = os.environ.get('VENV_ROOT', DEFAULT_VENV_ROOT)
    default_modules_config_file = os.environ.get('MODULES_CONFIG_FILE', DEFAULT_MODULES_CONFIG_FILE)
    default_cache_file = os.environ.get('CACHE_FILE', DEFAULT_CACHE_FILE)
    default_reload_interval = int(os.environ.get('RELOAD_INTERVAL', DEFAULT_RELOAD_INTERVAL))

    parser = argparse.ArgumentParser(
        description="JupyterHub config manager service",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        '-v', '--venv_root',
        default=default_venv_root,
        metavar='PATH',
        help='Path to the directory containing virtualenv subdirectories.',
    )

    parser.add_argument(
        '-m', '--modules_config_file',
        default=default_modules_config_file,
        metavar='PATH',
        help='Path to the JSON file describing available modules.',
    )

    parser.add_argument(
        '-c', '--cache_file',
        default=default_cache_file,
        metavar='PATH',
        help='Path to the cache file consumed by the JupyterHub spawner.',
    )

    parser.add_argument(
        '-r', '--reload_interval',
        type=int,
        default=default_reload_interval,
        metavar='SECONDS',
        help='Number of seconds to wait between scans.',
    )

    return parser
