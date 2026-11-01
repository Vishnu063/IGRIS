"""Manual text chat through the existing mission controller and private memory."""
import argparse
import json
from pathlib import Path
import sys

from .adapters.contracts import AdapterUnavailable, ContractError
from .adapters.hermes_chat import ChatReply, ChatRequest, DockerHermesAdapter, chat_text, response_text
from .controller import MissionController, State, TaskOutcome
from .conversations import ConversationMemory
from .guardian.policy import Denied, Permission, Policy


class ChatService:
    def __init__(self, owner, memory, backend, *, policy=None):
        if type(memory) is not ConversationMemory or memory.owner != owner:
            raise Denied('Trusted owner-bound conversation memory required.')
        self.owner, self.memory, self.backend = owner, memory, backend
        self.policy = policy if policy is not None else Policy(owner, frozenset({Permission.READ, Permission.FILE_MODIFY}))
        if self.policy.actor != owner: raise Denied('Chat actor mismatch.')
        self.controller = MissionController(owner, {'chat': self._route})
        self._requests = {}

    def _route(self, context):
        if context.actor != self.owner or context.approval_id is not None:
            return TaskOutcome('blocked', 'Unexpected chat authority.', 'unverified')
        conversation, request = self._requests[context.mission_id]
        try:
            reply = self.backend.reply(request)
            if type(reply) is not ChatReply or reply.request_id != request.request_id or reply.origin != 'real_local_inference':
                raise ContractError('No verified real response.')
            text = response_text(reply.text)
            self.memory.complete(self.owner, conversation, request.request_id, context.mission_id,
                                 text, reply.model_sha256, reply.api_calls, origin=reply.origin)
            return TaskOutcome('success', text, 'real', True)
        except AdapterUnavailable:
            return TaskOutcome('blocked', 'Local Hermes runtime unavailable or busy. No simulated fallback used.', 'unverified')
        except Exception:
            return TaskOutcome('failed', 'Chat generation or persistence failed. No completed exchange saved.', 'unverified')

    def ask(self, actor, conversation, text):
        if actor != self.owner: raise Denied('Chat access denied.')
        self.policy.require('file.read'); self.policy.require('file.create')
        chat_text(text)
        mission = self.controller.create(text, 'chat')
        request_id, window = self.memory.reserve(actor, conversation, mission.id, text)
        try:
            request = ChatRequest(request_id, mission.prompt, window)
            self._requests[mission.id] = (conversation, request)
            result = self.controller.run(mission.id)
            report = self.controller.report(mission.id)
            return {'conversation_id': conversation, 'request_id': request_id,
                    'mission': report, 'reply': result.message,
                    'saved': result.state == State.SUCCEEDED, 'tools_enabled': False}
        finally:
            self._requests.pop(mission.id, None)
            self.memory.abort(actor, conversation, request_id)  # No-op after committed success.


def main():
    parser = argparse.ArgumentParser(description='Explicit local IGRIS chat; no automatic service startup.')
    parser.add_argument('--remember', action='store_true', help='Approve storing sanitized conversation messages.')
    parser.add_argument('--state-dir', type=Path, default=Path(__file__).resolve().parents[2]/'runtime/chat')
    parser.add_argument('--session', help='Resume this owner-owned conversation ID.')
    parser.add_argument('--resume', action='store_true', help='Resume the latest conversation.')
    parser.add_argument('--once', action='store_true', help='Read one bounded message from stdin, never process arguments.')
    parser.add_argument('--json', action='store_true', help='Output structured result for --once.')
    parser.add_argument('--list', action='store_true', help='List owned sessions without inference.')
    args = parser.parse_args()
    if not args.remember and not args.list:
        parser.error('Pass --remember to approve persistent sanitized chat storage.')
    if args.json and not args.once: parser.error('--json requires --once.')
    if args.session and args.resume: parser.error('Choose --session or --resume.')
    directory = args.state_dir.absolute()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory/'chat.sqlite3'
    memory = ConversationMemory(path, 'owner', initialize=not path.exists())
    if args.list:
        print(json.dumps({'sessions': memory.sessions('owner')})); return 0
    conversation = args.session
    if conversation is None and args.resume:
        sessions = memory.sessions('owner')
        if sessions: conversation = sessions[0]['id']
    if conversation is None: conversation = memory.create('owner', approved=args.remember)
    else: memory.history('owner', conversation)  # Reject unknown session before constructing runtime.
    service = ChatService('owner', memory, DockerHermesAdapter())
    if args.once:
        raw = sys.stdin.buffer.read(8193)
        if len(raw) > 8192: raise ValueError('Chat message exceeds limit.')
        report = service.ask('owner', conversation, raw.decode('utf-8').rstrip('\n'))
        print(json.dumps(report, ensure_ascii=False) if args.json else report['reply'])
        return 0 if report['saved'] else 1
    print('IGRIS local chat. Native tools disabled. Session: '+conversation)
    print('Commands: /history, /sessions, /forget, /exit. Ctrl+C stops the active turn.')
    while True:
        try: text = input('You: ')
        except EOFError: break
        if text == '/exit': break
        if text == '/history':
            for role, content in memory.history('owner', conversation): print(role+': '+content)
            continue
        if text == '/sessions': print(json.dumps(memory.sessions('owner'))); continue
        if text == '/forget':
            memory.forget('owner', conversation)
            conversation = memory.create('owner', approved=True)
            print('Conversation deleted; new session: '+conversation); continue
        if not text.strip(): continue
        try:
            report = service.ask('owner', conversation, text)
            print('IGRIS: '+report['reply'])
        except (ValueError, KeyError, Denied) as exc:
            print('Chat request rejected ('+type(exc).__name__+'). Remove sensitive data or inspect session state.')
    return 0


if __name__ == '__main__':
    try: raise SystemExit(main())
    except KeyboardInterrupt:
        print('Stopped.', file=sys.stderr); raise SystemExit(130)
    except (Exception,) as exc:
        print('Chat unavailable ('+type(exc).__name__+'). Check private state and local runtime prerequisites.', file=sys.stderr)
        raise SystemExit(1)
