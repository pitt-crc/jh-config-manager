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

DEFAULT_VENV_ROOT = '/software/rhel9/manual/install/jupyterhub/hub.6.1.0/envs'
DEFAULT_MODULES_CONFIG_FILE = '/software/rhel9/manual/install/jupyterhub/modules_config.json'
DEFAULT_CACHE_FILE = '/software/rhel9/manual/install/jupyterhub/config_cache.json'
DEFAULT_RELOAD_INTERVAL = 30


def _positive_int(value: str) -> int:
    """Parse a strictly positive integer command-line or environment value.

    Args:
        value: The raw string to parse.

    Returns:
        The parsed integer.

    Raises:
        argparse.ArgumentTypeError: If the value is not an integer greater than zero.
    """

    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid integer value: {value!r}") from None

    if number < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {number}")

    return number


def create_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser for the config manager service.

    Returns:
        The configured argument parser.
    """

    default_venv_root = os.environ.get('VENV_ROOT', DEFAULT_VENV_ROOT)
    default_modules_config_file = os.environ.get('MODULES_CONFIG_FILE', DEFAULT_MODULES_CONFIG_FILE)
    default_cache_file = os.environ.get('CACHE_FILE', DEFAULT_CACHE_FILE)
    # Left unconverted so argparse validates it with `_positive_int` and reports a bad value cleanly.
    default_reload_interval = os.environ.get('RELOAD_INTERVAL', DEFAULT_RELOAD_INTERVAL)

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
        type=_positive_int,
        default=default_reload_interval,
        metavar='SECONDS',
        help='Number of seconds to wait between scans.',
    )

    return parser
