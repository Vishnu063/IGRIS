import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.voice.speech import SpeechOutput,speech_text,language_review
from igris.adapters.contracts import ContractError,AdapterUnavailable
from igris.isolated import Cancelled

class SpeechTests(unittest.TestCase):
    def test_language_ambiguity_confirmation_and_manual_preference(self):
        for text in ('Hello','नमस्ते','नमस्कार','Hello नमस्ते'):
            guess=language_review(text)
            self.assertTrue(guess['needs_confirmation']);self.assertFalse(guess['speech_language_detected'])
        for language in ('en','hi','mr'):
            guess=language_review('नमस्कार',preferred=language)
            self.assertEqual(guess['language'],language);self.assertFalse(guess['needs_confirmation'])
        with self.assertRaises(ValueError):language_review('Hello',preferred='unknown')
    def test_plain_text_bounds_and_no_markup(self):
        for value in ('','x'*241,'<speak>execute</speak>','[[phoneme]]','hello\nworld'):
            with self.subTest(value=value[:10]),self.assertRaises((ContractError,ValueError)):speech_text(value)
        self.assertEqual(speech_text('नमस्कार.'),'नमस्कार.')
    def test_disabled_mute_stop_never_starts_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'not-created.wav'
            with self.assertRaises(AdapterUnavailable):SpeechOutput().synthesize('Hello','en',target)
            output=SpeechOutput(enabled=True);output.mute()
            with self.assertRaises(AdapterUnavailable):output.synthesize('Hello','en',target)
            output.mute(False)
            with self.assertRaises(Cancelled):output.synthesize('Hello','en',target)
            self.assertFalse(target.exists())
    def test_cleanup_failure_does_not_skip_other_resources(self):
        from igris.voice.__main__ import cleanup_all
        calls=[]
        def failing():calls.append('microphone');raise RuntimeError('fixture')
        with self.assertRaises(RuntimeError):cleanup_all([failing,lambda:calls.append('chat'),lambda:calls.append('temporary')])
        self.assertEqual(calls,['microphone','chat','temporary'])
