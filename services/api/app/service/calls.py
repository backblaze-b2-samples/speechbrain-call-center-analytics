"""CRUD orchestration for the Call entity.

B2 is the sole data store. A call is a prefix
``calls/{date}/{queue}/{callId}/`` holding the source recording, a `meta.json`
record, and (after a run) `transcript.jsonl` + `analytics.json`. `queue`/`date`
are immutable because they are encoded in the object key; edits only patch
mutable `meta.json` fields.
"""

import json
import logging
import re
import uuid
from datetime import UTC, datetime

from app.config import settings
from app.repo import (
    delete_prefix,
    get_object_bytes,
    get_play_url,
    list_prefix,
    put_bytes,
)
from app.types.calls import (
    Call,
    CallAnalytics,
    CallMeta,
    CallStats,
    CallStatus,
    CreateCallRequest,
    TranscriptSegment,
    UpdateCallRequest,
)

logger = logging.getLogger(__name__)

CALLS_ROOT = "calls/"
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_EXT_BY_CT = {"audio/mpeg": ".mp3", "audio/mp3": ".mp3", "audio/wav": ".wav", "audio/x-wav": ".wav"}


class CallNotFoundError(Exception):
    def __init__(self, detail: str = "Call not found"):
        self.detail = detail
        super().__init__(detail)


class CallValidationError(Exception):
    def __init__(self, detail: str = "Invalid call"):
        self.detail = detail
        super().__init__(detail)


# --- key helpers ---


def prefix_for(meta: CallMeta) -> str:
    return f"{CALLS_ROOT}{meta.date}/{meta.queue.value}/{meta.call_id}/"


def meta_key_for(meta: CallMeta) -> str:
    return prefix_for(meta) + "meta.json"


def _recording_ext(filename: str, content_type: str) -> str:
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
        if ext in (".wav", ".mp3", ".m4a", ".flac", ".ogg"):
            return ext
    return _EXT_BY_CT.get(content_type, ".wav")


# --- meta persistence ---


def read_meta_at(meta_key: str) -> CallMeta:
    try:
        raw = get_object_bytes(meta_key)
    except RuntimeError as e:
        raise CallNotFoundError() from e
    return CallMeta.model_validate_json(raw)


def write_meta(meta: CallMeta) -> None:
    put_bytes(
        meta_key_for(meta),
        meta.model_dump_json(indent=2).encode("utf-8"),
        "application/json",
    )


def _find_meta_key(call_id: str) -> str:
    suffix = f"/{call_id}/meta.json"
    for obj in list_prefix(CALLS_ROOT):
        if obj["key"].endswith(suffix):
            return obj["key"]
    raise CallNotFoundError()


def load_call(call_id: str) -> CallMeta:
    return read_meta_at(_find_meta_key(call_id))


# --- CRUD ---


def create_call(
    req: CreateCallRequest, audio: bytes, filename: str, content_type: str
) -> Call:
    if not _DATE_RE.match(req.date):
        raise CallValidationError("date must be YYYY-MM-DD")
    if not audio:
        raise CallValidationError("recording is empty")

    call_id = uuid.uuid4().hex[:12]
    now = datetime.now(UTC)
    ext = _recording_ext(filename, content_type)
    recording_filename = f"recording{ext}"

    meta = CallMeta(
        call_id=call_id,
        title=req.title,
        queue=req.queue,
        date=req.date,
        language=req.language,
        expected_speakers=req.expected_speakers,
        asr_quality=req.asr_quality,
        agent_label=req.agent_label,
        customer_label=req.customer_label,
        compliance_keywords=req.compliance_keywords or [],
        notes=req.notes,
        status=CallStatus.uploaded,
        recording_key="",  # set below once the prefix is known
        recording_filename=recording_filename,
        created_at=now,
        updated_at=now,
    )
    meta.recording_key = prefix_for(meta) + recording_filename

    put_bytes(meta.recording_key, audio, content_type or "audio/wav")
    write_meta(meta)
    logger.info("Call created: id=%s queue=%s date=%s", call_id, req.queue.value, req.date)
    return Call.model_validate(meta.model_dump())


