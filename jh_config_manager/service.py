"""Background thread for refreshing the JupyterHub config cache on virtualenv and module changes.

The background thread polls for config changes on a fixed interval and updates
and the internal manager cache whenever the config state changes. This keeps
the cache file JupyterHub reads for spawner configuration up to date without
requiring a service restart.
"""

import time
from threading import Thread

from .manager import get_virtualenvs, load_modules_config, write_cache

__all__ = ['start_config_watcher']


def start_config_watcher(
    venv_root: str,
    modules_config_file: str,
    cache_file: str,
    reload_interval: int,
) -> Thread:
    """Launch a background daemon to refresh the JupyterHub config on a fixed interval.

    Args:
        venv_root: Path to the directory containing virtualenv subdirectories.
        modules_config_file: Path to the JSON file describing available modules.
        cache_file: Path to the cache file consumed by the JupyterHub spawner.
        reload_interval: Number of seconds to wait between scans.

    Returns:
        The started daemon thread.
    """

    def refresh_loop():
        last_venvs = []
        last_modules = {}

        while True:
            venvs = get_virtualenvs(venv_root)
            modules = load_modules_config(modules_config_file)

            if venvs != last_venvs or modules != last_modules:
                write_cache(cache_file, venvs, modules)
                last_venvs = venvs
                last_modules = modules
                print("[jh_config_manager] Cache updated.")

            time.sleep(reload_interval)

    print("[jh_config_manager] Service started.")
    t = Thread(target=refresh_loop, daemon=True)
    t.start()
    return t
