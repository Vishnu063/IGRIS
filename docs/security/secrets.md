# Secrets protection and evidence

Step 9 implements pattern-based protection, not a guarantee of complete data-loss
prevention. No real credentials were used in tests.

- `secrets.redact` removes configured provider-token/private-key/credential-URL
  patterns, bearer values, recognizable emails/phone numbers, and caller-supplied
  known secret values. A sensitive assignment label omits the whole payload to
  protect multiline/structured values. Unknown formats and prose personal data
  may be missed; false positives intentionally trade detail for confidentiality.
- Broker text reads pass through the prompt sanitizer before returning to callers.
  `prompt_text` is available for later model integrations; no AI provider is
  connected, and every future prompt assembly path must explicitly use it.
- Configured IGRIS logging uses RedactingFormatter after interpolation and
  traceback formatting. This protects emitted text, not original in-memory
  objects, other loggers, SDK debug traces or arbitrary third-party handlers.
- The local scanner checks high-confidence credential patterns in tracked and
  unignored UTF-8 worktree files AND exact staged index blobs. It reports only
  escaped path, line number and finding type. Unsupported/oversized files fail
  inspection rather than silently passing. Ignored files, history, remote GitHub
  data, generic unknown passwords and general customer PII are outside its scope.

```sh
$ PYTHONPATH=src python3 -m igris.guardian.scan
```

This is a manually run local scanner; hosted CI/pre-commit enforcement is not
installed. No exceptions for fixtures were added: synthetic sensitive strings
are assembled at test runtime. A literal synthetic URL initially triggered the
scanner and was rewritten without weakening detection.

Review added whole-payload omission for multiline sensitive labels and staged
blob inspection to prevent a clean worktree hiding a secret in the index.
One child-process test transiently failed; five diagnostic real invocations
succeeded in about 0.07–0.09 seconds and the full suite then passed without
relaxing limits. Root cause was not established; retain this as a reliability
observation rather than claiming a confirmed fix. Heredoc edits failed before
execution and were corrected. No security checks were disabled.

Future sensitive live use still requires protected secret injection, least
privilege, isolated identities, provider-specific checks, explicit consent for
customer data and review of all output/prompt paths. Never rely on redaction to
justify collecting unnecessary secrets or sending private information to models.
