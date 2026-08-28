"""The plan: the complete set of cut decisions, in seconds.

A plan says what the cut *is* — which pieces of the source play in what order, and
what the markers say — without knowing anything about the output format. Times are
seconds as floats throughout; conversion to frames happens only in the renderer.
"""

from dataclasses import dataclass, field

from roughcut.align import SpokenLine, align
from roughcut.analysis import Analysis, SourceMedia
from roughcut.stumbles import Stumble, stumbles
from roughcut.offscript import OffScript, OffScriptSettings, judge
from roughcut.pauses import Pause, PauseSettings, Tightened, pauses_to_shorten, tighten
from roughcut.script import ScriptLine, beats
from roughcut.splice import Span, SpliceSettings, trimmed_to_sound, widen
from roughcut.takes import Chosen, Take, choose
from roughcut.tokens import Transcript

ROUGH_CUT = "RoughCut"
ALTERNATES = "RoughCut_Alternates"

OFF_SCRIPT = "Off-script"
"""What a marker over kept off-script material is called on the timeline."""

BEFORE_EVERY_LINE = -1
"""Where an off-script region said before the first located line belongs."""


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
    """One script line: which reading of it plays, and where it now sits.

    The clips beside it say the same thing in timeline terms; this says it in script
    terms, which is what a person reading the report wants to know. A line reaches the
    timeline in one piece unless a pause inside it was shortened, which splits it.
    """

    line: ScriptLine
    chosen: Chosen
    """Every reading of the line that was found, and which of them won."""
    tightened: Tightened
    """The stretch the chosen take was read in, with its long pauses shortened."""
    timeline_start_seconds: float
    removed: tuple[Stumble, ...] = ()
    """The abandoned attempts taken out from inside the reading that plays."""

    @property
    def take(self) -> Take:
        """The reading that plays."""
        return self.chosen.take

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
class PlacedOffScript:
    """One kept off-script region: what was said, and where it now sits.

    It plays between the same two lines it was said between, which is what "in place"
    means once the cut is assembled in the order the script is written rather than in
    the order it was recorded.
    """

    off_script: OffScript
    tightened: Tightened
    """The stretch it was said in, with its long pauses shortened."""
    timeline_start_seconds: float

    def timeline_of(self, source_seconds: float) -> float:
        """Where a moment of the stretch it was said in lands on the timeline."""
        return self.timeline_start_seconds + self.tightened.offset_of(source_seconds)


Placed = PlacedLine | PlacedOffScript
"""Anything the rough cut plays, in the order it plays: lines, and what was kept between them."""


@dataclass(frozen=True)
class Plan:
    """Everything one import should produce — the rough cut and its alternates."""

    sequences: list[Sequence] = field(default_factory=list)
    lines: list[PlacedLine] = field(default_factory=list)
    """The script lines that made it into the cut, in script order."""
    missing: list[ScriptLine] = field(default_factory=list)
    """The lines the recording does not contain, skipped rather than fabricated."""
    off_script: list[OffScript] = field(default_factory=list)
    """Everything said that no line accounts for, kept or cut, in the order recorded."""
    shortened: list[Pause] = field(default_factory=list)
    """The pauses the cut took time out of, in the order they were recorded."""
    removed: list[Stumble] = field(default_factory=list)
    """The stumbles cut out from inside a take, in the order they were recorded."""

    @property
    def flagged(self) -> list[PlacedLine]:
        """The lines whose every take was disqualified — the ones worth re-recording."""
        return [line for line in self.lines if line.chosen.flagged]

    @property
    def kept(self) -> list[OffScript]:
        """The off-script regions the cut plays rather than removes."""
        return [region for region in self.off_script if region.kept]

    @property
    def cut(self) -> list[OffScript]:
        """The off-script regions the cut removes — restarts, mutters, stop phrases."""
        return [region for region in self.off_script if not region.kept]


