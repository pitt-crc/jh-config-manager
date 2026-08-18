"""Unit tests for the `manager` module."""

import json
import os
import shutil
import tempfile
from unittest import TestCase

from jh_config_manager.manager import get_virtualenvs, load_modules_config, write_cache


class GetVirtualenvsFunction(TestCase):
    """Verify directory discovery behavior of `get_virtualenvs`."""

    def setUp(self):
        """Create test fixtures using mock data."""

        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Remove the temporary directory created for the test."""

        shutil.rmtree(self.temp_dir)

    def test_returns_sorted_virtualenv_directory_names(self):
        """Verify virtualenv directories are returned sorted by name."""

        os.mkdir(os.path.join(self.temp_dir, 'zeta'))
        os.mkdir(os.path.join(self.temp_dir, 'alpha'))

        result = get_virtualenvs(self.temp_dir)

        self.assertEqual(result, ['alpha', 'zeta'])

    def test_excludes_files_from_results(self):
        """Verify non-directory entries are excluded from the results."""

        os.mkdir(os.path.join(self.temp_dir, 'envname'))
        open(os.path.join(self.temp_dir, 'not_a_dir.txt'), 'w').close()

        result = get_virtualenvs(self.temp_dir)

        self.assertEqual(result, ['envname'])

    def test_returns_empty_list_for_unreadable_root(self):
        """Verify an empty list is returned when the root directory cannot be scanned."""

        result = get_virtualenvs(os.path.join(self.temp_dir, 'does_not_exist'))

        self.assertEqual(result, [], 'Expected empty list when venv_root cannot be scanned')


class LoadModulesConfigFunction(TestCase):
    """Verify JSON parsing behavior of `load_modules_config`."""

    def setUp(self):
        """Create test fixtures using mock data."""

        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'modules.json')

    def tearDown(self):
        """Remove the temporary directory created for the test."""

        shutil.rmtree(self.temp_dir)

    def test_returns_parsed_module_configuration(self):
        """Verify the module configuration file is parsed into a dict."""

        data = {'python': ['3.11', '3.12']}
        with open(self.config_file, 'w') as f:
            json.dump(data, f)

        result = load_modules_config(self.config_file)

        self.assertEqual(result, data)

    def test_returns_empty_dict_for_missing_file(self):
        """Verify an empty dict is returned when the config file cannot be read."""

        result = load_modules_config(os.path.join(self.temp_dir, 'missing.json'))

        self.assertEqual(result, {}, 'Expected empty dict when modules_config_file cannot be read')

    def test_returns_empty_dict_for_malformed_json(self):
        """Verify an empty dict is returned when the config file contains invalid JSON."""

        with open(self.config_file, 'w') as f:
            f.write('{not valid json')

        result = load_modules_config(self.config_file)

        self.assertEqual(result, {})


class WriteCacheFunction(TestCase):
    """Verify cache-file serialization behavior of `write_cache`."""

    def setUp(self):
        """Create test fixtures using mock data."""

        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, 'cache.json')

    def tearDown(self):
        """Remove the temporary directory created for the test."""

        shutil.rmtree(self.temp_dir)

    def test_writes_combined_venv_and_module_state(self):
        """Verify virtualenvs and modules are written to the cache file as JSON."""

        write_cache(self.cache_file, ['alpha', 'beta'], {'python': ['3.12']})

        with open(self.cache_file) as f:
            result = json.load(f)

        self.assertEqual(result, {'virtualenvs': ['alpha', 'beta'], 'modules': {'python': ['3.12']}})

    def test_produces_no_cache_file_for_unwritable_path(self):
        """Verify write_cache produces no cache file when the target path cannot be written."""

        unwritable_path = os.path.join(self.temp_dir, 'missing_dir', 'cache.json')

        write_cache(unwritable_path, [], {})

        self.assertFalse(os.path.exists(unwritable_path))
