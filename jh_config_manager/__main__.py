"""Command-line entry point for running the JupyterHub config manager service."""

import time

from .cli import create_parser
from .service import start_config_watcher

__all__ = ['main']


def main() -> None:
    """Parse command-line arguments and start the config manager service."""

    parser = create_parser()
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
