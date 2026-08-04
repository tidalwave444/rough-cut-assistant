"""The plan: the complete set of cut decisions, in seconds.

A plan says what the cut *is* — which pieces of the source play in what order, and
what the markers say — without knowing anything about the output format. Times are
seconds as floats throughout; conversion to frames happens only in the renderer.
"""

from dataclasses import dataclass, field

from roughcut.analysis import Analysis, SourceMedia
from roughcut.script import ScriptLine

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
class Plan:
    """Everything one import should produce — the rough cut and its alternates."""

    sequences: list[Sequence] = field(default_factory=list)


def build_plan(analysis: Analysis, script: list[ScriptLine]) -> Plan:
    """Decide the cut: currently, the whole recording as one clip.

    Nothing is removed and no take is chosen, which is deliberate — this is the cut
    that proves the path from recording to importable XML exists. The pauses (06) and
    the takes (07) are decided here later, from the words and silences the analysis
    already carries; `script` is the alignment ticket's (05) input and is not yet read.

    Only the rough cut is produced. The alternates sequence arrives with take
    selection, because until something is rejected it would import empty.
    """
    source = analysis.source
    return Plan(
        sequences=[
            Sequence(
                id="sequence-1",
                name=ROUGH_CUT,
                source=source,
                clips=[
                    Clip(
                        source_in_seconds=0.0,
                        source_out_seconds=source.duration_seconds,
                        timeline_start_seconds=0.0,
                    )
                ],
            )
        ]
    )


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
