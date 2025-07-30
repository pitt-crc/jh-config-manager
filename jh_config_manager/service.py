import time
from threading import Thread
from .manager import get_virtualenvs, load_modules_config, write_cache

def start_config_watcher(venv_root, modules_config_file, cache_file, reload_interval):
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
