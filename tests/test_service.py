"""Unit tests for the `service` module."""

from threading import Thread
from unittest import TestCase
from unittest.mock import patch

from jh_config_manager import service

CUDA_MODULES = {'cuda': {'display_name': 'CUDA', 'modules': ['cuda/12.3.0']}}


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

    def test_writes_cache_on_first_scan_even_when_empty(
        self, mock_sleep, mock_get_virtualenvs, mock_load_modules_config, mock_write_cache
    ):
        """Verify the cache file is created on the first scan even if there are no virtualenvs or modules."""

        mock_get_virtualenvs.return_value = []
        mock_load_modules_config.return_value = {}
        mock_sleep.side_effect = RuntimeError('stop loop')

        result = service.start_config_watcher('venv_root', 'modules.json', 'cache.json', 30)
        result.join(timeout=1)

        mock_write_cache.assert_called_once_with('cache.json', [], {})

    def test_produces_no_cache_write_when_state_is_unchanged(
        self, mock_sleep, mock_get_virtualenvs, mock_load_modules_config, mock_write_cache
    ):
        """Verify write_cache is called once across repeated scans that return identical state."""

        mock_get_virtualenvs.return_value = ['alpha']
        mock_load_modules_config.return_value = {}
        mock_sleep.side_effect = [None, None, RuntimeError('stop loop')]

        result = service.start_config_watcher('venv_root', 'modules.json', 'cache.json', 30)
        result.join(timeout=1)

        self.assertEqual(mock_write_cache.call_count, 1)

    def test_keeps_previous_virtualenvs_when_scan_fails(
        self, mock_sleep, mock_get_virtualenvs, mock_load_modules_config, mock_write_cache
    ):
        """Verify a failed virtualenv scan does not overwrite the cache with an empty list."""

        mock_get_virtualenvs.side_effect = [['alpha'], OSError('NFS hiccup'), ['alpha']]
        mock_load_modules_config.return_value = {}
        mock_sleep.side_effect = [None, None, RuntimeError('stop loop')]

        result = service.start_config_watcher('venv_root', 'modules.json', 'cache.json', 30)
        result.join(timeout=1)

        mock_write_cache.assert_called_once_with('cache.json', ['alpha'], {})

    def test_keeps_previous_modules_when_config_becomes_invalid(
        self, mock_sleep, mock_get_virtualenvs, mock_load_modules_config, mock_write_cache
    ):
        """Verify a malformed modules file does not overwrite the cache with empty modules."""

        mock_get_virtualenvs.return_value = ['alpha']
        mock_load_modules_config.side_effect = [CUDA_MODULES, ValueError('bad json')]
        mock_sleep.side_effect = [None, RuntimeError('stop loop')]

        result = service.start_config_watcher('venv_root', 'modules.json', 'cache.json', 30)
        result.join(timeout=1)

        mock_write_cache.assert_called_once_with('cache.json', ['alpha'], CUDA_MODULES)

    def test_skips_write_until_both_sources_have_loaded_once(
        self, mock_sleep, mock_get_virtualenvs, mock_load_modules_config, mock_write_cache
    ):
        """Verify nothing is written while a source has never loaded, protecting any pre-existing cache."""

        mock_get_virtualenvs.return_value = ['alpha']
        mock_load_modules_config.side_effect = OSError('missing')
        mock_sleep.side_effect = RuntimeError('stop loop')

        result = service.start_config_watcher('venv_root', 'modules.json', 'cache.json', 30)
        result.join(timeout=1)

        mock_write_cache.assert_not_called()

    def test_retries_cache_write_after_failure(
        self, mock_sleep, mock_get_virtualenvs, mock_load_modules_config, mock_write_cache
    ):
        """Verify a failed write is retried on the next scan even though the scanned state is unchanged."""

        mock_get_virtualenvs.return_value = ['alpha']
        mock_load_modules_config.return_value = {}
        mock_write_cache.side_effect = [OSError('disk full'), None]
        mock_sleep.side_effect = [None, None, RuntimeError('stop loop')]

        result = service.start_config_watcher('venv_root', 'modules.json', 'cache.json', 30)
        result.join(timeout=1)

        self.assertEqual(mock_write_cache.call_count, 2)

    def test_publishes_only_valid_module_sets(
        self, mock_sleep, mock_get_virtualenvs, mock_load_modules_config, mock_write_cache
    ):
        """Verify malformed module sets are dropped from the cache while valid ones are still published."""

        mock_get_virtualenvs.return_value = ['alpha']
        mock_load_modules_config.return_value = {**CUDA_MODULES, 'broken': {'modules': []}}
        mock_sleep.side_effect = RuntimeError('stop loop')

        result = service.start_config_watcher('venv_root', 'modules.json', 'cache.json', 30)
        result.join(timeout=1)

        mock_write_cache.assert_called_once_with('cache.json', ['alpha'], CUDA_MODULES)

    def test_keeps_previous_modules_when_every_module_set_is_invalid(
        self, mock_sleep, mock_get_virtualenvs, mock_load_modules_config, mock_write_cache
    ):
        """Verify a modules file with no valid entries does not wipe the previously published modules."""

        mock_get_virtualenvs.return_value = ['alpha']
        mock_load_modules_config.side_effect = [CUDA_MODULES, {'broken': {'modules': []}}]
        mock_sleep.side_effect = [None, RuntimeError('stop loop')]

        result = service.start_config_watcher('venv_root', 'modules.json', 'cache.json', 30)
        result.join(timeout=1)

        mock_write_cache.assert_called_once_with('cache.json', ['alpha'], CUDA_MODULES)