def build_plan(
    analysis: Analysis,
    script: list[ScriptLine],
    pauses: PauseSettings = PauseSettings(),
    off_script: OffScriptSettings = OffScriptSettings(),
    splice: SpliceSettings = SpliceSettings(),
) -> Plan:
    """Decide the cut: one clip per script line, spliced in the order they are written.

    Each line plays from its last complete reading, and a marker sits at its start
    carrying its text — so scrubbing the timeline says which visual belongs where. A
    line the recording does not contain is skipped and reported; the cut is still
    usable without it.

    The dead air between lines goes entirely, because nothing splices it back in, and
    so does the quiet at either end of a stretch that plays: it begins where sound
    begins. A long stretch of quiet *inside* a line is shortened to a floor instead —
    it is speech the cut keeps, and a read with no pauses left in it is a read nobody
    wants.

    An attempt abandoned in the middle of a line comes out of it, because the clip runs
    from the line's first word to its last and the stumble between them would otherwise
    play. Only that: a word the transcriber misheard was spoken perfectly well and
    stays where it was said.

    Speech no line accounts for goes only where something says it should — it is short,
    or it is an abandoned attempt at the line beside it, or it is on the stop-phrase
    list. Anything else stays where it was said with a marker on it, because a line you
    improvised and meant must never disappear without your seeing it.

    Everything that plays is widened into the quiet either side of it before it becomes
    a clip, because a word goes on sounding after the transcriber has stopped
    recognising it and a splice on the timestamp lands on top of the last consonant.

    Every reading the cut passed over is laid end to end in a second sequence beside
    it, so that overruling a choice takes seconds. It is always emitted, even when
    nothing lost: one import gives both sequences, and an alternates timeline that is
    there and empty says "nothing was rejected" where a missing one says nothing.
    """
    alignment = align(analysis.words, script)
    regions = judge(alignment.leftovers, off_script)
    ordered = _in_order(
        [(line, choose(line.takes)) for line in alignment.spoken],
        [region for region in regions if region.kept],
    )
    placed = _placed(
        ordered,
        widen(
            trimmed_to_sound([_span_of(item) for item in ordered], analysis.silences),
            analysis.silences,
            analysis.source.duration_seconds,
            splice,
        ),
        pauses_to_shorten(analysis.silences, pauses),
        alignment.heard,
    )
    lines = [item for item in placed if isinstance(item, PlacedLine)]
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
                        timeline_start_seconds=item.timeline_of(segment.start_seconds),
                    )
                    for item in placed
                    for segment in item.tightened.segments
                ],
                markers=[marker for item in placed for marker in _markers(item)],
            ),
            _alternates_sequence(lines, analysis.source),
        ],
        lines=lines,
        missing=alignment.missing,
        off_script=regions,
        shortened=sorted(
            (pause for item in placed for pause in item.tightened.pauses),
            key=lambda pause: pause.quiet_start_seconds,
        ),
        removed=sorted(
            (removal for line in lines for removal in line.removed),
            key=lambda removal: removal.start_seconds,
        ),
    )


_Reading = tuple[SpokenLine, Chosen]
"""One script line and the decision about which reading of it plays."""


def _placed(
    ordered: list[_Reading | OffScript],
    spans: list[Span],
    pauses: list[Pause],
    heard: Transcript,
) -> list[Placed]:
    """Lay the cut out: each piece on the end of the last, in the order it plays.

    The spans are what each piece takes from the recording once it has been trimmed to
    where its sound begins and padded back, so they are what the pauses are then taken
    out of and what the timeline is measured from — both of those are part of the cut
    and not flourishes added to it afterwards.

    A line gives up one more thing than an aside does: the stumble in the middle of it.
    Nothing off the script can be read against a line to find one, and there is no line
    there whose words would be lost by looking.
    """
    placed: list[Placed] = []
    timeline = 0.0
    for item, span in zip(ordered, spans, strict=True):
        if isinstance(item, OffScript):
            tightened = tighten(span.start_seconds, span.end_seconds, pauses)
            placed.append(
                PlacedOffScript(
                    off_script=item,
                    tightened=tightened,
                    timeline_start_seconds=timeline,
                )
            )
        else:
            line, chosen = item
            removed = tuple(stumbles(chosen.take, heard))
            tightened = tighten(
                span.start_seconds,
                span.end_seconds,
                pauses,
                [removal.cut for removal in removed],
            )
            placed.append(
                PlacedLine(
                    line=line.line,
                    chosen=chosen,
                    tightened=tightened,
                    timeline_start_seconds=timeline,
                    removed=removed,
                )
            )
        timeline += tightened.duration_seconds
    return placed


