"""Where every splice lands: a cut that holds the sound and nothing either side of it.

Each piece of the recording that plays arrives here bounded by word timestamps, and
leaves bounded by the audio, in two steps. First it is trimmed to where its own sound
begins and ends, because the transcriber will run a word over the quiet that follows
it and a take begins where sound begins. Then both ends are widened by a pad, because
a word-end timestamp lands where the word stops being *recognisable*, which is earlier
than it stops being *audible*: a final consonant fades below the threshold and a cut
placed on the timestamp lands on top of it.

The two are one decision made in that order, and only in that order — a pad measured
from an untrimmed boundary and a trim would be moving the same in-point against each
other. Trimmed first, the pad is a small step back into quiet from a boundary that is
already right, and a splice sounds like a join rather than a word cut short.

This is the mirror of a pause cut and asks the audio the same question. Collapsing a
pause holds the cut **inside** the corroborated quiet; padding a splice extends a clip
**into** it. Both are bounded by the same fact — where the detector says the room went
quiet — which is also why the two are separate settings: one number meaning both could
be tuned for neither.

The pad crosses whatever the transcriber stopped short of and stops at the far edge of
the quiet beside it. A gap the detector heard no quiet in gets no pad on that side:
something was audible there, and the something might be a mutter nobody kept.

Word timestamps bound nothing here, which is decision 0001 applied to the other direction.
On real transcripts almost every word butts straight up against the next, so the quiet
between two lines sits *underneath* the words rather than between them; a pad that
stopped at the neighbouring word's declared edge would be refused everywhere it is
needed. What a pad may never cross is the other rail:

- Where two pieces that both play have a gap between them, neither may reach past the
  middle of it. A gap wide enough for only one pad is shared rather than double-claimed,
  so no moment of the recording is ever laid down twice — and two pieces the transcript
  butts together have no gap at all, so neither grows.

Two things this deliberately does not do, both of them decision 0001's reasoning again.

It does not require the pad to *reach* the quiet. The stretch between a word's declared
end and the start of the detected quiet is the fading consonant itself — 0.19 s, 0.28 s
and 0.63 s at the three real splices in `sequence.mp4` — so a pad that had to land in
silence to be allowed would be refused at every one of them, which is the fault this
exists to fix. The cost is the other side of the same coin: where the sound beside a
clip belongs to something the cut dropped rather than to its own word, up to a pad's
width of it plays. The pad is small because that is the bound on how wrong it can be.

And it pads the head and tail of a take, having just trimmed them — which decision 0001 says
of pause collapsing it must not: "a take begins where sound begins", so quiet there is
removed in full rather than collapsed to a floor. That still holds. The trim is what
removes it in full; a floor is a beat held between two words and nothing here restores
one. A pad is the same hundredths decision 0001 already keeps around every cut it makes,
the same reason.

A splice is not always between two spans. Taking a stumble out of the middle of a take
opens one inside it, and its two edges are word timestamps like any other, so they are
placed here too — `bounded_by_sound` at the bottom, which is the same two steps read
against what lies either side of a removal rather than either side of a gap.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from roughcut.analysis import Silence
from roughcut.pauses import Cut

# Long enough for a final consonant to play out, short enough that it disappears under
# any gap a person leaves between two attempts. Its own number rather than the pause
# pad's: that one holds a cut inside the quiet and this one extends a clip into it, so
# a value that suits one is the wrong direction for the other.
DEFAULT_PADDING_SECONDS = 0.15

THE_RECORDING_BEGINS = 0.0
"""How far back the first thing that plays may reach: there is no recording before it."""


@dataclass(frozen=True)
class SpliceSettings:
    """How much of the quiet either side of a splice the cut keeps."""

    padding_seconds: float = DEFAULT_PADDING_SECONDS


@dataclass(frozen=True)
class Span:
    """A stretch of the recording that plays: a take, or a kept off-script region."""

    start_seconds: float
    end_seconds: float


def trimmed_to_sound(spans: Sequence[Span], silences: Sequence[Silence]) -> list[Span]:
    """Every span begun where its sound begins and ended where its sound stops.

    A take begins where sound begins (decision 0001), so quiet at the head or the tail of
    one comes out in full rather than collapsing to a floor — a floor is a beat held
    between two words, and the outside of a splice is not that. Where the transcriber
    declared a word to start before the room stopped being quiet, a span therefore
    begins inside that word's declared span.

    This runs before `widen` rather than after, so that the trim and the pad do not
    move the same in-point in opposite directions: the pad is a small step back into
    quiet, taken from a boundary that is already right.
    """
    return [_trimmed(span, silences) for span in spans]


def _trimmed(span: Span, silences: Sequence[Silence]) -> Span:
    """One span with the quiet at either end of it taken off.

    Both ends are held inside the span they came from, so a stretch the detector heard
    as quiet from end to end shrinks to nothing rather than turning inside out.
    """
    start = min(_quiet_runs_until(span.start_seconds, silences), span.end_seconds)
    return Span(start, max(_quiet_set_in_at(span.end_seconds, silences), start))


def _quiet_runs_until(moment: float, silences: Sequence[Silence]) -> float:
    """Where the quiet covering this moment runs out — the moment itself if none does.

    Quiet that begins exactly on the moment counts, since that is the transcriber and
    the detector agreeing about where a take's silence starts; quiet that ends there
    does not, since the sound is already back.
    """
    return max(
        (
            silence.end_seconds
            for silence in silences
            if silence.start_seconds <= moment < silence.end_seconds
        ),
        default=moment,
    )


def _quiet_set_in_at(moment: float, silences: Sequence[Silence]) -> float:
    """Where the quiet covering this moment set in — the moment itself if none does."""
    return min(
        (
            silence.start_seconds
            for silence in silences
            if silence.start_seconds < moment <= silence.end_seconds
        ),
        default=moment,
    )


def widen(
    spans: Sequence[Span],
    silences: Sequence[Silence],
    recording_seconds: float,
    settings: SpliceSettings = SpliceSettings(),
) -> list[Span]:
    """Every span padded into the quiet either side of it, in the order given.

    All of them together rather than one at a time: what a span may claim depends on
    what plays next to it in the recording, which the span alone does not know. The
    recording's own length is the last wall — the piece that plays out the end of it
    has nothing beyond to grow into.
    """
    order = sorted(range(len(spans)), key=lambda index: spans[index].start_seconds)
    widened = list(spans)
    for place, index in enumerate(order):
        before = spans[order[place - 1]] if place else None
        after = spans[order[place + 1]] if place + 1 < len(order) else None
        widened[index] = _widened(
            spans[index], before, after, silences, recording_seconds, settings
        )
    return widened


def _widened(
    span: Span,
    before: Span | None,
    after: Span | None,
    silences: Sequence[Silence],
    recording_seconds: float,
    settings: SpliceSettings,
) -> Span:
    """One span grown into its own half of the gaps either side of it."""
    return Span(
        start_seconds=_padded_start(span, before, silences, settings.padding_seconds),
        end_seconds=_padded_end(
            span, after, silences, recording_seconds, settings.padding_seconds
        ),
    )


def _padded_start(
    span: Span, before: Span | None, silences: Sequence[Silence], padding: float
) -> float:
    """How early this span may begin: the pad, or as far back as the quiet runs."""
    floor = _shared(before.end_seconds, span.start_seconds) if before else THE_RECORDING_BEGINS
    return _grown_back(span.start_seconds, floor, silences, padding)


def _padded_end(
    span: Span,
    after: Span | None,
    silences: Sequence[Silence],
    recording_seconds: float,
    padding: float,
) -> float:
    """How late this span may end: the pad, or as far on as the quiet runs."""
    ceiling = _shared(span.end_seconds, after.start_seconds) if after else recording_seconds
    return _grown_forward(span.end_seconds, ceiling, silences, padding)


def _grown_back(start: float, floor: float, silences: Sequence[Silence], padding: float) -> float:
    """A boundary stepped back into the quiet behind it, no further than the floor."""
    quiet = _quiet_before(floor, start, silences)
    if quiet is None:
        return start
    return min(start, max(start - padding, quiet))


def _grown_forward(
    end: float, ceiling: float, silences: Sequence[Silence], padding: float
) -> float:
    """A boundary stepped on into the quiet ahead of it, no further than the ceiling."""
    quiet = _quiet_after(end, ceiling, silences)
    if quiet is None:
        return end
    return max(end, min(end + padding, quiet))


def bounded_by_sound(
    cut: Cut,
    silences: Sequence[Silence],
    settings: SpliceSettings = SpliceSettings(),
) -> Cut:
    """A removal's two edges placed where every other splice's are.

    A removal is a gap the cut opens in the middle of a take, so its two edges are the
    tail of one piece that plays and the head of the next — and they arrive here as
    word timestamps, which say nothing about where the sound is (decision 0001). Each
    is therefore trimmed to the sound and then padded back, the same two steps in the
    same order as every span above.

    The quiet an edge may move into is the quiet the removal does not itself reach
    into. A stretch the removal runs through is already the removal's: it comes out
    whole, and an edge stepping further into it would be two rules cutting the same
    piece of recording between them. Every other stretch the detector heard is offered,
    whatever the pause rule would do with it — the bar sits at a beat, so a rule handed
    only the quiet no pause claims is handed nothing at all and can never fire.

    Each pad therefore only steps back into the quiet its own trim moved it out of, and
    an edge already sitting on sound does not move at all. Neither may cross the word
    timestamp it started from: beyond that lies the removed speech, and a pad that
    reached it would play the stumble again on one side or the other.

    Which bounds how much of the fault this answers. The head is reachable: the quiet a
    removal ends *in* lies outside it, so that edge trims to the far side of the quiet
    and pads back, and the word after the splice arrives on time. The tail is not. The
    word before a removal goes on sounding after the transcriber stops recognising it,
    and the stretch it fades into is quiet the removal itself reaches into — which the
    rail above will not let an edge move through. Ticket 17 holds that finding.
    """
    padding = settings.padding_seconds
    beside = _outside(cut, silences)
    trimmed_tail = _quiet_set_in_at(cut.start_seconds, beside)
    trimmed_head = _quiet_runs_until(cut.end_seconds, beside)
    tail_ends = _grown_forward(trimmed_tail, cut.start_seconds, beside, padding)
    head_begins = (
        max(cut.end_seconds, trimmed_head - padding)
        if trimmed_head > cut.end_seconds
        else cut.end_seconds
    )
    return Cut(min(tail_ends, head_begins), head_begins)


def _outside(cut: Cut, silences: Sequence[Silence]) -> list[Silence]:
    """The quiet lying against this removal rather than inside it.

    Quiet a removal reaches into comes out with the removal, so an edge has nothing to
    find there: it would only be moving through a stretch that has already gone. What is
    left is the quiet waiting on either side of the removal — the fading tail of the word
    before it, and the run-up to the word after — which is where both edges belong.
    """
    return [
        silence
        for silence in silences
        if silence.start_seconds >= cut.end_seconds or silence.end_seconds <= cut.start_seconds
    ]


def _shared(start: float, end: float) -> float:
    """The middle of a gap two pieces both reach into: as far as either one may come."""
    return (start + end) / 2


def _quiet_before(gap_start: float, gap_end: float, silences: Sequence[Silence]) -> float | None:
    """How far back the last quiet in this gap runs, or None if the gap holds none.

    The last one, because it is the one the piece after the gap grows back into. What
    was heard between that quiet and the first word — the attack of a consonant the
    transcriber declared later than it began — is what the pad is for, so the pad
    crosses it. What lies on the far side of the quiet is some other sound, and a pad
    that reached it would play something nobody chose to keep.
    """
    quiet = _overlapping(gap_start, gap_end, silences)
    if not quiet:
        return None
    return max(max(quiet, key=lambda silence: silence.start_seconds).start_seconds, gap_start)


def _quiet_after(gap_start: float, gap_end: float, silences: Sequence[Silence]) -> float | None:
    """How far on the first quiet in this gap runs, or None if the gap holds none.

    The first one, for the reason its mirror above takes the last: it is the quiet the
    piece before the gap grows forward into, and the sound on the far side of it is
    some other sound.
    """
    quiet = _overlapping(gap_start, gap_end, silences)
    if not quiet:
        return None
    return min(min(quiet, key=lambda silence: silence.start_seconds).end_seconds, gap_end)


def _overlapping(
    gap_start: float, gap_end: float, silences: Sequence[Silence]
) -> list[Silence]:
    """Every stretch the detector heard as quiet that reaches into this gap."""
    return [
        silence
        for silence in silences
        if silence.start_seconds < gap_end and silence.end_seconds > gap_start
    ]
