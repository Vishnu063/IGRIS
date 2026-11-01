"""Concrete scoped tasks after rejecting earlier unsupported model advice."""
import sys
import test_specialists_live as matrix
matrix.CASES=[
 ('backend','Write only a short Python function valid_title(value) that returns True exactly when value is a string with at least one non-whitespace character, and False for None, numbers and empty or whitespace strings. Use isinstance and strip. Do not add API endpoints, frameworks or unrelated advice.',r'(?i)def\s+valid_title',r'isinstance',r'\.strip\('),
 ('project_manager','Supplied tasks: implement one Python http.server handler on day 1; test it with unittest on day 2; then request owner approval. There is no frontend or database. Present the ordered two-day plan and the test-before-approval dependency. Use only supplied task names and dependencies; do not introduce any library or framework.',r'http\.server',r'unittest',r'(?i)(approv|owner)'),
 ('voice_ai','For manual push-to-talk, Start begins recording; Stop finalizes audio; Cancel must discard audio; unavailable microphone requires manual text entry, never fabricated transcription. Explain the resulting state transitions and how Stop differs from Cancel. No automatic recording.',r'(?i)stop',r'(?i)cancel',r'(?i)discard',r'(?i)text'),
 ('devops','Supplied Docker inspection evidence: State.Running=false, State.Status=exited, State.ExitCode=0, RestartCount=0. Report whether this container is running and its exit code. Do not speculate about why it stopped or propose a restart. Two short sentences only.',r'(?i)(not running|exited|stopped)',r'0')]
if __name__=='__main__':
 sys.argv=sys.argv[:1]+[row[0] for row in matrix.CASES];matrix.main()
