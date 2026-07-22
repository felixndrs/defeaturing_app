# AI Defeaturing Review

Compares an original CAD model with a defeatured one, recognises and classifies
every geometry change, has an LLM assess each change against measured evidence,
and documents the result as an engineering PDF plus an interactive review bundle.

Scope of the current MVP: **STEP vs. STEP**. Other formats and feature types are
added through the extension points described below, without restructuring.

## Running locally (tested path)

Requires Python 3.12 and Node.js. Docker is optional and not required.

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

API docs are then at http://localhost:8000/docs.

```powershell
# Tests
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Copy `.env.example` to `.env` to configure. `LLM_PROVIDER=null` (the default)
runs the whole pipeline offline with deterministic placeholder assessments, so
no API key and no cost is needed for development or tests.

Docker Compose files are present for the later Linux/cloud deployment but are
not yet exercised on this machine.

## Extension points

Adding capability means adding a file, not editing the pipeline:

| To add | Create | Register with |
|---|---|---|
| A file format | `backend/app/importers/<fmt>_importer.py` | `@register_importer` |
| A feature type | `backend/app/analysis/detectors/<name>.py` | `@register_detector` |
| An LLM backend | `backend/app/llm/<name>.py` | `@register_provider` |

Everything flows through the internal data model in
`backend/app/domain/models.py` — that module is the contract between importers,
analysis stages, detectors, the LLM layer and reporting, and is the right place
to start reading.

## Non-negotiable invariant

No geometry change may be lost. Every difference that no detector claims is
emitted as an `unknown` feature carrying its raw evidence, and a test asserts
that classified + unknown changes account for the complete diff.
