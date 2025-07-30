import os
import tempfile
import json
from jh_config_manager import manager


def test_write_and_read_cache():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = os.path.join(tmpdir, "cache.json")
        venvs = ['env1', 'env2']
        modules = {'mod1': {'modules': ['a']}}

        manager.write_cache(cache_file, venvs, modules)

        with open(cache_file) as f:
            data = json.load(f)

        assert data['virtualenvs'] == venvs
        assert data['modules'] == modules
