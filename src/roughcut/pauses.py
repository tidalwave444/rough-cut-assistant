"""Pause collapsing: a cut as tight as the room actually was.

A long stretch of quiet is *shortened, never closed*. That is a product decision rather
than an implementation shortcut: a read with every pause removed sounds machine-gunned,
and putting the pacing back afterwards means re-trimming every edit point by hand — far
more work than trimming a little further.

Where the quiet is, is the detector's question and not the transcriber's. A pause is a
detected silence region, and the words are not consulted at all: the transcriber leaves
almost no gap between two words, stretching a word over the pause that follows it
instead, so the quiet sits *underneath* the words rather than between them. A cut may
therefore fall inside a word's declared span — see decision 0001, which is also why the pad
below matters: it is what keeps a collapse off audible sound, since the word claiming
that time no longer says anything about where sound is.

Quiet at the head or the tail of a stretch that plays is not collapsed but removed in
full. A floor is a beat held between two words, which is not what sits on the outside
of a splice. That is `splice.py`'s to do, because it decides where a clip's edges land
and this decides what comes out from between them.

A collapsed pause is not the only thing that comes out from between them: a stumble
inside a take does too (`stumbles.py`). What is taken out and why are that module's
business, but what a cut *does* — shorten the stretch and pull everything after it
earlier — is one piece of arithmetic, and `Tightened` below is where both of them meet
it. A moment covered by a pause and a removal at once is still only removed once.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from roughcut.analysis import Silence

# The longest quiet that reads as a beat inside a line rather than as a blank section.
# One bar, and both defaults below are it: the listen of 28 August on `Sequence 07`
# heard 0.30 s as a hole and passed over 0.15 s, so anything longer than this is
# shortened, and what it is shortened to is this same length. Anything longer left
# behind would be the fault the listen reported, only shorter.
#
# That listen is the evidence decision 0003 named and it went the other way to the one
# 0003 expected — not breathless, still loose. 0003 still states 0.7 s and 0.3 s in its
# text, so it trails this and a person has to bring it forward.
A_BEAT_AT_MOST_SECONDS = 0.2

# Above a beat, the quiet is worth an edit point; at or under it, the read is left
# alone. Below the bar the cut has nothing to gain and a splice to pay for.
DEFAULT_THRESHOLD_SECONDS = A_BEAT_AT_MOST_SECONDS

# What a shortened pause becomes. A beat, not nothing.
DEFAULT_FLOOR_SECONDS = A_BEAT_AT_MOST_SECONDS

# Kept either side of every cut, inside the silence. A word's first consonant starts
# below the detector's threshold, so a cut placed at the edge of the quiet clips it.
# The floor keeps more than this and so is what usually decides where the cut falls:
# the pad is the rail underneath, and it binds only where the floor is set below twice
# it — a cut that centres in the quiet is already half a floor from either edge.
DEFAULT_PADDING_SECONDS = 0.05


@dataclass(frozen=True)
class PauseSettings:
    """How tight the cut is: what counts as a long pause, and what it becomes."""

    threshold_seconds: float = DEFAULT_THRESHOLD_SECONDS
    floor_seconds: float = DEFAULT_FLOOR_SECONDS
    padding_seconds: float = DEFAULT_PADDING_SECONDS


@dataclass(frozen=True)
class Cut:
    """A stretch of something that plays, taken out from the middle of it.

    A collapsed pause gives one up, and so does a stumble removed from inside a
    take. What is taken out and why differ entirely; what it does to the timeline does
    not, so a tightened stretch reasons about the two together.
    """

    start_seconds: float
    end_seconds: float

    @property
    def seconds(self) -> float:
        return self.end_seconds - self.start_seconds


@dataclass(frozen=True)
class Pause:
    """A stretch of quiet, and the piece of it the cut takes out.

    What is left of the quiet is the floor, or twice the pad where that is longer —
    the pad being the rail that stops a collapse reaching the edge of the region and
    the sound waiting on the other side of it.
    """

    quiet_start_seconds: float
    quiet_end_seconds: float
    cut_start_seconds: float
    cut_end_seconds: float

    @property
    def cut(self) -> Cut:
        """The piece of the recording this pause gives up."""
        return Cut(self.cut_start_seconds, self.cut_end_seconds)

    @property
    def quiet_seconds(self) -> float:
        return self.quiet_end_seconds - self.quiet_start_seconds

    @property
    def removed_seconds(self) -> float:
        return self.cut.seconds

    @property
    def remaining_seconds(self) -> float:
        """How long the quiet still lasts in the cut — the floor, or more."""
        return self.quiet_seconds - self.removed_seconds


def pauses_to_shorten(
    silences: Sequence[Silence],
    settings: PauseSettings = PauseSettings(),
) -> list[Pause]:
    """Every stretch of quiet in this recording long enough to be worth an edit point.

    Every region of the whole recording, including the dead air between attempts: what
    survives to be collapsed is decided later, by which of them fall inside a stretch
    the cut plays. Dead air between two takes needs no collapsing, because the splice
    removes the whole of it.
    """
    found = (_shortened(silence, settings) for silence in silences)
    return [pause for pause in found if pause is not None]


def _shortened(silence: Silence, settings: PauseSettings) -> Pause | None:
    """What this stretch of quiet gives up, or None if it keeps all of it.

    The cut is centred, so what is left sits half either side of the splice: the beat
    is held where it was heard rather than shunted to one end of the region. Which is
    also why the pad rarely decides anything — half the floor is already more than a
    pad — so it is written as the second of two bars rather than as an inset.
    """
    quiet = silence.end_seconds - silence.start_seconds
    if quiet <= settings.threshold_seconds:
        return None
    stays = max(settings.floor_seconds, 2 * settings.padding_seconds)
    removed = quiet - stays
    if removed <= 0:
        return None
    middle = (silence.start_seconds + silence.end_seconds) / 2
    return Pause(
        quiet_start_seconds=silence.start_seconds,
        quiet_end_seconds=silence.end_seconds,
        cut_start_seconds=middle - removed / 2,
        cut_end_seconds=middle + removed / 2,
    )


@dataclass(frozen=True)
class Segment:
    """A piece of the recording that survives the shortening, and so reaches a clip."""

    start_seconds: float
    end_seconds: float


@dataclass(frozen=True)
class Tightened:
    """A stretch of the recording with everything the cut takes out of it gone.

    The long pauses inside it, shortened to a floor, and whatever else was removed
    from the middle of it — an abandoned attempt at the line.

    Everything after a cut plays earlier than it was recorded, so this is also the map
    from a moment in the source to where that moment lands on the timeline — which is
    what keeps a marker on the words it names.
    """

    start_seconds: float
    end_seconds: float
    pauses: tuple[Pause, ...] = ()
    """The quiet inside this stretch that was shortened rather than left as recorded."""
    removed: tuple[Cut, ...] = ()
    """What else came out of the middle of it — an abandoned attempt at the line."""

    @property
    def cuts(self) -> list[Cut]:
        """Everything this stretch gives up, in order and never twice over.

        Merged rather than listed, because a pause and a removal can cover the same
        moment — a stumble the speaker paused in the middle of — and a second of the
        recording removed by both is still only a second.
        """
        taken = [*(pause.cut for pause in self.pauses), *self.removed]
        return _merged(sorted(taken, key=lambda cut: cut.start_seconds))

    @property
    def duration_seconds(self) -> float:
        """How long the stretch runs once everything cut out of it is gone."""
        return self.end_seconds - self.start_seconds - sum(cut.seconds for cut in self.cuts)

    @property
    def segments(self) -> list[Segment]:
        """The pieces of source that survive, in order — one more than the cuts."""
        edges = [self.start_seconds]
        for cut in self.cuts:
            edges += [cut.start_seconds, cut.end_seconds]
        edges.append(self.end_seconds)
        return [Segment(edges[index], edges[index + 1]) for index in range(0, len(edges), 2)]

    def offset_of(self, source_seconds: float) -> float:
        """Where a moment of the source falls, measured from the start of the stretch.

        A moment inside a cut lands on the splice rather than in the hole where the
        removed piece used to be, so nothing is ever placed at a time that no longer
        exists. A moment outside the stretch altogether lands on the nearer end of it,
        for the same reason: a stretch begins where sound begins, which can be later
        than the transcriber declared its first word to start.
        """
        offset = source_seconds - self.start_seconds
        for cut in self.cuts:
            if source_seconds >= cut.end_seconds:
                offset -= cut.seconds
            elif source_seconds > cut.start_seconds:
                offset -= source_seconds - cut.start_seconds
        return min(max(offset, 0.0), self.duration_seconds)


def _merged(cuts: Sequence[Cut]) -> list[Cut]:
    """Cuts in order, with any that overlap or meet joined into one."""
    merged: list[Cut] = []
    for cut in cuts:
        if merged and cut.start_seconds <= merged[-1].end_seconds:
            merged[-1] = Cut(
                merged[-1].start_seconds, max(merged[-1].end_seconds, cut.end_seconds)
            )
        else:
            merged.append(cut)
    return merged


def tighten(
    start_seconds: float,
    end_seconds: float,
    pauses: Sequence[Pause],
    removed: Sequence[Cut] = (),
) -> Tightened:
    """The stretch between two times, minus the pauses and removals inside it.

    A pause straddling the ends belongs to the dead air between two stretches, which
    the splice removes in full — there is nothing left of it to collapse.

    A pause a removal reaches into is dropped on the same reasoning: the removal owns
    that stretch, and what is left of the quiet is against a splice rather than
    between two words, which is not what a floor is held for. Dropping it wherever the
    two so much as touch, rather than only where the removal swallows the quiet whole,
    keeps the report honest — a pause and a removal that both claim the same second
    would otherwise each report having taken it, while the cut takes it once. The cost
    is a long pause beside a small removal going uncollapsed, which is a quiet cut
    slightly loose rather than a cut described wrongly.
    """
    inside = tuple(
        cut
        for cut in (_held(cut, start_seconds, end_seconds) for cut in removed)
        if cut is not None
    )
    return Tightened(
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        pauses=tuple(
            pause
            for pause in pauses
            if start_seconds <= pause.quiet_start_seconds
            and pause.quiet_end_seconds <= end_seconds
            and not _reached_by(pause, inside)
        ),
        removed=inside,
    )


def _held(cut: Cut, start_seconds: float, end_seconds: float) -> Cut | None:
    """A cut bounded by the stretch it is taken from, or None if none of it is left."""
    held = Cut(max(cut.start_seconds, start_seconds), min(cut.end_seconds, end_seconds))
    return held if held.seconds > 0 else None


def _reached_by(pause: Pause, removed: Sequence[Cut]) -> bool:
    """Whether a removal has taken any of this pause's quiet with it."""
    return any(
        cut.start_seconds < pause.quiet_end_seconds
        and pause.quiet_start_seconds < cut.end_seconds
        for cut in removed
    )
