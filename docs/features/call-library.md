<!-- last_verified: 2026-07-23 -->
# Feature: Call Library

## Purpose
A sample-scoped asset explorer over the `calls/` prefix — list, filter, and open calls — distinct from the full-bucket Files browser.

## Used By
- UI: `/calls` (`apps/web/src/components/calls/call-library-table.tsx`) and `/calls/[callId]` (detail)
- API: `GET /calls?queue=&date=`, `GET /calls/{id}`, `GET /calls/{id}/audio`, `PATCH /calls/{id}`, `DELETE /calls/{id}`

## Core Functions
- `services/api/app/service/calls.py` — `list_calls`, `get_call`, `update_call`, `delete_call`, `get_audio_url`
- `services/api/app/repo/b2_storage.py` — `list_prefix`, `delete_prefix` (scoped), `get_play_url`
- `apps/web/src/lib/queries.ts` — `useCalls` (polls while any call is `processing`), `useCall`, `useUpdateCall`, `useDeleteCall`, `useCallAudio`
- Components: `call-library-table.tsx`, `call-form.tsx` (edit dialog), `delete-call-dialog.tsx`, `call-badges.tsx`

## Inputs
- Filters: `queue` (selector), `date` (date picker)

## Outputs
- List of `Call` rows: title, queue, date, #speakers, sentiment, status
- Detail: presigned inline audio playback, transcript, analytics, run/edit/delete

## Flow
- Library lists `meta.json` under `calls/`, newest first; queue/date filters narrow it
- A row opens the detail page; status/sentiment badges reflect `meta.json`
- Edit opens a pre-filled form (queue/date read-only — immutable); Delete scopes to the call prefix

## Edge Cases
- No calls → empty state with a "New call" action
- Filter with no matches → empty table
- Delete removes only that call's prefix (recording + all artifacts), never other calls

## UX States
- Empty: "No calls yet"
- Loading: row skeletons
- Error: inline `ErrorState` with retry

## Verification
- Test files: `services/api/tests/test_calls.py` (`test_call_crud_lifecycle`, `test_delete_is_scoped_to_the_call_prefix`)
- Quick verify command: `pnpm test:api`
- Pass criteria: CRUD round-trips; scoped delete leaves unrelated objects intact

## Related Docs
- [Call Ingest](call-ingest.md)
- [File Browser](file-browser.md) (the full-bucket explorer, retained)
