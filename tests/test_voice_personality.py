import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.voice.personality import GREETINGS,VOICE_STYLE,greeting
class PersonalityTests(unittest.TestCase):
 def test_status_claims_are_filtered(self):
  observed=[]
  greeting(choose=lambda choices:observed.extend(choices) or choices[0])
  self.assertNotIn(GREETINGS[2],observed);self.assertNotIn(GREETINGS[4],observed)
  all_options=[]
  greeting(guardian_verified=True,all_systems_verified=True,choose=lambda c:all_options.extend(c) or c[0])
  self.assertEqual(tuple(all_options),GREETINGS)
 def test_original_voice_and_invalid_status_selection(self):
  self.assertFalse(VOICE_STYLE['engine_verified'])
  with self.assertRaises(ValueError):greeting(choose=lambda c:GREETINGS[2])
