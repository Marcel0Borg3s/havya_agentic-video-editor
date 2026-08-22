"""Editorial analysis: silence, pauses, hesitations, repetitions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.models.schemas import Shot, WordTimestamp

# Hesitation markers (Portuguese + English).
_HESITATIONS = {
    "um", "uh", "ah", "eh", "hm", "hmm", "err", "hã", "é", "né",
    "tipo", "tipo assim", "sabe", "então", "aí", "bom", "pois",
}

# Minimum gap (seconds) to consider a pause.
_LONG_PAUSE_THRESHOLD = 0.8

# Minimum silence gap (seconds) at start/end of shot.
_SILENCE_THRESHOLD = 0.5


@dataclass
class ShotAnalysis:
    """Analysis results for a single shot."""
    silence_start: float = 0.0
    silence_end: float = 0.0
    long_pauses: list[tuple[float, float]] = field(default_factory=list)
    hesitations: list[dict] = field(default_factory=list)
    repetitions: list[dict] = field(default_factory=list)
    word_count: int = 0
    speech_ratio: float = 0.0


def _gap_duration(w1: WordTimestamp, w2: WordTimestamp) -> float:
    """Gap between end of w1 and start of w2."""
    return max(0.0, w2.start - w1.end)


def detect_silence(shot: Shot) -> tuple[float, float]:
    """Detect silence at start and end of a shot.

    Returns (silence_start, silence_end) in seconds.
    """
    if not shot.words:
        return (shot.end_time - shot.start_time, 0.0)

    first_word = shot.words[0]
    last_word = shot.words[-1]

    silence_start = max(0.0, first_word.start - shot.start_time)
    silence_end = max(0.0, shot.end_time - last_word.end)

    return (silence_start, silence_end)


def detect_long_pauses(shot: Shot) -> list[tuple[float, float]]:
    """Detect long pauses between words.

    Returns list of (start, end) timestamps for each long pause.
    """
    pauses: list[tuple[float, float]] = []
    for i in range(len(shot.words) - 1):
        gap = _gap_duration(shot.words[i], shot.words[i + 1])
        if gap >= _LONG_PAUSE_THRESHOLD:
            pauses.append((shot.words[i].end, shot.words[i + 1].start))
    return pauses


def detect_hesitations(shot: Shot) -> list[dict]:
    """Detect hesitation markers in the transcript.

    Returns list of {word, start, end, index} dicts.
    """
    hesitations: list[dict] = []
    for i, word in enumerate(shot.words):
        text = word.word.lower().strip(" .,!?;:")
        if text in _HESITATIONS:
            hesitations.append({
                "word": word.word,
                "start": word.start,
                "end": word.end,
                "index": i,
            })
    return hesitations


def detect_repetitions(shot: Shot) -> list[dict]:
    """Detect consecutive repeated words or short phrases.

    Returns list of {words, start, end, count} dicts.
    """
    repetitions: list[dict] = []
    if len(shot.words) < 2:
        return repetitions

    i = 0
    while i < len(shot.words) - 1:
        w1 = shot.words[i].word.lower().strip(" .,!?;:")
        w2 = shot.words[i + 1].word.lower().strip(" .,!?;:")

        if w1 and w1 == w2:
            # Found repetition, count how many times.
            count = 2
            start_idx = i
            while (
                i + count < len(shot.words)
                and shot.words[i + count].word.lower().strip(" .,!?;:") == w1
            ):
                count += 1

            repetitions.append({
                "words": w1,
                "start": shot.words[start_idx].start,
                "end": shot.words[start_idx + count - 1].end,
                "count": count,
            })
            i += count
        else:
            i += 1

    return repetitions


def analyze_shot(shot: Shot) -> ShotAnalysis:
    """Run all analyses on a single shot."""
    silence_start, silence_end = detect_silence(shot)
    long_pauses = detect_long_pauses(shot)
    hesitations = detect_hesitations(shot)
    repetitions = detect_repetitions(shot)

    word_count = len(shot.words)
    shot_duration = shot.end_time - shot.start_time

    # Speech ratio: time spent speaking vs shot duration.
    if shot.words and shot_duration > 0:
        speech_time = sum(
            w.end - w.start for w in shot.words
        )
        speech_ratio = min(1.0, speech_time / shot_duration)
    else:
        speech_ratio = 0.0

    return ShotAnalysis(
        silence_start=silence_start,
        silence_end=silence_end,
        long_pauses=long_pauses,
        hesitations=hesitations,
        repetitions=repetitions,
        word_count=word_count,
        speech_ratio=speech_ratio,
    )
