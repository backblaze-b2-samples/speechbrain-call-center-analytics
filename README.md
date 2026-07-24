<!-- last_verified: 2026-07-23 -->
# SpeechBrain Call Center Analytics

Turn a pile of call recordings into searchable, speaker-labeled transcripts and
per-call analytics — **entirely on-device** with [SpeechBrain](https://speechbrain.github.io/),
storing every recording and derived artifact on
**[Backblaze B2](https://www.backblaze.com/cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-oss-speechbrain-call-center)**.

Built for contact-center / CX teams and insurance-fintech QA orgs that need to
process large archives of telephony audio. Upload a call, run the local pipeline
— **voice-activity segmentation → ASR transcription → speaker diarization →
per-segment emotion/sentiment** — and the app writes a timestamped
speaker-labeled `transcript.jsonl` and a per-call `analytics.json` back to B2
**alongside the source recording**. One recording in becomes three objects out,
roughly tripling stored data per call. QA dashboards, compliance review, and
retraining pipelines then read recordings + artifacts straight from B2 over the
**S3-compatible API**, using a `calls/{date}/{queue}/` prefix layout as the index.

**No second API key. B2 credentials only — everything else runs on your hardware.**

## What you get

- **Call ingest** — upload WAV/MP3 telephony audio with metadata into a
  `date/queue` prefix on B2.
- **Transcription & diarization (local)** — SpeechBrain VAD + wav2vec2 ASR +
  ECAPA speaker embeddings clustered into speakers, producing a timestamped,
  speaker-labeled transcript.
- **Call analytics (local)** — per-segment emotion rolled into a call sentiment
  score, configurable compliance-keyword flagging, silence ratio, and
  agent/customer talk-time split.
- **Call Library** — a sample-scoped asset explorer over the `calls/` prefix
  with queue/date filters and per-call status.
- **QA dashboard** — calls processed, audio hours ingested, artifacts written
  (the 3× fan-out), average sentiment, and a queue breakdown.
- The reusable starter scaffolding: a full-bucket **Files** browser, generic
  **Upload**, layered FastAPI backend with structural tests, `/health`,
  `/metrics`, per-IP rate limiting, and the shadcn/ui design system.

## How the pipeline runs (CPU / GPU)

The SpeechBrain models run locally. Device is **auto-detected at runtime** —
the first available of **CUDA → Apple MPS → CPU**, defaulting to CPU. No GPU is
required. Pin it with `SPEECHBRAIN_DEVICE` if needed.

> **MPS caveat:** wav2vec2 / SpeechBrain have incomplete Apple-MPS operator
> coverage. If an op fails on MPS the engine transparently demotes to CPU and
> retries; set `SPEECHBRAIN_DEVICE=cpu` to skip MPS entirely. In practice the
> sample runs CUDA → CPU on most hosts.

> **First run downloads ~1–2 GB of SpeechBrain models** (cached under
> `~/.cache/sb-ccanalytics`, override with `SPEECHBRAIN_CACHE`). All four models
> are **non-gated** — no Hugging Face token and no terms to accept.

## Four non-gated models

| Stage | Model |
|-------|-------|
| Voice-activity segmentation | `speechbrain/vad-crdnn-libriparty` |
| ASR transcription | `speechbrain/asr-wav2vec2-commonvoice-14-en` |
| Speaker embeddings (diarization) | `speechbrain/spkrec-ecapa-voxceleb` |
| Emotion recognition | `speechbrain/emotion-recognition-wav2vec2-IEMOCAP` |

Diarization deliberately uses SpeechBrain's own ECAPA embeddings + clustering
(scikit-learn `AgglomerativeClustering`) rather than pyannote, avoiding
pyannote's gated-model terms-acceptance step.

## Quick Start

You need: Node.js >= 20, pnpm >= 9, Python >= 3.11, and a free
**[Backblaze B2 account](https://www.backblaze.com/cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-oss-speechbrain-call-center)**.

**1. Install dependencies**

```bash
pnpm install
```

**2. Set up the backend**

```bash
cd services/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # includes torch/torchaudio/speechbrain (large)
cd ../..
```

**3. Add your B2 credentials**

```bash
cp .env.example .env
```

Open `.env`, then in the [Backblaze B2 dashboard](https://secure.backblaze.com/b2_buckets.htm?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-oss-speechbrain-call-center):

1. **Create a bucket** and paste its values into `.env`:
   - **Bucket Unique Name** → `B2_BUCKET_NAME`
   - **Region** (e.g. `us-west-004`, shown on the bucket) → `B2_REGION`
     *(the S3 endpoint `https://s3.<region>.backblazeb2.com` is derived from it)*
2. **Create an application key** with `Read and Write`:
   - **keyID** → `B2_APPLICATION_KEY_ID`
   - **applicationKey** → `B2_APPLICATION_KEY` *(only shown once)*

> Walkthroughs: [creating a bucket](https://www.backblaze.com/docs/cloud-storage-create-and-manage-buckets?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-oss-speechbrain-call-center) · [creating app keys](https://www.backblaze.com/docs/cloud-storage-create-and-manage-app-keys?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-oss-speechbrain-call-center).

**4. Run it**

```bash
pnpm dev
```

Frontend at `localhost:3000`, API at `localhost:8000`. Go to **Calls → New call**,
upload a recording, and watch the pipeline transcribe and analyze it. Interactive
API docs (Swagger UI) at `localhost:8000/docs`.

`pnpm dev` runs `pnpm doctor` first — a preflight check for the common setup
gotchas (wrong Node/Python version, missing venv, missing/placeholder `.env`,
ports in use). Run it standalone any time with `pnpm doctor`.

## B2 key layout

B2 is the sole data store — there is no database.

```
calls/{date}/{queue}/{callId}/
    recording.{wav|mp3}     # source audio (create)
    meta.json               # the call record (edit target); holds status
    transcript.jsonl        # {start,end,speaker,text,emotion} per line (run writes)
    analytics.json          # sentiment, flagged_phrases, silence_ratio, talk_time… (run writes)
```

`status ∈ {uploaded, processing, done, error}` lives in `meta.json`, driving a
clean poll model. `queue`/`date` are immutable (they're encoded in the key);
editing a call changes only mutable `meta.json` fields. Deletes are scoped to a
single call's prefix — never bucket-wide.

## Tech Stack

- TypeScript, Next.js 16, React 19, Tailwind v4, shadcn/ui, Recharts
- TanStack Query — caching, dedup, polling for every fetch
- Python 3.11+, FastAPI, boto3, Pydantic v2
- **SpeechBrain, PyTorch, torchaudio, librosa, soundfile, scikit-learn** (local speech pipeline)
- Backblaze B2 (S3-compatible object storage)
- pnpm workspaces (monorepo)

## Commands

| Command | What it does |
|---------|-------------|
| `pnpm dev` | Start frontend + backend |
| `pnpm dev:web` / `pnpm dev:api` | Frontend / backend only |
| `pnpm build` | Build frontend |
| `pnpm lint` / `pnpm lint:api` | Lint frontend / backend (ruff) |
| `pnpm test:web` / `pnpm test:api` | Run frontend / backend tests |
| `pnpm check:structure` | Verify layering + SDK-containment rules |

Backend tests **monkeypatch the speech engine**, so `pnpm test:api` never
downloads a model or imports torch.

## Documentation Map

| Doc | Purpose |
|-----|---------|
| [AGENTS.md](AGENTS.md) | Agent table of contents — start here |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layout, layering, pipeline data flow |
| [docs/features/](docs/features/) | Feature docs (call ingest, transcription/diarization, analytics, library, dashboard) |
| [docs/app-workflows.md](docs/app-workflows.md) | User journeys |
| [docs/SECURITY.md](docs/SECURITY.md) · [docs/RELIABILITY.md](docs/RELIABILITY.md) | Security / reliability |

## License

MIT License — see [LICENSE](LICENSE) for details.
