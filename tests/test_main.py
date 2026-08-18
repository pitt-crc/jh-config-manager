"""Unit tests for the `main` module."""

from unittest import TestCase
from unittest.mock import patch

from jh_config_manager import __main__ as main_module


@patch.object(main_module, 'time')
@patch.object(main_module, 'start_config_watcher')
@patch.object(main_module, 'create_parser')
class MainFunction(TestCase):
    """Verify command-line startup behavior of `main`."""

    def test_starts_config_watcher_with_parsed_arguments(
        self, mock_create_parser, mock_start_config_watcher, mock_time
    ):
        """Verify the config watcher is started using the parsed command-line arguments."""

        mock_args = mock_create_parser.return_value.parse_args.return_value
        mock_args.venv_root = '/venvs'
        mock_args.modules_config_file = '/modules.json'
        mock_args.cache_file = '/cache.json'
        mock_args.reload_interval = 30
        mock_time.sleep.side_effect = RuntimeError('stop loop')

        with self.assertRaises(RuntimeError):
            main_module.main()

        mock_start_config_watcher.assert_called_once_with(
            venv_root='/venvs',
            modules_config_file='/modules.json',
            cache_file='/cache.json',
            reload_interval=30,
        )
