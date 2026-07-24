<!-- last_verified: 2026-07-23 -->
# Feature: Transcription & Diarization (SpeechBrain, local)

## Purpose
Run a fully-local SpeechBrain pipeline over a call recording to produce a timestamped, speaker-labeled transcript — with **no external API and no API key** beyond B2.

## Used By
- UI: `/calls/[callId]` — **Analyze / Re-analyze** button + Transcript tab (`apps/web/src/components/calls/transcript-viewer.tsx`)
- API: `POST /calls/{id}/analyze` (BackgroundTask), `GET /calls/{id}/transcript`

## Core Functions
- `services/api/app/repo/speech_engine.py` — the sole `torch`/`torchaudio`/`speechbrain` home: `segment` (VAD), `transcribe` (wav2vec2 ASR), `embed` (ECAPA), `emotion`; `get_device` (CUDA→MPS→CPU autodetect)
- `services/api/app/repo/audio_io.py` — decode + resample to 16 kHz mono
- `services/api/app/service/analysis.py` — orchestration + `_cluster` (scikit-learn `AgglomerativeClustering`) + speaker labeling
- `apps/web/src/lib/queries.ts` — `useAnalyzeCall`, `useCall` (polls while `processing`), `useCallTranscript`

## Inputs
- The call's `recording.*` from B2, plus `meta.expected_speakers` ({2, 3, auto}) and `asr_quality`

## Outputs
- `transcript.jsonl` written to the call prefix — one `{start, end, speaker, text, emotion}` per line
- `meta.json` updated: `status=done` (or `error`), `duration_sec`, `num_speakers`
- Side effect: ~1–2 GB one-time model download (cached, non-gated)

## Flow
- `analyze_call` (semaphore-bounded) sets `status=processing`
- Decode → 16 kHz mono; VAD segments the audio (whole-file fallback if no speech)
- Per segment: ASR text, ECAPA embedding, emotion
- Cluster embeddings into speakers (k from `expected_speakers`, or auto via distance threshold); 2 speakers map to `agent_label`/`customer_label` by first-speaking order
- Write `transcript.jsonl`, then compute analytics, then flip `status=done`

## Edge Cases
- No speech detected → whole-file fallback so ASR still runs
- MPS operator gap → engine demotes to CPU and retries (`SPEECHBRAIN_DEVICE=cpu` to force)
- Corrupt/unreadable audio → `status=error` with a message; the background task never crashes
- `expected_speakers=auto` → cluster count estimated, clamped to the number of segments

## UX States
- Empty: "No transcript yet — run analysis"
- Loading: detail page polls while `processing`; transcript skeletons
- Error: destructive alert with `meta.error`; Re-analyze available

## Verification
- Test files: `services/api/tests/test_calls.py` (`test_analysis_status_flow_and_artifacts`) — speech engine monkeypatched, no model download
- Quick verify command: `pnpm test:api`
- Pass criteria: status transitions to `done`, transcript has one line per segment, speakers labeled
- Real end-to-end (actual model download + inference) is exercised by the verify pipeline step, not CI

## Related Docs
- [Call Analytics](analytics.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
