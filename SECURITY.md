# Security Policy

## Supported versions

BIM Intelligence is an early prototype (version 0.1.0). There is no long-term-support release;
security fixes are made on the `main` branch only.

| Component | Supported range                                           |
| --------- | --------------------------------------------------------- |
| Python    | 3.10–3.12 (3.12 recommended)                              |
| Node.js   | 20.19+ in the 20.x series, or 22.12+ in the 22.x series   |

CI is configured for Python 3.12 on Ubuntu and Windows and for Node.js 20 and 22.

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub:
**Security → Report a vulnerability** on the
[repository page](https://github.com/natnew/BIM-Intelligence/security).

Do not open a public issue, discussion or pull request for an undisclosed vulnerability, and do
not include exploit code, credentials, real project models or unredacted logs in any public
report. Ordinary defects and feature requests belong in
[GitHub Issues](https://github.com/natnew/BIM-Intelligence/issues).

A useful report includes the affected component, the version or commit, steps to reproduce with
synthetic data, and the impact you observed.

## Security model and implemented controls

- **Uploads.** The API accepts `.ifc` models and `.ids`, `.md` or `.txt` requirement documents. It
  checks extensions, enforces size limits (`MAX_IFC_MB`, default 200; `MAX_DOC_MB`, default 25),
  validates IDS files against IDS 1.0 and requires narrative files to be non-empty UTF-8 text.
  Invalid input returns a structured `application/problem+json` error. See the
  [model upload route](./backend/bim_intelligence/api/model.py),
  [document upload route](./backend/bim_intelligence/api/documents.py) and
  [configuration](./backend/bim_intelligence/config.py).
- **File-system boundaries.** Session and run identifiers are validated before they are used in a
  path, and stored file names are fixed rather than taken from the client. Session changes are
  made under a lock. Model uploads are stored byte-for-byte in content-addressed versions and
  published by a single atomic write; version-bound reads use the model hash with
  `ETag`/`If-Match`. See the [session store](./backend/bim_intelligence/store/session_store.py).
- **Network binding.** The server binds to loopback by default and refuses a non-loopback address
  unless `ALLOW_REMOTE=true`. The application has no authentication, so remote binding is not a
  protected deployment mode.
- **Credentials.** Provide `MODEL_API_KEY` through the environment or an untracked `.env` file.
  The health endpoint reports only whether a key is configured, never its value.
- **Model calls.** `LLM_MODE` defaults to `off`. Live mode requires `LLM_MODE=live`,
  `ALLOW_LIVE_LLM=true` and a key. The provider URL is fixed to `https://api.meta.ai/v1`, and
  `-contributor` model identifiers are rejected unless `ALLOW_CONTRIBUTOR_MODELS=true`. A
  persistent spend ledger caps calls and cost per review and per installation; it is an
  application safeguard, not a provider-enforced billing limit. See the
  [LLM client](./backend/bim_intelligence/llm/client.py).
- **Untrusted documents and model output.** Uploaded Markdown and text are treated as untrusted
  input. Model output is schema-validated; extracted requirements must quote their source
  verbatim and be confirmed by a person; review plans may only reference confirmed checks; and
  explanations are checked against the recorded evidence. Model text can never create a
  `Finding`. See the
  [requirement handling code](./backend/bim_intelligence/requirements/narrative.py).
- **IFC integrity.** Uploaded IFC files are read, never modified or re-saved.
- **No telemetry.** The application sends no analytics. The viewer's WebAssembly and worker files
  are served locally.

## Data you send to a model provider

In Live mode, review planning sends the objective, a model summary and requirement metadata to
the Meta Model API; an explanation request also sends the selected finding's evidence and element
properties. The IFC file itself is never sent. Only use Live mode with data you have the right to
share with a third-party provider, and review the provider's data terms first.

## Known limitations

BIM Intelligence is a local-development application, not a hardened hosted service:

- no user authentication, authorisation or multi-tenant isolation;
- data protection depends on the permissions of the machine and file system it runs on;
- uploaded files are not malware-scanned, and IFC parsing is not sandboxed;
- no independent penetration test or security certification has been carried out.

Do not expose it to an untrusted network or use it with confidential project data without your
own security review.
