"""Small, shared adapter-validation primitives."""
import re
from ..guardian.secrets import prompt_text


class ContractError(ValueError):
    pass


class AdapterUnavailable(RuntimeError):
    pass


def identifier(value):
    if type(value) is not str or not re.fullmatch(r'[a-f0-9]{32}', value):
        raise ContractError('Invalid correlation identifier.')
    return value


def safe_text(value, limit=8192):
    if type(value) is not str or not value.strip():
        raise ContractError('Invalid text field.')
    try:
        size = len(value.encode('utf-8'))
    except UnicodeError:
        raise ContractError('Invalid text encoding.') from None
    if size > limit:
        raise ContractError('Text field exceeds limit.')
    return prompt_text(value)
