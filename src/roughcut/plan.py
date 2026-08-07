"""The plan: the complete set of cut decisions, in seconds.

A plan says what the cut *is* — which pieces of the source play in what order, and
what the markers say — without knowing anything about the output format. Times are
seconds as floats throughout; conversion to frames happens only in the renderer.
"""

from dataclasses import dataclass, field

from roughcut.align import Leftover, SpokenLine, align
from roughcut.analysis import Analysis, SourceMedia
from roughcut.pauses import Pause, PauseSettings, Tightened, pauses_to_shorten, tighten
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

    The clips beside it say the same thing in timeline terms; this says it in script
    terms, which is what a person reading the report wants to know. A line reaches the
    timeline in one piece unless a pause inside it was shortened, which splits it.
    """

    line: ScriptLine
    tightened: Tightened
    """The stretch it was read in, with the long pauses inside it shortened."""
    timeline_start_seconds: float

    @property
    def source_in_seconds(self) -> float:
        return self.tightened.start_seconds

    def timeline_of(self, source_seconds: float) -> float:
        """Where a moment of the stretch this line was read in lands on the timeline.

        Both the clips and the markers ask this: a shortened pause moves everything
        after it earlier, and neither may be placed as though it hadn't.
        """
        return self.timeline_start_seconds + self.tightened.offset_of(source_seconds)


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
    shortened: list[Pause] = field(default_factory=list)
    """The pauses the cut took time out of, in the order they were recorded."""


def build_plan(
    analysis: Analysis, script: list[ScriptLine], settings: PauseSettings = PauseSettings()
) -> Plan:
    """Decide the cut: one clip per script line, spliced in the order they are written.

    Each line plays from where it was first read well enough to stand for the line,
    and a marker sits at its start carrying its text — so scrubbing the timeline says
    which visual belongs where. A line the recording does not contain is skipped and
    reported; the cut is still usable without it.

    The dead air between lines goes entirely, because nothing splices it back in. A
    long pause *inside* a line is shortened to a floor instead: it is speech the cut
    keeps, and a read with no pauses left in it is a read nobody wants.

    What is not decided yet: where a line was read more than once the first reading
    plays while the rest are recorded as retakes (07). Only the rough cut is produced
    — the alternates sequence arrives with take selection, because until something is
    rejected it would import empty.
    """
    alignment = align(analysis.words, script)
    placed = _placed(
        alignment.spoken, pauses_to_shorten(analysis.words, analysis.silences, settings)
    )
    return Plan(
        sequences=[
            Sequence(
                id="sequence-1",
                name=ROUGH_CUT,
                source=analysis.source,
                clips=[
                    Clip(
                        source_in_seconds=segment.start_seconds,
                        source_out_seconds=segment.end_seconds,
                        timeline_start_seconds=line.timeline_of(segment.start_seconds),
                    )
                    for line in placed
                    for segment in line.tightened.segments
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
        shortened=sorted(
            (pause for line in placed for pause in line.tightened.pauses),
            key=lambda pause: pause.gap_start_seconds,
        ),
    )


def _placed(spoken: list[SpokenLine], pauses: list[Pause]) -> list[PlacedLine]:
    """Lay the located lines end to end, in script order, each already tightened."""
    placed = []
    timeline = 0.0
    for line in spoken:
        tightened = tighten(line.start_seconds, line.end_seconds, pauses)
        placed.append(
            PlacedLine(
                line=line.line,
                tightened=tightened,
                timeline_start_seconds=timeline,
            )
        )
        timeline += tightened.duration_seconds
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
            timeline_position_seconds=placed.timeline_of(
                spoken.time_of_token(beat.token_offset)
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
