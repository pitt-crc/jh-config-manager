"""Unit tests for the `lmod` module.

Lmod itself is not needed. The tests use a small fake that behaves like the real one where it matters to the code under test:
`module` is a shell function defined by an init script, the listing goes to stderr (stdout carries shell code), directories are
headed by their path, defaults are flagged "(D)", errors come back with a non-zero status, and the tree listed follows MODULEPATH.
"""

import os
import shutil
import tempfile
import time
from unittest import TestCase
from unittest.mock import patch

from jh_config_manager.lmod import discover_modules, find_init_script, parse_avail

# What `module -t avail` prints, copied in shape from Lmod's documentation and typical sites: headers, flags, a folded directory,
# a message, and a blank line.
SAMPLE = """
/software/modulefiles/Core:
StdEnv
amber/24
cuda/12.3.0
cuda/11.8.0(D)
gcc/12.2.0
openmpi/4.1.7-stdwe7
python/
/software/modulefiles/Extra:
Use "module spider" to find all possible modules and extensions.
nccl/2.23.4-1
zlib/1.3 (L)
"""


def fake_lmod_init(directory, body):
    """Write an init script that defines a `module` function with the given bash body, and return its path."""
    path = os.path.join(directory, 'init.sh')
    with open(path, 'w') as f:
        f.write('module() {\n' + body + '\n}\n')
    return path


class ParseAvailFunction(TestCase):
    def test_extracts_the_module_names(self):
        self.assertEqual(
            parse_avail(SAMPLE),
            ['amber/24', 'cuda/11.8.0', 'cuda/12.3.0', 'gcc/12.2.0', 'nccl/2.23.4-1', 'openmpi/4.1.7-stdwe7', 'StdEnv', 'zlib/1.3'])

    def test_removes_flags_but_keeps_the_name(self):
        self.assertEqual(parse_avail('cuda/11.8.0(D)\nzlib/1.3 (L)\ngcc/12.2.0 (D,L)\nfoo/1 (default)'),
                         ['cuda/11.8.0', 'foo/1', 'gcc/12.2.0', 'zlib/1.3'])

    def test_ignores_headers_directories_messages_and_blank_lines(self):
        text = '/a/b:\n\nUse "module spider" to find modules.\ngcc/\nLmod is automatically replacing "x" with "y".\n   \n'
        self.assertEqual(parse_avail(text), [])

    def test_ignores_names_that_are_not_safe_to_use_in_a_shell_command(self):
        text = 'good/1.0\nbad;rm -rf /\n$(id)\nspace name/1\nback`tick`/1\n-flag\nquote"d/1\nsemi:colon/1\n'
        self.assertEqual(parse_avail(text), ['good/1.0'])

    def test_removes_duplicates_and_sorts_ignoring_case(self):
        self.assertEqual(parse_avail('b/1\nA/1\nb/1\na/2\n'), ['A/1', 'a/2', 'b/1'])

    def test_tolerates_windows_line_endings_and_surrounding_whitespace(self):
        self.assertEqual(parse_avail('  gcc/12.2.0  \r\ncuda/12.3.0\r\n'), ['cuda/12.3.0', 'gcc/12.2.0'])

    def test_empty_input(self):
        self.assertEqual(parse_avail(''), [])