def _span_of(item: _Reading | OffScript) -> Span:
    """The stretch of the recording a piece was spoken in, before any padding."""
    if isinstance(item, OffScript):
        return Span(item.start_seconds, item.end_seconds)
    _, chosen = item
    return Span(chosen.take.start_seconds, chosen.take.end_seconds)


def _in_order(readings: list[_Reading], kept: list[OffScript]) -> list[_Reading | OffScript]:
    """The script in written order, each kept region after the line it followed.

    The cut is assembled in script order, so "in place" cannot mean "at the time it was
    said" — it means between the same two lines it was said between. A region therefore
    follows the last line read before it, which is where a listener would expect it and
    is stable however far out of order the session was recorded.
    """
    after: dict[int, list[OffScript]] = {}
    for region in kept:
        after.setdefault(_line_before(readings, region), []).append(region)
    ordered: list[_Reading | OffScript] = list(after.get(BEFORE_EVERY_LINE, []))
    for index, reading in enumerate(readings):
        ordered.append(reading)
        ordered.extend(after.get(index, []))
    return ordered


def _line_before(readings: list[_Reading], region: OffScript) -> int:
    """Which line this region follows: the last one heard before it began.

    Every reading of every line counts, not only the one that plays. A retake is
    usually introduced by a mutter, so a region said between two attempts at a line
    belongs after that line — where using the chosen take alone would put it before,
    because the reading that won is the one on the far side of it.

    Compared by when a reading began rather than by where its line sits in the script,
    so a session recorded out of order still puts a region after whatever was actually
    said last before it.
    """
    heard = [
        (take.start_seconds, index)
        for index, (line, _) in enumerate(readings)
        for take in line.takes
        if take.start_seconds < region.start_seconds
    ]
    return max(heard, default=(0.0, BEFORE_EVERY_LINE))[1]


def _alternates_sequence(placed: list[PlacedLine], source: SourceMedia) -> Sequence:
    """The readings that lost, butt-spliced in script order and each one marked.

    Untightened and unpadded: an alternate is there to be auditioned and dragged into
    the cut, not to be used as it stands, so it plays exactly as it was recorded.
    """
    clips = []
    markers = []
    timeline = 0.0
    for line in placed:
        for decision in line.chosen.alternates:
            take = decision.take
            clips.append(
                Clip(
                    source_in_seconds=take.start_seconds,
                    source_out_seconds=take.end_seconds,
                    timeline_start_seconds=timeline,
                )
            )
            markers.append(
                Marker(
                    name=take.name,
                    comment=decision.reason,
                    timeline_position_seconds=timeline,
                )
            )
            timeline += take.duration_seconds
    return Sequence(
        id="sequence-2", name=ALTERNATES, source=source, clips=clips, markers=markers
    )


def _markers(placed: Placed) -> list[Marker]:
    """What the timeline says about this piece of it.

    A line says which line it is; a kept off-script region says that is what it is and
    quotes it, so that the one thing a person has to decide about — whether they meant
    it — is legible from the timeline without replaying the audio.
    """
    if isinstance(placed, PlacedOffScript):
        return [Marker(OFF_SCRIPT, placed.off_script.text, placed.timeline_start_seconds)]
    return _line_markers(placed)


def _line_markers(placed: PlacedLine) -> list[Marker]:
    """One marker per beat of the line, at the moment that beat was reached.

    Named for the line so the timeline reads in script terms, and numbered within it
    when the line enumerates — `Line 6.2` is the second item of the sixth line.
    """
    found = beats(placed.line)
    return [
        Marker(
            name=_marker_name(placed.line.number, index, len(found)),
            comment=beat.text,
            timeline_position_seconds=placed.timeline_of(
                placed.take.time_of_token(beat.token_offset)
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


def alternates(plan: Plan) -> Sequence:
    """The sequence holding the readings the cut passed over."""
    for sequence in plan.sequences:
        if sequence.name == ALTERNATES:
            return sequence
    raise ValueError(f"This plan has no {ALTERNATES} sequence")


def timeline_duration_seconds(sequence: Sequence) -> float:
    """How long the cut runs — the end of its last clip on the timeline."""
    return max(
        (
            clip.timeline_start_seconds + (clip.source_out_seconds - clip.source_in_seconds)
            for clip in sequence.clips
        ),
        default=0.0,
    )
