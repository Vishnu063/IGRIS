"""Strict, credential-free configuration. Does not grant execution permission."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Mapping


class ConfigurationError(ValueError):
    """Safe diagnostic that never includes configuration values."""


@dataclass(frozen=True)
class Features:
    hermes: bool
    n8n: bool
    ops_pilot: bool
    specialists: bool
    voice: bool
    dashboard: bool
    business: bool


@dataclass(frozen=True)
class Settings:
    profile: str
    bind_host: str
    budget_inr: int
    log_level: str
    features: Features

    def logging_config(self) -> dict:
        """Console-only settings; callers must avoid logging sensitive content."""
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {'standard': {'()': 'igris.guardian.secrets.RedactingFormatter', 'format': '%(levelname)s %(name)s %(message)s'}},
            'handlers': {'console': {
                'class': 'logging.StreamHandler', 'level': self.log_level,
                'formatter': 'standard', 'stream': 'ext://sys.stderr'}},
            'loggers': {'igris': {
                'level': self.log_level, 'handlers': ['console'], 'propagate': False}},
        }


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigurationError('Duplicate configuration key.')
        result[key] = value
    return result


def load_settings(profile=None, *, environ: Mapping[str, str] | None = None,
                  config_dir: Path | None = None) -> Settings:
    """Load a fixed dev/test profile. Never load dotenv, credentials or services.

    config_dir is a trusted caller/test hook, not an untrusted request field.
    Environment can select a profile or log level, never permissions or spending.
    """
    env = os.environ if environ is None else environ
    allowed_env = {'IGRIS_PROFILE', 'IGRIS_LOG_LEVEL'}
    if any(key.startswith('IGRIS_') and key not in allowed_env for key in env):
        raise ConfigurationError('Unsupported IGRIS environment setting.')
    selected = profile if profile is not None else env.get('IGRIS_PROFILE', 'development')
    if type(selected) is not str or selected not in ('development', 'test'):
        raise ConfigurationError('Unsupported configuration profile.')
    directory = Path(config_dir) if config_dir is not None else Path(__file__).resolve().parents[2] / 'config'
    try:
        with (directory / (selected + '.json')).open('rb') as handle:
            raw = handle.read(65537)
        if len(raw) > 65536:
            raise ConfigurationError('Configuration exceeds size limit.')
        data = json.loads(raw, object_pairs_hook=_object)
    except ConfigurationError:
        raise
    except (OSError, ValueError, UnicodeError, RecursionError):
        raise ConfigurationError('Cannot read valid configuration.') from None
    expected = {'schema_version', 'profile', 'bind_host', 'budget_inr', 'logging', 'features'}
    if type(data) is not dict or set(data) != expected:
        raise ConfigurationError('Invalid configuration schema.')
    if type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise ConfigurationError('Unsupported schema version.')
    if data['profile'] != selected:
        raise ConfigurationError('Profile does not match selected configuration.')
    if data['bind_host'] != '127.0.0.1':
        raise ConfigurationError('Only loopback binding is supported.')
    if type(data['budget_inr']) is not int or data['budget_inr'] != 0:
        raise ConfigurationError('Only zero-budget configuration is supported.')
    logging = data['logging']
    if type(logging) is not dict or set(logging) != {'level'}:
        raise ConfigurationError('Invalid logging configuration.')
    level = env.get('IGRIS_LOG_LEVEL', logging['level'])
    levels = ('INFO', 'WARNING', 'ERROR', 'CRITICAL')
    if type(logging['level']) is not str or logging['level'] not in levels:
        raise ConfigurationError('Invalid configured logging level.')
    if type(level) is not str or level not in levels:
        raise ConfigurationError('Invalid logging override.')
    features = data['features']
    if type(features) is not dict or set(features) != set(Features.__dataclass_fields__):
        raise ConfigurationError('Invalid feature configuration.')
    if any(type(value) is not bool for value in features.values()):
        raise ConfigurationError('Feature flags must be booleans.')
    if any(features.values()):
        raise ConfigurationError('Unimplemented integrations must remain disabled.')
    return Settings(selected, data['bind_host'], data['budget_inr'], level, Features(**features))
