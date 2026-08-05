"""The plan: the complete set of cut decisions, in seconds.

A plan says what the cut *is* — which pieces of the source play in what order, and
what the markers say — without knowing anything about the output format. Times are
seconds as floats throughout; conversion to frames happens only in the renderer.
"""

from dataclasses import dataclass, field

from roughcut.align import Leftover, SpokenLine, align
from roughcut.analysis import Analysis, SourceMedia
from roughcut.script import ScriptLine, beats

ROUGH_CUT = "RoughCut"


@dataclass(frozen=True)
class Clip:
    """One piece of the source, placed on the timeline.

    The clip occupies the timeline for exactly as long as it lasts in the source,
    so only its start on the timeline is given.
    """

    source_in_seconds: float
    source_out_seconds: float
    timeline_start_seconds: float


@dataclass(frozen=True)
class Marker:
    """A note on the timeline — a script line, or a record of what was removed."""

    name: str
    comment: str
    timeline_position_seconds: float


@dataclass(frozen=True)
class Sequence:
    """One timeline: clips butt-spliced on a single audio track, plus its markers."""

    id: str
    name: str
    source: SourceMedia
    clips: list[Clip] = field(default_factory=list)
    markers: list[Marker] = field(default_factory=list)


@dataclass(frozen=True)
class PlacedLine:
    """One script line: where it was found, and where it now plays.

    The clip beside it says the same thing in timeline terms; this says it in script
    terms, which is what a person reading the report wants to know.
    """

    line: ScriptLine
    source_in_seconds: float
    source_out_seconds: float
    timeline_start_seconds: float


@dataclass(frozen=True)
class Plan:
    """Everything one import should produce — the rough cut and its alternates."""

    sequences: list[Sequence] = field(default_factory=list)
    lines: list[PlacedLine] = field(default_factory=list)
    """The script lines that made it into the cut, in script order."""
    missing: list[ScriptLine] = field(default_factory=list)
    """The lines the recording does not contain, skipped rather than fabricated."""
    leftovers: list[Leftover] = field(default_factory=list)
    """Speech the cut does not use: retakes, and material off the script."""


def build_plan(analysis: Analysis, script: list[ScriptLine]) -> Plan:
    """Decide the cut: one clip per script line, spliced in the order they are written.

    Each line plays from where it was first read well enough to stand for the line,
    and a marker sits at its start carrying its text — so scrubbing the timeline says
    which visual belongs where. A line the recording does not contain is skipped and
    reported; the cut is still usable without it.

    What is not decided yet: pauses are left as they were spoken (06), and where a
    line was read more than once the first reading plays while the rest are recorded
    as retakes (07). Only the rough cut is produced — the alternates sequence arrives
    with take selection, because until something is rejected it would import empty.
    """
    alignment = align(analysis.words, script)
    placed = _placed(alignment.spoken)
    return Plan(
        sequences=[
            Sequence(
                id="sequence-1",
                name=ROUGH_CUT,
                source=analysis.source,
                clips=[
                    Clip(
                        source_in_seconds=line.source_in_seconds,
                        source_out_seconds=line.source_out_seconds,
                        timeline_start_seconds=line.timeline_start_seconds,
                    )
                    for line in placed
                ],
                markers=[
                    marker
                    for spoken, line in zip(alignment.spoken, placed, strict=True)
                    for marker in _markers(spoken, line)
                ],
            )
        ],
        lines=placed,
        missing=alignment.missing,
        leftovers=alignment.leftovers,
    )


def _placed(spoken: list[SpokenLine]) -> list[PlacedLine]:
    """Lay the located lines end to end, in script order."""
    placed = []
    timeline = 0.0
    for line in spoken:
        placed.append(
            PlacedLine(
                line=line.line,
                source_in_seconds=line.start_seconds,
                source_out_seconds=line.end_seconds,
                timeline_start_seconds=timeline,
            )
        )
        timeline += line.end_seconds - line.start_seconds
    return placed


def _markers(spoken: SpokenLine, placed: PlacedLine) -> list[Marker]:
    """One marker per beat of the line, at the moment that beat was reached.

    Named for the line so the timeline reads in script terms, and numbered within it
    when the line enumerates — `Line 6.2` is the second item of the sixth line.
    """
    found = beats(spoken.line)
    return [
        Marker(
            name=_marker_name(spoken.line.number, index, len(found)),
            comment=beat.text,
            timeline_position_seconds=(
                placed.timeline_start_seconds
                + spoken.time_of_token(beat.token_offset)
                - placed.source_in_seconds
            ),
        )
        for index, beat in enumerate(found, start=1)
    ]


def _marker_name(number: int, index: int, beats: int) -> str:
    return f"Line {number}" if beats == 1 else f"Line {number}.{index}"


def rough_cut(plan: Plan) -> Sequence:
    """The sequence that is the cut, as opposed to the alternates beside it."""
    for sequence in plan.sequences:
        if sequence.name == ROUGH_CUT:
            return sequence
    raise ValueError(f"This plan has no {ROUGH_CUT} sequence")


def timeline_duration_seconds(sequence: Sequence) -> float:
    """How long the cut runs — the end of its last clip on the timeline."""
    return max(
        (
            clip.timeline_start_seconds + (clip.source_out_seconds - clip.source_in_seconds)
            for clip in sequence.clips
        ),
        default=0.0,
    )
