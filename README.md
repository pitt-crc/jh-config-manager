# CRC JupyterHub Configuration Manager

`jh_config_manager` is a dynamic configuration manager service for 
[JupyterHub](https://jupyterhub.readthedocs.io/) that monitors and updates virtual environment and module configuration
information. It writes this information to a cache file for use by custom spawners or UI components.

## Features

- Periodically scans a directory for available virtual environments
- Reads a JSON configuration file describing modules
- Writes a unified cache JSON file used by JupyterHub to dynamically populate user options
- Designed to run as a background JupyterHub service

## Installation

Clone the repository and install the package into your virtual environment:

```
git clone <your-repo-url>
cd jh_config_manager
pip install .
```
or through pip:
```
pip install jh-config-manager
```
## Configuration
### Arguments:
- venv_root: Path to the root directory containing virtual environments
- modules_config_file: Path to the JSON file describing modules
- cache_file: Path to the output cache file (used by JupyterHub spawner)
- reload_interval: Number of seconds between scans (default: 30)

### in jupyterhub_config.py:
```python
c.JupyterHub.services = [
    {
        'name': 'jh-config-manager',
        'command': [
            'python', '-m', 'jh_config_manager',
            '--venv_root=/ihome/crc/install/jupyterhub/hub.5.2.1/envs',
            '--modules_config_file=/ihome/crc/install/jupyterhub/modules_config.json',
            '--cache_file=/ihome/crc/install/jupyterhub/config_cache.json',
            '--reload_interval=30'
        ],
    }
]
```

### Example JSON Module Config File:
```json
{
    "amber24": {
        "display_name": "Amber 2024",
        "modules": ["openmpi/4.1.1", "amber/24-jupyterhub"]
    },
    "cuda11.2": {
        "display_name": "CUDA 11.2",
        "modules": ["cuda/11.2"]
    }
}
```

### Example Cache File:
```json
{
  "virtualenvs": ["venv1", "venv2"],
  "modules": {
        "amber24": {
            "display_name": "Amber 2024",
            "modules": ["openmpi/4.1.1", "amber/24-jupyterhub"]
        },
        "cuda11.2": {
            "display_name": "CUDA 11.2",
            "modules": ["cuda/11.2"]
        }
    }
}
```
## Testing
To run the service manually, use the following command:
```
python -m jh_config_manager \
  --venv_root=/your/path/to/envs \
  --modules_config_file=/your/path/to/modules_config.json \
  --cache_file=/your/path/to/output_cache.json \
  --reload_interval=10
```