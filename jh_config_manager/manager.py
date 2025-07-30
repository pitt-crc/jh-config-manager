import os
import json

def get_virtualenvs(venv_root):
    try:
        return sorted([
            d for d in os.listdir(venv_root)
            if os.path.isdir(os.path.join(venv_root, d))
        ])
    except Exception as e:
        print(f"[jh_config_manager] Error scanning virtualenvs: {e}")
        return []

def load_modules_config(modules_config_file):
    try:
        with open(modules_config_file) as f:
            return json.load(f)
    except Exception as e:
        print(f"[jh_config_manager] Error loading modules config: {e}")
        return {}

def write_cache(cache_file, venvs, modules):
    try:
        with open(cache_file, 'w') as f:
            json.dump({'virtualenvs': venvs, 'modules': modules}, f)
    except Exception as e:
        print(f"[jh_config_manager] Error writing cache: {e}")
