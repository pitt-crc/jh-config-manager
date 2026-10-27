"""Unit tests for module discovery inside the `service` module's refresh loop."""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from jh_config_manager import service

SETS = {'cuda': {'display_name': 'CUDA', 'modules': ['cuda/12.3.0']}}


class Clock:
    """A fake clock: every sleep() advances time by the sleep length and, after `ticks` sleeps, stops the loop."""

    def __init__(self, ticks):
        self.now = 0.0
        self.ticks = ticks

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds
        self.ticks -= 1
        if self.ticks <= 0:
            raise RuntimeError('stop loop')


class RunWatcher(TestCase):
    def run_watcher(self, ticks=1, reload_interval=30, scan_results=(), **kwargs):
        """Run the refresh loop for `ticks` iterations; return (write_cache mock, discover_modules mock)."""
        clock = Clock(ticks)
        fake_time = MagicMock(monotonic=clock.monotonic, sleep=clock.sleep)
        with patch.object(service, 'time', fake_time), \
                patch.object(service, 'get_virtualenvs', return_value=['tf']), \
                patch.object(service, 'load_modules_config', return_value=SETS), \
                patch.object(service, 'write_cache') as write_cache, \
                patch.object(service, 'discover_modules', side_effect=list(scan_results)) as discover:
            thread = service.start_config_watcher('venvs', 'modules.json', 'cache.json', reload_interval, **kwargs)
            thread.join(timeout=10)
        return write_cache, discover


class DiscoveryOff(RunWatcher):
    def test_no_scan_and_the_cache_format_is_unchanged(self):
        write_cache, discover = self.run_watcher(ticks=3)

        discover.assert_not_called()
        write_cache.assert_called_once_with('cache.json', ['tf'], SETS)   # exactly three arguments, as before

    def test_an_empty_init_script_means_off(self):
        _, discover = self.run_watcher(lmod_init='')
        discover.assert_not_called()


class DiscoveryOn(RunWatcher):
    def test_the_first_scan_happens_before_the_first_write(self):
        write_cache, discover = self.run_watcher(scan_results=[['cuda/12.3.0', 'gcc/12.2.0']], lmod_init='/lmod/init')

        discover.assert_called_once_with('/lmod/init', None)
        write_cache.assert_called_once_with('cache.json', ['tf'], SETS, ['cuda/12.3.0', 'gcc/12.2.0'])

    def test_the_modulepath_is_passed_on(self):
        _, discover = self.run_watcher(scan_results=[['a/1']], lmod_init='/lmod/init', modulepath='/x:/y')
        discover.assert_called_once_with('/lmod/init', '/x:/y')

    def test_scans_are_spaced_by_their_own_interval_not_the_reload_interval(self):
        # reload every 30 s, scan every 100 s: ticks at t=0,30,60,90,120 -> scans at t=0 and t=120
        _, discover = self.run_watcher(ticks=5, reload_interval=30, modules_scan_interval=100,
                                       scan_results=[['a/1'], ['a/1']], lmod_init='/lmod/init')
        self.assertEqual(discover.call_count, 2)

    def test_the_cache_is_rewritten_only_when_the_list_changes(self):
        write_cache, discover = self.run_watcher(ticks=4, reload_interval=100, modules_scan_interval=100,
                                                 scan_results=[['a/1'], ['a/1'], ['a/1', 'b/2'], ['a/1', 'b/2']],
                                                 lmod_init='/lmod/init')
        self.assertEqual(discover.call_count, 4)
        self.assertEqual([c.args[3] for c in write_cache.call_args_list], [['a/1'], ['a/1', 'b/2']])

    def test_a_failed_scan_keeps_the_previous_list(self):
        write_cache, _ = self.run_watcher(ticks=3, reload_interval=100, modules_scan_interval=100,
                                          scan_results=[['a/1'], RuntimeError('NFS hiccup'), RuntimeError('still down')],
                                          lmod_init='/lmod/init')
        self.assertEqual([c.args[3] for c in write_cache.call_args_list], [['a/1']])   # never replaced by None or []

    def test_an_empty_scan_keeps_the_previous_list(self):
        """MODULEPATH lost, or Lmod briefly unable to read the tree: do not make the picker disappear."""
        write_cache, _ = self.run_watcher(ticks=2, reload_interval=100, modules_scan_interval=100,
                                          scan_results=[['a/1'], []], lmod_init='/lmod/init')
        self.assertEqual([c.args[3] for c in write_cache.call_args_list], [['a/1']])

    def test_a_first_scan_that_fails_still_writes_the_cache_without_a_list(self):
        """The rest of the cache (environments, module sets) must not wait for or depend on Lmod."""
        write_cache, _ = self.run_watcher(ticks=2, reload_interval=100, modules_scan_interval=100,
                                          scan_results=[RuntimeError('no Lmod'), ['a/1']], lmod_init='/lmod/init')
        self.assertEqual([c.args[3] for c in write_cache.call_args_list], [None, ['a/1']])

    def test_a_first_empty_scan_writes_no_list(self):
        write_cache, _ = self.run_watcher(scan_results=[[]], lmod_init='/lmod/init')
        write_cache.assert_called_once_with('cache.json', ['tf'], SETS, None)


class AutoDetection(RunWatcher):
    def test_auto_uses_the_script_that_is_found(self):
        with patch.object(service, 'find_init_script', return_value='/found/init'):
            _, discover = self.run_watcher(scan_results=[['a/1']], lmod_init='auto')
        discover.assert_called_once_with('/found/init', None)

    def test_auto_that_finds_nothing_turns_discovery_off_without_stopping_the_service(self):
        with patch.object(service, 'find_init_script', return_value=None):
            write_cache, discover = self.run_watcher(lmod_init='auto')
        discover.assert_not_called()
        write_cache.assert_called_once_with('cache.json', ['tf'], SETS)

    def test_resolve_lmod_init(self):
        self.assertIsNone(service.resolve_lmod_init(''))
        self.assertEqual(service.resolve_lmod_init('/etc/profile.d/lmod.sh'), '/etc/profile.d/lmod.sh')
        with patch.object(service, 'find_init_script', return_value='/x'):
            self.assertEqual(service.resolve_lmod_init('auto'), '/x')
