import time

class PushToTalk:
    def __init__(self, microphone=None, *, clock=time.monotonic):
        self.microphone=microphone;self.clock=clock;self.state='idle';self.started=None
    @property
    def indicator(self):return {'state':self.state,'recording_or_unknown':self.state!='idle'}
    def press(self, *, permission_granted=False):
        if permission_granted is not True or self.microphone is None:raise PermissionError('Explicit permission and configured microphone required.')
        if self.state!='idle':raise RuntimeError('Capture already active or uncertain.')
        try:self.microphone.start()
        except Exception:
            try:self.microphone.stop()
            except Exception:self.state='error'
            raise RuntimeError('Capture start failed.') from None
        self.state='recording';self.started=self.clock()
    def release(self):
        if self.state=='idle':return
        try:self.microphone.stop()
        except Exception:
            self.state='error';raise RuntimeError('Capture state unknown; inspect microphone permissions/device.') from None
        self.state='idle';self.started=None
    def check_deadline(self):
        if self.state=='recording' and self.clock()-self.started>=30:self.release()
    def cancel(self):self.release()