def list_calls(queue: str | None = None, date: str | None = None) -> list[Call]:
    calls: list[Call] = []
    for obj in list_prefix(CALLS_ROOT):
        if not obj["key"].endswith("/meta.json"):
            continue
        try:
            meta = read_meta_at(obj["key"])
        except CallNotFoundError:
            continue
        if queue and meta.queue.value != queue:
            continue
        if date and meta.date != date:
            continue
        calls.append(Call.model_validate(meta.model_dump()))
    calls.sort(key=lambda c: c.created_at, reverse=True)
    return calls


def get_call(call_id: str) -> Call:
    return Call.model_validate(load_call(call_id).model_dump())


def update_call(call_id: str, req: UpdateCallRequest) -> Call:
    meta = load_call(call_id)
    patch = req.model_dump(exclude_unset=True)
    for field, value in patch.items():
        setattr(meta, field, value)
    meta.updated_at = datetime.now(UTC)
    write_meta(meta)
    return Call.model_validate(meta.model_dump())


def delete_call(call_id: str) -> int:
    meta = load_call(call_id)
    # Scoped delete — ONLY this call's prefix, never bucket-wide.
    return delete_prefix(prefix_for(meta))


# --- artifacts ---


def get_transcript(call_id: str) -> list[TranscriptSegment]:
    meta = load_call(call_id)
    key = prefix_for(meta) + "transcript.jsonl"
    try:
        raw = get_object_bytes(key)
    except RuntimeError:
        return []
    out: list[TranscriptSegment] = []
    for line in raw.decode("utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(TranscriptSegment.model_validate_json(line))
    return out


def get_analytics(call_id: str) -> CallAnalytics:
    meta = load_call(call_id)
    key = prefix_for(meta) + "analytics.json"
    try:
        raw = get_object_bytes(key)
    except RuntimeError as e:
        raise CallNotFoundError("Analytics not available — run analysis first") from e
    return CallAnalytics.model_validate_json(raw)


def get_audio_url(call_id: str) -> str:
    meta = load_call(call_id)
    return get_play_url(meta.recording_key)


# --- dashboard aggregation ---


def get_call_stats() -> CallStats:
    metas: list[CallMeta] = []
    for obj in list_prefix(CALLS_ROOT):
        if obj["key"].endswith("/meta.json"):
            try:
                metas.append(read_meta_at(obj["key"]))
            except CallNotFoundError:
                continue
    all_objs = list_prefix(CALLS_ROOT)
    recordings = sum(1 for m in metas)
    artifacts = len(all_objs)  # recordings + meta + transcript + analytics
    audio_hours = sum((m.duration_sec or 0) for m in metas) / 3600.0
    sentiments = [_sentiment_num(m.sentiment_label) for m in metas if m.sentiment_label]
    queue_breakdown: dict[str, int] = {}
    for m in metas:
        queue_breakdown[m.queue.value] = queue_breakdown.get(m.queue.value, 0) + 1
    return CallStats(
        total_calls=len(metas),
        calls_done=sum(1 for m in metas if m.status == CallStatus.done),
        calls_processing=sum(1 for m in metas if m.status == CallStatus.processing),
        audio_hours=round(audio_hours, 2),
        artifacts_written=artifacts,
        fan_out_ratio=round(artifacts / recordings, 2) if recordings else 0.0,
        avg_sentiment=round(sum(sentiments) / len(sentiments), 3) if sentiments else None,
        queue_breakdown=queue_breakdown,
    )


def _sentiment_num(label: str) -> float:
    return {"positive": 1.0, "neutral": 0.0, "negative": -1.0}.get(label, 0.0)


def compliance_keywords_for(meta: CallMeta) -> list[str]:
    """Per-call keywords, falling back to the configured defaults."""
    if meta.compliance_keywords:
        return [k.lower() for k in meta.compliance_keywords]
    return settings.compliance_keywords


def json_line(seg: TranscriptSegment) -> str:
    return json.dumps(seg.model_dump(), ensure_ascii=False)