class DiscoverModulesFunction(TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_lists_what_lmod_writes_to_stderr(self):
        """Real Lmod writes the listing to stderr and shell code to stdout, and the `module` function evaluates that shell
        code itself, so none of it reaches the caller; the code under test must read the listing from stderr."""
        init = fake_lmod_init(self.tmp, "eval 'true'; printf '%s\\n' 'gcc/12.2.0' 'cuda/12.3.0(D)' >&2")
        self.assertEqual(discover_modules(init), ['cuda/12.3.0', 'gcc/12.2.0'])

    def test_a_listing_on_stdout_is_read_too(self):
        """Not every Lmod version writes to the same stream, so both are read."""
        init = fake_lmod_init(self.tmp, "printf '%s\\n' 'gcc/12.2.0' 'cuda/12.3.0(D)'")
        self.assertEqual(discover_modules(init), ['cuda/12.3.0', 'gcc/12.2.0'])

    def test_passes_the_requested_arguments_to_module(self):
        init = fake_lmod_init(self.tmp, 'if [ "$*" = "-t avail" ]; then echo ok/1 >&2; else echo wrong/1 >&2; exit 3; fi')
        self.assertEqual(discover_modules(init), ['ok/1'])

    def test_follows_the_modulepath_it_is_given(self):
        for tree, names in (('core', ['gcc/12.2.0']), ('apps', ['amber/24', 'cuda/12.3.0'])):
            os.makedirs(os.path.join(self.tmp, tree))
            for name in names:
                os.makedirs(os.path.dirname(os.path.join(self.tmp, tree, name)), exist_ok=True)
                open(os.path.join(self.tmp, tree, name + '.lua'), 'w').close()
        init = fake_lmod_init(self.tmp, r'''
            IFS=: read -ra dirs <<< "$MODULEPATH"
            for d in "${dirs[@]}"; do
                echo "$d:" >&2
                (cd "$d" && find . -name '*.lua' | sed 's#^\./##; s#\.lua$##' | sort) >&2
            done''')

        self.assertEqual(discover_modules(init, modulepath=os.path.join(self.tmp, 'core')), ['gcc/12.2.0'])
        both = f"{os.path.join(self.tmp, 'core')}:{os.path.join(self.tmp, 'apps')}"
        self.assertEqual(discover_modules(init, modulepath=both), ['amber/24', 'cuda/12.3.0', 'gcc/12.2.0'])

    def test_without_a_modulepath_the_services_own_is_used(self):
        init = fake_lmod_init(self.tmp, 'echo "from-env/${MODULEPATH}" >&2')
        with patch.dict(os.environ, {'MODULEPATH': 'x'}):
            self.assertEqual(discover_modules(init), ['from-env/x'])

    def test_turns_off_paging_and_colour(self):
        init = fake_lmod_init(self.tmp, 'echo "p-${LMOD_PAGER}/c-${LMOD_COLORIZE}/t-${TERM}" >&2')
        self.assertEqual(discover_modules(init), ['p-none/c-no/t-dumb'])

    def test_reports_lmods_error_and_exit_status(self):
        init = fake_lmod_init(self.tmp, 'echo "Lmod has detected the following error: MODULEPATH is empty" >&2; return 1')
        with self.assertRaises(RuntimeError) as ctx:
            discover_modules(init)
        self.assertIn('exit status 1', str(ctx.exception))
        self.assertIn('MODULEPATH is empty', str(ctx.exception))

    def test_a_missing_init_script_is_reported(self):
        with self.assertRaises(OSError):
            discover_modules(os.path.join(self.tmp, 'nope.sh'))

    def test_an_init_script_that_fails_to_define_module_is_reported(self):
        path = os.path.join(self.tmp, 'empty.sh')
        open(path, 'w').write('# defines nothing\n')
        with self.assertRaises(RuntimeError):
            discover_modules(path)

    def test_gives_up_on_a_hung_lmod_and_stops_what_it_started(self):
        marker = os.path.join(self.tmp, 'still-running')
        init = fake_lmod_init(self.tmp, f'(sleep 2; touch "{marker}") & sleep 30')
        started = time.monotonic()
        with self.assertRaises(RuntimeError) as ctx:
            discover_modules(init, timeout=1)
        self.assertLess(time.monotonic() - started, 10)
        self.assertIn('did not answer within 1s', str(ctx.exception))
        time.sleep(3)
        self.assertFalse(os.path.exists(marker), 'a process started by Lmod outlived the timeout')

    def test_a_hostile_init_path_is_not_interpreted_as_shell_code(self):
        """The path is handed over as an argument, not spliced into the command."""
        # A file name can hold quotes and semicolons but not slashes, so the injected command creates a file by relative name
        # in the working directory; the test runs from an empty one and checks nothing appeared there.
        path = os.path.join(self.tmp, 'x"; touch pwned; echo "$(touch pwned2)')
        open(path, 'w').write('module() { echo safe/1 >&2; }\n')
        here = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, here)
        self.assertEqual(discover_modules(path), ['safe/1'])
        self.assertFalse(os.path.exists('pwned') or os.path.exists('pwned2'))


class FindInitScriptFunction(TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def make(self, *parts):
        path = os.path.join(self.tmp, *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'w').close()
        return path

    def test_prefers_lmod_pkg(self):
        init = self.make('lmod', 'init', 'bash')
        with patch.dict(os.environ, {'LMOD_PKG': os.path.join(self.tmp, 'lmod')}):
            self.assertEqual(find_init_script(), init)

    def test_falls_back_to_lmod_dir(self):
        init = self.make('lmod', 'init', 'bash')
        os.makedirs(os.path.join(self.tmp, 'lmod', 'libexec'))   # LMOD_DIR is Lmod's libexec directory; the script is beside it
        with patch.dict(os.environ, {'LMOD_DIR': os.path.join(self.tmp, 'lmod', 'libexec')}, clear=False):
            os.environ.pop('LMOD_PKG', None)
            self.assertEqual(find_init_script(), init)

    def test_returns_none_when_nothing_is_found(self):
        with patch.dict(os.environ, {}, clear=True), patch('os.path.isfile', return_value=False):
            self.assertIsNone(find_init_script())
