"""Unit tests for the `create_parser` function."""

import os
from unittest import TestCase
from unittest.mock import patch

from jh_config_manager.cli import (create_parser, DEFAULT_CACHE_FILE, DEFAULT_MODULES_CONFIG_FILE, DEFAULT_RELOAD_INTERVAL, DEFAULT_VENV_ROOT)


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
