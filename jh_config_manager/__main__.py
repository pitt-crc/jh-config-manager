import argparse
import os
import time
from jh_config_manager.service import start_config_watcher

def main():
    parser = argparse.ArgumentParser(description="JupyterHub config manager service")

    parser.add_argument('--venv_root', default=os.environ.get('VENV_ROOT', '/ihome/crc/install/jupyterhub/hub.5.2.1/envs'))
    parser.add_argument('--modules_config_file', default=os.environ.get('MODULES_CONFIG_FILE', '/ihome/crc/install/jupyterhub/modules_config.json'))
    parser.add_argument('--cache_file', default=os.environ.get('CACHE_FILE', '/ihome/crc/install/jupyterhub/config_cache.json'))
    parser.add_argument('--reload_interval', type=int, default=int(os.environ.get('RELOAD_INTERVAL', 30)))

    args = parser.parse_args()

    start_config_watcher(
        venv_root=args.venv_root,
        modules_config_file=args.modules_config_file,
        cache_file=args.cache_file,
        reload_interval=args.reload_interval
    )

    print("[jh_config_manager] Service running. Watching for changes...")
    while True:
        time.sleep(60)

if __name__ == '__main__':
    main()
