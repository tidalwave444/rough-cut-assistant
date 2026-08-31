"""The golden tests: both real recordings, end to end below the seam.

Each recording's analysis is committed, so this runs the whole cut — plan, XML, report —
against real transcript timings without a GPU or the MP4. One assertion therefore covers
the schema, the timebase, the sequence structure and the report's wording at once.

Two recordings rather than one, because a hand-written fixture holds one thing at a time
and the faults that reach the operator are two rules meeting. Every fault found between
28 and 31 August was found by cutting `Sequence 07` and listening, and not one of them
was caught here — a span-finder nothing called, a rule that could never fire, a measure
that lowered the coverage it was built to raise, and a line playing seven seconds of the
attempt it abandoned. All four are visible in these files. `sequence.mp4` is the small,
clean read; `Sequence 07.mp4` is the messy one, and it is the one that catches things.

The XML golden is the record of what *plays*: a report can say a line was found at full
coverage while the clips beneath it play the whole abandoned attempt, which is exactly
what happened. Read the clip list, not the summary.

Rewrite the expected files with `pytest --update-golden` when the change is intended.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import pytest

from roughcut.analysis import Analysis, SourceMedia, load_analysis
from roughcut.plan import Plan, build_plan
from roughcut.render import render_fcp7
from roughcut.report import render_report
from roughcut.script import ScriptLine, read_script

REPO = Path(__file__).resolve().parents[1]
COMMITTED = REPO / "tests" / "committed"
RECORDINGS = REPO / "recordings"


@dataclass(frozen=True)
class Committed:
    """One recording the whole cut is asserted against, and where its four files live."""

    name: str
    analysis: Path
    script: Path
    golden_xml: Path
    golden_report: Path

    def read(self) -> tuple[Analysis, list[ScriptLine]]:
        return load_analysis(self.analysis), read_script(self.script)

    def plan(self) -> tuple[Analysis, list[ScriptLine], Plan]:
        analysis, script = self.read()
        return analysis, script, build_plan(analysis, script)


FIXTURE = Committed(
    name="sequence.mp4",
    analysis=COMMITTED / "sequence.analysis.json",
    script=RECORDINGS / "textt.txt",
    golden_xml=COMMITTED / "sequence.golden.xml",
    golden_report=COMMITTED / "sequence.golden.report.txt",
)

SEQUENCE_07 = Committed(
    name="Sequence 07.mp4",
    analysis=COMMITTED / "Sequence 07.analysis.json",
    script=RECORDINGS / "text_for_Sequence 07.txt",
    golden_xml=COMMITTED / "Sequence 07.golden.xml",
    golden_report=COMMITTED / "Sequence 07.golden.report.txt",
)

RECORDED = [pytest.param(FIXTURE, id="sequence"), pytest.param(SEQUENCE_07, id="sequence-07")]


def assert_golden(path: Path, produced: str, update: bool) -> None:
    if update:
        path.write_text(produced, encoding="utf-8")
    assert produced == path.read_text(encoding="utf-8")


@pytest.mark.parametrize("recording", RECORDED)
def test_a_recording_renders_the_expected_sequence(
    recording: Committed, update_golden: bool
) -> None:
    # What plays, in frames. The one artifact that cannot describe a cut as healthier
    # than it is: a clip is source in, source out and a place on the timeline, so an
    # abandoned attempt still playing is a clip list nobody can read as anything else.
    _, _, plan = recording.plan()

    assert_golden(recording.golden_xml, render_fcp7(plan), update_golden)


@pytest.mark.parametrize("recording", RECORDED)
def test_a_recording_reports_the_expected_cut(
    recording: Committed, update_golden: bool
) -> None:
    # Where every line was found is the reviewable part of an alignment change: a
    # heuristic that moves a line shows up here as a line moving, not as a frame count.
    analysis, script, plan = recording.plan()

    assert_golden(recording.golden_report, render_report(analysis, script, plan), update_golden)


@pytest.mark.parametrize("recording", RECORDED)
def test_a_recording_splices_every_clip_onto_the_end_of_the_last(
    recording: Committed,
) -> None:
    # Asserted on the real recordings rather than on hand-picked times, because this is
    # where awkward numbers come from: a shortened pause puts clip boundaries on
    # fractions of a frame, and one audio track can hold neither two clipitems at once
    # nor a frame of hole between them.
    _, _, plan = recording.plan()

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


def test_the_committed_analyses_describe_the_recordings_they_are_named_for() -> None:
    # Each artifact is what every later ticket is tested against, so its provenance is
    # asserted here rather than trusted: these are the measured facts of both files.
    assert load_analysis(FIXTURE.analysis).source == SourceMedia(
        filename="sequence.mp4",
        duration_seconds=86.25,
        fps=60.0,
        ntsc=False,
        audio_sample_rate=48000,
        audio_channels=2,
    )
    assert load_analysis(SEQUENCE_07.analysis).source == SourceMedia(
        filename="Sequence 07.mp4",
        duration_seconds=142.566667,
        fps=60.0,
        ntsc=False,
        audio_sample_rate=48000,
        audio_channels=2,
    )
