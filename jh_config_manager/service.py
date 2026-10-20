"""Background thread for refreshing the JupyterHub config cache on virtualenv and module changes.

The background thread polls for config changes on a fixed interval and rewrites
the cache file whenever the config state changes. Scan or write failures never
overwrite the cache with empty data, and a failed write is retried on the next scan. This keeps
the cache file JupyterHub reads for spawner configuration up to date without
requiring a service restart.
"""

import time
from threading import Thread

from .manager import get_virtualenvs, load_modules_config, validate_modules_config, write_cache

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
        venvs = None
        modules = None
        last_written = None
        last_problems = []

        while True:
            # A failed scan keeps the last good value rather than publishing an empty one.
            try:
                venvs = get_virtualenvs(venv_root)
            except Exception as e:
                print(f"[jh_config_manager] Error scanning virtualenvs, keeping previous state: {e}")

            try:
                modules, problems = validate_modules_config(load_modules_config(modules_config_file))
                if problems != last_problems:  # report each distinct set of problems once, not every scan
                    for problem in problems:
                        print(f"[jh_config_manager] Ignoring invalid module set {problem}")
                    last_problems = problems
            except Exception as e:
                print(f"[jh_config_manager] Error loading modules config, keeping previous state: {e}")

            if venvs is not None and modules is not None and (venvs, modules) != last_written:
                try:
                    write_cache(cache_file, venvs, modules)
                except Exception as e:
                    # last_written is left unchanged so the write is retried on the next scan.
                    print(f"[jh_config_manager] Error writing cache, will retry: {e}")
                else:
                    last_written = (venvs, modules)
                    print("[jh_config_manager] Cache updated.")

            time.sleep(reload_interval)

    print("[jh_config_manager] Service started.")
    t = Thread(target=refresh_loop, daemon=True)
    t.start()
    return t
