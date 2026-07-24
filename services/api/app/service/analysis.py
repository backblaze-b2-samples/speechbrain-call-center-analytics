"""SpeechBrain pipeline orchestration.

Given a call, this runs the fully-local analysis end to end:
VAD segmentation -> per-segment {ASR text, ECAPA embedding, emotion} ->
cluster embeddings into speakers -> compute analytics -> write
``transcript.jsonl`` + ``analytics.json`` to B2 and flip ``meta.status``.

Runs under a concurrency semaphore (default 1) so several long recordings can't
load torch tensors for many calls at once and exhaust memory. The heavy speech
primitives live in ``repo/speech_engine.py`` (the sole torch/speechbrain home);
this module only orchestrates and does the numeric rollups.
"""

import logging
import os
import tempfile
from datetime import UTC, datetime
from threading import Semaphore

from app.config import settings
from app.repo import audio_io, get_object_bytes, put_bytes, speech_engine
from app.service.calls import (
    compliance_keywords_for,
    json_line,
    load_call,
    prefix_for,
    write_meta,
)
from app.types.calls import (
    CallAnalytics,
    CallStatus,
    FlaggedPhrase,
    SpeakerCount,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)

_semaphore = Semaphore(max(1, settings.analysis_max_concurrency))

# IEMOCAP-style emotion labels -> valence in [-1, 1]. Both short codes (the
# model's own labels) and full words are mapped so the rollup is robust.
_VALENCE = {
    "hap": 1.0, "happy": 1.0, "exc": 0.7, "excited": 0.7,
    "neu": 0.0, "neutral": 0.0,
    "sad": -0.6, "sadness": -0.6,
    "ang": -1.0, "angry": -1.0, "anger": -1.0,
    "fru": -0.7, "frustrated": -0.7,
}
_MIN_SEG_SEC = 0.1


def analyze_call(call_id: str) -> None:
    """Entry point (runs inside a FastAPI BackgroundTask). Serialized by a
    semaphore so concurrent runs don't exhaust memory."""
    with _semaphore:
        _run(call_id)


def _run(call_id: str) -> None:
    meta = load_call(call_id)
    meta.status = CallStatus.processing
    meta.error = None
    meta.updated_at = datetime.now(UTC)
    write_meta(meta)

    prefix = prefix_for(meta)
    try:
        waveform, sr = audio_io.load_waveform(get_object_bytes(meta.recording_key))
        duration = round(len(waveform) / sr, 2) if sr else 0.0

        with tempfile.TemporaryDirectory() as td:
            wav_path = os.path.join(td, "audio.wav")
            audio_io.write_wav(wav_path, waveform, sr)
            boundaries = speech_engine.segment(wav_path)
        if not boundaries:
            boundaries = [(0.0, duration)]

        segs = _analyze_segments(waveform, sr, boundaries)
        if not segs:
            segs = [(0.0, duration, speech_engine.transcribe(waveform),
                     speech_engine.embed(waveform), speech_engine.emotion(waveform))]

        labels = _cluster([s[3] for s in segs], meta.expected_speakers)
        names = _speaker_names(labels, segs, meta)
        transcript = [
            TranscriptSegment(
                start=round(s, 2), end=round(e, 2),
                speaker=names[lab], text=text, emotion=emo,
            )
            for (s, e, text, _emb, emo), lab in zip(segs, labels, strict=True)
        ]

        put_bytes(
            prefix + "transcript.jsonl",
            ("\n".join(json_line(t) for t in transcript)).encode("utf-8"),
            "application/x-ndjson",
        )
        analytics = _analytics(transcript, duration, compliance_keywords_for(meta))
        put_bytes(
            prefix + "analytics.json",
            analytics.model_dump_json(indent=2).encode("utf-8"),
            "application/json",
        )

        meta.status = CallStatus.done
        meta.duration_sec = duration
        meta.num_speakers = analytics.num_speakers
        meta.sentiment_label = analytics.sentiment_label
        meta.updated_at = datetime.now(UTC)
        write_meta(meta)
        logger.info("Analysis done: call=%s speakers=%d", call_id, analytics.num_speakers)
    except Exception as e:
        # Record the failure into the entity; a broken recording must not crash
        # the background task or leave the call stuck in "processing".
        meta.status = CallStatus.error
        meta.error = str(e)[:500]
        meta.updated_at = datetime.now(UTC)
        write_meta(meta)
        logger.exception("Analysis failed: call=%s", call_id)


def _analyze_segments(waveform, sr, boundaries):
    out = []
    min_len = int(_MIN_SEG_SEC * sr)
    for start, end in boundaries:
        chunk = waveform[int(start * sr) : int(end * sr)]
        if len(chunk) < min_len:
            continue
        out.append(
            (start, end, speech_engine.transcribe(chunk),
             speech_engine.embed(chunk), speech_engine.emotion(chunk))
        )
    return out


def _cluster(embeddings, expected: SpeakerCount) -> list[int]:
    import numpy as np
    from sklearn.cluster import AgglomerativeClustering

    n = len(embeddings)
    if n <= 1:
        return [0] * n
    x = np.vstack([np.asarray(e).ravel() for e in embeddings])
    if expected == SpeakerCount.auto:
        model = AgglomerativeClustering(
            n_clusters=None, distance_threshold=1.0, metric="cosine", linkage="average"
        )
    else:
        k = min(int(expected.value), n)
        if k <= 1:
            return [0] * n
        model = AgglomerativeClustering(n_clusters=k, metric="cosine", linkage="average")
    return model.fit_predict(x).tolist()


def _speaker_names(labels, segs, meta) -> dict[int, str]:
    first_seen: dict[int, float] = {}
    for (start, *_rest), lab in zip(segs, labels, strict=True):
        first_seen.setdefault(lab, start)
    order = sorted(first_seen, key=lambda lab: first_seen[lab])
    if meta.expected_speakers == SpeakerCount.two and len(order) == 2:
        return {order[0]: meta.agent_label, order[1]: meta.customer_label}
    return {lab: f"Speaker {i + 1}" for i, lab in enumerate(order)}


def _analytics(
    transcript: list[TranscriptSegment], duration: float, keywords: list[str]
) -> CallAnalytics:
    emotions: dict[str, int] = {}
    talk_time: dict[str, float] = {}
    valence_sum = 0.0
    valence_weight = 0.0
    speech_time = 0.0

    for seg in transcript:
        dur = max(0.0, seg.end - seg.start)
        speech_time += dur
        talk_time[seg.speaker] = round(talk_time.get(seg.speaker, 0.0) + dur, 2)
        if seg.emotion:
            emotions[seg.emotion] = emotions.get(seg.emotion, 0) + 1
            v = _VALENCE.get(seg.emotion.lower())
            if v is not None:
                valence_sum += v * dur
                valence_weight += dur

    score = round(valence_sum / valence_weight, 3) if valence_weight else 0.0
    label = "positive" if score > 0.15 else "negative" if score < -0.15 else "neutral"

    full_text = " ".join(seg.text.lower() for seg in transcript)
    flagged = [
        FlaggedPhrase(phrase=kw, count=full_text.count(kw))
        for kw in keywords
        if kw and full_text.count(kw) > 0
    ]

    silence_ratio = 0.0
    if duration > 0:
        silence_ratio = round(max(0.0, 1.0 - speech_time / duration), 3)

    return CallAnalytics(
        num_speakers=len(talk_time),
        duration_sec=duration,
        sentiment_score=score,
        sentiment_label=label,
        silence_ratio=silence_ratio,
        talk_time=talk_time,
        flagged_phrases=flagged,
        emotions=emotions,
    )
