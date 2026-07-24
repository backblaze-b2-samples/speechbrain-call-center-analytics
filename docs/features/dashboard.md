<!-- last_verified: 2026-07-23 -->
# Feature: Dashboard

## Purpose
An at-a-glance QA overview of the call-analytics workflow — throughput, audio volume, the storage fan-out, sentiment, and queue mix.

## Used By
- UI: `/` (dashboard home)
- API: `GET /calls/stats`, `GET /calls`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — 4 stat cards
- `apps/web/src/components/dashboard/upload-chart.tsx` — calls-by-queue bar chart
- `apps/web/src/components/dashboard/recent-uploads-table.tsx` — recent calls
- `apps/web/src/lib/queries.ts` — `useCallStats()`, `useCalls()`
- `services/api/app/service/calls.py` — `get_call_stats()` aggregation over `calls/` meta
- `services/api/app/repo/b2_storage.py` — `list_prefix()`

## Canonical Files
- Stats aggregation: `services/api/app/service/calls.py`

## Inputs
- None (dashboard loads automatically)

## Outputs
- `GET /calls/stats` → `CallStats` (`total_calls`, `calls_done`, `calls_processing`, `audio_hours`, `artifacts_written`, `fan_out_ratio`, `avg_sentiment`, `queue_breakdown`)
- `GET /calls` → recent `Call[]` for the table

## Flow
- Page loads → two queries (stats, recent calls)
- Cards: Calls Processed, Audio Ingested (hours), Artifacts on B2 (with the ×fan-out ratio — the "3× per recording" story), Avg Sentiment (the mean of the continuous per-call `sentiment_score`, matching the -1..+1 scale each call's Analytics shows; falls back to the discrete label only for calls with no numeric score)
- Chart: calls grouped by queue
- Table: most-recent calls with queue, sentiment, status (click-through to detail)

## Edge Cases
- API unavailable → inline error states with retry
- No calls → empty chart/table messages, cards show zeros only once stats are known
- Large call count → stats paginate through all `calls/` objects via `ContinuationToken`

## UX States
- Loading: skeletons for cards, chart, table
- Empty: "No calls yet"
- Loaded: populated cards, chart, table

## Verification
- Test files: `services/api/tests/test_calls.py` (`test_call_stats_reports_fanout`)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: stats report the 4-object fan-out for one analyzed call

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
