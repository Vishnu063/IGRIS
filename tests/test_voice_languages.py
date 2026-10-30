import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.voice.languages import route_language
class LanguageTests(unittest.TestCase):
 def test_representative_routes_and_ambiguity(self):
  self.assertEqual(route_language('Hello',preferred='en').languages,('en',))
  self.assertEqual(route_language('नमस्ते',preferred='hi').languages,('hi',))
  self.assertEqual(route_language('नमस्कार',preferred='mr').languages,('mr',))
  self.assertEqual(route_language('Hello नमस्कार',preferred='mr').languages,('en','mr'))
  self.assertTrue(route_language('नमस्ते').needs_confirmation)
  self.assertFalse(route_language('Hello').speech_verified)
 def test_bad_inputs(self):
  for text in ('','x'*4097):
   with self.assertRaises(ValueError):route_language(text)
