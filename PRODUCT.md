# Product

## Register

product

## Users

Contact-center / CX operations, QA and compliance reviewers, and
insurance-fintech teams that process large archives of call recordings. Their
context: telephony audio piles up faster than anyone can listen to it, and they
need it turned into transcripts, speaker attribution, sentiment, and
compliance-keyword flags — without shipping sensitive customer audio to a
third-party API. They want the recordings and every derived artifact to live in
their own durable object storage, queryable by date and queue, feeding QA
dashboards, compliance review, and model-retraining pipelines.

## Product Purpose

A full-stack sample (Next.js 16 + React 19 + Tailwind v4 + shadcn/ui frontend,
FastAPI backend) that runs a **fully-local SpeechBrain pipeline** —
voice-activity segmentation, ASR transcription, speaker diarization, and
per-segment emotion/sentiment — over call recordings and stores the source
audio plus a timestamped speaker-labeled transcript and per-call analytics on
**Backblaze B2**, organized by `date/queue`. The story is *B2 as the durable
storage layer for a high-volume, write-heavy AI audio workflow*: one recording
in becomes three objects out. Success = a reviewer can ingest a call, get a
speaker-labeled transcript and analytics with **no external API key** (B2
credentials only), and read recordings + artifacts straight from B2 over the
S3-compatible API.

## Brand Personality

Confident, precise, quietly professional. Voice is direct and free of hype. The
interface should feel like a modern operations tool for QA and compliance
reviewers — considered, calm, trustworthy — not a marketing showpiece. It
handles sensitive customer audio, so the design earns trust through restraint
and clarity rather than a loud identity of its own.

## Anti-references

- **Generic AI/SaaS slop.** No gradient text, hero-metric templates, identical
  icon-card grids, tracked uppercase eyebrows, or decorative glassmorphism. These are
  the exact 2026 AI tells this kit exists to help builders avoid.
- **Over-branded / loud.** No heavy brand-color drenching, decorative motion, or flashy
  effects. It is scaffolding to be rebranded, not a hero page.
- **Toy / prototype feel.** No missing states, inconsistent components, or placeholder
  polish. Must read as production-grade.
- **Enterprise-drab.** No Bootstrap-era gray boxes or dense-but-lifeless admin-panel
  look. Considered, like modern dev tools (Linear, GitHub Primer, Stripe).

## Design Principles

- **Practice what you preach.** The kit itself must model the production quality it
  asks agents to produce. Slop here propagates into every project built on it.
- **Neutral foundation, easy to rebrand.** Identity lives in tokens (`globals.css`) and
  one config file. Screens are built from the shared UI kit so a rebrand is a token
  swap, not a rewrite.
- **Earned familiarity over novelty.** Use standard, trusted affordances (top bar +
  side nav, command palette, data tables). The tool disappears into the task.
- **Every state is designed.** Default, hover, focus, active, disabled, loading (skeleton),
  empty (teaches the interface), and error (says what's wrong + offers retry) — never
  half-shipped.
- **Consistency is the feature.** One button vocabulary, one form-control set, one icon
  style across every screen. Divergence is a bug.

## Accessibility & Inclusion

Target **WCAG 2.1 AA**. Body text ≥ 4.5:1, large/bold text ≥ 3:1, visible focus
indicators on every interactive element, full keyboard navigation, correct semantic
landmarks and heading order, labelled form controls, and a `prefers-reduced-motion`
alternative for every animation. Full light and dark theme parity.
