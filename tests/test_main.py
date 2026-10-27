"""Unit tests for the `main` module."""

import io
from contextlib import redirect_stderr, redirect_stdout
from unittest import TestCase
from unittest.mock import patch

from jh_config_manager import __main__ as main_module


def parsed_args(**overrides):
    """A stand-in for the parsed command line, with every option set."""
    values = dict(venv_root='/venvs', modules_config_file='/modules.json', cache_file='/cache.json', reload_interval=30,
                  lmod_init='', modulepath='', modules_scan_interval=600, dump_modules=False)
    values.update(overrides)
    return type('Args', (), values)()


@patch.object(main_module, 'time')
@patch.object(main_module, 'start_config_watcher')
@patch.object(main_module, 'create_parser')
class MainFunction(TestCase):
    """Verify command-line startup behavior of `main`."""

    def test_starts_config_watcher_with_parsed_arguments(
        self, mock_create_parser, mock_start_config_watcher, mock_time
    ):
        """Verify the config watcher is started using the parsed command-line arguments."""

        mock_create_parser.return_value.parse_args.return_value = parsed_args()
        mock_time.sleep.side_effect = RuntimeError('stop loop')

        with self.assertRaises(RuntimeError):
            main_module.main()

        mock_start_config_watcher.assert_called_once_with(
            venv_root='/venvs',
            modules_config_file='/modules.json',
            cache_file='/cache.json',
            reload_interval=30,
            lmod_init='',
            modulepath='',
            modules_scan_interval=600,
        )

    def test_passes_the_module_discovery_options_on(self, mock_create_parser, mock_start_config_watcher, mock_time):
        mock_create_parser.return_value.parse_args.return_value = parsed_args(
            lmod_init='/etc/profile.d/lmod.sh', modulepath='/a:/b', modules_scan_interval=60)
        mock_time.sleep.side_effect = RuntimeError('stop loop')

        with self.assertRaises(RuntimeError):
            main_module.main()

        kwargs = mock_start_config_watcher.call_args.kwargs
        self.assertEqual((kwargs['lmod_init'], kwargs['modulepath'], kwargs['modules_scan_interval']),
                         ('/etc/profile.d/lmod.sh', '/a:/b', 60))

    def test_exits_nonzero_when_config_watcher_thread_dies(
        self, mock_create_parser, mock_start_config_watcher, mock_time
    ):
        """Verify the service exits with a failure status if the watcher thread stops, so the Hub restarts it."""

        mock_create_parser.return_value.parse_args.return_value = parsed_args()
        mock_start_config_watcher.return_value.is_alive.return_value = False

        with self.assertRaises(SystemExit) as ctx:
            main_module.main()

        self.assertEqual(ctx.exception.code, 1)


@patch.object(main_module, 'start_config_watcher')
@patch.object(main_module, 'create_parser')
class DumpModulesOption(TestCase):
    """`--dump_modules` is a diagnostic: it prints what discovery finds and does not start the service."""

    def run_main(self, mock_create_parser, **overrides):
        mock_create_parser.return_value.parse_args.return_value = parsed_args(dump_modules=True, **overrides)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err), self.assertRaises(SystemExit) as ctx:
            main_module.main()
        return ctx.exception.code, out.getvalue(), err.getvalue()

    def test_prints_the_modules_and_a_summary(self, mock_create_parser, mock_start_config_watcher):
        with patch.object(main_module, 'discover_modules', return_value=['cuda/12.3.0', 'gcc/12.2.0']) as discover:
            code, out, err = self.run_main(mock_create_parser, lmod_init='/etc/profile.d/lmod.sh', modulepath='/a:/b')

        self.assertEqual(code, 0)
        self.assertEqual(out.split(), ['cuda/12.3.0', 'gcc/12.2.0'])
        self.assertIn('2 modules found', err)
        self.assertIn('MODULEPATH=/a:/b', err)
        discover.assert_called_once_with('/etc/profile.d/lmod.sh', '/a:/b')
        mock_start_config_watcher.assert_not_called()

    def test_reports_a_failure_with_the_reason(self, mock_create_parser, mock_start_config_watcher):
        with patch.object(main_module, 'discover_modules', side_effect=RuntimeError('boom')):
            code, out, err = self.run_main(mock_create_parser, lmod_init='/etc/profile.d/lmod.sh')

        self.assertEqual(code, 1)
        self.assertIn('boom', err)
        self.assertEqual(out, '')

    def test_an_empty_result_is_a_failure_so_scripts_notice(self, mock_create_parser, mock_start_config_watcher):
        with patch.object(main_module, 'discover_modules', return_value=[]):
            code, _, err = self.run_main(mock_create_parser, lmod_init='/etc/profile.d/lmod.sh')

        self.assertEqual(code, 1)
        self.assertIn('0 modules found', err)

    def test_asks_for_the_init_script_when_none_is_given(self, mock_create_parser, mock_start_config_watcher):
        code, _, err = self.run_main(mock_create_parser)

        self.assertEqual(code, 2)
        self.assertIn('--lmod_init', err)
