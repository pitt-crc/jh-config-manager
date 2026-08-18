# CRC JupyterHub Configuration Manager

`jh_config_manager` is a dynamic configuration manager service for [JupyterHub](https://jupyterhub.readthedocs.io/) that
monitors and updates virtual environment and module configuration information. It writes this information to a cache
file for use by custom spawners or UI components.

## How It Works

The config manager runs as a background process. It periodically scans a directory containing virtual environments and
reads a JSON file describing administrator-managed LMOD modules. When it detects a change in either source, it writes
the combined state to a unified cache file, which JupyterHub reads to dynamically populate user-facing spawner options.

The process is designed to run continuously as a JupyterHub service, requiring no manual intervention or restarts to
pick up new environments or module configurations.

## CLI Options

The background service is configured via the command-line arguments or using environmental variables.
Command-line arguments take precedence over environment variables, which in turn take precedence over built-in defaults.

| Argument                      | Environment Variable  | Default                                             | Description                                                    |
|-------------------------------|-----------------------|-----------------------------------------------------|----------------------------------------------------------------|
| `-v`, `--venv_root`           | `VENV_ROOT`           | `/ihome/crc/install/jupyterhub/hub.5.2.1/envs`      | Path to the root directory containing virtual environments     |
| `-m`, `--modules_config_file` | `MODULES_CONFIG_FILE` | `/ihome/crc/install/jupyterhub/modules_config.json` | Path to the JSON file describing modules                       |
| `-c`, `--cache_file`          | `CACHE_FILE`          | `/ihome/crc/install/jupyterhub/config_cache.json`   | Path to the output cache file (used by the JupyterHub spawner) |
| `-r`, `--reload_interval`     | `RELOAD_INTERVAL`     | `30`                                                | Number of seconds between scans                                |

## Installation

This project is available directly from PyPI:

```bash
pipx install jh-config-manager
```

Confirm the CLI command is available in your runtime environment:

```bash
jh-config-manager -h
```

The `jh_config_manager` utility is intended to run as a managed JupyterHub service rather than a standalone script,
so that it starts and stops alongside the Hub and is automatically restarted if it exits unexpectedly. To register it,
add an entry to the `services` list in `jupyterhub_config.py`, supplying whichever arguments differ from your
environment's defaults:

```python
c.JupyterHub.services = [
    {
        'name': 'jh-config-manager',
        'command': [
            'python', '-m', 'jh_config_manager',
            '--venv_root=/ihome/crc/install/jupyterhub/hub.5.2.1/envs',
            '--modules_config_file=/ihome/crc/install/jupyterhub/modules_config.json',
            '--cache_file=/ihome/crc/install/jupyterhub/config_cache.json',
            '--reload_interval=30',
        ],
    },
]
```

The module configuration file is maintained by administrators and defines the sets of LMOD modules available to users
through the spawner UI. Each top-level key identifies a module set and maps to a display name shown to users and a
list of modules to load when that set is selected:

```json
{
  "amber24": {
    "display_name": "Amber 2024",
    "modules": [
      "openmpi/4.1.1",
      "amber/24-jupyterhub"
    ]
  },
  "cuda11.2": {
    "display_name": "CUDA 11.2",
    "modules": [
      "cuda/11.2"
    ]
  }
}
```

The service continuously monitors the virtual environments and module configuration file for changes. Whenever either
source changes, it regenerates the cache file in full, combining both into a single document that JupyterHub consults at
spawn time. An example output is provided below:

```json
{
  "virtualenvs": [
    "venv1",
    "venv2"
  ],
  "modules": {
    "amber24": {
      "display_name": "Amber 2024",
      "modules": [
        "openmpi/4.1.1",
        "amber/24-jupyterhub"
      ]
    },
    "cuda11.2": {
      "display_name": "CUDA 11.2",
      "modules": [
        "cuda/11.2"
      ]
    }
  }
}
```
