"""Helper functions for managing the JupyterHub cache file.

These functions discover the available virtualenvs and Lmod module
configuration, and write the combined state to the cache file. They are
invoked on a fixed interval by the `service` module to detect changes and
keep the cache file JupyterHub spawners rely on up to date.
"""

import json
import os
import re
import tempfile

__all__ = [
    'get_virtualenvs',
    'load_modules_config',
    'validate_modules_config',
    'write_cache',
]

# Lmod names such as `openmpi/4.1.7-stdwe7`. The spawner joins module names with ':' and the batch script
# word-splits on it, so ':' and whitespace must never appear.
_MODULE_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._+/-]*$')


def _is_environment(path: str) -> bool:
    """Return whether a directory looks like a usable Python environment.

    Accepts both `venv`/`virtualenv` environments (`pyvenv.cfg`) and conda environments (`conda-meta`),
    since the spawner activates environments with a conda-style `bin/activate <path>`. An interpreter at
    `bin/python` is also accepted.

    Args:
        path: Path to a candidate environment directory.

    Returns:
        True if the directory contains a recognizable environment marker.
    """

    return (
        os.path.isfile(os.path.join(path, 'pyvenv.cfg'))
        or os.path.isdir(os.path.join(path, 'conda-meta'))
        or os.path.exists(os.path.join(path, 'bin', 'python'))
    )


def get_virtualenvs(venv_root: str) -> list[str]:
    """Return the sorted names of environment directories found under a root directory.

    Hidden directories and directories that are not recognizable Python environments (see
    `_is_environment`) are skipped, so stray folders such as backups or scratch directories
    never appear in the spawner.

    Args:
        venv_root: Path to the directory containing virtualenv subdirectories.

    Returns:
        The sorted virtualenv directory names.

    Raises:
        OSError: If the root directory cannot be scanned.
    """

    return sorted([
        d for d in os.listdir(venv_root)
        if not d.startswith('.') and _is_environment(os.path.join(venv_root, d))
    ])


def load_modules_config(modules_config_file: str) -> dict:
    """Load and parse the JSON module configuration file.

    Args:
        modules_config_file: Path to the JSON file describing available modules.

    Returns:
        The parsed module configuration.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the file is not valid JSON or its top level is not an object.
    """

    with open(modules_config_file) as f:
        config = json.load(f)

    if not isinstance(config, dict):
        raise ValueError(f"expected a JSON object at the top level, got {type(config).__name__}")

    return config


def validate_modules_config(config: dict) -> tuple[dict, list[str]]:
    """Validate a parsed module configuration and drop malformed entries.

    An entry is valid when it is an object whose `modules` is a non-empty list of Lmod-style module names and
    whose optional `display_name` is a string. A missing `display_name` defaults to the entry's key, which is
    what the spawner would display anyway.

    Args:
        config: The parsed module configuration, as returned by `load_modules_config`.

    Returns:
        A tuple of the cleaned configuration (valid entries only) and a list of human-readable problems,
        one per dropped entry.

    Raises:
        ValueError: If the configuration has entries but none of them are valid, so the caller can keep its
            previous state rather than publishing an empty module list.
    """

    valid = {}
    problems = []

    for key, entry in config.items():
        if not isinstance(entry, dict):
            problems.append(f"'{key}': expected an object, got {type(entry).__name__}")
            continue

        display_name = entry.get('display_name', key)
        if not isinstance(display_name, str) or not display_name.strip():
            problems.append(f"'{key}': display_name must be a non-empty string")
            continue

        modules = entry.get('modules')
        if not isinstance(modules, list) or not modules:
            problems.append(f"'{key}': modules must be a non-empty list")
            continue

        bad = [m for m in modules if not isinstance(m, str) or not _MODULE_NAME.match(m)]
        if bad:
            problems.append(f"'{key}': invalid module name(s) {bad!r}")
            continue

        valid[key] = {**entry, 'display_name': display_name}

    if config and not valid:
        raise ValueError(f"no valid module sets found ({len(problems)} invalid entries)")

    return valid, problems


def write_cache(cache_file: str, venvs: list[str], modules: dict) -> None:
    """Atomically write the combined virtualenv and module state to the JupyterHub cache file as JSON.

    The state is written to a temporary file in the same directory and then renamed over the
    cache file, so readers (the spawner) never observe a partially written file.

    Args:
        cache_file: Path to the cache file consumed by the JupyterHub spawner.
        venvs: Virtualenv directory names to record in the cache.
        modules: Module configuration to record in the cache.

    Raises:
        OSError: If the cache file cannot be written.
    """

    cache_dir = os.path.dirname(os.path.abspath(cache_file))
    fd, tmp_path = tempfile.mkstemp(dir=cache_dir, prefix='.config_cache.', suffix='.tmp')

    try:
        with os.fdopen(fd, 'w') as f:
            json.dump({'virtualenvs': venvs, 'modules': modules}, f)
            f.flush()
            os.fsync(f.fileno())

        os.chmod(tmp_path, 0o644)  # mkstemp creates 0600; the spawner may run as another user
        os.replace(tmp_path, cache_file)

    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
