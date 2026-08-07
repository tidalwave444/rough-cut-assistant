"""Pause collapsing: a cut that is tighter than the recording without being breathless.

A long gap between two words is *shortened, never closed*. That is a product decision
rather than an implementation shortcut: a read with every pause removed sounds
machine-gunned, and putting the pacing back afterwards means re-trimming every edit
point by hand — far more work than trimming a little further.

Where the cut lands is decided by the audio, not by the transcript. A transcript gap
says roughly where nothing was said; a silence region says where nothing was heard.
So an eligible gap gives up only the part of it a silence corroborates, padded away
from the words either side and centred in the quiet, which leaves a breath on both
sides of the splice. A gap no silence corroborates is left exactly as it was spoken.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from roughcut.analysis import Silence, Word

# Long enough that shortening it is worth an edit point; short enough that the dead
# air between two attempts never survives. Tuned for a quiet room and a scripted read.
DEFAULT_THRESHOLD_SECONDS = 0.7

# What a shortened gap becomes. A beat, not nothing.
DEFAULT_FLOOR_SECONDS = 0.3

# Kept either side of every cut, inside the silence. A word's first consonant starts
# below the detector's threshold, so a cut placed at the edge of the quiet clips it.
DEFAULT_PADDING_SECONDS = 0.05


@dataclass(frozen=True)
class PauseSettings:
    """How tight the cut is: what counts as a long pause, and what it becomes."""

    threshold_seconds: float = DEFAULT_THRESHOLD_SECONDS
    floor_seconds: float = DEFAULT_FLOOR_SECONDS
    padding_seconds: float = DEFAULT_PADDING_SECONDS


@dataclass(frozen=True)
class Pause:
    """A gap between two words, and the piece of it the cut takes out.

    The gap is what was spoken; the cut is what is removed from inside the silence
    that corroborates it. They differ by the floor — plus whatever the quiet was too
    short to give up.
    """

    gap_start_seconds: float
    gap_end_seconds: float
    cut_start_seconds: float
    cut_end_seconds: float

    @property
    def gap_seconds(self) -> float:
        return self.gap_end_seconds - self.gap_start_seconds

    @property
    def removed_seconds(self) -> float:
        return self.cut_end_seconds - self.cut_start_seconds

    @property
    def remaining_seconds(self) -> float:
        """How long the pause still lasts in the cut — the floor, or more."""
        return self.gap_seconds - self.removed_seconds


def pauses_to_shorten(
    words: Sequence[Word],
    silences: Sequence[Silence],
    settings: PauseSettings = PauseSettings(),
) -> list[Pause]:
    """Every gap in this recording that is both long enough and audibly quiet.

    Only gaps between consecutive words are considered, so the quiet before the first
    word and after the last is not a pause: there is nothing on one side of it to
    shorten towards.
    """
    found = []
    for before, after in zip(words, words[1:]):
        pause = _shortened(before.end_seconds, after.start_seconds, silences, settings)
        if pause is not None:
            found.append(pause)
    return found


def _shortened(
    gap_start: float, gap_end: float, silences: Sequence[Silence], settings: PauseSettings
) -> Pause | None:
    """What this gap gives up, or None if it keeps all of it."""
    if gap_end - gap_start <= settings.threshold_seconds:
        return None
    quiet = _longest_quiet(gap_start, gap_end, silences, settings.padding_seconds)
    if quiet is None:
        return None
    start, end = quiet
    removed = min(gap_end - gap_start - settings.floor_seconds, end - start)
    if removed <= 0:
        return None
    middle = (start + end) / 2
    return Pause(gap_start, gap_end, middle - removed / 2, middle + removed / 2)


def _longest_quiet(
    gap_start: float, gap_end: float, silences: Sequence[Silence], padding: float
) -> tuple[float, float] | None:
    """The longest stretch of corroborated quiet within this gap, padded off the words.

    Each silence is clipped to the gap before it is padded, so a region that runs into
    the words either side — as one does, since a last consonant fades below the
    detector's threshold — can never place a cut inside a word.

    One region, even where several overlap the gap: a gap the detector heard as two
    stretches of quiet with something audible between them can only give up one of
    them, because taking both would cut away whatever was said in the middle. Such a
    gap therefore lands short of the floor, which is the conservative direction.
    """
    windows = [
        (
            max(silence.start_seconds, gap_start) + padding,
            min(silence.end_seconds, gap_end) - padding,
        )
        for silence in silences
    ]
    return max(
        (window for window in windows if window[1] > window[0]),
        key=lambda window: window[1] - window[0],
        default=None,
    )


@dataclass(frozen=True)
class Segment:
    """A piece of the recording that survives the shortening, and so reaches a clip."""

    start_seconds: float
    end_seconds: float


@dataclass(frozen=True)
class Tightened:
    """A stretch of the recording with the long pauses inside it shortened.

    Everything after a shortened pause plays earlier than it was recorded, so this is
    also the map from a moment in the source to where that moment lands on the
    timeline — which is what keeps a marker on the words it names.
    """

    start_seconds: float
    end_seconds: float
    pauses: tuple[Pause, ...] = ()

    @property
    def duration_seconds(self) -> float:
        """How long the stretch runs once its pauses are shortened."""
        removed = sum(pause.removed_seconds for pause in self.pauses)
        return self.end_seconds - self.start_seconds - removed

    @property
    def segments(self) -> list[Segment]:
        """The pieces of source that survive, in order — one more than the cuts."""
        edges = [self.start_seconds]
        for pause in self.pauses:
            edges += [pause.cut_start_seconds, pause.cut_end_seconds]
        edges.append(self.end_seconds)
        return [Segment(edges[index], edges[index + 1]) for index in range(0, len(edges), 2)]

    def offset_of(self, source_seconds: float) -> float:
        """Where a moment of the source falls, measured from the start of the stretch.

        A moment inside a cut lands on the splice rather than in the hole where the
        silence used to be, so nothing is ever placed at a time that no longer exists.
        """
        offset = source_seconds - self.start_seconds
        for pause in self.pauses:
            if source_seconds >= pause.cut_end_seconds:
                offset -= pause.removed_seconds
            elif source_seconds > pause.cut_start_seconds:
                offset -= source_seconds - pause.cut_start_seconds
        return offset


def tighten(start_seconds: float, end_seconds: float, pauses: Sequence[Pause]) -> Tightened:
    """The stretch between two times, minus whichever pauses fall wholly inside it.

    A pause straddling the ends belongs to the dead air between two stretches, which
    the splice removes in full — there is nothing left of it to collapse.
    """
    return Tightened(
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        pauses=tuple(
            pause
            for pause in pauses
            if start_seconds <= pause.gap_start_seconds and pause.gap_end_seconds <= end_seconds
        ),
    )
