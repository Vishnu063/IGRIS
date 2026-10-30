# CI/CD preparation — Step 24

The GitHub Actions definition is valid YAML written as JSON to permit strict
standard-library parsing. It is manual-only: no push, pull_request, schedule or
hosted execution is activated. Pinned checkout/setup-python/upload-artifact action
SHAs were resolved read-only from GitHub. Permissions are contents:read; checkout
credentials are not persisted, jobs time out and artifacts expire after one day.

Prepared checks cover compile/build validation, unit/local integration tests,
credential-pattern scanning, standard-library dependency inventory and a
reproducible development-source ZIP with file hashes. No deployment job exists.
The ZIP explicitly declares production_ready=false and excludes local state and
.env files. Pattern scanning and an import inventory are not a full vulnerability
or licensing audit. Review included source/configuration for secrets before use.

Local tests execute available checks and artifact verification. Hosted workflow
execution and action/runner behavior remain PENDING_EXTERNAL_VERIFICATION. Do not
dispatch the workflow until the owner verifies a zero-cost entitlement or approves
spending; no CI minutes or storage purchases are authorized here. No dependency
installation is needed. Node must already exist for the n8n validation tests.
