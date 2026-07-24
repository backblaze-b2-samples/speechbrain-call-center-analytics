"""Call CRUD, scoped-delete, and analysis status-flow tests.

The SpeechBrain primitives and audio I/O are monkeypatched to canned values,
so pytest NEVER downloads a model or imports torch. B2 is replaced by an
in-memory dict, so no network or credentials are needed. The clustering +
analytics math runs for real against the canned embeddings.
"""

import numpy as np
import pytest

from app.repo import audio_io, speech_engine
from app.service import analysis as analysis_service
from app.service import calls as calls_service


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
            "asr_quality": "fast",
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
