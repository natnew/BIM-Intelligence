# Security Policy

## Project maturity and supported development environments

BIM Intelligence is pre-alpha and under active development. The repository does not declare a
stable release or a supported-release window. The development compatibility range is Python
3.10–3.12 and Node.js 20 or 22; CI currently runs Python 3.12 and both listed Node.js versions.
This compatibility information is not a production-support or security-maintenance guarantee.

## Reporting a vulnerability

No private vulnerability-reporting channel or security contact is currently verified for this
repository. Do not post exploit details, sensitive logs or a working attack against a real project
in a public issue or discussion. Until the owner enables GitHub private vulnerability reporting or
publishes an approved private contact, there is no verified confidential reporting route. The owner
must establish one before the project invites public security reports.

General software defects and feature requests can be reported through
[GitHub Issues](https://github.com/natnew/BIM-Intelligence/issues), but do not use a public issue
for an undisclosed vulnerability.

## Security boundaries and implemented controls

- **Uploads:** the API accepts `.ifc` models and `.ids`, `.md` or `.txt` requirement documents,
  applies configurable size limits, validates extensions, and returns structured errors for
  unsupported or invalid inputs. IDS files are validated as IDS 1.0. Narrative files must be
  non-empty UTF-8 text. See the [model upload route](./backend/bim_intelligence/api/model.py),
  [document upload route](./backend/bim_intelligence/api/documents.py) and
  [configuration](./backend/bim_intelligence/config.py).
- **File-system boundaries:** session and run identifiers are validated before use in paths;
  stored artefact names are fixed rather than taken from client filenames. Session mutations use a
  lock. Model uploads are stored byte-for-byte in immutable, content-addressed versions, and the
  model, index and summary are activated together. Version-bound reads use the model hash and
  `ETag`/`If-Match` checks. These are application controls, not host-level access controls. See the
  [session store](./backend/bim_intelligence/store/session_store.py) and
  [architecture decisions](./docs/DECISIONS.md).
- **Network binding:** the server binds to loopback by default. A non-loopback bind requires
  `ALLOW_REMOTE=true`. The application has no user authentication or authorisation, so remote
  binding must not be treated as a protected deployment mode.
- **Credentials:** keep `MODEL_API_KEY` in the environment or an untracked local `.env` file. Never
  commit, paste into issues, or include it in logs. The health endpoint reports whether a key is
  configured but does not return the key itself.
- **Model calls:** `LLM_MODE` defaults to `off`. Live mode requires `MODEL_API_KEY` and
  `ALLOW_LIVE_LLM=true`; model identifiers ending in `-contributor` are rejected unless
  `ALLOW_CONTRIBUTOR_MODELS=true`. The configured API URL is constrained to
  `https://api.meta.ai/v1`. These code-level controls do not establish provider retention,
  confidentiality or training guarantees. See [configuration](./backend/bim_intelligence/config.py)
  and the [LLM client](./backend/bim_intelligence/llm/client.py).
- **Untrusted documents:** uploaded Markdown and text are treated as untrusted source content.
  Model-proposed requirements need source-quote verification and human confirmation; plans are
  bounded by confirmed checks and validated output schemas. The model's text cannot create a
  deterministic `Finding`. See the [requirement handling code](./backend/bim_intelligence/requirements/narrative.py)
  and [engineering rules](./AGENTS.md).
- **IFC integrity:** the application analyses uploaded model bytes and does not provide a model
  authoring workflow. IFC files are not rewritten during ingestion or review.

Do not transmit confidential BIM models, client documents, extracted content or derived excerpts to
an external model provider without explicit owner approval, applicable data rights and a
task-specific security and provenance review. Local inspection permission is not permission to
transmit. Keep confidential project material out of public issues and demonstrations.

## Known limitations

The repository is a local-development application, not a hardened hosted service. It has no
application-level authentication, tenant authorisation or deployment isolation. Data protection
therefore depends in part on the machine and file-system permissions used to run it. The repository
does not establish that uploaded files are malware-scanned or that IFC parsing runs in a sandbox;
it also records no independent penetration test, security certification or production security
assessment. Live provider processing and its data terms require separate review. Do not infer
security assurance from the presence of the controls above.

Configuration names and local run instructions are in [`.env.example`](./.env.example) and the
[README](./README.md). Never include secrets or confidential project data when requesting help.
