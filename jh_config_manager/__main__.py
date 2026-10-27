"""Command-line entry point for running the JupyterHub config manager service."""

import sys
import time

from .cli import create_parser
from .lmod import discover_modules
from .service import resolve_lmod_init, start_config_watcher

__all__ = ['main']


def dump_modules(lmod_init: str, modulepath: str) -> int:
    """Diagnostic for `--dump_modules`: print what module discovery finds, and return the exit status."""

    init_script = resolve_lmod_init(lmod_init)
    if not init_script:
        print("Give Lmod's init script with --lmod_init (for example /etc/profile.d/lmod.sh), or --lmod_init=auto.",
              file=sys.stderr)
        return 2

    try:
        found = discover_modules(init_script, modulepath or None)
    except Exception as e:
        print(f"Could not list modules with {init_script}: {e}", file=sys.stderr)
        return 1

    for name in found:
        print(name)
    print(f"{len(found)} modules found through {init_script}"
          + (f" with MODULEPATH={modulepath}" if modulepath else " with the service's own MODULEPATH"), file=sys.stderr)
    return 0 if found else 1


def main() -> None:
    """Parse command-line arguments and start the config manager service."""

    parser = create_parser()
    args = parser.parse_args()

    if args.dump_modules:
        sys.exit(dump_modules(args.lmod_init, args.modulepath))

    watcher = start_config_watcher(
        venv_root=args.venv_root,
        modules_config_file=args.modules_config_file,
        cache_file=args.cache_file,
        reload_interval=args.reload_interval,
        lmod_init=args.lmod_init,
        modulepath=args.modulepath,
        modules_scan_interval=args.modules_scan_interval,
    )

    print("[jh_config_manager] Service running. Watching for changes...")
    while watcher.is_alive():
        time.sleep(60)

    # Exit non-zero so JupyterHub notices the service is no longer refreshing the cache.
    print("[jh_config_manager] Config watcher thread stopped unexpectedly. Exiting.")
    sys.exit(1)


if __name__ == "__main__":
    main()
