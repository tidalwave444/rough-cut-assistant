"""The one test that opens the real recording — needs ffmpeg, the model and a GPU.

Excluded from the default run (`pytest -m slow` runs it). It is the only place a
Whisper or driver regression can be caught, so it checks shape and plausibility:
nothing here asserts what was said, because model output is not a stable contract.
"""

from pathlib import Path

import pytest

from roughcut.analysis import Analysis
from roughcut.analyze import AnalysisSettings, analyze_recording

pytestmark = pytest.mark.slow

RECORDING = Path(__file__).resolve().parents[1] / "media" / "sequence.mp4"

# The fixture's measured facts, from the spike.
DURATION_SECONDS = 86.25
EXPECTED_FPS = 60.0
KNOWN_PAUSE = (55.31, 56.56)

# A transcript of the fixture runs to about 165 words. The band is wide because a
# model change is allowed to move it; an empty or runaway transcript is not.
FEWEST_WORDS = 120
MOST_WORDS = 220


@pytest.fixture(scope="module")
def analysis() -> Analysis:
    if not RECORDING.is_file():
        pytest.skip(f"The fixture recording is not present at {RECORDING}")
    return analyze_recording(RECORDING, AnalysisSettings())


def test_the_frame_rate_is_read_from_the_container(analysis: Analysis) -> None:
    source = analysis.source
    assert source.fps == EXPECTED_FPS
    assert source.duration_seconds == pytest.approx(DURATION_SECONDS, abs=0.01)
    assert (source.audio_sample_rate, source.audio_channels) == (48000, 2)


def test_the_whole_script_is_transcribed(analysis: Analysis) -> None:
    assert FEWEST_WORDS <= len(analysis.words) <= MOST_WORDS


def test_every_word_starts_before_it_ends(analysis: Analysis) -> None:
    assert all(word.start_seconds <= word.end_seconds for word in analysis.words)


def test_the_words_run_forwards(analysis: Analysis) -> None:
    starts = [word.start_seconds for word in analysis.words]
    assert starts == sorted(starts)


def test_no_word_is_spoken_outside_the_recording(analysis: Analysis) -> None:
    assert analysis.words[0].start_seconds >= 0.0
    assert analysis.words[-1].end_seconds <= DURATION_SECONDS


def test_the_pauses_the_room_actually_has_are_found(analysis: Analysis) -> None:
    # 29 regions at the default threshold when the spike measured it; the count is
    # allowed to drift with the detector, an empty result is not.
    assert len(analysis.silences) >= 20


def test_the_pause_the_spike_cut_by_hand_is_detected(analysis: Analysis) -> None:
    start, end = KNOWN_PAUSE
    assert any(
        silence.start_seconds <= start + 0.1 and silence.end_seconds >= end - 0.1
        for silence in analysis.silences
    )


def test_an_analysis_of_the_recording_records_nothing_about_where_it_came_from(
    analysis: Analysis,
) -> None:
    # The fingerprint is the cache's business — see `analysis_for`.
    assert analysis.fingerprint is None
