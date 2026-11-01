"""Manual optional microphone backend; unavailable devices fail closed."""
import threading
import time
import wave
from pathlib import Path
from uuid import uuid4

from ..adapters.contracts import AdapterUnavailable
from ..memory import private_file


class ManualCapture:
    def __init__(self,workspace,*,stream_factory=None):
        self.workspace=Path(workspace).absolute()
        self.stream_factory=stream_factory
        self.state='idle';self._stream=None;self._timer=None
        self._frames=[];self._bytes=0;self._lock=threading.Lock()

    def start(self,*,permission_granted=False):
        if permission_granted is not True:raise PermissionError('Explicit microphone request and OS permission required.')
        if self.state!='idle':raise RuntimeError('Recording already active or uncertain.')
        factory=self.stream_factory
        if factory is None:
            try:
                import importlib
                audio=importlib.import_module('sounddevice')
            except (ImportError,OSError):raise AdapterUnavailable('No verified microphone backend. Use an approved WAV or text chat.') from None
            factory=audio.RawInputStream
        self._frames=[];self._bytes=0
        def receive(data,frames,timing,status):
            with self._lock:
                # Hard bound even if a device ignores requested callback block size.
                piece=bytes(data)[:max(0,960000-self._bytes)]
                self._frames.append(piece);self._bytes+=len(piece)
        try:
            self._stream=factory(samplerate=16000,channels=1,dtype='int16',blocksize=800,callback=receive)
            self._stream.start();self.state='recording'
            self._timer=threading.Timer(30,self.stop);self._timer.daemon=True;self._timer.start()
        except Exception:
            self.state='error'
            if self._stream:
                try:self._stream.close();self.state='idle'
                except Exception:pass
            raise AdapterUnavailable('Microphone unavailable or OS permission denied; no capture verified.') from None

    def stop(self):
        if self.state=='idle':return
        if self._timer:self._timer.cancel()
        try:
            if self._stream:self._stream.stop();self._stream.close()
            self.state='idle'
        except Exception:
            self.state='error';raise RuntimeError('Capture state unknown; inspect the device.') from None

    def save(self):
        self.stop()
        with self._lock:data=b''.join(self._frames);self._frames=[];self._bytes=0
        if not data:raise ValueError('No finalized recording.')
        self.workspace.mkdir(mode=0o700,parents=True,exist_ok=True)
        name='recording-'+uuid4().hex+'.wav';path=private_file(self.workspace/name,create=True)
        with wave.open(str(path),'wb') as output:
            output.setnchannels(1);output.setsampwidth(2);output.setframerate(16000);output.writeframes(data)
        return path

    def cancel(self):
        self.stop()
        with self._lock:self._frames=[];self._bytes=0
