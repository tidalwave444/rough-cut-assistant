import pytest

from roughcut.analysis import SourceMedia, Word
from roughcut.script import ScriptLine

WORD_SECONDS = 0.5
"""How long a word takes in a hand-written recording — near enough to a real read."""

FIXTURE_SOURCE = SourceMedia(
    filename="sequence.mp4",
    duration_seconds=86.25,
    fps=60.0,
    ntsc=False,
    audio_sample_rate=48000,
)
"""The committed recording, as the spike measured it: 86.25 s of 60fps 1920x1080
with 48kHz stereo. Shared so that one recording is described in one place."""

SCRIPT = [
    ScriptLine(1, "Building a real project with vibe coding — Part 2."),
    ScriptLine(2, "Today we are moving from setup to actual development."),
    ScriptLine(3, "In the next part we will begin the implementation."),
]
"""The script every hand-written recording below reads from."""

# As heard rather than as written: the transcriber has no dashes and spells numbers.
LINE_1 = "Building a real project with vibe coding, part two."
LINE_2 = "Today we are moving from setup to actual development."
LINE_3 = "In the next part we will begin the implementation."

LINE_2_STOPS_SHORT = "Today we are moving from setup"
"""Line 2 abandoned six words in — an attempt that never reaches the end of it."""


def spoken(text: str, *, at: float) -> list[Word]:
    """A sentence heard from `at`, one word every `WORD_SECONDS`.

    The whole point of the seam: a fixture recording is a sentence and a time, and no
    test below it needs an MP4 to describe what was said when.
    """
    return [
        Word(word, at + index * WORD_SECONDS, at + (index + 1) * WORD_SECONDS, 0.9)
        for index, word in enumerate(text.split())
    ]


def clean_read() -> list[Word]:
    """The script read once through, in order, with dead air between the lines."""
    return spoken(LINE_1, at=0.0) + spoken(LINE_2, at=6.0) + spoken(LINE_3, at=13.0)


def retakes(*attempts: str) -> list[Word]:
    """Line 2 attempted several times, between a clean line 1 and a clean line 3.

    Seven seconds apart, so every attempt starts on a round number and the dead air
    between them is longer than any attempt is short.
    """
    words = spoken(LINE_1, at=0.0)
    for index, attempt in enumerate(attempts):
        words += spoken(attempt, at=6.0 + index * 7.0)
    return words + spoken(LINE_3, at=6.0 + len(attempts) * 7.0)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-golden",
        action="store_true",
        help="Rewrite the golden files from the current renderer, for review as a diff.",
    )


@pytest.fixture
def update_golden(request: pytest.FixtureRequest) -> bool:
    """Whether the golden files should be rewritten rather than asserted against.

    An intentional change to the output is then a deliberate, reviewable diff instead
    of a hand-edited expectation.
    """
    return bool(request.config.getoption("--update-golden"))
