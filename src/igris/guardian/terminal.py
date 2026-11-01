"""Separate controlling-terminal decision channel; no stdin/chat approval parser."""
import json
import os
import select
import time

from .policy import Denied


class TerminalReview:
    def __init__(self, *, fd=None):
        # fd injection is for trusted PTY tests only; no CLI argument exposes it.
        self.fd=os.dup(fd) if fd is not None else os.open('/dev/tty',os.O_RDWR|os.O_NOCTTY)
        if not os.isatty(self.fd):self.close();raise Denied('A controlling terminal is required.')

    def close(self):
        if self.fd is not None:os.close(self.fd);self.fd=None

    def choose(self, review, *, timeout=60):
        challenge=review.digest[:12]
        message='\nIGRIS OWNER ACTION REVIEW\n'+json.dumps(review.public(),indent=2,ensure_ascii=True)
        message+='\nType APPROVE '+challenge+' or REJECT (anything else cancels): '
        os.write(self.fd,message.encode())
        deadline=min(time.monotonic()+timeout,review.deadline)
        data=b''
        while time.monotonic()<deadline:
            ready,_,_=select.select([self.fd],[],[],max(0,deadline-time.monotonic()))
            if not ready:return 'timed_out'
            chunk=os.read(self.fd,64-len(data))
            if not chunk:return 'cancelled'
            data+=chunk
            if b'\n' in data or len(data)>=64:break
        answer=data.decode('ascii',errors='replace').strip()
        if answer=='APPROVE '+challenge:return 'approve'
        if answer=='REJECT':return 'reject'
        return 'cancelled'
