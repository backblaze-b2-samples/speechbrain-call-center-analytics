<!-- last_verified: 2026-07-23 -->
# App Workflows

User journeys inside the application. The primary journeys are the Call ones;
the generic Upload/Files/Dashboard journeys below are the retained starter
surfaces.

## Ingest a Call

- User navigates to `/calls/new`
- Picks a WAV/MP3 recording and fills metadata: title, queue (selector),
  date (defaults to today), expected speakers (radio), ASR quality (selector),
  agent/customer labels, compliance keywords, notes
- Submitting `POST /calls` writes the recording + `meta.json` under
  `calls/{date}/{queue}/{callId}/`; "Run analysis immediately" (default on)
  kicks off the pipeline
- On success the user lands on the call detail page
- See: [Call Ingest](features/call-ingest.md)

## Analyze & Review a Call

- On `/calls/[callId]` the user clicks **Analyze** (or **Re-analyze**)
- Status shows **Processing**; the page polls until **Done** (or **Error**)
- Transcript tab: timestamped, speaker-colored segments with per-segment emotion
- Analytics tab: sentiment score/label, talk-time split, silence ratio,
  flagged compliance phrases
- The recording plays inline via a presigned URL
- **Edit** opens a pre-filled dialog (queue/date read-only); **Delete** removes
  the call's entire B2 prefix after confirmation
- See: [Transcription & Diarization](features/transcription-diarization.md), [Call Analytics](features/analytics.md)

## Browse the Call Library

- User navigates to `/calls`
- Table lists calls (newest first) with queue, date, #speakers, sentiment, status
- Filter by queue and/or date; rows link to the detail page
- While any call is processing the list auto-refreshes
- See: [Call Library](features/call-library.md)

## Upload Files

- User navigates to `/upload`
- Drops or selects files in the dropzone
- Client validates file size (max 100MB) and type
- Progress bar shows per-file upload status
- On success: toast notification, green checkmark
- On failure: red status icon with error message
- User can clear completed uploads
- See: [File Upload](features/file-upload.md)

## Browse and Manage Files

- User navigates to `/files`
- Page loads file list from API (sorted most recent first)
- Files displayed in tree view with folders and type-specific icons
- Top-level folders auto-expand on load
- Hover a file row to see action buttons (preview / download / delete)
- **Preview**: opens dialog with image/PDF preview + metadata panel
- **Download**: fetches presigned URL, browser downloads file
- **Delete**: removes file from B2, row removed from tree, toast confirms
- Empty bucket shows "No files found" with upload prompt
- See: [File Browser](features/file-browser.md)

## View Dashboard

- User navigates to `/` (home)
- Three parallel API calls load: stats, recent files, upload activity
- Stats cards show: total files, storage used, uploads today, total downloads
- Upload chart shows last 7 days of upload activity as bar chart
- Recent uploads table shows last 10 files with filename, size, type, date
- Empty state: "No files uploaded yet" messages
- See: [Dashboard](features/dashboard.md)
