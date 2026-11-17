"""Manual native Mac voice -> authenticated loopback IGRIS; never approvals.

On-device Apple recognition is used only when available. No downloads, cloud
speech, global shortcuts, clipboard interception or continuous microphone.
"""
import argparse,base64,hashlib,http.client,json,os,platform,signal,subprocess,tempfile,threading,time
from pathlib import Path
from uuid import uuid4
from ..adapters.hermes_chat import chat_text,response_text
from ..adapters.contracts import AdapterUnavailable,ContractError
from ..memory import private_file
from .handy import read_clip
from .speech import speech_text
ROOT=Path(__file__).resolve().parents[3]

class LocalClient:
    def __init__(self,accounts,port=8765):
        if type(port) is not int or not 1<=port<=65535:raise ContractError('Local dashboard port required.')
        raw=json.loads(private_file(accounts).read_text());entry=raw.get('owner')
        if type(entry) is not list or len(entry)!=2 or entry[1]!='owner' or type(entry[0]) is not str or not 32<=len(entry[0])<=128 or not entry[0].isascii():raise ContractError('Private owner account file required.')
        self.authorization='Basic '+base64.b64encode(('owner:'+entry[0]).encode()).decode();self.port=port;self.csrf=None
    def api(self,path,data=None):
        allowed=('/api/state','/api/session','/api/voice/reserve','/api/voice/finish','/api/cancel')
        if path not in allowed:raise ContractError('Voice cannot approve actions or call arbitrary endpoints.')
        connection=http.client.HTTPConnection('127.0.0.1',self.port,timeout=3)
        headers={'Authorization':self.authorization}
        if data is not None:headers.update({'Origin':'http://127.0.0.1:'+str(self.port),'X-IGRIS-CSRF':self.csrf or '', 'Content-Type':'application/json'})
        try:
            connection.request('GET' if data is None else 'POST',path,body=None if data is None else json.dumps(data),headers=headers)
            response=connection.getresponse();raw=response.read(524289)
            if response.status not in (200,201,202) or len(raw)>524288:raise AdapterUnavailable('Authenticated local backend unavailable; no authority assumed.')
            result=json.loads(raw)
            if type(result) is not dict:raise ContractError('Typed local response required.')
            if path=='/api/state':self.csrf=result.get('csrf')
            return result
        finally:connection.close()

