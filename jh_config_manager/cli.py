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
    'DEFAULT_MODULES_SCAN_INTERVAL',
    'create_parser'
]

DEFAULT_VENV_ROOT = '/software/rhel9/manual/install/jupyterhub/hub.6.1.0/envs'
DEFAULT_MODULES_CONFIG_FILE = '/software/rhel9/manual/install/jupyterhub/modules_config.json'
DEFAULT_CACHE_FILE = '/software/rhel9/manual/install/jupyterhub/config_cache.json'
DEFAULT_RELOAD_INTERVAL = 30
DEFAULT_MODULES_SCAN_INTERVAL = 600


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
    default_lmod_init = os.environ.get('LMOD_INIT_FILE', '')
    default_modulepath = os.environ.get('JH_MODULEPATH', '')
    default_modules_scan_interval = os.environ.get('MODULES_SCAN_INTERVAL', DEFAULT_MODULES_SCAN_INTERVAL)

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

    parser.add_argument(
        '-l', '--lmod_init',
        default=default_lmod_init,
        metavar='PATH',
        help='Path to Lmod\'s bash init script (for example /etc/profile.d/lmod.sh), or "auto" to look for it. When given, '
             'the modules Lmod reports as available are listed automatically in the cache for the spawner form. '
             'Discovery is off when empty.',
    )

    parser.add_argument(
        '-p', '--modulepath',
        default=default_modulepath,
        metavar='PATHS',
        help='Colon-separated MODULEPATH to list modules from, instead of the one in the service\'s environment. Needed for '
             'a hierarchical module tree, where only the directories on the path are listed.',
    )

    parser.add_argument(
        '-s', '--modules_scan_interval',
        type=_positive_int,
        default=default_modules_scan_interval,
        metavar='SECONDS',
        help='Number of seconds between Lmod scans (a scan is slower than the other checks, so it runs less often).',
    )

    parser.add_argument(
        '--dump_modules',
        action='store_true',
        help='Diagnostic: list the modules found through --lmod_init once, print them, and exit.',
    )

    return parser
