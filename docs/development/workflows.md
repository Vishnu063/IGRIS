# Development workflows — Step 22

create_webapp materializes a reviewed disposable frontend, Python API and SQLite
sample with API/dependency documentation. The HTTP API is read-only; local Store
writes are parameterized and bounded. Dependencies are standard-library only;
no package manager, external API, paid service or specialist is activated.

Tests compile the generated backend, execute its reviewed code, exercise actual
SQLite writes and local HTTP integration, and check frontend rendering uses
textContent. Browser rendering, arbitrary frontend/backend generation, external
API compatibility and production hardening are not verified. There is no claim
that a commerce or mobile application has been built. Specialist activation is
still governed by later steps; none is needed for this sample.

These are trusted operator development utilities, not unrestricted agent tools.
Never execute third-party/model-generated source through this harness without
review and separate OS sandboxing. No general untrusted build runner is provided.
