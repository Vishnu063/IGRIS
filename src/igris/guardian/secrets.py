"""Defense-in-depth redaction; patterns cannot recognize every unknown secret."""
import logging
import re

REDACTED = '[REDACTED]'
PATTERNS = (
    ('private-key', re.compile(r'-----BEGIN (?:[A-Z ]*PRIVATE KEY)-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)')),
    ('github-token', re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b')),
    ('aws-access-key', re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b')),
    ('api-token', re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b')),
    ('jwt', re.compile(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b')),
    ('credential-url', re.compile(r'[A-Za-z][A-Za-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@[^\s]+')),
    ('bearer-token', re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}')),
)
LABEL = re.compile(r'''(?ix)["']?(?<![A-Za-z0-9])(?:api[_-]?key|access[_-]?key|secret[_-]?key|aws[_-]?secret[_-]?access[_-]?key|github[_-]?token|auth(?:entication|orization)?[_-]?token|token|password|passwd|client[_-]?secret|customer[_-]?(?:info|name|data)|email|phone|address)["']?\s*[:=]''')
EMAIL = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
PHONE = re.compile(r'(?<!\w)\+?\d[\d ()-]{8,}\d(?!\w)')


def redact(text: str, *, known_secrets=()) -> str:
    if type(text) is not str or len(text) > 65536:
        return '[CONTENT OMITTED]'
    for secret in known_secrets:
        if type(secret) is str and secret:
            text = text.replace(secret, REDACTED)
    for _, pattern in PATTERNS:
        text = pattern.sub(REDACTED, text)
    # Omit the whole payload on a sensitive label: values may span lines.
    if LABEL.search(text):
        return REDACTED
    text = EMAIL.sub(REDACTED, text)
    return PHONE.sub(REDACTED, text)


def prompt_text(text: str, *, known_secrets=()) -> str:
    """Required sanitizer for future prompt assembly; no model is connected."""
    return redact(text, known_secrets=known_secrets)


class RedactingFormatter(logging.Formatter):
    def format(self, record):
        # Redact after interpolation and exception formatting, not just msg.
        return redact(super().format(record))


def findings(text: str):
    """High-confidence credential patterns only, without returning matched values."""
    return [(text.count('\n', 0, match.start()) + 1, kind)
            for kind, pattern in PATTERNS for match in pattern.finditer(text)]
