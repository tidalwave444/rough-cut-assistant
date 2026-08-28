"""The golden test: the real recording, end to end below the seam.

The analysis of the fixture recording is committed, so this runs the whole cut — plan,
XML, report — against real transcript timings without a GPU or the MP4. One assertion
therefore covers the schema, the timebase, the sequence structure and the report's
wording at once.

Rewrite the expected files with `pytest --update-golden` when the change is intended.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from roughcut.analysis import load_analysis
from roughcut.plan import build_plan
from roughcut.render import render_fcp7
from roughcut.report import render_report
from roughcut.script import read_script

REPO = Path(__file__).resolve().parents[1]
ANALYSIS = REPO / "tests" / "committed" / "sequence.analysis.json"
SCRIPT = REPO / "recordings" / "textt.txt"
GOLDEN_XML = REPO / "tests" / "committed" / "sequence.golden.xml"
GOLDEN_REPORT = REPO / "tests" / "committed" / "sequence.golden.report.txt"


def assert_golden(path: Path, produced: str, update: bool) -> None:
    if update:
        path.write_text(produced, encoding="utf-8")
    assert produced == path.read_text(encoding="utf-8")


def test_the_fixture_recording_renders_the_expected_sequence(update_golden: bool) -> None:
    analysis = load_analysis(ANALYSIS)
    plan = build_plan(analysis, read_script(SCRIPT))

    assert_golden(GOLDEN_XML, render_fcp7(plan), update_golden)


def test_the_fixture_recording_reports_the_expected_cut(update_golden: bool) -> None:
    # Where every line was found is the reviewable part of an alignment change: a
    # heuristic that moves a line shows up here as a line moving, not as a frame count.
    analysis = load_analysis(ANALYSIS)
    script = read_script(SCRIPT)

    report = render_report(analysis, script, build_plan(analysis, script))

    assert_golden(GOLDEN_REPORT, report, update_golden)


def test_the_fixture_cut_splices_every_clip_onto_the_end_of_the_last() -> None:
    # Asserted on the real recording rather than on hand-picked times, because this is
    # where awkward numbers come from: a shortened pause puts clip boundaries on
    # fractions of a frame, and one audio track can hold neither two clipitems at once
    # nor a frame of hole between them.
    analysis = load_analysis(ANALYSIS)
    plan = build_plan(analysis, read_script(SCRIPT))

    # The rough cut alone: the alternates sequence beside it starts its own timeline
    # at zero, and reading the two as one run of clips would report a false overlap.
    clipitems = ET.fromstring(render_fcp7(plan)).findall(
        "./sequence[name='RoughCut']/media/audio/track/clipitem"
    )

    frames = [
        (int(item.findtext("start") or ""), int(item.findtext("end") or ""))
        for item in clipitems
    ]
    assert [start for start, _ in frames[1:]] == [end for _, end in frames[:-1]]


def test_the_committed_analysis_describes_the_fixture_recording() -> None:
    # The artifact is what every later ticket is tested against, so its provenance is
    # asserted here rather than trusted: these are the spike's measured facts.
    source = load_analysis(ANALYSIS).source

    assert source.filename == "sequence.mp4"
    assert source.duration_seconds == 86.25
    assert (source.fps, source.ntsc) == (60.0, False)
    assert (source.audio_sample_rate, source.audio_channels) == (48000, 2)
