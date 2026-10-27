"""Unit tests for the `create_parser` function."""

import os
from unittest import TestCase
from unittest.mock import patch

from jh_config_manager.cli import *


class CreateParserFunction(TestCase):
    """Verify argument and environment-variable defaulting behavior of `create_parser`."""

    @patch.dict(os.environ, {}, clear=True)
    def test_uses_module_constants_when_environment_unset(self):
        """Verify parser defaults fall back to the module-level constants when no environment variables are set."""

        args = create_parser().parse_args([])

        self.assertEqual(args.venv_root, DEFAULT_VENV_ROOT)
        self.assertEqual(args.modules_config_file, DEFAULT_MODULES_CONFIG_FILE)
        self.assertEqual(args.cache_file, DEFAULT_CACHE_FILE)
        self.assertEqual(args.reload_interval, DEFAULT_RELOAD_INTERVAL)

    @patch.dict(
        os.environ,
        {
            'VENV_ROOT': '/custom/venvs',
            'MODULES_CONFIG_FILE': '/custom/modules.json',
            'CACHE_FILE': '/custom/cache.json',
            'RELOAD_INTERVAL': '60',
        },
        clear=True,
    )
    def test_uses_environment_variables_as_defaults(self):
        """Verify parser defaults are overridden by environment variables when present."""

        args = create_parser().parse_args([])

        self.assertEqual(args.venv_root, '/custom/venvs')
        self.assertEqual(args.modules_config_file, '/custom/modules.json')
        self.assertEqual(args.cache_file, '/custom/cache.json')
        self.assertEqual(args.reload_interval, 60)

    @patch.dict(os.environ, {}, clear=True)
    def test_command_line_arguments_override_defaults(self):
        """Verify explicit command-line arguments take precedence over defaults."""

        args = create_parser().parse_args([
            '-v', '/explicit/venvs',
            '-m', '/explicit/modules.json',
            '-c', '/explicit/cache.json',
            '-r', '15',
        ])

        self.assertEqual(args.venv_root, '/explicit/venvs')
        self.assertEqual(args.modules_config_file, '/explicit/modules.json')
        self.assertEqual(args.cache_file, '/explicit/cache.json')
        self.assertEqual(args.reload_interval, 15)

    @patch.dict(os.environ, {'RELOAD_INTERVAL': 'abc'}, clear=True)
    def test_rejects_non_numeric_reload_interval_from_environment(self):
        """Verify a non-numeric RELOAD_INTERVAL produces a clean usage error instead of a traceback."""

        with patch('sys.stderr'), self.assertRaises(SystemExit) as ctx:
            create_parser().parse_args([])

        self.assertEqual(ctx.exception.code, 2)

    @patch.dict(os.environ, {}, clear=True)
    def test_rejects_non_positive_reload_interval(self):
        """Verify a reload interval below 1 is rejected, since 0 would busy-loop the scanner."""

        for value in ('0', '-5'):
            with self.subTest(value=value), patch('sys.stderr'), self.assertRaises(SystemExit):
                create_parser().parse_args(['-r', value])


class ModuleDiscoveryOptions(TestCase):
    """Options for listing the modules Lmod offers."""

    @patch.dict(os.environ, {}, clear=True)
    def test_discovery_is_off_by_default(self):
        args = create_parser().parse_args([])

        self.assertEqual(args.lmod_init, '')
        self.assertEqual(args.modulepath, '')
        self.assertEqual(args.modules_scan_interval, DEFAULT_MODULES_SCAN_INTERVAL)
        self.assertFalse(args.dump_modules)

    @patch.dict(os.environ, {'LMOD_INIT_FILE': '/etc/profile.d/lmod.sh', 'JH_MODULEPATH': '/a:/b', 'MODULES_SCAN_INTERVAL': '90'},
                clear=True)
    def test_environment_variables_set_the_defaults(self):
        args = create_parser().parse_args([])

        self.assertEqual((args.lmod_init, args.modulepath, args.modules_scan_interval), ('/etc/profile.d/lmod.sh', '/a:/b', 90))

    @patch.dict(os.environ, {'LMOD_INIT_FILE': '/from/env'}, clear=True)
    def test_command_line_arguments_win(self):
        args = create_parser().parse_args(['-l', 'auto', '-p', '/x', '-s', '30', '--dump_modules'])

        self.assertEqual((args.lmod_init, args.modulepath, args.modules_scan_interval, args.dump_modules), ('auto', '/x', 30, True))

    @patch.dict(os.environ, {}, clear=True)
    def test_the_scan_interval_must_be_a_positive_number(self):
        for value in ('0', '-5', 'abc'):
            with self.subTest(value=value), patch('sys.stderr'), self.assertRaises(SystemExit):
                create_parser().parse_args(['-s', value])

    @patch.dict(os.environ, {'MODULES_SCAN_INTERVAL': 'soon'}, clear=True)
    def test_a_bad_scan_interval_in_the_environment_is_a_usage_error(self):
        with patch('sys.stderr'), self.assertRaises(SystemExit) as ctx:
            create_parser().parse_args([])

        self.assertEqual(ctx.exception.code, 2)
