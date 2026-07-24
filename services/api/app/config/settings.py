from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Backblaze B2 (Standard #3 env names) ---
    # The S3 endpoint is derived from the region (see `b2_endpoint` below), so a
    # clone only ever sets the region, never a raw endpoint URL. Required (no
    # baked-in region default) — main.py fails fast at startup if it's unset,
    # naming B2_REGION. .env.example shows the expected form.
    b2_region: str = ""
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    # Optional: only used to build public object URLs for a public bucket. The
    # app runs fine without it (presigned URLs are used everywhere else).
    b2_public_url_base: str = ""

    # --- SpeechBrain pipeline (fully local, no external provider) ---
    # Device selection is auto-detected at runtime (CUDA -> Apple MPS -> CPU)
    # in repo/speech_engine.py. Set this to pin a device, e.g. "cpu" if an MPS
    # op errors on Apple silicon (wav2vec2 has incomplete MPS coverage).
    speechbrain_device: str = ""
    # Bound concurrent analyses so several long recordings can't exhaust memory
    # by loading torch tensors for many calls at once. 1 = strictly serial.
    analysis_max_concurrency: int = 1
    # Comma-separated compliance phrases flagged in transcripts by default. A
    # per-call `compliance_keywords` list in meta.json overrides this.
    default_compliance_keywords: str = (
        "cancel,refund,complaint,supervisor,lawsuit,record this call,data breach"
    )

    api_port: int = 8000
    # Interactive API docs (/docs, /redoc, /openapi.json). On by default for
    # local dev and starter-kit exploration; set false to hide the full API
    # surface in production.
    enable_docs: bool = True
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits
    max_file_size: int = 100 * 1024 * 1024  # 100MB

    # Optional confinement for key-addressed reads/deletes. Empty by default so
    # the by-key routes accept any key shape (they deliberately support nested
    # folders and reserved-word segments). Point a fork at a bucket shared with
    # other data? Set to e.g. "uploads/" to restrict all key ops to app uploads.
    allowed_key_prefix: str = ""

    # Rate limiting (per client IP, per 60s window). In-process per replica —
    # documented in docs/RELIABILITY.md; horizontal scaling needs a shared
    # store (e.g. Redis). Writes/downloads get the tighter cap.
    rate_limit_per_minute: int = 120
    # Covers uploads, deletes, downloads and previews — kept generous enough
    # that a normal browsing/upload session doesn't trip it.
    rate_limit_write_per_minute: int = 60

    # Small durable counters (downloads, etc). Point at a persistent
    # volume in production if you care about surviving restarts.
    download_count_file: str = "data/download_count.json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def b2_endpoint(self) -> str:
        """S3-compatible endpoint derived from the region.

        One region setting yields the canonical Backblaze S3 host — no raw
        endpoint URL (and therefore no hardcoded region) anywhere in source.
        """
        return f"https://s3.{self.b2_region}.backblazeb2.com"

    @property
    def cors_origins(self) -> list[str]:
        # Drop empties so a trailing comma or API_CORS_ORIGINS="" doesn't yield
        # a stray "" origin.
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    @property
    def compliance_keywords(self) -> list[str]:
        return [
            k.strip().lower()
            for k in self.default_compliance_keywords.split(",")
            if k.strip()
        ]


settings = Settings()
