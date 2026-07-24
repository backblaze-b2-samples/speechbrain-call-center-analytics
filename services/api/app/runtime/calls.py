import logging

# Blocking B2 handlers are sync `def` so Starlette runs them in its threadpool
# (see runtime/files.py rationale). `create` is async only to stream the upload.
from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.service.analysis import analyze_call
from app.service.calls import (
    CallNotFoundError,
    CallValidationError,
    create_call,
    delete_call,
    get_analytics,
    get_audio_url,
    get_call,
    get_call_stats,
    get_transcript,
    list_calls,
    load_call,
    update_call,
)
from app.types.calls import (
    Call,
    CallAnalytics,
    CallStats,
    CallStatus,
    CreateCallRequest,
    Queue,
    SpeakerCount,
    TranscriptSegment,
    UpdateCallRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_AUDIO_CT = {"audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3", "application/octet-stream"}


def _not_found(e: CallNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=e.detail)


@router.post("/calls", response_model=Call)
async def create_call_endpoint(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    queue: Queue = Form(Queue.support),
    date: str = Form(...),
    language: str = Form("en"),
    expected_speakers: SpeakerCount = Form(SpeakerCount.two),
    agent_label: str = Form("Agent"),
    customer_label: str = Form("Customer"),
    compliance_keywords: str = Form(""),
    notes: str = Form(""),
    analyze: bool = Form(False),
):
    content_type = file.content_type or "application/octet-stream"
    if content_type not in _AUDIO_CT:
        raise HTTPException(status_code=415, detail=f"Unsupported audio type '{content_type}'")

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.max_file_size:
            raise HTTPException(status_code=413, detail="Recording too large")
        chunks.append(chunk)
    audio = b"".join(chunks)

    keywords = [k.strip() for k in compliance_keywords.split(",") if k.strip()]
    req = CreateCallRequest(
        title=title, queue=queue, date=date, language=language,
        expected_speakers=expected_speakers,
        agent_label=agent_label, customer_label=customer_label,
        compliance_keywords=keywords or None, notes=notes,
    )
    try:
        call = await run_in_threadpool(
            create_call, req, audio, file.filename or "recording.wav", content_type
        )
    except CallValidationError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None

    # Optionally kick off analysis immediately after ingest.
    if analyze:
        background.add_task(analyze_call, call.call_id)
    return call


@router.get("/calls/stats", response_model=CallStats)
def call_stats_endpoint():
    return get_call_stats()


@router.get("/calls", response_model=list[Call])
def list_calls_endpoint(queue: str | None = None, date: str | None = None):
    return list_calls(queue=queue, date=date)


@router.get("/calls/{call_id}", response_model=Call)
def get_call_endpoint(call_id: str):
    try:
        return get_call(call_id)
    except CallNotFoundError as e:
        raise _not_found(e) from None


@router.get("/calls/{call_id}/transcript", response_model=list[TranscriptSegment])
def get_transcript_endpoint(call_id: str):
    try:
        return get_transcript(call_id)
    except CallNotFoundError as e:
        raise _not_found(e) from None


@router.get("/calls/{call_id}/analytics", response_model=CallAnalytics)
def get_analytics_endpoint(call_id: str):
    try:
        return get_analytics(call_id)
    except CallNotFoundError as e:
        raise _not_found(e) from None


@router.get("/calls/{call_id}/audio")
def get_audio_endpoint(call_id: str):
    try:
        return {"url": get_audio_url(call_id)}
    except CallNotFoundError as e:
        raise _not_found(e) from None
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Failed to presign audio") from None


@router.patch("/calls/{call_id}", response_model=Call)
def update_call_endpoint(call_id: str, req: UpdateCallRequest):
    try:
        return update_call(call_id, req)
    except CallNotFoundError as e:
        raise _not_found(e) from None


@router.delete("/calls/{call_id}")
def delete_call_endpoint(call_id: str):
    try:
        deleted = delete_call(call_id)
    except CallNotFoundError as e:
        raise _not_found(e) from None
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to delete call") from None
    logger.info("Call deleted: id=%s objects=%d", call_id, deleted)
    return {"deleted": True, "call_id": call_id, "objects": deleted}


@router.post("/calls/{call_id}/analyze")
def analyze_call_endpoint(call_id: str, background: BackgroundTasks):
    try:
        load_call(call_id)  # 404 early if the call is gone
    except CallNotFoundError as e:
        raise _not_found(e) from None
    background.add_task(analyze_call, call_id)
    return {"call_id": call_id, "status": CallStatus.processing.value}
