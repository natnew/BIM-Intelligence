# Support and Troubleshooting

BIM Intelligence is an early prototype. Start with the [README](./README.md) for the product
overview, setup and the example workflow.

## Development environment and startup

You need Python 3.10–3.12 (3.12 recommended) and Node.js 20.19+ or 22.12+. From the repository
root, install and start the backend:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn bim_intelligence.api.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
```

In a second terminal, start the frontend:

```bash
cd frontend
npm ci
npm run dev                      # http://localhost:5173
```

The health check is <http://127.0.0.1:8000/api/v1/health> and the interactive API documentation is
<http://127.0.0.1:8000/api/v1/docs>. The health response shows service and library versions, the
LLM mode and whether an API key is configured; it never shows the key.

## Supported inputs

- **Models:** `.ifc` only (IFC2X3, IFC4 and IFC4X3).
- **Requirements:** `.ids` (IDS 1.0), `.md` or `.txt`.
- **Not accepted:** PDF, RVT and NWD.
- Each valid IDS specification becomes a confirmed, executable requirement. Markdown and text are
  stored as source documents and do not become checks automatically.
- A review needs at least one confirmed requirement: upload a valid IDS, or add the built-in
  classification-consistency rule.

See the [architecture](./docs/ARCHITECTURE.md) for how the components fit together.

## Common problems

### Installation fails

- Check your Python version. IfcOpenShell publishes wheels for Python 3.10–3.12 only, so 3.13 and
  later will not install.
- Install the backend from the repository root with `python -m pip install -e ".[dev]"`, and the
  frontend with `npm ci` from `frontend/`.
- If a command is not found, check that the virtual environment is active and that you are in the
  right directory.

### The IFC upload or viewer fails

Check that the file has an `.ifc` extension and is within `MAX_IFC_MB` (200 MB by default). A
rejected upload returns a structured error explaining why. To tell a file problem from a setup
problem, try the synthetic fixture in
[`tests/fixtures/minimal.ifc`](./tests/fixtures/minimal.ifc).

### The IDS is rejected or no checks are available

The importer accepts IDS 1.0 and reports malformed or schema-invalid files as validation errors.
Markdown and text files are stored as source documents, not converted into checks. If no confirmed
check exists, upload a valid IDS before running a review.

### "Model version mismatch"

Every review run is pinned to the model it ran against. If the model is replaced afterwards, the
application refuses to mix data from the two versions. Run a new review against the current model,
or open the run that matches it.

### AI review is unavailable

`LLM_MODE=off` is the default, and the deterministic review works without an API key: choose
**Continue without AI**. To enable Muse Spark, set `LLM_MODE=live`, `ALLOW_LIVE_LLM=true`,
`LLM_MODEL=muse-spark-1.3` and `MODEL_API_KEY` in the backend `.env`, then restart the backend.
Live requests are billed by the provider. See [`.env.example`](./.env.example) for every setting.

## Reporting defects and requesting features

Use [GitHub Issues](https://github.com/natnew/BIM-Intelligence/issues). Include the steps to
reproduce, the expected and observed behaviour, your operating system and Python and Node.js
versions, and the relevant error message with any secrets removed. A reproduction with the
committed synthetic fixture is the most helpful.

Do not attach real architectural models, project documents, screenshots of project information,
API keys or unredacted logs to a public issue. To report a security vulnerability, follow
[SECURITY.md](./SECURITY.md).
