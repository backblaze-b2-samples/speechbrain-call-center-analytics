# Build plan — `speechbrain-call-center-analytics`

> Source of truth for the starter tree: `.claude/scratch/vcsk-ee452cf1-43d6-4f17-aac8-f0b813a7d0ce/`
> (fresh clone of `vibe-coding-starter-kit`). Delta below is computed against that tree.

## 1. Purpose

`speechbrain-call-center-analytics` is a B2 sample for **contact-center / CX teams and
insurance-fintech QA orgs** that need to process large archives of call recordings.
A user ingests a call recording (WAV/MP3 telephony audio), the app runs a **fully-local
SpeechBrain pipeline** — voice-activity segmentation, ASR transcription, speaker
diarization, and per-segment emotion/sentiment — then writes a timestamped
speaker-labeled transcript (`transcript.jsonl`) and a per-call analytics file
(`analytics.json`) back to B2 **alongside the source recording**, roughly tripling
stored data per call. QA dashboards, compliance review, and retraining pipelines then
read recordings + derived artifacts straight from B2 over the **S3-compatible API**,
using a `date/queue` prefix layout as the index. The sample's story is *B2 as the
durable storage layer for a high-volume, write-heavy AI audio workflow* — no second API
key, **B2 credentials only**, everything else runs on-device.

## 2. Architecture delta from `vibe-coding-starter-kit`

The starter kit is the ceiling — strip what this app doesn't need, keep the reusable
B2-backed scaffolding, add the call-analytics domain on top.

### KEEP (as-is — do not strip/rename/replace)
- **UI kit** `apps/web/src/components/ui/` (all shadcn primitives), design tokens in
  `apps/web/src/app/globals.css`, and the `/design` reference page.
- **Bucket explorer** — `/files` route, `apps/web/src/app/files/`,
  `apps/web/src/components/files/`, and the **Files** sidebar entry. *Non-negotiable
  keep* (full-bucket browse). No tension here: QA reviewers genuinely want raw-bucket
  browse to spot-check any object, so it stays.
- **Upload** — `/upload` route + `apps/web/src/components/upload/` + the **Upload**
  sidebar entry, as the generic raw-bucket ingest surface (starter contract). The
  sample's domain ingest is a *separate* scoped "New Call" flow (see ADD); the generic
  uploader stays for arbitrary objects.
- **Settings** — `/settings` + `settings-form.tsx` (kept as the demo-only form + the
  in-repo **form-UX exemplar**; §4 mirrors its selector + FormDescription patterns).
- FastAPI **layered architecture** (`types→config→repo→service→runtime`), structural
  tests, `/health`, `/metrics`, per-IP rate limiting, JSON logging, magic-byte upload
  validation.
- **Data layer discipline**: every fetch through TanStack Query hooks in
  `apps/web/src/lib/queries.ts` + `api-client.ts`; new endpoints touch exactly
  `runtime/<router>.py` + `lib/api-client.ts` + `lib/queries.ts`.
- `repo/b2_client.py` core storage helpers (extend, do **not** rewrite): `get_s3_client`
  (lru_cache + `user_agent_extra`), list cache/single-flight, presign, delete.
- Generic file-metadata extraction (`service/metadata.py`, Pillow) — **kept and left
  unfeatured**; it still backs the retained Files browser detail panel. (Low-value to
  rip out; keeping it avoids a wide blast radius that would burn fix rounds. Drop
  `PyPDF2` only — no PDFs in this app — if trivial and tests stay green; otherwise keep.)

