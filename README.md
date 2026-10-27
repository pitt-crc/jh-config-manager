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
| `-v`, `--venv_root`           | `VENV_ROOT`           | `/software/rhel9/manual/install/jupyterhub/hub.6.1.0/envs`      | Path to the root directory containing virtual environments     |
| `-m`, `--modules_config_file` | `MODULES_CONFIG_FILE` | `/software/rhel9/manual/install/jupyterhub/modules_config.json` | Path to the JSON file describing modules                       |
| `-c`, `--cache_file`          | `CACHE_FILE`          | `/software/rhel9/manual/install/jupyterhub/config_cache.json`   | Path to the output cache file (used by the JupyterHub spawner) |
| `-r`, `--reload_interval`     | `RELOAD_INTERVAL`     | `30`                                                | Number of seconds between scans                                |
| `-l`, `--lmod_init`           | `LMOD_INIT_FILE`      | *(empty: discovery off)*                            | Lmod's bash init script, or `auto`; turns on module discovery  |
| `-p`, `--modulepath`          | `JH_MODULEPATH`       | *(the service's own `MODULEPATH`)*                  | Colon-separated `MODULEPATH` to list modules from              |
| `-s`, `--modules_scan_interval` | `MODULES_SCAN_INTERVAL` | `600`                                           | Seconds between Lmod scans                                     |
| `--dump_modules`              |                       |                                                     | Diagnostic: print the modules found, once, and exit            |

## Automatic Module Discovery (Lmod)

By default the module choices come only from the curated sets in the modules configuration file. With `--lmod_init` the service
also asks **Lmod** which modules exist and records them in the cache as `available_modules`, so the spawner can offer a
searchable list of all of them without anyone maintaining it by hand:

```json
{"virtualenvs": ["tf"], "modules": {"...": "..."}, "available_modules": ["amber/24", "cuda/12.3.0", "gcc/12.2.0"]}
```

- **How:** it runs `module -t avail` in a bash that has sourced Lmod's init script (the listing a user gets in a login shell),
  every `--modules_scan_interval` seconds (default 10 minutes; a scan can take seconds on a network filesystem). Names that
  are not safe to put in a shell command are dropped.
- **Off by default.** Without `--lmod_init` nothing changes and the cache file keeps its earlier format.
- **Failures keep the last list.** If a scan fails, times out (a hung Lmod and what it started are killed after 120 s) or comes
  back empty, the previous list stays published, and the rest of the cache is not held up.
- **Needs Lmod on the machine that runs the service**: the Hub host, not the compute nodes. If `/etc/profile.d/lmod.sh` exists
  there, `--lmod_init=/etc/profile.d/lmod.sh` is usually all that is needed; `--lmod_init=auto` looks in the usual places.
- **Hierarchical module trees.** `avail` lists what is loadable with the *current* `MODULEPATH`. On a flat tree that is every
  module. On a hierarchy (Core / compiler / MPI), modules that sit below a compiler are not listed until that compiler is loaded;
  list the extra directories in `--modulepath` to include them (a module that needs another one loaded first must then be
  selected after it, see the spawner's README).
- **Check what it finds before relying on it** (this has been tested against a fake Lmod, not yet against a real one):

  ```bash
  python -m jh_config_manager --lmod_init=/etc/profile.d/lmod.sh --dump_modules
  ```

  prints one module name per line and a count, or the reason Lmod failed; the exit status is non-zero when nothing was found.

## Failure Behavior

The cache file is replaced atomically, so the spawner never reads a partially written file. If a scan fails (for
example an unreadable `venv_root` or malformed JSON in the modules file), the service logs the error and keeps
publishing the last good state instead of an empty one; nothing is written until both sources have loaded once. A
failed write is retried on the next scan. If the watcher thread stops, the service exits with status 1 so JupyterHub
restarts it.

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
            '--venv_root=/software/rhel9/manual/install/jupyterhub/hub.6.1.0/envs',
            '--modules_config_file=/software/rhel9/manual/install/jupyterhub/modules_config.json',
            '--cache_file=/software/rhel9/manual/install/jupyterhub/config_cache.json',
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

Entries are validated before they reach the spawner. A module set is dropped (and logged once) unless `modules` is a
non-empty list of Lmod-style names made of letters, digits and `. _ + / -` (no spaces, colons or shell characters), and
`display_name`, if present, is a non-empty string. A missing `display_name` defaults to the key. If a file has entries
but none are valid, the previously published modules are kept.

Environments are discovered as the immediate subdirectories of `venv_root` that look like Python environments: they
contain `pyvenv.cfg` (venv/virtualenv), `conda-meta` (conda), or `bin/python`. Hidden directories and other folders,
such as backups, are ignored.

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
