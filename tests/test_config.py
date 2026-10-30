"""Configuration tests use temporary files and synthetic markers, no credentials."""
from dataclasses import FrozenInstanceError
import io
import json
import logging
import logging.config
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from igris.config import ConfigurationError, load_settings


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)
        self.data = json.loads((ROOT / 'config/test.json').read_text())

    def load(self, data=None, env=None):
        (self.path / 'test.json').write_text(json.dumps(self.data if data is None else data))
        return load_settings('test', environ={} if env is None else env, config_dir=self.path)

    def test_profiles_load_without_credentials(self):
        for profile, level in [('development', 'INFO'), ('test', 'WARNING')]:
            with self.subTest(profile=profile):
                settings = load_settings(profile, environ={})
                self.assertEqual(settings.profile, profile)
                self.assertEqual(settings.log_level, level)
                self.assertEqual(settings.budget_inr, 0)
                self.assertFalse(any(vars(settings.features).values()))
        self.assertEqual(load_settings(environ={}).profile, 'development')

    def test_environment_precedence_and_provider_secrets_ignored(self):
        env = {'IGRIS_PROFILE': 'test', 'IGRIS_LOG_LEVEL': 'ERROR',
               'EXAMPLE_PROVIDER_TOKEN': 'SYNTHETIC_DO_NOT_LOG'}
        self.assertEqual(load_settings(environ=env).profile, 'test')
        settings = load_settings('development', environ=env)
        self.assertEqual(settings.profile, 'development')
        self.assertEqual(settings.log_level, 'ERROR')
        self.assertNotIn('SYNTHETIC_DO_NOT_LOG', repr(settings))

    def test_unsafe_configuration_rejected(self):
        cases = [('budget_inr', 1), ('budget_inr', True), ('budget_inr', '0'),
                 ('bind_host', '0.0.0.0'), ('schema_version', True),
                 ('profile', 'development'), ('extra', 'SYNTHETIC_DO_NOT_LOG')]
        for key, value in cases:
            with self.subTest(field=key, value=value):
                data = dict(self.data, **{key: value})
                with self.assertRaises(ConfigurationError) as caught:
                    self.load(data)
                self.assertNotIn('SYNTHETIC_DO_NOT_LOG', str(caught.exception))

    def test_flags_require_booleans_and_disabled_integrations(self):
        for name in self.data['features']:
            for value in (True, 'false', 0):
                with self.subTest(feature=name, value=value):
                    data = dict(self.data, features=dict(self.data['features'], **{name: value}))
                    with self.assertRaises(ConfigurationError):
                        self.load(data)
        with self.assertRaises(ConfigurationError):
            self.load(dict(self.data, features={}))

    def test_environment_cannot_override_permissions_or_budget(self):
        for env in ({'IGRIS_BUDGET_INR': '1'}, {'IGRIS_VOICE': 'true'},
                    {'IGRIS_PROFILE': '../../outside'}, {'IGRIS_PROFILE': 'production'},
                    {'IGRIS_LOG_LEVEL': 'DEBUG'}):
            with self.subTest(env=env), self.assertRaises(ConfigurationError):
                load_settings(environ=env)

    def test_logging_rejects_injection_and_invalid_settings(self):
        for value in ({'level': 'DEBUG'}, {'level': 'INFO', 'class': 'unsafe'},
                      {'level': 1}, [], None):
            with self.subTest(value=value), self.assertRaises(ConfigurationError):
                self.load(dict(self.data, logging=value))

    def test_malformed_missing_duplicate_and_oversized_files(self):
        for raw in ('{', '[]', '{"key":1,"key":2}', '[' * 2000 + ']' * 2000, 'x' * 65537):
            (self.path / 'test.json').write_text(raw)
            with self.subTest(size=len(raw)), self.assertRaises(ConfigurationError):
                load_settings('test', environ={}, config_dir=self.path)
        (self.path / 'test.json').unlink()
        with self.assertRaises(ConfigurationError) as caught:
            load_settings('test', environ={}, config_dir=self.path)
        self.assertNotIn(self.directory.name, str(caught.exception))

    def test_settings_are_immutable(self):
        settings = self.load()
        with self.assertRaises(FrozenInstanceError):
            settings.budget_inr = 100
        with self.assertRaises(FrozenInstanceError):
            settings.features.voice = True

    def test_logging_dictionary_works_and_filters_info(self):
        logger = logging.getLogger('igris')
        previous = (logger.handlers[:], logger.level, logger.propagate, logger.disabled)
        output = io.StringIO()
        try:
            with patch('sys.stderr', output):
                logging.config.dictConfig(self.load().logging_config())
                logger.info('ordinary suppressed event')
                logger.warning('ordinary test event')
            self.assertNotIn('suppressed', output.getvalue())
            self.assertIn('WARNING igris ordinary test event', output.getvalue())
        finally:
            logger.handlers, logger.level, logger.propagate, logger.disabled = previous


if __name__ == '__main__':
    unittest.main()
