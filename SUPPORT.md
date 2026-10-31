# Support and Troubleshooting

BIM Intelligence is pre-alpha software under active development. Start with the
[README](./README.md) for project status, setup, the intended workflow and links to the technical
documentation.

## Development environment and startup

The development range is Python 3.10–3.12 (develop on 3.12) and Node.js 20 or 22. From a clean
checkout, install and start the backend from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn bim_intelligence.api.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`. In a second terminal,
run the frontend:

```powershell
cd frontend
npm ci
npm run dev
```

The API health check is <http://127.0.0.1:8000/api/v1/health>; interactive API documentation is
<http://127.0.0.1:8000/api/v1/docs>. The health response includes service and library versions,
LLM mode and a key-configured boolean; it does not expose the key.

## Supported input and review behaviour

- Model uploads: `.ifc` only (IFC2X3, IFC4 and IFC4X3 parsing is described by the API).
- Requirement uploads: `.ids` (IDS 1.0), `.md` or `.txt`.
- PDF, RVT and NWD are not accepted by the implemented upload routes.
- Valid IDS specifications become confirmed requirements. Markdown and text are stored as source
  material and do not automatically create executable requirements.
- A review needs confirmed executable requirements. A session with none cannot run a review;
  upload a valid IDS or add an available registered native requirement. The model does not turn
  unconfirmed narrative text into a check by itself.

See the [requirements documentation](./docs/REQUIREMENTS.md) and
[architecture](./docs/ARCHITECTURE.md) for the distinction between implemented behaviour and
planned workflow.

## Common problems

### Installation fails

- Use Python 3.10, 3.11 or 3.12; IfcOpenShell support is constrained by the repository's declared
  Python range. Install backend dependencies from the repository root with
  `python -m pip install -e ".[dev]"`.
- Use Node.js 20 or 22 and install the locked frontend dependencies with `npm ci` from `frontend/`.
- If a command is not found, confirm the Python virtual environment is active or that the terminal
  is running from the expected directory.

### IFC upload or viewer fails

Confirm the file has an `.ifc` extension and is within the configured `MAX_IFC_MB` limit (200 MB by
default). The backend validates and indexes the model; a rejected upload returns a structured API
error. The browser viewer loads the same stored model version. Try the committed synthetic fixture
to distinguish a project-specific input problem from a local setup issue. Do not attach confidential
models to public issues.

### IDS is rejected or no checks are available

The importer accepts IDS 1.0 and reports malformed or schema-invalid files as validation errors.
Check the file is a valid `.ids` document. A `.md` or `.txt` upload is retained as source material,
not converted automatically into executable checks. If no confirmed check is present, upload a
valid IDS or add an available registered native requirement before running a review.

### Model-version mismatch

Review runs are pinned to the model hash. If a model is replaced after a run, the application
rejects stale reads rather than combining data from different versions. Reopen or run a review
against the active model version and select the corresponding run.

### Meta Model API or offline mode

The default is `LLM_MODE=off`; deterministic IDS review does not require an API key. Live requests
are optional and require explicit configuration of `MODEL_API_KEY`, `LLM_MODE=live` and
`ALLOW_LIVE_LLM=true`. They may incur cost and must not be enabled without explicit project-owner
approval. Keep credentials out of issues and logs. See [`.env.example`](./.env.example) and
[AGENTS.md](./AGENTS.md#8-security-requirements).

## Reporting defects and requesting features

Use [GitHub Issues](https://github.com/natnew/BIM-Intelligence/issues) for reproducible software
defects and feature requests. Include the steps to reproduce, expected and observed behaviour,
operating system, Python and Node versions, relevant command and test results, and a sanitised error
message. Prefer a committed synthetic fixture or a minimal synthetic example.

Do not upload architectural models, project documents, extracted text, screenshots containing
project information, API credentials or unredacted logs to public issues. For a suspected security
vulnerability, follow [SECURITY.md](./SECURITY.md); do not publish exploit details.
