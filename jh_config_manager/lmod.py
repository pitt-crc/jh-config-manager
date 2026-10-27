"""Discover the modules users can load, by asking Lmod.

This runs `module -t avail` in a bash that has sourced Lmod's init script, which is the same listing a user gets in a login
shell (including the site's settings), and turns it into a clean list of module names for the spawner's form.

Two things about Lmod shape the code:

* Lmod writes the human-readable listing to **stderr**; stdout carries shell code for the `module` function to evaluate. So the
  command redirects stderr onto stdout, and the output is parsed as text.
* `avail` shows what is loadable *with the current MODULEPATH*. On a flat tree (one directory of module files) that is everything;
  on a hierarchical tree (Core / compiler / MPI) it is only the top level, and modules that need a compiler loaded first do not
  appear until it is. For those, list the directories to include in MODULEPATH (`--modulepath`).

Nothing here is specific to a site. If the listing looks wrong on your system, run `python -m jh_config_manager --lmod_init=...
--dump_modules` to see exactly what was found.
"""

import os
import re
import signal
import subprocess

from .manager import _MODULE_NAME

__all__ = ['find_init_script', 'parse_avail', 'discover_modules']

# Places Lmod's bash init script commonly lives, tried in order after $LMOD_PKG and $LMOD_DIR
_INIT_CANDIDATES = (
    '/etc/profile.d/lmod.sh',
    '/usr/share/lmod/lmod/init/bash',
    '/usr/share/lmod/lmod/init/profile',
    '/opt/apps/lmod/lmod/init/bash',
    '/usr/local/lmod/lmod/init/bash',
)

_TRAILING_FLAGS = re.compile(r'\s*\([^)]*\)\s*$')   # "(D)" default, "(L)" loaded, "(default)" ...


def find_init_script():
    """Return the path of Lmod's bash init script on this machine, or None if it cannot be found."""
    candidates = []
    if os.environ.get('LMOD_PKG'):
        candidates.append(os.path.join(os.environ['LMOD_PKG'], 'init', 'bash'))
    if os.environ.get('LMOD_DIR'):
        candidates.append(os.path.join(os.environ['LMOD_DIR'], '..', 'init', 'bash'))
    candidates.extend(_INIT_CANDIDATES)

    for path in candidates:
        if os.path.isfile(path):
            return os.path.normpath(path)
    return None


def parse_avail(text):
    """Turn the output of `module -t avail` into a sorted list of unique module names.

    Directory headers ("/path/to/modulefiles:"), blank lines, folded directories ("gcc/"), Lmod's messages (anything with spaces
    left over) and names that are not safe to put in a shell command are ignored; trailing flags such as "(D)" are removed.
    """
    names = set()
    for line in text.splitlines():
        line = _TRAILING_FLAGS.sub('', line.strip())
        if not line or line.endswith(':') or line.startswith('/') or line.endswith('/'):
            continue
        if _MODULE_NAME.match(line):
            names.add(line)
    return sorted(names, key=lambda name: (name.lower(), name))


def discover_modules(init_script, modulepath=None, timeout=120):
    """List the available modules by running Lmod.

    Args:
        init_script: Path of Lmod's bash init script (see `find_init_script`).
        modulepath: Optional MODULEPATH to use instead of the one in this process's environment.
        timeout: Seconds to wait for Lmod before giving up.

    Returns:
        The sorted module names.

    Raises:
        OSError: If the init script is missing.
        RuntimeError: If Lmod fails or times out.
    """
    if not os.path.isfile(init_script):
        raise OSError(f'Lmod init script not found: {init_script}')

    env = dict(os.environ)
    env.update(TERM='dumb', LMOD_PAGER='none', LMOD_COLORIZE='no')   # no paging, no colour codes in the listing
    if modulepath:
        env['MODULEPATH'] = modulepath

    # The init script is passed as an argument, never spliced into the command text
    command = 'source "$1" && module -t avail 2>&1'
    proc = subprocess.Popen(
        ['bash', '--noprofile', '--norc', '-c', command, 'jh_config_manager', init_script],
        env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        start_new_session=True,   # so a hung Lmod and everything it started can be stopped together
    )
    try:
        output, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise RuntimeError(f'Lmod did not answer within {timeout}s')

    if proc.returncode != 0:
        tail = ' | '.join(line.strip() for line in output.strip().splitlines()[-3:])
        raise RuntimeError(f'`module avail` failed (exit status {proc.returncode}): {tail}')

    return parse_avail(output)
