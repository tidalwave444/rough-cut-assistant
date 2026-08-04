import pytest

from roughcut.analysis import SourceMedia

FIXTURE_SOURCE = SourceMedia(
    filename="sequence.mp4",
    duration_seconds=86.25,
    fps=60.0,
    ntsc=False,
    audio_sample_rate=48000,
)
"""The committed recording, as the spike measured it: 86.25 s of 60fps 1920x1080
with 48kHz stereo. Shared so that one recording is described in one place."""


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
