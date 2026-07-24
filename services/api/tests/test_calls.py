"""Call CRUD, scoped-delete, and analysis status-flow tests.

The SpeechBrain primitives and audio I/O are monkeypatched to canned values,
so pytest NEVER downloads a model or imports torch. B2 is replaced by an
in-memory dict, so no network or credentials are needed. The clustering +
analytics math runs for real against the canned embeddings.
"""

from datetime import UTC, datetime

import numpy as np
import pytest

from app.repo import audio_io, speech_engine
from app.service import analysis as analysis_service
from app.service import calls as calls_service
from app.types.calls import CallMeta, CallStatus, Queue


@pytest.fixture
def store(monkeypatch):
    """In-memory B2, wired into both service modules that touch storage."""
    data: dict[str, bytes] = {}

    def put_bytes(key, body, content_type):
        data[key] = bytes(body)

    def get_object_bytes(key):
        if key not in data:
            raise RuntimeError(f"missing {key}")
        return data[key]

    def list_prefix(prefix):
        return [{"key": k, "size": len(v), "last_modified": None} for k, v in data.items() if k.startswith(prefix)]

    def delete_prefix(prefix):
        assert prefix and prefix.strip(), "scoped delete must have a prefix"
        keys = [k for k in data if k.startswith(prefix)]
        for k in keys:
            del data[k]
        return len(keys)

    def get_play_url(key, expires_in=3600):
        return f"https://example.test/{key}"

    for mod in (calls_service,):
        monkeypatch.setattr(mod, "put_bytes", put_bytes)
        monkeypatch.setattr(mod, "get_object_bytes", get_object_bytes)
        monkeypatch.setattr(mod, "list_prefix", list_prefix)
        monkeypatch.setattr(mod, "delete_prefix", delete_prefix)
        monkeypatch.setattr(mod, "get_play_url", get_play_url)
    monkeypatch.setattr(analysis_service, "put_bytes", put_bytes)
    monkeypatch.setattr(analysis_service, "get_object_bytes", get_object_bytes)
    return data


@pytest.fixture
def fake_engine(monkeypatch):
    """Canned two-speaker call: greeting (neutral) then a refund ask (angry)."""
    texts = ["hello this is support how can i help", "i want a refund please"]
    emos = ["neu", "ang"]
    embeds = [np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0])]
    counter = {"n": 0}

    def _next():
        i = counter["n"] % 2
        counter["n"] += 1
        return i

    monkeypatch.setattr(audio_io, "load_waveform", lambda b: (np.zeros(16_000 * 4, dtype=np.float32), 16_000))
    monkeypatch.setattr(audio_io, "write_wav", lambda *a, **k: None)
    monkeypatch.setattr(speech_engine, "segment", lambda path: [(0.0, 2.0), (2.0, 4.0)])
    monkeypatch.setattr(speech_engine, "transcribe", lambda seg: texts[_next()])
    monkeypatch.setattr(speech_engine, "embed", lambda seg: embeds[counter["n"] % 2])
    monkeypatch.setattr(speech_engine, "emotion", lambda seg: emos[counter["n"] % 2])


def _create_via_api(client):
    return client.post(
        "/calls",
        files={"file": ("call.wav", b"RIFFfake", "audio/wav")},
        data={
            "title": "Refund request",
            "queue": "support",
            "date": "2026-07-23",
            "expected_speakers": "2",
            "compliance_keywords": "refund,complaint",
        },
    )


