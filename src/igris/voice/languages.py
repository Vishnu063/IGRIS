from dataclasses import dataclass
import re

@dataclass(frozen=True)
class LanguageRoute:
    languages: tuple[str,...]
    needs_confirmation: bool
    speech_verified: bool=False


def route_language(text, *, preferred=None):
    if type(text) is not str or not text.strip() or len(text)>4096:raise ValueError('Bounded text required.')
    if preferred not in (None,'en','hi','mr'):raise ValueError('Unsupported language preference.')
    latin=bool(re.search('[A-Za-z]',text)); devanagari=bool(re.search('[\u0900-\u097f]',text))
    if devanagari:
        # Hindi and Marathi share a script. Never pretend script detection can distinguish them.
        indic=preferred if preferred in ('hi','mr') else None
        return LanguageRoute((('en',) if latin else ()) + ((indic,) if indic else ('hi','mr')),indic is None)
    if latin:return LanguageRoute((preferred or 'en',),preferred is None)
    return LanguageRoute((preferred,) if preferred else (),True)