### TRIM (remove / rewrite starter-specific content)
- **Starter-kit branding & narrative**: README hero ("Vibe Coding Starter Kit / stop
  wiring boilerplate"), `PRODUCT.md` vibe-coder framing, "Building Your App" section →
  rewritten for the call-center analytics use case (§5).
- **Illustrative dashboard defaults** — `apps/web/src/components/dashboard/`
  (stats-cards, upload-chart, recent-uploads-table) are *adapted* (per starter contract
  the dashboard is the one screen designed to be rewritten) to call-center metrics (§ADD).
- `app-config.ts` identity strings and every `vibe-coding-starter-kit` identifier (§6).

### ADD (new for this sample)
- **Calls domain (the primary entity + the sample-specific scoped asset explorer)**:
  - `apps/web/src/app/calls/page.tsx` — **Call Library**: the sample's asset explorer,
    **scoped to the `calls/` prefix** (distinct from the full-bucket `/files` explorer).
    Lists calls with queue / date / status / #speakers / sentiment; filter by queue+date.
  - `apps/web/src/app/calls/new/page.tsx` — **New Call** create form (§4).
  - `apps/web/src/app/calls/[callId]/page.tsx` — **Call detail**: audio player
    (presigned playback), transcript viewer (timestamped, speaker-colored segments),
    diarization talk-time bar, analytics panel (sentiment, flagged phrases, silence
    ratio), an **Analyze / Re-analyze** (run) button, **Edit** and **Delete** actions.
  - `apps/web/src/components/calls/*` — call-library table, transcript viewer,
    analytics panel, call form (create+edit share one component), delete confirm dialog.
  - **Sidebar**: add a **Calls** entry (e.g. `Headphones`/`PhoneCall` lucide icon) to
    `app-sidebar.tsx`, keeping Dashboard / Upload / Files / Settings / Design.
- **Backend (layered)**:
  - `services/api/app/types/calls.py` — Pydantic models + enums: `Queue`,
    `SpeakerCount`, `AsrQuality`, `CallStatus`; `CallMeta`, `Call`, `TranscriptSegment`,
    `CallAnalytics`, `CreateCallRequest`, `UpdateCallRequest`.
  - `services/api/app/repo/speech_engine.py` — **SpeechBrain adapter**. The *sole* home
    of `speechbrain` / `torch` / `torchaudio` imports (lazy, inside functions).
    Device autodetect **CUDA → MPS → CPU** (CPU default; `SPEECHBRAIN_DEVICE` override).
    Loads/caches the four pretrained models (lru_cache) and exposes primitives:
    `segment(audio)`, `transcribe(seg)`, `embed(seg)`, `emotion(seg)`. Split into a
    second repo module if it approaches the 300-line cap.
  - `services/api/app/repo/b2_client.py` — extend with: `put_bytes(key, data, ct)`,
    `get_bytes(key)`, `list_prefix(prefix)`, `delete_prefix(prefix)` (scoped multi-delete
    — **only** under the given call prefix, never bucket-wide).
  - `services/api/app/service/calls.py` — CRUD orchestration: create (write recording +
    `meta.json`), list/get (read `meta.json` + artifacts), edit (patch `meta.json`),
    delete (scoped `delete_prefix`), dashboard aggregation over `calls/` meta.
  - `services/api/app/service/analysis.py` — pipeline orchestration: VAD-segment → per
    segment {ASR text, ECAPA embedding, emotion} → cluster embeddings
    (sklearn `AgglomerativeClustering`, k=expected_speakers) into speaker labels →
    compute analytics (flagged phrases via configurable keyword match, silence ratio from
    VAD, talk-time split from diarization) → write `transcript.jsonl` + `analytics.json`,
    set `meta.status`. Runs under a **concurrency semaphore (default 1)** to bound memory.
  - `services/api/app/runtime/calls.py` — routes (§3); `run` via FastAPI `BackgroundTasks`.
  - `apps/web/src/lib/api-client.ts` + `queries.ts` — call CRUD+run hooks; the library +
    detail poll (`refetchInterval`) while `status ∈ {processing}`.
- **Feature docs**: `docs/features/call-ingest.md`, `transcription-diarization.md`,
  `analytics.md`, `call-library.md` (§5).
- Updated `requirements.txt` (§ pins below), `.env.example`, README, ARCHITECTURE,
  AGENTS.md, PRODUCT.

### B2 key layout (B2 is the sole data store — no DB, per starter)
```
calls/{date}/{queue}/{callId}/
    recording.{wav|mp3}     # source audio (create)
    meta.json               # entity record: title, queue, date, labels, language,
                            #   expected_speakers, asr_quality, compliance_keywords,
                            #   notes, status, timestamps  (edit target)
    transcript.jsonl        # {start,end,speaker,text,emotion} per line (run writes)
    analytics.json          # sentiment, flagged_phrases, silence_ratio, talk_time,
                            #   num_speakers, duration_sec               (run writes)
```
`status ∈ {uploaded, processing, done, error}` lives in `meta.json` → clean poll model.
`queue`/`date` are immutable (encoded in the key); edit changes only `meta.json` fields.

## 3. B2 surface (S3-compatible only — no b2-native)

| Op | S3 call | Used by |
|----|---------|---------|
| Write recording / meta / transcript / analytics | `put_object` | create, run, edit |
| List calls by prefix | `list_objects_v2` (continuation) | library, dashboard |
| Object metadata | `head_object` | detail |
| Read recording (for pipeline) / read artifacts (serve) | `get_object` | run, detail |
| Presigned audio playback + artifact download | `generate_presigned_url` | detail |
| Delete a call (scoped to its prefix) | `delete_object(s)` | delete |

All via boto3 in `repo/` with `Config(signature_version="s3v4", user_agent_extra=...)`.
**No b2-native SDK.** Standard #3 env names enforced (§6). This exercises the write-heavy
"triple the stored data per call" story (1 recording in → +2 derived artifacts written).

## 4. Key features (seed README + `docs/features/*`)

1. **Call ingest** — upload a telephony recording into a `date/queue` prefix with call
   metadata. *(deployment: local — no external provider; B2 write only.)*
2. **Transcription & diarization (SpeechBrain, local)** — VAD segmentation + wav2vec2 ASR
   + ECAPA speaker embeddings clustered into speakers → timestamped speaker-labeled
   transcript. *(deployment: **local**; provider none/on-device; per-run cost **$0**,
   B2 credentials only; env key n/a. CPU default, GPU autodetect CUDA→MPS→CPU.)*
3. **Call analytics (SpeechBrain, local)** — per-segment emotion → call sentiment score;
   configurable compliance keyword flagging; silence ratio; agent/customer talk-time
   split → `analytics.json`. *(deployment: **local**; cost **$0**.)*
4. **Call Library** — sample-scoped asset explorer over the `calls/` prefix, with
   queue/date filters and per-call status.
5. **QA dashboard** — calls processed, audio hours ingested, artifacts written (shows the
   3× fan-out), average sentiment, queue breakdown, recent calls.

**AI provider selection** (per `api-provider-selection.md`): SpeechBrain is the *whole
point* and the workload is **on-device** → **local is the default** (rule 1, "point is
on-device capability"). No external API, **no key beyond `B2_*`**, per-run cost **$0**.
Hard rule honored: CPU default + GPU autodetect CUDA→MPS→CPU. **MPS caveat**: wav2vec2 /
SpeechBrain ops have incomplete MPS coverage — if an MPS op errors, fall back to CPU
(document `SPEECHBRAIN_DEVICE=cpu`); effectively the sample runs CUDA→CPU on most hosts.

**No Genblaze**: the description's Trending OSS is SpeechBrain and the suggested stack
does **not** mention Genblaze / `genblaze-*` / `genblaze-s3`, so provider calls are **not**
routed through the Genblaze SDK. (Rule N/A — there is no external provider at all.)

**Deliberately NOT pyannote**: diarization uses SpeechBrain's own ECAPA embeddings +
clustering, avoiding pyannote's HF **gated-model** terms-acceptance trap. All four models
(`vad-crdnn-libriparty`, `asr-wav2vec2-commonvoice-14-en`, `spkrec-ecapa-voxceleb`,
`emotion-recognition-wav2vec2-IEMOCAP`) are **non-gated** — no HF token, no terms click.

### Primary-entity lifecycle — entity: **Call**
All five verbs are **built in the UI** (no omissions → `omitted_ui_verbs: []`):
- **create** — `/calls/new` form → `POST /calls` (multipart audio + metadata).
- **read** — `/calls` library + `/calls/[callId]` detail (`GET /calls`, `/calls/{id}`,
  `/calls/{id}/transcript`, `/calls/{id}/analytics`, `/calls/{id}/audio`).
- **edit** — edit dialog → `PATCH /calls/{id}` (mutable `meta.json` fields; re-run picks
  up changed analysis params).
- **delete** — confirm dialog → `DELETE /calls/{id}` (scoped prefix delete of all 4
  object kinds).
- **run** — **Analyze / Re-analyze** button → `POST /calls/{id}/analyze`
  (BackgroundTask; status poll to `done`/`error`).

### Form UX conventions
Mirror `settings-form.tsx` (react-hook-form + zod + shadcn `Form`).
- **Finite-value fields → selectors (create AND edit)**:
  - `queue` → **Select**: {sales, support, billing, retention, collections}.
  - `expectedSpeakers` → **RadioGroup**: {2 (agent + customer), 3, auto}.
  - `asrQuality` → **Select**: {fast, accurate}.
- **Free text**: `title`, `agentLabel`, `customerLabel`, `notes` (Input/Textarea).
- **CREATE-only safe defaults** (placeholder / `FormDescription` guidance — **never** an
  autofill button): queue → "support"; expectedSpeakers → "2 — agent + customer (most
  calls)"; asrQuality → "fast (recommended for 8–16 kHz telephony)"; title placeholder
  "e.g. Refund request — 2026-07-23". Date defaults to today.
- **EDIT form** opens pre-filled from `meta.json` (real resource) — same selectors, **no**
  default hints. `queue`/`date` shown read-only (immutable — they're in the object key).

## 5. Doc transforms
- **README.md** — rewrite hero + "What it looks like" + features + Tech Stack for the
  call-center pipeline; **keep** the B2 quickstart but update env-var names (§6) and the
  UTM `utm_content` tag; add a "how the pipeline runs locally (CPU/GPU)" + "first run
  downloads ~1–2 GB of SpeechBrain models" note.
- **PRODUCT.md** — rewrite Users/Purpose for CX/QA/compliance teams.
- **ARCHITECTURE.md** — add the SpeechBrain pipeline data flow, the new layer files, the
  `calls/` prefix layout, and the **speech-engine SDK-containment invariant**.
- **AGENTS.md** — add invariant: `speechbrain`/`torch`/`torchaudio` imported **only** in
  `repo/speech_engine.py`; note the calls 3-file endpoint touch; `calls/` layout.
- **docs/features/**: keep `file-upload.md`, `file-browser.md`; **adapt** `dashboard.md`;
  keep `metadata-extraction.md` (reframed as *generic* file metadata, secondary); **add**
  `call-ingest.md`, `transcription-diarization.md`, `analytics.md`, `call-library.md`.
- Move this plan to `docs/exec-plans/completed/initial-scaffold.md` on PASS (Phase 5).

## 6. Rename table (`vibe-coding-starter-kit` → `speechbrain-call-center-analytics`)

| Kind | From | To |
|------|------|----|
| kebab repo/dir | `vibe-coding-starter-kit` | `speechbrain-call-center-analytics` |
| pnpm scope | `@vibe-coding-starter-kit/web`, `/shared` | `@speechbrain-call-center-analytics/web`, `/shared` |
| py project name | `vibe-coding-starter-kit` (pyproject) | `speechbrain-call-center-analytics` |
| APP_NAME | `"OSS Starter Kit"` | `"SpeechBrain Call Center Analytics"` |
| APP_DESCRIPTION | file-mgmt blurb | `"Transcribe, diarize & analyze call recordings — stored on Backblaze B2"` |
| Railway svc / image tags | `vibe-coding-starter-kit-*` | `speechbrain-call-center-analytics-*` |
| CI filter names | `@vibe-coding-starter-kit/web` | new scope |
| user_agent_extra + utm_content | `b2ai-oss-start` | `b2ai-oss-speechbrain-call-center` |
| titles/headings | "Vibe Coding Starter Kit" | "SpeechBrain Call Center Analytics" |

### B2 env-var rename — Standard #3 (parent CLAUDE.md; starter deviates — MUST fix)
| Starter (deviation) | Standard #3 (required) | Note |
|---------------------|------------------------|------|
| `B2_KEY_ID` / `b2_key_id` | `B2_APPLICATION_KEY_ID` / `b2_application_key_id` | rename everywhere |
| `B2_ENDPOINT` / `b2_endpoint` | `B2_REGION` / `b2_region` | add region; derive endpoint `https://s3.{region}.backblazeb2.com` via a `settings` property; update `b2_client.get_s3_client` to use it |
| `B2_PUBLIC_URL` / `b2_public_url` | `B2_PUBLIC_URL_BASE` / `b2_public_url_base` | rename in settings + `_public_url` |
| `B2_APPLICATION_KEY`, `B2_BUCKET_NAME` | unchanged (already Standard) | keep |

Update: `config/settings.py`, `repo/b2_client.py`, `.env.example`, README quickstart,
any `infra/railway` + CI references. Default `b2_region` = `us-west-004` (matches the
starter's default endpoint region) so nothing silently breaks.

## 7. Dependency pins (`services/api/requirements.txt` — heavy ML stack)

Add (pin windows chosen for macOS-arm64 clean-install + torch/numpy compat; the
end-to-end verify step — not this build — exercises real model download):
```
torch>=2.2,<2.9
torchaudio>=2.2,<2.9          # must track torch; audio load/resample
speechbrain>=1.0,<1.1         # 1.0 speechbrain.inference API
huggingface_hub>=0.23,<1.0    # SpeechBrain pulls pretrained models (non-gated)
soundfile>=0.12.1             # libsndfile 1.1 → robust WAV + MP3 read w/o ffmpeg
librosa>=0.10,<0.12           # load + resample to 16 kHz mono
scikit-learn>=1.3             # AgglomerativeClustering for diarization
numpy<2                       # torch/torchaudio/numba (librosa) compatibility
```
Keep existing fastapi/uvicorn/boto3/pydantic/Pillow/dev deps. Drop `PyPDF2` only if the
Files browser + tests stay green without it (else keep). **Clean-install risk is real**
(large wheels, numba↔numpy) — the builder pins explicitly and does **not** rely on a
"boots green" check; the heavy end-to-end run is validated later by the verify step.

## 8. Testing strategy (keep the build green in CI without downloading models)
- `repo/speech_engine.py` lazy-imports `torch`/`speechbrain` **inside functions** →
  cheap module import; structural AST test still sees imports contained to `repo/`.
- Tests **monkeypatch** `service.analysis` pipeline primitives (or `speech_engine`
  functions) to return canned segments/embeddings → `pnpm test:api` never downloads a
  model or runs torch. Add `tests/test_calls.py` (CRUD + scoped-delete + status flow)
  and keep structural tests green (new layer files respect layering; `boto3` only in
  `repo/`; every file < 300 lines — split `speech_engine`/`analysis` if needed).
- Frontend: adapt/keep vitest unit tests; ensure `pnpm lint`, `pnpm build`,
  `pnpm check:structure` all pass (build-timeout memory: confirm the LAST phases —
  doc-theming + frontend wiring — actually completed; run the reviewer + `pnpm lint`/
  `pnpm build`).

## 9. Non-goals / scope guards
- One entity (**Call**), CRUD+run only — no batch-queue UI, no auth, no DB.
- Never push to a remote, create binary/screenshot assets, or touch sibling samples —
  those belong to later pipeline steps.
- Scoped deletes only (per call prefix); never bucket-wide.
