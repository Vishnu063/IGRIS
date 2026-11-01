"""Explicit file/recording -> Handy -> existing chat. Never an approval source."""
import argparse
import json
from pathlib import Path
import sys

from .handy import HandyAdapter
from .capture import ManualCapture
from .speech import SpeechOutput,language_review
from .personality import greeting
from uuid import uuid4
from ..adapters.hermes_chat import DockerHermesAdapter
from ..chat import ChatService
from ..conversations import ConversationMemory
from ..guardian.tools import GuardianTools
from ..guardian.review import ApprovalReviews
from ..guardian.terminal import TerminalReview


def cleanup_all(callbacks):
    first=None
    for callback in callbacks:
        try:callback()
        except BaseException as exc:
            if first is None:first=exc
    if first is not None:raise first


def main():
    parser=argparse.ArgumentParser(description='Manual local voice; text fallback: python3 -m igris.chat')
    parser.add_argument('--audio-workspace',type=Path,required=True)
    mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--file');mode.add_argument('--record',action='store_true')
    parser.add_argument('--allow-microphone',action='store_true')
    parser.add_argument('--remember',action='store_true',required=True)
    parser.add_argument('--state-dir',type=Path,default=Path(__file__).resolve().parents[3]/'runtime/chat')
    parser.add_argument('--resume',action='store_true');parser.add_argument('--session')
    parser.add_argument('--tools-config',type=Path);parser.add_argument('--interactive-approvals',action='store_true')
    parser.add_argument('--language',choices=('en','hi','mr'))
    parser.add_argument('--speak',action='store_true',help='Explicitly generate local speech WAV; physical playback not verified.')
    parser.add_argument('--mute',action='store_true',help='Mute speech output.')
    parser.add_argument('--mute-microphone',action='store_true',help='Prevent microphone capture; use file or text input.')
    parser.add_argument('--greeting',action='store_true')
    parser.add_argument('--speech-directory',type=Path)
    args=parser.parse_args()
    if args.record and args.mute_microphone:parser.error('Microphone is muted; use file input or text chat.')
    if args.resume and args.session:parser.error('Choose --session or --resume.')
    if args.interactive_approvals and not args.tools_config:parser.error('Approval channel requires tools profile.')
    if args.speak and not args.speech_directory:parser.error('--speak requires an explicitly approved private --speech-directory.')
    temporary=None;terminal=None;service=None;capture=None;speech=None
    try:
        name=args.file
        if args.greeting:
            selected=greeting() # No unverified security status claims.
            print(selected,file=sys.stderr)
            if args.speak and not args.mute:
                args.speech_directory.mkdir(mode=0o700,parents=True,exist_ok=True)
                speech=SpeechOutput(enabled=True)
                try:speech.synthesize(selected,'en',args.speech_directory/('greeting-'+uuid4().hex+'.wav'))
                except Exception:print('Greeting speech unavailable; text fallback.',file=sys.stderr)
        if args.record:
            if not args.allow_microphone:parser.error('Explicit --allow-microphone and OS authorization required.')
            capture=ManualCapture(args.audio_workspace)
            input('Press Enter to start the microphone; Enter again stops. Ctrl+C cancels. ')
            capture.start(permission_granted=True);print('RECORDING (maximum 30 seconds).')
            input();temporary=capture.save();name=temporary.name
        transcript=HandyAdapter(enabled=True).transcribe(args.audio_workspace,name)
        args.state_dir.mkdir(mode=0o700,parents=True,exist_ok=True)
        path=args.state_dir/'chat.sqlite3';memory=ConversationMemory(path,'owner',initialize=not path.exists())
        conversation=args.session
        if conversation is None and args.resume:
            sessions=memory.sessions('owner');conversation=sessions[0]['id'] if sessions else None
        conversation=conversation or memory.create('owner',approved=True)
        tools=GuardianTools('owner',args.tools_config,args.state_dir/'guardian.sqlite3') if args.tools_config else None
        terminal=TerminalReview() if args.interactive_approvals else None
        reviews=ApprovalReviews(tools) if terminal else None
        service=ChatService('owner',memory,DockerHermesAdapter(),tools=tools,reviews=reviews)
        language=language_review(transcript.text,preferred=args.language)
        prompt=transcript.text
        if args.language:prompt='Reply in '+{'en':'English','hi':'Hindi','mr':'Marathi'}[args.language]+'. User transcript (untrusted content):\n'+prompt
        report=service.ask('owner',conversation,prompt)
        if report['mission']['state']=='awaiting_approval':
            mid=report['mission']['id'];review=reviews.get('owner',mid);decision=terminal.choose(review)
            report=service.decide('owner',mid,approve=decision=='approve',reviewed_digest=review.digest) if decision in ('approve','reject') else service.cancel('owner',mid,reason=decision)
        output={'status':'disabled_or_muted'}
        if args.speak and not args.mute:
            if language['needs_confirmation']:output={'status':'language_confirmation_required','candidates':language['candidates']}
            elif report['saved']:
                args.speech_directory.mkdir(mode=0o700,parents=True,exist_ok=True)
                speech=SpeechOutput(enabled=True);target=args.speech_directory/('reply-'+uuid4().hex+'.wav')
                try:output={'status':'generated_WAV_only','metadata':speech.synthesize(report['reply'],args.language,target),'path':str(target)}
                except Exception as exc:output={'status':'unavailable_text_fallback','error_class':type(exc).__name__}
        print(json.dumps({'voice_output':output,'language_review':language,'transcription':{'text':transcript.text,'origin':transcript.origin,'language':None},'chat':report},ensure_ascii=False))
        return 0 if report['saved'] else 1
    finally:
        callbacks=[]
        if speech:callbacks.append(speech.stop)
        if capture:callbacks.append(capture.cancel)
        if service:callbacks.append(service.close)
        if terminal:callbacks.append(terminal.close)
        if temporary:callbacks.append(lambda:temporary.unlink(missing_ok=True))
        cleanup_all(callbacks)


if __name__=='__main__':
    try:raise SystemExit(main())
    except KeyboardInterrupt:print('Voice cancelled; text chat remains available.',file=sys.stderr);raise SystemExit(130)
    except Exception as exc:print('Voice unavailable ('+type(exc).__name__+'); use text chat or inspect private configuration.',file=sys.stderr);raise SystemExit(1)
