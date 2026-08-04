"""The plan: the complete set of cut decisions, in seconds.

A plan says what the cut *is* — which pieces of the source play in what order, and
what the markers say — without knowing anything about the output format. Times are
seconds as floats throughout; conversion to frames happens only in the renderer.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceMedia:
    """The recording a sequence draws from, as probed from the container.

    Referenced by bare filename: the tool and Premiere run in different filesystem
    namespaces, so the user relinks once on import.
    """

    filename: str
    duration_seconds: float
    fps: float
    ntsc: bool
    width: int
    height: int
    audio_sample_rate: int
    audio_channels: int
    audio_bit_depth: int = 16


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