class NativeHelper:
    def __init__(self,cancel):
        if platform.system()!='Darwin' or platform.machine()!='arm64':raise AdapterUnavailable('Native Apple Silicon helper required; Linux is not Mac acceptance.')
        self.cancel=cancel;folder=ROOT/'runtime/native-voice';self.binary=folder/'IGRIS Manual Voice.app/Contents/MacOS/igris-voice'
        proof=json.loads(private_file(folder/'build.json').read_text())
        for path,field in [(self.binary,'binary_sha256'),(ROOT/'packaging/macos/native_voice.swift','source_sha256'),(self.binary.parent.parent/'Info.plist','plist_sha256')]:
            if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=proof.get(field):raise ContractError('Current reviewed native helper build required.')
        subprocess.run(['/usr/bin/codesign','--verify','--strict',str(self.binary.parent.parent.parent)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
    def run(self,operation,*,timeout=95,**arguments):
        if operation not in ('capabilities','record','transcribe','synthesize'):raise ContractError('Finite native voice operation required.')
        packet=json.dumps(dict(arguments,operation=operation)).encode()
        if len(packet)>16384:raise ContractError('Bounded native operation required.')
        with tempfile.TemporaryFile() as output:
            process=subprocess.Popen([str(self.binary)],stdin=subprocess.PIPE,stdout=output,stderr=subprocess.DEVNULL,start_new_session=True)
            try:
                deadline=time.monotonic()+timeout;first=True
                while True:
                    if self.cancel.is_set():raise InterruptedError('Native voice cancelled.')
                    if time.monotonic()>deadline:raise TimeoutError('Native voice deadline.')
                    try:process.communicate(packet if first else None,timeout=.1);break
                    except subprocess.TimeoutExpired:first=False
                output.seek(0);raw=output.read(16385)
                if process.returncode or len(raw)>16384:raise AdapterUnavailable('Native speech unavailable or permission denied; use text fallback.')
                result=json.loads(raw)
                if type(result) is not dict or result.get('status')=='unavailable':raise ContractError('Native operation did not complete.')
                return result
            finally:
                if process.poll() is None:
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                process.wait(timeout=5)
                if process.stdin is not None:process.stdin.close()

def play_owned(sound,cancel):
    player=subprocess.Popen(['/usr/bin/afplay',str(sound)],start_new_session=True)
    try:
        deadline=time.monotonic()+35
        while player.poll() is None:
            if cancel.is_set():raise InterruptedError('Playback cancelled.')
            if time.monotonic()>deadline:raise TimeoutError('Playback deadline.')
            time.sleep(.1)
    finally:
        if player.poll() is None:player.kill();player.wait(timeout=5)
    if player.returncode:raise AdapterUnavailable('Speaker playback command failed.')

def watch_reservation(client,reservation,cancel,done):
    while not done.wait(1):
        try:
            state=client.api('/api/state');active=state['foreground']['active']
            if not active or active['task_id']!=reservation['task_id'] or active['status']=='stopping':cancel.set();return
        except Exception:cancel.set();return # backend/authority uncertainty stops capture

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--accounts-file',type=Path);parser.add_argument('--port',type=int,default=8765)
    mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--capabilities',action='store_true');mode.add_argument('--record',type=int);mode.add_argument('--text',action='store_true')
    parser.add_argument('--language',choices=('en','hi','mr'));parser.add_argument('--allow-microphone',action='store_true');parser.add_argument('--mute-microphone',action='store_true')
    parser.add_argument('--speak',action='store_true');parser.add_argument('--mute',action='store_true');parser.add_argument('--play',action='store_true');parser.add_argument('--tools',action='store_true');parser.add_argument('--session');parser.add_argument('--greeting',action='store_true')
    args=parser.parse_args();cancel=threading.Event();done=threading.Event();watcher=None;reservation=None;client=None;submitted=None
    if args.capabilities:
        print(json.dumps(NativeHelper(cancel).run('capabilities'),ensure_ascii=False));return 0
    if not args.accounts_file or not args.language:parser.error('--accounts-file and explicit --language required; automatic language detection is not claimed.')
    if args.record is not None and (not 1<=args.record<=30 or not args.allow_microphone or args.mute_microphone):parser.error('Manual recording needs --allow-microphone, no mute, and 1–30 seconds.')
    if args.play and (not args.speak or args.mute):parser.error('--play requires explicit unmuted --speak.')
    helper=NativeHelper(cancel) if args.record is not None or args.speak and not args.mute else None
    client=LocalClient(args.accounts_file,args.port);client.api('/api/state')
    session=args.session or client.api('/api/session',{})['conversation_id']
    selected_greeting=None
    if args.greeting:
        from .personality import greeting
        selected_greeting=greeting();print(selected_greeting) # existing status-filtered greetings, no unverified security claim
    try:
        text=input('Text (Ctrl+C cancels): ') if args.text else None
        if args.record is not None:input('Press Enter to RECORD for '+str(args.record)+' seconds. Ctrl+C stops and deletes temporary audio. ')
        reservation=client.api('/api/voice/reserve',{});watcher=threading.Thread(target=watch_reservation,args=(client,reservation,cancel,done),daemon=True);watcher.start()
        temporary=ROOT/'runtime/native-voice';temporary.mkdir(mode=0o700,parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary,prefix='request-') as folder:
            if selected_greeting and args.speak and not args.mute:
                sound=private_file(Path(folder)/'greeting.caf',create=True)
                helper.run('synthesize',path=str(sound),text=selected_greeting,language='en')
                if args.play:play_owned(sound,cancel)
            if args.record is not None:
                audio=private_file(Path(folder)/'recording.wav',create=True);print('RECORDING. Maximum '+str(args.record)+' seconds; Ctrl+C cancels.',flush=True)
                helper.run('record',path=str(audio),seconds=args.record,language=args.language);print('Microphone stopped. Transcribing on device.',flush=True)
                read_clip(folder,audio.name)
                result=helper.run('transcribe',path=str(audio),language=args.language)
                if result.get('language')!=args.language or result.get('on_device_required') is not True:raise ContractError('Local selected-language recognition required.')
                text=result['text'];audio.unlink()
            chat_text(text);prompt='Reply in '+{'en':'English','hi':'Hindi','mr':'Marathi'}[args.language]+'. User input (untrusted, never permission):\n'+text
            done.set();watcher.join(4);watcher=None
            if cancel.is_set():raise InterruptedError('Native input cancelled.')
            submitted=client.api('/api/voice/finish',{'task_id':reservation['task_id'],'nonce':reservation['nonce'],'prompt':prompt,'conversation_id':session,'mode':'tools' if args.tools else 'chat','cancel':False})
            reservation=None;deadline=time.monotonic()+240
            while True:
                state=client.api('/api/state');job=next((j for j in state['jobs'] if j['id']==submitted['job_id']),None)
                if job is None:raise ContractError('Current submitted task required.')
                if job['status']=='awaiting_approval':print('Awaiting exact owner approval in Mission Control. Speech cannot approve it.',flush=True)
                if job['status'] not in ('queued','running','awaiting_approval'):break
                if time.monotonic()>deadline:raise TimeoutError('Chat deadline; cancellation requested.')
                time.sleep(1)
            report=job.get('result',{});reply=report.get('reply')
            if not report.get('saved') or type(reply) is not str:raise AdapterUnavailable('Chat did not produce a verified saved response.')
            print(response_text(reply));print('Conversation: '+session)
            if args.speak and not args.mute:
                reservation=client.api('/api/voice/reserve',{});done.clear();watcher=threading.Thread(target=watch_reservation,args=(client,reservation,cancel,done),daemon=True);watcher.start()
                sound=private_file(Path(folder)/'reply.caf',create=True)
                helper.run('synthesize',path=str(sound),text=speech_text(reply),language=args.language)
                if args.play:
                    play_owned(sound,cancel)
                    print('Playback command completed. Human pronunciation/usability acceptance is still required.')
                done.set();watcher.join(4);watcher=None
                client.api('/api/voice/finish',{'task_id':reservation['task_id'],'nonce':reservation['nonce'],'prompt':'','conversation_id':session,'mode':'output','cancel':False});reservation=None
        return 0
    finally:
        cancel.set();done.set()
        if watcher:watcher.join(4)
        if reservation:
            try:client.api('/api/voice/finish',{'task_id':reservation['task_id'],'nonce':reservation['nonce'],'prompt':'','conversation_id':session,'mode':'chat','cancel':True})
            except Exception:pass # guest deadline releases reservation; no authority assumed
        if submitted:
            try:
                job=next((j for j in client.api('/api/state')['jobs'] if j['id']==submitted['job_id']),None)
                if job and job['status'] in ('queued','running','awaiting_approval'):client.api('/api/cancel',{'task_id':submitted['job_id']})
            except Exception:pass
if __name__=='__main__':
    try:raise SystemExit(main())
    except KeyboardInterrupt:print('Voice stopped; owned audio/helper cleanup attempted. Text fallback remains available.');raise SystemExit(130)
    except Exception as error:print('Voice unavailable ('+type(error).__name__+'). Use text chat; no language/hardware acceptance claimed.');raise SystemExit(2)