@pytest.mark.asyncio
async def test_call_crud_lifecycle(client, store):
    created = await _create_via_api(client)
    assert created.status_code == 200, created.text
    call = created.json()
    call_id = call["call_id"]
    assert call["status"] == "uploaded"
    assert call["queue"] == "support"

    listed = await client.get("/calls")
    assert listed.status_code == 200
    assert any(c["call_id"] == call_id for c in listed.json())

    got = await client.get(f"/calls/{call_id}")
    assert got.status_code == 200
    assert got.json()["title"] == "Refund request"

    patched = await client.patch(f"/calls/{call_id}", json={"title": "Refund — resolved"})
    assert patched.status_code == 200
    assert patched.json()["title"] == "Refund — resolved"

    deleted = await client.delete(f"/calls/{call_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True

    missing = await client.get(f"/calls/{call_id}")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_delete_is_scoped_to_the_call_prefix(client, store):
    created = await _create_via_api(client)
    call_id = created.json()["call_id"]
    # An unrelated object living outside this call's prefix must survive.
    store["calls/2026-07-23/support/OTHER/meta.json"] = b"{}"
    store["uploads/unrelated.txt"] = b"keep me"

    await client.delete(f"/calls/{call_id}")

    assert "uploads/unrelated.txt" in store
    assert "calls/2026-07-23/support/OTHER/meta.json" in store
    assert not any(f"/{call_id}/" in k for k in store)


@pytest.mark.asyncio
async def test_analysis_status_flow_and_artifacts(client, store, fake_engine):
    created = await _create_via_api(client)
    call_id = created.json()["call_id"]

    # Run the real pipeline (canned engine) synchronously.
    analysis_service.analyze_call(call_id)

    got = await client.get(f"/calls/{call_id}")
    body = got.json()
    assert body["status"] == "done"
    assert body["num_speakers"] == 2
    assert body["duration_sec"] == pytest.approx(4.0, abs=0.1)
    # Stage is cleared on a terminal status; the continuous sentiment score is
    # denormalized into meta.json so the dashboard can average the real score.
    assert body["stage"] is None
    assert body["sentiment_score"] is not None
    assert -1.0 <= body["sentiment_score"] <= 1.0

    transcript = (await client.get(f"/calls/{call_id}/transcript")).json()
    assert len(transcript) == 2
    speakers = {seg["speaker"] for seg in transcript}
    assert speakers == {"Agent", "Customer"}

    analytics = (await client.get(f"/calls/{call_id}/analytics")).json()
    assert analytics["num_speakers"] == 2
    assert analytics["sentiment_label"] in {"negative", "neutral", "positive"}
    flagged = {f["phrase"]: f["count"] for f in analytics["flagged_phrases"]}
    assert flagged.get("refund", 0) >= 1


@pytest.mark.asyncio
async def test_analyze_missing_call_is_404(client, store):
    resp = await client.post("/calls/deadbeef/analyze")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_call_stats_reports_fanout(client, store, fake_engine):
    created = await _create_via_api(client)
    call_id = created.json()["call_id"]
    analysis_service.analyze_call(call_id)

    stats = (await client.get("/calls/stats")).json()
    assert stats["total_calls"] == 1
    assert stats["calls_done"] == 1
    # recording + meta + transcript + analytics = 4 objects for 1 recording.
    assert stats["artifacts_written"] == 4
    assert stats["fan_out_ratio"] == pytest.approx(4.0)


@pytest.mark.asyncio
async def test_avg_sentiment_is_continuous_mean_not_label_rounded(client, store):
    """C2: the dashboard 'Avg Sentiment' averages the continuous per-call
    sentiment_score, not the discrete label->number map. A legacy call with only
    a label (no numeric score) falls back to the label map."""
    now = datetime.now(UTC)

    def _seed(call_id: str, label: str, score: float | None) -> None:
        meta = CallMeta(
            call_id=call_id,
            title=call_id,
            queue=Queue.support,
            date="2026-07-23",
            status=CallStatus.done,
            recording_key=f"calls/2026-07-23/support/{call_id}/recording.wav",
            recording_filename="recording.wav",
            sentiment_label=label,
            sentiment_score=score,
            created_at=now,
            updated_at=now,
        )
        calls_service.write_meta(meta)

    # Two negative-labeled calls carry distinct continuous scores; one legacy
    # call has only a label and no numeric score (-> falls back to 0.0).
    _seed("aaaaaaaaaaaa", "negative", -0.46)
    _seed("bbbbbbbbbbbb", "negative", -0.50)
    _seed("cccccccccccc", "neutral", None)

    stats = (await client.get("/calls/stats")).json()
    # Continuous mean = (-0.46 + -0.50 + 0.0) / 3 = -0.32
    assert stats["avg_sentiment"] == pytest.approx(-0.32, abs=1e-3)
    # NOT the discrete label-rounded mean (-1 + -1 + 0) / 3 = -0.667
    assert abs(stats["avg_sentiment"] - (-0.667)) > 0.1


@pytest.mark.asyncio
async def test_pipeline_records_advancing_stage(client, store, fake_engine, monkeypatch):
    """B1/B2: the backend records each pipeline stage into meta.json in order
    while processing, then clears it on the terminal status. This real signal is
    what drives the detail page's advancing progress indicator."""
    created = await _create_via_api(client)
    call_id = created.json()["call_id"]

    stages_seen: list[str | None] = []
    orig_write = analysis_service.write_meta

    def _capture(meta):
        stages_seen.append(meta.stage.value if meta.stage else None)
        return orig_write(meta)

    monkeypatch.setattr(analysis_service, "write_meta", _capture)
    analysis_service.analyze_call(call_id)

    for name in ("segmentation", "transcription", "diarization", "analytics"):
        assert name in stages_seen, f"stage {name!r} never recorded: {stages_seen}"
    assert (
        stages_seen.index("segmentation")
        < stages_seen.index("transcription")
        < stages_seen.index("diarization")
        < stages_seen.index("analytics")
    )
    # Stage is cleared (None) once the run reaches a terminal status.
    assert stages_seen[-1] is None
