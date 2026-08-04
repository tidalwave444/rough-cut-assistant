"""The golden test: the real recording, end to end below the seam.

The analysis of the fixture recording is committed, so this runs the whole cut — plan,
XML, report — against real transcript timings without a GPU or the MP4. One assertion
therefore covers the schema, the timebase, the sequence structure and the report's
wording at once.

Rewrite the expected files with `pytest --update-golden` when the change is intended.
"""

from pathlib import Path

from roughcut.analysis import load_analysis
from roughcut.plan import build_plan
from roughcut.render import render_fcp7
from roughcut.script import read_script

REPO = Path(__file__).resolve().parents[1]
ANALYSIS = REPO / "tests" / "fixtures" / "sequence.analysis.json"
SCRIPT = REPO / "media" / "textt.txt"
GOLDEN_XML = REPO / "tests" / "fixtures" / "sequence.golden.xml"


def assert_golden(path: Path, produced: str, update: bool) -> None:
    if update:
        path.write_text(produced, encoding="utf-8")
    assert produced == path.read_text(encoding="utf-8")


def test_the_fixture_recording_renders_the_expected_sequence(update_golden: bool) -> None:
    analysis = load_analysis(ANALYSIS)
    plan = build_plan(analysis, read_script(SCRIPT))

    assert_golden(GOLDEN_XML, render_fcp7(plan), update_golden)


def test_the_committed_analysis_describes_the_fixture_recording() -> None:
    # The artifact is what every later ticket is tested against, so its provenance is
    # asserted here rather than trusted: these are the spike's measured facts.
    source = load_analysis(ANALYSIS).source

    assert source.filename == "sequence.mp4"
    assert source.duration_seconds == 86.25
    assert (source.fps, source.ntsc) == (60.0, False)
    assert (source.audio_sample_rate, source.audio_channels) == (48000, 2)
