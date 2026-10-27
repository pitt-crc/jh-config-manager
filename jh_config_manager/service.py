"""Background thread for refreshing the JupyterHub config cache on virtualenv and module changes.

The background thread polls for config changes on a fixed interval and rewrites
the cache file whenever the config state changes. Scan or write failures never
overwrite the cache with empty data, and a failed write is retried on the next scan. This keeps
the cache file JupyterHub reads for spawner configuration up to date without
requiring a service restart.

When Lmod discovery is enabled the thread also asks Lmod which modules are available, on a slower schedule than the other
checks, and records the list in the cache so the spawner form can offer it.
"""

import time
from threading import Thread

from .lmod import discover_modules, find_init_script
from .manager import get_virtualenvs, load_modules_config, validate_modules_config, write_cache

__all__ = ['start_config_watcher', 'resolve_lmod_init']


def resolve_lmod_init(lmod_init: str) -> str | None:
    """The Lmod init script to use for a `--lmod_init` value: "" means discovery is off, "auto" means look for it.

    Returns:
        The path, or None if discovery is off or "auto" found nothing (a message says which).
    """

    if not lmod_init:
        return None

    if lmod_init != 'auto':
        return lmod_init

    path = find_init_script()
    if path is None:
        print("[jh_config_manager] --lmod_init=auto: Lmod's init script was not found, so modules will not be discovered. "
              "Give its path with --lmod_init.")
    return path


def start_config_watcher(
    venv_root: str,
    modules_config_file: str,
    cache_file: str,
    reload_interval: int,
    lmod_init: str = '',
    modulepath: str = '',
    modules_scan_interval: int = 600,
) -> Thread:
    """Launch a background daemon to refresh the JupyterHub config on a fixed interval.

    Args:
        venv_root: Path to the directory containing virtualenv subdirectories.
        modules_config_file: Path to the JSON file describing available modules.
        cache_file: Path to the cache file consumed by the JupyterHub spawner.
        reload_interval: Number of seconds to wait between scans.
        lmod_init: Lmod's bash init script, "auto" to look for it, or "" to leave module discovery off.
        modulepath: MODULEPATH to list modules from, or "" to use the service's own.
        modules_scan_interval: Number of seconds between Lmod scans.

    Returns:
        The started daemon thread.
    """

    init_script = resolve_lmod_init(lmod_init)

    def refresh_loop():
        venvs = None
        modules = None
        available = None       # the modules Lmod last reported; None until a scan has succeeded
        last_scan = None
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

            # Asking Lmod can take seconds on a network filesystem, so it runs less often than the checks above
            if init_script and (last_scan is None or time.monotonic() - last_scan >= modules_scan_interval):
                last_scan = time.monotonic()
                try:
                    found = discover_modules(init_script, modulepath or None)
                    if not found:
                        print("[jh_config_manager] Lmod listed no modules, keeping previous list. "
                              "Check --modulepath (run with --dump_modules to see what is found).")
                    elif found != available:
                        available = found
                        print(f"[jh_config_manager] Lmod lists {len(available)} modules.")
                except Exception as e:
                    print(f"[jh_config_manager] Error listing modules with Lmod, keeping previous list: {e}")

            state = (venvs, modules, available)
            if venvs is not None and modules is not None and state != last_written:
                try:
                    # Without discovery the cache keeps the format earlier versions wrote
                    write_cache(cache_file, venvs, modules, *([available] if init_script else []))
                except Exception as e:
                    # last_written is left unchanged so the write is retried on the next scan.
                    print(f"[jh_config_manager] Error writing cache, will retry: {e}")
                else:
                    last_written = state
                    print("[jh_config_manager] Cache updated.")

            time.sleep(reload_interval)

    print("[jh_config_manager] Service started." + (" Module discovery through Lmod is on." if init_script else ""))
    t = Thread(target=refresh_loop, daemon=True)
    t.start()
    return t
