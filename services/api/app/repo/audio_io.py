"""Audio decoding / resampling helpers for the speech pipeline.

Reads telephony recordings (WAV/MP3) into a mono float32 waveform at 16 kHz —
the sample rate every SpeechBrain model here expects — and writes a canonical
16 kHz mono WAV that the file-based VAD reads. Kept out of ``speech_engine.py``
so that module stays under the 300-line structural ceiling and holds only the
torch/speechbrain surface. No boto3 here (this is not storage I/O).
"""

import io

TARGET_SR = 16_000


def load_waveform(data: bytes) -> tuple["object", int]:
    """Decode `data` to a mono float32 numpy array resampled to 16 kHz.

    Uses soundfile (libsndfile 1.1 reads WAV and MP3) and falls back to librosa
    for containers soundfile can't open. Returns ``(waveform, 16000)``.
    """
    import numpy as np

    try:
        import soundfile as sf

        wav, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=False)
    except Exception:
        import librosa

        wav, sr = librosa.load(io.BytesIO(data), sr=None, mono=False)

    wav = np.asarray(wav, dtype=np.float32)
    # Downmix to mono (soundfile yields [frames, channels] for multichannel).
    if wav.ndim > 1:
        wav = wav.mean(axis=1 if wav.shape[0] > wav.shape[1] else 0)
        wav = np.asarray(wav, dtype=np.float32)

    if sr != TARGET_SR:
        import librosa

        wav = librosa.resample(wav, orig_sr=sr, target_sr=TARGET_SR)
        wav = np.asarray(wav, dtype=np.float32)

    return wav, TARGET_SR


def write_wav(path: str, waveform: "object", sr: int = TARGET_SR) -> None:
    """Write a mono float32 waveform to `path` as a 16-bit PCM WAV."""
    import soundfile as sf

    sf.write(path, waveform, sr, subtype="PCM_16")
