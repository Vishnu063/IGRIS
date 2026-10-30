# Configuration and secrets guidance

Step 5 implements configuration loading only, not the assistant or Guardian.
Python 3.10+ is required by the current source; tests used Python 3.12.14.
No packages or services need installation for these checks.

## Profiles and precedence

`config/development.json` and `config/test.json` are complete, credential-free,
version-1 profiles. `load_settings()` defaults to development. A trusted caller's
explicit profile takes precedence over `IGRIS_PROFILE`; `IGRIS_LOG_LEVEL`
overrides the selected file's level. Only development/test are supported; no
production profile exists. `.env.example` documents safe variables but is never
automatically sourced or parsed. No dependency on dotenv is introduced.

Unknown JSON fields, duplicate keys, oversized files, invalid types, unsupported
profiles, non-loopback binding, nonzero budgets and enabled unfinished features
are rejected. Unknown `IGRIS_` environment variables are rejected to catch typos
or attempted unsafe overrides. Unrelated provider environment variables are
ignored and never copied into settings. Errors omit input values and file paths.
`config_dir` is a trusted development/test hook, not an API input or file-access
security boundary; Guardian path enforcement belongs to later steps.

Run configuration verification without installation:

```sh
$ PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Feature flags

Hermes, n8n, Ops Pilot, specialists, voice, dashboard and business runtime flags
are all false. Enabling any flag is rejected until later implementation adds a
verified integration and policy gate. A flag must never confer permissions.
Zero budget validation is a configuration guard, not financial enforcement.
Loopback configuration does not start or authenticate a server.

## Logging configuration

`Settings.logging_config()` returns a standard-library logging dictionary for
the `igris` namespace, with console output, no propagation to the root logger,
and no file creation. It does not apply logging settings automatically, disable
existing application loggers, or instantiate arbitrary classes from JSON.
Supported levels are INFO, WARNING, ERROR and CRITICAL; DEBUG is disabled here.
Test logging uses WARNING by default. Messages/exceptions are not redacted yet:
never log request bodies, configuration dictionaries, tokens or customer data.
Step 9 must implement and test redaction before integrating sensitive inputs.
Other application loggers and provider SDKs require separate review.

## Secrets management

- Never put API keys, GitHub/AWS credentials, passwords, authentication tokens or
  customer information in versioned configuration, example files or test output.
- Until a credential-consuming adapter is approved, no real secrets are needed.
  Future integrations should read narrowly scoped references from an approved
  environment/OS secret store at the execution boundary, never the AI prompt.
- Inject credentials only into the authorized component; avoid shell history,
  command arguments and broad environment dumps. Never commit local `.env`.
- `.gitignore` helps prevent accidents but is not secret scanning. No vault,
  encryption, secret scanner or key rotation service is implemented in this step.
- Do not request or print real credentials for tests. Use obvious synthetic
  markers only; mocked credential handling never proves provider connectivity.
- If exposure is suspected, stop affected execution, revoke/rotate through the
  provider, report sanitized evidence and follow an approved history cleanup
  procedure. Removing a file or Git commit does not revoke a credential.
- Restrict future local secret-file access to the owner, keep secrets out of
  ordinary backups, and establish secure recovery separately in Step 45.

Configuration is not permission management or a substitute for independent
Guardian enforcement. Secrets protection and approval controls remain later work.
