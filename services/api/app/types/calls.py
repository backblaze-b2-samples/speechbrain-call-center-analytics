"""Pydantic models and enums for the Call entity.

A Call is the primary domain entity. Its canonical record lives in
``calls/{date}/{queue}/{callId}/meta.json`` on B2 — there is no database. The
derived pipeline artifacts (transcript, analytics) live alongside it under the
same prefix.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Queue(StrEnum):
    """Contact-center queue a call belongs to. Immutable (encoded in the key)."""

    sales = "sales"
    support = "support"
    billing = "billing"
    retention = "retention"
    collections = "collections"


class SpeakerCount(StrEnum):
    """Expected number of speakers, used to seed diarization clustering."""

    two = "2"  # agent + customer (most calls)
    three = "3"
    auto = "auto"  # estimate the count from the embeddings


class CallStatus(StrEnum):
    """Lifecycle status stored in meta.json — drives the detail-page poll."""

    uploaded = "uploaded"
    processing = "processing"
    done = "done"
    error = "error"


class PipelineStage(StrEnum):
    """Current analysis stage, written to meta.json while status == processing
    (cleared to None on a terminal status). Drives the detail-page progress
    indicator. Order: segmentation -> transcription -> diarization -> analytics."""

    segmentation = "segmentation"
    transcription = "transcription"
    diarization = "diarization"
    analytics = "analytics"


class CreateCallRequest(BaseModel):
    """Metadata submitted with the audio file on the New Call form."""

    title: str = Field(min_length=1, max_length=200)
    queue: Queue = Queue.support
    date: str  # YYYY-MM-DD (immutable — part of the object key)
    language: str = "en"
    expected_speakers: SpeakerCount = SpeakerCount.two
    agent_label: str = "Agent"
    customer_label: str = "Customer"
    compliance_keywords: list[str] | None = None
    notes: str = ""


class UpdateCallRequest(BaseModel):
    """Mutable meta.json fields. `queue`/`date` are immutable (in the key)."""

    title: str | None = Field(default=None, max_length=200)
    language: str | None = None
    expected_speakers: SpeakerCount | None = None
    agent_label: str | None = None
    customer_label: str | None = None
    compliance_keywords: list[str] | None = None
    notes: str | None = None


class CallMeta(BaseModel):
    """The persisted call record (serialized to meta.json)."""

    call_id: str
    title: str
    queue: Queue
    date: str
    language: str = "en"
    expected_speakers: SpeakerCount = SpeakerCount.two
    agent_label: str = "Agent"
    customer_label: str = "Customer"
    compliance_keywords: list[str] = Field(default_factory=list)
    notes: str = ""
    status: CallStatus = CallStatus.uploaded
    # Current pipeline stage while status == processing; None on a terminal
    # status. Drives the detail-page progress indicator.
    stage: PipelineStage | None = None
    recording_key: str
    recording_filename: str
    duration_sec: float | None = None
    # Denormalized analysis summary — written into meta.json when a run
    # completes so the Call Library table lists without reading analytics.json.
    num_speakers: int | None = None
    sentiment_label: str | None = None
    # Continuous per-call sentiment in [-1, 1] (mirrors analytics.sentiment_score),
    # denormalized so the dashboard averages the real score, not the label.
    sentiment_score: float | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class TranscriptSegment(BaseModel):
    """One diarized, transcribed VAD segment (a line in transcript.jsonl)."""

    start: float
    end: float
    speaker: str
    text: str
    emotion: str | None = None


class FlaggedPhrase(BaseModel):
    phrase: str
    count: int


class CallAnalytics(BaseModel):
    """Per-call rollup written to analytics.json by the analysis pipeline."""

    num_speakers: int
    duration_sec: float
    sentiment_score: float  # -1.0 (negative) .. 1.0 (positive)
    sentiment_label: str  # negative | neutral | positive
    silence_ratio: float  # 0..1 — non-speech time / total time
    talk_time: dict[str, float]  # speaker label -> seconds spoken
    flagged_phrases: list[FlaggedPhrase] = Field(default_factory=list)
    emotions: dict[str, int] = Field(default_factory=dict)  # emotion -> segment count


class Call(CallMeta):
    """API response for a call. Currently identical to the persisted record;
    kept as a distinct name so response-only fields can be added later without
    touching the storage model."""


class CallList(BaseModel):
    calls: list[Call]


class CallStats(BaseModel):
    """Dashboard aggregation over the calls/ prefix."""

    total_calls: int
    calls_done: int
    calls_processing: int
    audio_hours: float
    artifacts_written: int  # recordings + derived artifacts (the 3x fan-out)
    fan_out_ratio: float  # artifacts_written / recordings
    avg_sentiment: float | None
    queue_breakdown: dict[str, int]
