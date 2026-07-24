<!-- last_verified: 2026-07-23 -->
# Feature: Call Ingest

## Purpose
Upload a telephony recording with call metadata into a `date/queue` prefix on B2, creating the primary **Call** entity.

## Used By
- UI: `/calls/new` — the New Call form (`apps/web/src/components/calls/call-form.tsx`, `mode="create"`)
- API: `POST /calls` (multipart: audio file + metadata form fields)

## Core Functions
- `services/api/app/runtime/calls.py` — `create_call_endpoint` (streams + size-guards the upload)
- `services/api/app/service/calls.py` — `create_call` (writes `recording.*` + `meta.json`)
- `services/api/app/repo/b2_storage.py` — `put_bytes`
- `apps/web/src/lib/queries.ts` — `useCreateCall`

## Inputs
- `file`: UploadFile (WAV/MP3 telephony audio)
- `title`, `queue`, `date` (YYYY-MM-DD), `expected_speakers`, `agent_label`, `customer_label`, `compliance_keywords` (comma-separated), `notes`: Form fields
- `analyze`: bool — kick off analysis immediately after ingest

## Outputs
- `Call` (status `uploaded`, or `processing` if `analyze=true`)
- Side effects: writes `calls/{date}/{queue}/{callId}/recording.*` and `meta.json` to B2

## Flow
- User picks a recording and fills metadata (queue/speakers are selectors; create-only safe-default hints shown)
- `POST /calls` streams the file (413 over `max_file_size`), validates the audio content type
- `create_call` mints a `callId`, writes the recording then `meta.json`
- On success the UI routes to `/calls/{callId}`; if `analyze` was checked, the run starts

## Edge Cases
- Non-audio content type → 415
- Recording over the size limit → 413
- Malformed `date` (not YYYY-MM-DD) → 400
- Empty recording → 400

## UX States
- Empty: file input with a "WAV or MP3" hint
- Loading: submit disabled while uploading
- Error: toast with the API detail; missing-file inline error

## Verification
- Test files: `services/api/tests/test_calls.py`
- Required cases: create → list/get; unsupported type; missing call
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest green, no ruff violations

## Related Docs
- [Transcription & Diarization](transcription-diarization.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
