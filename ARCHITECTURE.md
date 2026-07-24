<!-- last_verified: 2026-07-15 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Call Library (scoped to the `calls/` prefix), New Call form, Call detail
    (audio player, transcript viewer, analytics panel, run/edit/delete)
  - QA dashboard (calls processed, audio hours, artifact fan-out, sentiment, queue mix)
  - Retained starter surfaces: full-bucket Files browser, generic Upload, Settings, Design
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for the Call entity: create (ingest), read, edit, delete, and
    **run** (analyze) — see `runtime/calls.py`
  - Fully-local **SpeechBrain pipeline** (VAD → ASR → ECAPA diarization → emotion)
    in `repo/speech_engine.py`, orchestrated by `service/analysis.py`
  - B2 S3 integration via boto3 (`repo/b2_client.py`, `repo/b2_storage.py`)
  - Health check, structured JSON logging, Prometheus-format metrics, per-IP rate limiting
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API (files + calls)
  - Consumed by `apps/web/` as workspace dependency

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (FileMetadata, UploadStats, etc.)
    config/                Settings loaded from environment
    repo/                  B2 S3 client (data access layer)
    service/               Business logic (upload, files, metadata)
    runtime/               FastAPI route handlers
  tests/                   pytest tests (structural + integration)
```

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **Speech-engine SDK containment**: `torch`, `torchaudio`, and `speechbrain`
  are imported **only** in `app/repo/speech_engine.py` (audio decode/resample in
  `app/repo/audio_io.py`). All imports are **lazy** (inside functions) so
  importing the module stays cheap and the test suite never triggers a model
  download. `service/analysis.py` orchestrates the pipeline through the
  `speech_engine` primitives — it never imports the ML SDKs directly.
- **Runtime device selection**: the compute device is auto-detected at runtime
  (CUDA → Apple MPS → CPU, CPU default) in `speech_engine.get_device()`; a GPU is
  never hard-required, and an MPS op failure demotes to CPU and retries.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No cross-layer mutable state**: Configuration is read-only after init, and no mutable state is shared *between* layers. Intra-layer caches/counters (the listing cache in `repo/b2_client.py`, the download counter in `repo/counter.py`, the rate-limit and metrics state in `runtime/`) are module-local and guarded by a `threading.Lock`.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. File keys reject empty and path-traversal patterns; optional prefix confinement via `ALLOWED_KEY_PREFIX` (off by default).

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repo
  - See `infra/railway/README.md` for configuration

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API), the sole data store
  (no application database). Calls are laid out by `date/queue`:

  ```
  calls/{date}/{queue}/{callId}/
      recording.{wav|mp3}   # source audio (create)
      meta.json             # the call record + status (edit target)
      transcript.jsonl      # {start,end,speaker,text,emotion} per line (run writes)
      analytics.json        # sentiment, flagged_phrases, silence_ratio, talk_time (run writes)
  ```

  - `meta.json` carries `status ∈ {uploaded, processing, done, error}`, so the
    UI polls it rather than needing a job store.
  - `queue`/`date` are immutable — they're part of the object key. Edits patch
    only mutable `meta.json` fields.
  - Listing/aggregation via `list_objects_v2`; artifact reads via `get_object`;
    playback/downloads via `generate_presigned_url`. Deletes are scoped to a
    single call's prefix (`delete_objects`), never bucket-wide.

## External Services

- **Backblaze B2 S3 API** — file storage, retrieval, deletion, presigned URLs

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins. `CORSMiddleware` is registered LAST in `main.py` (outermost) so it wraps **every** response, including uncaught-exception 500s — otherwise the browser would block error responses and the UI would only see an opaque "network error". See [docs/RELIABILITY.md](docs/RELIABILITY.md#error-handling). A per-IP rate-limit middleware sits inner to CORS; see [docs/SECURITY.md](docs/SECURITY.md#rate-limiting).
- **API -> B2** — authenticated via application keys, signature v4
- **Client -> B2** — presigned URLs for download (10-min expiry, forced attachment)

## Data Flows

- **Call ingest**: Browser -> `POST /calls` (multipart audio + metadata) ->
  `service.calls.create_call` writes `recording.*` + `meta.json` (status
  `uploaded`) under `calls/{date}/{queue}/{callId}/` -> response
- **Analyze (run)**: Browser -> `POST /calls/{id}/analyze` -> FastAPI
  `BackgroundTask` runs `service.analysis.analyze_call` (semaphore-bounded):
  reads the recording, VAD-segments, per segment {ASR, ECAPA embedding, emotion},
  clusters embeddings into speakers, computes analytics -> writes
  `transcript.jsonl` + `analytics.json` and flips `meta.status` to `done`
  (or `error`). Browser polls `GET /calls/{id}` while `status == processing`.
- **Library / dashboard**: Browser -> `GET /calls` / `GET /calls/stats` ->
  `service.calls` lists `meta.json` under `calls/` and aggregates
- **Detail**: `GET /calls/{id}`, `/transcript`, `/analytics`, `/audio`
  (presigned inline playback)
- **Edit**: `PATCH /calls/{id}` patches mutable `meta.json` fields
- **Delete**: `DELETE /calls/{id}` -> scoped `delete_prefix` of the call's prefix
- Retained starter file flows (`/upload`, `/files`) are unchanged.

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request; also the catch-all that converts uncaught exceptions to a typed JSON 500)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## Canonical Files

- Call routes (run via BackgroundTasks): `services/api/app/runtime/calls.py`
- CRUD orchestration: `services/api/app/service/calls.py`
- Pipeline orchestration: `services/api/app/service/analysis.py`
- SpeechBrain adapter (sole torch/speechbrain home): `services/api/app/repo/speech_engine.py`
- Audio decode/resample: `services/api/app/repo/audio_io.py`
- B2 data access (repo layer): `services/api/app/repo/b2_client.py`, `b2_storage.py`
- Pydantic models: `services/api/app/types/` (`calls.py`, `files.py`, `upload.py`, `stats.py`)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`; call tests: `tests/test_calls.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`; hooks: `lib/queries.ts`
- Call UI: `apps/web/src/app/calls/`, `apps/web/src/components/calls/`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Call Ingest](docs/features/call-ingest.md)
- [Transcription & Diarization](docs/features/transcription-diarization.md)
- [Call Analytics](docs/features/analytics.md)
- [Call Library](docs/features/call-library.md)
- [Dashboard](docs/features/dashboard.md)
- Retained starter surfaces: [File Upload](docs/features/file-upload.md), [File Browser](docs/features/file-browser.md), [Metadata Extraction](docs/features/metadata-extraction.md) (generic, secondary)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
