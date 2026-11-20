"""Speech services for manim-voiceover.

Pick one with the ``DTAK_VOICE`` environment variable (or ``dtak render --voice``):

* ``silent`` (default): no speech, but a *silent* audio clip as long as the
  narration would be when read at ``DTAK_WPM`` words per minute (default 140).
  Timing is right, it works offline and needs no API key: use it while
  designing, and to export a timed draft for the person recording the voice.
* ``gtts``: Google Translate TTS (needs ``uv sync --extra gtts`` and internet;
  sends the narration text to Google).
* ``recorder``: record your own voice beat by beat in the terminal
  (manim-voiceover's RecorderService; needs a microphone and PyAudio).

Audio files are cached under ``media/<episode>/voiceovers`` and reused while
the narration text does not change.
"""

from __future__ import annotations

import os
import re
import wave
from pathlib import Path

from manim_voiceover.services.base import SpeechService

DEFAULT_WPM = 140
SAMPLE_RATE = 16_000


def spoken_text(markdown: str) -> str:
    """Narration as it should be spoken: no markdown, no reference markers."""
    text = re.sub(r"\[REF[^\]]*\]", "", markdown)
    text = text.replace("**", "").replace("`", "")
    return " ".join(text.split())


def estimate_seconds(text: str, wpm: float = DEFAULT_WPM) -> float:
    words = len(spoken_text(text).split())
    return words / wpm * 60.0


class SilentDraftService(SpeechService):
    """Writes silence with the duration the narration will take."""

    def __init__(self, wpm: float = DEFAULT_WPM, **kwargs):
        self.wpm = wpm
        super().__init__(**kwargs)

    def generate_from_text(self, text, cache_dir=None, path=None, **kwargs):
        cache_dir = Path(cache_dir or self.cache_dir)
        input_data = {"input_text": text, "service": "silent", "wpm": self.wpm}
        cached = self.get_cached_result(input_data, cache_dir)
        if cached is not None:
            return cached
        audio = path or (self.get_audio_basename(input_data) + ".wav")
        seconds = max(estimate_seconds(text, self.wpm), 0.5)
        with wave.open(str(cache_dir / audio), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            w.writeframes(b"\x00\x00" * int(seconds * SAMPLE_RATE))
        return {"input_text": text, "input_data": input_data, "original_audio": str(audio)}


def make_speech_service(cache_dir: Path, name: str | None = None) -> SpeechService:
    name = (name or os.environ.get("DTAK_VOICE") or "silent").lower()
    cache_dir.mkdir(parents=True, exist_ok=True)
    if name == "silent":
        wpm = float(os.environ.get("DTAK_WPM", DEFAULT_WPM))
        return SilentDraftService(wpm=wpm, cache_dir=str(cache_dir))
    if name == "gtts":
        from manim_voiceover.services.gtts import GTTSService

        return GTTSService(cache_dir=str(cache_dir))
    if name == "recorder":
        from manim_voiceover.services.recorder import RecorderService

        return RecorderService(cache_dir=str(cache_dir))
    raise ValueError(f"unknown DTAK_VOICE={name!r} (use silent, gtts or recorder)")
