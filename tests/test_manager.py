"""Unit tests for the `manager` module."""

import json
import os
import shutil
import tempfile
from unittest import TestCase

from jh_config_manager.manager import *


class GetVirtualenvsFunction(TestCase):
    """Verify directory discovery behavior of `get_virtualenvs`."""

    def setUp(self):
        """Create test fixtures using mock data."""

        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Remove the temporary directory created for the test."""

        shutil.rmtree(self.temp_dir)

    def make_venv(self, name):
        """Create a `venv`-style environment directory under the temporary root."""

        path = os.path.join(self.temp_dir, name)
        os.mkdir(path)
        open(os.path.join(path, 'pyvenv.cfg'), 'w').close()
        return path

    def test_returns_sorted_virtualenv_directory_names(self):
        """Verify virtualenv directories are returned sorted by name."""

        self.make_venv('zeta')
        self.make_venv('alpha')

        result = get_virtualenvs(self.temp_dir)

        self.assertEqual(result, ['alpha', 'zeta'])

    def test_excludes_files_from_results(self):
        """Verify non-directory entries are excluded from the results."""

        self.make_venv('envname')
        open(os.path.join(self.temp_dir, 'not_a_dir.txt'), 'w').close()

        result = get_virtualenvs(self.temp_dir)

        self.assertEqual(result, ['envname'])

    def test_excludes_directories_that_are_not_environments(self):
        """Verify plain directories, such as backups or scratch space, are not listed."""

        self.make_venv('real')
        os.mkdir(os.path.join(self.temp_dir, 'backup'))

        result = get_virtualenvs(self.temp_dir)

        self.assertEqual(result, ['real'])

    def test_excludes_hidden_directories(self):
        """Verify hidden environment directories are not listed."""

        self.make_venv('.hidden')
        self.make_venv('visible')

        result = get_virtualenvs(self.temp_dir)

        self.assertEqual(result, ['visible'])

    def test_includes_conda_environments(self):
        """Verify a conda environment, identified by `conda-meta`, is listed."""

        os.makedirs(os.path.join(self.temp_dir, 'condaenv', 'conda-meta'))

        result = get_virtualenvs(self.temp_dir)

        self.assertEqual(result, ['condaenv'])

    def test_includes_directories_with_a_python_interpreter(self):
        """Verify a directory containing `bin/python` is listed even without other markers."""

        os.makedirs(os.path.join(self.temp_dir, 'bare', 'bin'))
        open(os.path.join(self.temp_dir, 'bare', 'bin', 'python'), 'w').close()

        result = get_virtualenvs(self.temp_dir)

        self.assertEqual(result, ['bare'])

    def test_raises_for_unreadable_root(self):
        """Verify OSError propagates when the root directory cannot be scanned, so callers can keep prior state."""

        with self.assertRaises(OSError):
            get_virtualenvs(os.path.join(self.temp_dir, 'does_not_exist'))


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

    def test_raises_for_missing_file(self):
        """Verify OSError propagates when the config file cannot be read."""

        with self.assertRaises(OSError):
            load_modules_config(os.path.join(self.temp_dir, 'missing.json'))

    def test_raises_for_malformed_json(self):
        """Verify ValueError propagates when the config file contains invalid JSON."""

        with open(self.config_file, 'w') as f:
            f.write('{not valid json')

        with self.assertRaises(ValueError):
            load_modules_config(self.config_file)

    def test_raises_for_non_object_top_level(self):
        """Verify ValueError propagates when the config file is valid JSON but not an object."""

        with open(self.config_file, 'w') as f:
            json.dump(['not', 'an', 'object'], f)

        with self.assertRaises(ValueError):
            load_modules_config(self.config_file)


class ValidateModulesConfigFunction(TestCase):
    """Verify entry filtering behavior of `validate_modules_config`."""

    def test_returns_valid_entries_unchanged(self):
        """Verify well-formed entries pass through with no problems reported."""

        config = {'amber24': {'display_name': 'Amber 2024', 'modules': ['openmpi/4.1.7-stdwe7', 'amber/24']}}

        valid, problems = validate_modules_config(config)

        self.assertEqual(valid, config)
        self.assertEqual(problems, [])

    def test_returns_empty_result_for_empty_config(self):
        """Verify an empty configuration is valid, since an admin may legitimately offer no module sets."""

        self.assertEqual(validate_modules_config({}), ({}, []))

    def test_defaults_missing_display_name_to_key(self):
        """Verify a missing display_name falls back to the entry key."""

        valid, problems = validate_modules_config({'cuda123': {'modules': ['cuda/12.3.0']}})

        self.assertEqual(valid['cuda123']['display_name'], 'cuda123')
        self.assertEqual(problems, [])

    def test_drops_invalid_entries_and_keeps_valid_ones(self):
        """Verify each malformed entry is dropped with a problem message while valid ones survive."""

        config = {
            'good': {'display_name': 'Good', 'modules': ['gcc/12.2.0']},
            'not_an_object': 'gcc',
            'no_modules': {'display_name': 'X'},
            'empty_modules': {'display_name': 'X', 'modules': []},
            'modules_not_list': {'display_name': 'X', 'modules': 'gcc/12.2.0'},
            'bad_display_name': {'display_name': 5, 'modules': ['gcc']},
            'blank_display_name': {'display_name': '  ', 'modules': ['gcc']},
        }

        valid, problems = validate_modules_config(config)

        self.assertEqual(list(valid), ['good'])
        self.assertEqual(len(problems), 6)

    def test_drops_entries_with_unsafe_module_names(self):
        """Verify module names that would break the spawner's ':'-joined list or the shell are rejected."""

        unsafe = ['gcc:12', 'gcc 12', 'gcc;rm -rf', '$(id)', '', '-flag', 5, None]
        config = {f'set{i}': {'modules': ['gcc/12', name]} for i, name in enumerate(unsafe)}
        config['ok'] = {'modules': ['gcc/12']}

        valid, problems = validate_modules_config(config)

        self.assertEqual(list(valid), ['ok'])
        self.assertEqual(len(problems), len(unsafe))

    def test_raises_when_no_entry_is_valid(self):
        """Verify ValueError is raised when every entry is invalid, so the caller keeps its previous state."""

        with self.assertRaises(ValueError):
            validate_modules_config({'bad': {'modules': []}})


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

    def test_raises_and_produces_no_cache_file_for_unwritable_path(self):
        """Verify OSError propagates and no cache file is produced when the target directory is missing."""

        unwritable_path = os.path.join(self.temp_dir, 'missing_dir', 'cache.json')

        with self.assertRaises(OSError):
            write_cache(unwritable_path, [], {})

        self.assertFalse(os.path.exists(unwritable_path))

    def test_replaces_existing_cache_file(self):
        """Verify an existing cache file is fully replaced by the new state."""

        write_cache(self.cache_file, ['old'], {'old': {}})
        write_cache(self.cache_file, ['new'], {})

        with open(self.cache_file) as f:
            result = json.load(f)

        self.assertEqual(result, {'virtualenvs': ['new'], 'modules': {}})

    def test_leaves_no_temporary_files_after_success(self):
        """Verify only the cache file remains in the directory after a successful write."""

        write_cache(self.cache_file, ['alpha'], {})

        self.assertEqual(os.listdir(self.temp_dir), ['cache.json'])

    def test_preserves_existing_cache_and_cleans_up_when_serialization_fails(self):
        """Verify a failed write leaves the prior cache intact and removes the temporary file."""

        write_cache(self.cache_file, ['good'], {})

        with self.assertRaises(TypeError):
            write_cache(self.cache_file, ['bad'], {'unserializable': object()})

        with open(self.cache_file) as f:
            result = json.load(f)

        self.assertEqual(result, {'virtualenvs': ['good'], 'modules': {}})
        self.assertEqual(os.listdir(self.temp_dir), ['cache.json'])

    def test_cache_file_is_world_readable(self):
        """Verify the cache file is readable by other users, such as the spawner's account."""

        write_cache(self.cache_file, [], {})

        self.assertEqual(os.stat(self.cache_file).st_mode & 0o777, 0o644)
