"""Helper functions for managing the JupyterHub cache file.

These functions discover the available virtualenvs and Lmod module
configuration, and write the combined state to the cache file. They are
invoked on a fixed interval by the `service` module to detect changes and
keep the cache file JupyterHub spawners rely on up to date.
"""

import json
import os

__all__ = [
    'get_virtualenvs',
    'load_modules_config',
    'write_cache',
]


def get_virtualenvs(venv_root: str) -> list[str]:
    """Return the sorted names of virtualenv directories found under a root directory.

    Returns an empty list if the root directory cannot be scanned

    Args:
        venv_root: Path to the directory containing virtualenv subdirectories.

    Returns:
        The sorted virtualenv directory names.
    """

    try:
        return sorted([
            d for d in os.listdir(venv_root)
            if os.path.isdir(os.path.join(venv_root, d))
        ])

    except Exception as e:
        print(f"[jh_config_manager] Error scanning virtualenvs: {e}")
        return []


def load_modules_config(modules_config_file: str) -> dict:
    """Load and parse the JSON module configuration file.

    Returns an empty dict if the file cannot be read.

    Args:
        modules_config_file: Path to the JSON file describing available modules.

    Returns:
        The parsed module configuration.
    """

    try:
        with open(modules_config_file) as f:
            return json.load(f)

    except Exception as e:
        print(f"[jh_config_manager] Error loading modules config: {e}")
        return {}


def write_cache(cache_file: str, venvs: list[str], modules: dict) -> None:
    """Write the combined virtualenv and module state to the JupyterHub cache file as JSON.

    Args:
        cache_file: Path to the cache file consumed by the JupyterHub spawner.
        venvs: Virtualenv directory names to record in the cache.
        modules: Module configuration to record in the cache.
    """

    try:
        with open(cache_file, 'w') as f:
            json.dump({'virtualenvs': venvs, 'modules': modules}, f)

    except Exception as e:
        print(f"[jh_config_manager] Error writing cache: {e}")
