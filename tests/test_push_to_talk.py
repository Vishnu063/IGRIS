import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.voice.push_to_talk import PushToTalk
class Mic:
 def __init__(self):self.starts=0;self.stops=0;self.fail=False
 def start(self):self.starts+=1
 def stop(self):
  if self.fail:raise OSError('synthetic failure')
  self.stops+=1
class PushTests(unittest.TestCase):
 def test_permission_user_stop_and_indicator(self):
  mic=Mic();ptt=PushToTalk(mic)
  self.assertEqual(mic.starts,0)
  with self.assertRaises(PermissionError):ptt.press()
  ptt.press(permission_granted=True);self.assertTrue(ptt.indicator['recording_or_unknown'])
  with self.assertRaises(RuntimeError):ptt.press(permission_granted=True)
  ptt.cancel();self.assertEqual(ptt.state,'idle');self.assertEqual(mic.stops,1)
 def test_deadline_and_stop_error_remain_visible(self):
  now=[0];mic=Mic();ptt=PushToTalk(mic,clock=lambda:now[0]);ptt.press(permission_granted=True)
  now[0]=31;ptt.check_deadline();self.assertEqual(ptt.state,'idle')
  ptt.press(permission_granted=True);mic.fail=True
  with self.assertRaises(RuntimeError):ptt.release()
  self.assertEqual(ptt.state,'error');self.assertTrue(ptt.indicator['recording_or_unknown'])
 def test_no_physical_backend_by_default(self):
  with self.assertRaises(PermissionError):PushToTalk().press(permission_granted=True)
