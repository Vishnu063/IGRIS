import io
import logging
import logging.config
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.config import load_settings
from igris.guardian.executor import execute
from igris.guardian.policy import Permission, Policy
from igris.guardian.scan import scan_repository
from igris.guardian.secrets import RedactingFormatter, findings, prompt_text, redact


class SecretTests(unittest.TestCase):
    def test_provider_keys_credentials_and_private_keys(self):
        values = ['ghp_' + 'A' * 36, 'github_pat_' + 'B' * 50,
                  'AKIA' + 'C' * 16, 'ASIA' + 'D' * 16, 'sk-' + 'E' * 32,
                  'eyJ' + 'a' * 10 + '.' + 'b' * 10 + '.' + 'c' * 10,
                  'postgres://' + 'user:' + 'synthetic-password@' + 'localhost/db',
                  'Bearer ' + 'F' * 30,
                  '-----BEGIN ' + 'PRIVATE KEY-----\nsynthetic body\n-----END PRIVATE KEY-----']
        for value in values:
            with self.subTest(kind=value[:4]):
                self.assertNotIn(value, redact(value))
                self.assertTrue(findings(value))
                self.assertNotIn(value, repr(findings(value)))

    def test_labels_customer_data_and_known_secret(self):
        for key in ('api_key', 'AWS_SECRET_ACCESS_KEY', 'DB_PASSWORD', 'OPENAI_API_KEY', 'password', 'token', 'customer_name', 'address'):
            self.assertNotIn('synthetic value tail', redact(f'{key}: "synthetic value tail"'))
        self.assertNotIn('test@example.invalid', prompt_text('test@example.invalid'))
        self.assertNotIn('+91 98765 43210', redact('+91 98765 43210'))
        self.assertEqual(redact('plain arbitrary-value', known_secrets=['arbitrary-value']), 'plain [REDACTED]')
        self.assertEqual(redact('ordinary fixture'), 'ordinary fixture')
        self.assertNotIn('multiline synthetic', redact('password:\nmultiline synthetic'))
        self.assertEqual(redact('x' * 65537), '[CONTENT OMITTED]')

    def test_formatted_arguments_and_tracebacks_redacted(self):
        output = io.StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(RedactingFormatter('%(message)s'))
        logger = logging.Logger('redaction-test')
        logger.addHandler(handler)
        value = 'ghp_' + 'Z' * 36
        logger.warning('event %s', value)
        try:
            raise RuntimeError(value)
        except RuntimeError:
            logger.exception('failure')
        self.assertNotIn(value, output.getvalue())
        self.assertIn('[REDACTED]', output.getvalue())

    def test_configured_logger_uses_redaction(self):
        logger = logging.getLogger('igris')
        old = (logger.handlers[:], logger.level, logger.propagate, logger.disabled)
        value = 'sk-' + 'X' * 32
        stream = io.StringIO()
        try:
            with patch('sys.stderr', stream):
                logging.config.dictConfig(load_settings('test', environ={}).logging_config())
                logger.error('failure %s', value)
            self.assertNotIn(value, stream.getvalue())
        finally:
            logger.handlers, logger.level, logger.propagate, logger.disabled = old

    def test_real_broker_read_is_sanitized_before_return(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = 'ghp_' + 'Y' * 36
            (root / 'note.txt').write_text('payload ' + value)
            result = execute(Policy('owner', frozenset({Permission.READ})), root,
                             {'operation': 'file.read', 'arguments': {'path': 'note.txt'}})
            self.assertTrue(result['ok'])
            self.assertNotIn(value, str(result))

    def test_scanner_reports_synthetic_fixture_without_exposure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            value = 'AKIA' + 'Q' * 16
            (root / 'fixture.txt').write_text(value)
            result = scan_repository(root)
            self.assertIn(('fixture.txt', 1, 'aws-access-key'), result)
            self.assertNotIn(value, repr(result))
            (root / 'fixture.txt').write_text('ordinary fixture')
            self.assertEqual(scan_repository(root), [])
            (root / 'fixture.txt').write_text(value)
            subprocess.run(['git', 'add', 'fixture.txt'], cwd=root, check=True)
            (root / 'fixture.txt').write_text('ordinary fixture')
            self.assertIn(('index:fixture.txt', 1, 'aws-access-key'), scan_repository(root))
