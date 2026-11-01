# Optional local document conversion

MarkItDown 0.1.9 is Microsoft's MIT-licensed converter, not an agent runtime. The integration registers only PDF, DOCX, XLSX, PPTX and HTML converters with built-ins and plugins disabled. No Azure, OCR service, LLM provider, URL converter, speech or media processing is enabled. A networkless, non-root, read-only Docker worker receives one immutable file snapshot, Python and optional packages; never credentials, Guardian databases or the source workspace.

Explicit developer setup in the authorized cloud Linux x86_64 workspace:

```sh
$ runtime/python3149/python/bin/python3.14 -m venv --without-pip runtime/markitdown/venv
$ python3 -m pip --isolated --python runtime/markitdown/venv/bin/python install --no-input --no-compile --no-cache-dir --no-deps --require-hashes --only-binary=:all: --index-url https://pypi.org/simple -r integrations/markitdown/requirements-linux-x86_64.lock
$ PYTHONPATH=src python3 -m igris.integrations.markitdown_cli --enable-runtime --workspace /workspace/IGRIS/runtime/documents --file report.pdf --summarize
$ python3 scripts/test_markitdown_live.py
```

Create the private (0700) documents directory yourself and copy only approved documents there. The runtime accepts explicit allowlists of at most ten documents, each at most 4 MiB. Owner terminal approval binds exact paths, input hashes, runtime hashes and execution context. Changed content invalidates approval. Descriptor traversal rejects symlinks and hardlinks. ZIP containers reject traversal, duplicate names, encryption, embedded macros/objects, XML entities and external relationships; expansion is limited to 32 MiB, 500 members and a 100:1 ratio. Larger legitimate compressed documents can therefore be rejected. No archive is extracted into the host filesystem.

The worker has a 60-second wall deadline, 45-second CPU allowance, 1 GiB memory ceiling and bounded output. Markdown is capped at 6000 UTF-8 bytes with an explicit truncation flag. Secrets are redacted before returning text. The optional real Hermes summary uses only the first 2500 characters, marks truncation, treats document instructions as untrusted user data and exposes no native tools. Conversion is available through this manual CLI/API, not an automatically activated chat attachment feature.

Actual tests use generated, genuine PDF/Office/HTML fixtures and real conversion. A real Hermes response summarizes the shared Mumbai/zero-budget facts across all five formats. HTML includes an external image and malicious tool instructions: neither gains network or tool authority. Scanned/image-only PDFs have no OCR support; empty extraction is possible and must not be called a successful text reading. Layout, formulas and tables can lose fidelity. This is parser isolation, not a certification that arbitrary hostile documents are safe; kernel, parser and same-user risks remain. No Mac compatibility or human document quality claim follows from Linux fixtures.
