import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.notifications import EVENTS,notification
class NotificationTests(unittest.TestCase):
 def test_quiet_filter_and_allowed_events(self):
  for event in EVENTS:self.assertIsNotNone(notification(event,'Bounded event.',meaningful=True))
  for event in ('narration','token_stream','debug','progress'):self.assertIsNone(notification(event,'Routine chatter'))
  self.assertIsNone(notification('milestone','Ordinary progress.'))
 def test_sensitive_messages_and_priorities(self):
  self.assertEqual(notification('security_event','password: synthetic fixture')['message'],'[REDACTED]')
  self.assertEqual(notification('blocked','Unavailable.')['priority'],'high')
