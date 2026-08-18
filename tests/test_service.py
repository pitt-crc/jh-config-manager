"""Unit tests for the `service` module."""

from threading import Thread
from unittest import TestCase
from unittest.mock import patch

from jh_config_manager import service


@patch.object(service, 'write_cache')
@patch.object(service, 'load_modules_config')
@patch.object(service, 'get_virtualenvs')
@patch.object(service.time, 'sleep')
class StartConfigWatcherFunction(TestCase):
    """Verify the background cache-refresh behavior of `start_config_watcher`."""

    def test_returns_started_daemon_thread(
        self, mock_sleep, mock_get_virtualenvs, mock_load_modules_config, mock_write_cache
    ):
        """Verify a started daemon thread is returned."""

        mock_get_virtualenvs.return_value = []
        mock_load_modules_config.return_value = {}
        mock_sleep.side_effect = RuntimeError('stop loop')

        result = service.start_config_watcher('venv_root', 'modules.json', 'cache.json', 30)
        result.join(timeout=1)

        self.assertIsInstance(result, Thread)
        self.assertTrue(result.daemon, 'Expected the config watcher thread to run as a daemon')

    def test_writes_cache_when_virtualenvs_change(
        self, mock_sleep, mock_get_virtualenvs, mock_load_modules_config, mock_write_cache
    ):
        """Verify the cache is written when the discovered virtualenvs differ from the prior scan."""

        mock_get_virtualenvs.return_value = ['alpha']
        mock_load_modules_config.return_value = {}
        mock_sleep.side_effect = RuntimeError('stop loop')

        result = service.start_config_watcher('venv_root', 'modules.json', 'cache.json', 30)
        result.join(timeout=1)

        mock_write_cache.assert_called_once_with('cache.json', ['alpha'], {})

    def test_produces_no_cache_write_when_state_is_unchanged(
        self, mock_sleep, mock_get_virtualenvs, mock_load_modules_config, mock_write_cache
    ):
        """Verify write_cache produces no call when the scanned state matches the prior iteration."""

        mock_get_virtualenvs.return_value = []
        mock_load_modules_config.return_value = {}
        mock_sleep.side_effect = RuntimeError('stop loop')

        result = service.start_config_watcher('venv_root', 'modules.json', 'cache.json', 30)
        result.join(timeout=1)

        mock_write_cache.assert_not_called()
