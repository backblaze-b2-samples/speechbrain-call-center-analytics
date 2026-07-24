<!-- last_verified: 2026-07-23 -->
# Feature: Call Analytics (SpeechBrain, local)

## Purpose
Roll the per-segment pipeline output into a per-call analytics summary — sentiment, compliance-keyword flags, silence ratio, and agent/customer talk-time split.

## Used By
- UI: `/calls/[callId]` — Analytics tab (`apps/web/src/components/calls/analytics-panel.tsx`)
- API: `GET /calls/{id}/analytics` (written by `POST /calls/{id}/analyze`)

## Core Functions
- `services/api/app/service/analysis.py` — `_analytics` (sentiment valence rollup, flagged phrases, silence ratio, talk-time)
- `services/api/app/service/calls.py` — `compliance_keywords_for` (per-call override → config default), `get_analytics`
- `services/api/app/types/calls.py` — `CallAnalytics`, `FlaggedPhrase`
- `apps/web/src/lib/queries.ts` — `useCallAnalytics`

## Inputs
- The in-memory transcript segments (with per-segment emotion) and total duration
- `meta.compliance_keywords` (falls back to `DEFAULT_COMPLIANCE_KEYWORDS` in settings)

## Outputs
- `analytics.json` written to the call prefix: `num_speakers`, `duration_sec`, `sentiment_score` (-1..1), `sentiment_label`, `silence_ratio`, `talk_time` (per speaker seconds), `flagged_phrases`, `emotions`
- `meta.json` updated with the denormalized `sentiment_label` (for the library table) and `sentiment_score` — the continuous -1..1 score, denormalized so the dashboard "Avg Sentiment" averages the real per-call scores rather than the discrete labels

## Flow
- Map each segment's emotion to a valence (hap/neu/sad/ang…), duration-weight, average → `sentiment_score` → label (>0.15 positive, <-0.15 negative, else neutral)
- Count compliance-keyword occurrences across the joined transcript text
- `silence_ratio = 1 - (speech_time / duration)`; `talk_time` sums segment durations per speaker

## Edge Cases
- No emotion signal → score 0.0 / neutral
- Duration 0 → silence ratio 0
- No keyword hits → empty flagged list ("No compliance keywords detected")
- Analytics requested before a run → 404 ("run analysis first"); UI shows the empty state

## UX States
- Empty: "No analytics yet — run analysis"
- Loading: metric skeletons
- Loaded: sentiment badge + score, speakers, silence %, duration, talk-time bar, flagged-phrase chips

## Verification
- Test files: `services/api/tests/test_calls.py` (`test_analysis_status_flow_and_artifacts`, `test_call_stats_reports_fanout`)
- Quick verify command: `pnpm test:api`
- Pass criteria: `analytics.json` present with sentiment + flagged phrases; keyword match counted

## Related Docs
- [Transcription & Diarization](transcription-diarization.md)
- [Dashboard](dashboard.md)
