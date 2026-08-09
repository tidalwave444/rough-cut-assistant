"""Alignment: which stretch of the recording is which script line.

Two passes, and the order of them is the whole design.

The **spine** comes first: a longest-matching-block alignment of the whole transcript
against the whole script, which is monotonic and therefore says where the good read of
each line sits without any span competing globally. Repeated phrases cannot steal each
other's matches, because a match can only ever move forward through both texts.

Only then are the **leftovers** — the speech the spine did not claim — scored, and only
against the script lines neighbouring them. A leftover that reads like a located line
is another take of it. A leftover that reads like a line the spine could not place *is*
that line: a pickup recorded out of order is invisible to a monotonic spine, and this
is where it is recovered. Anything else is off-script material.

Alignment finds every reading of every line and measures each of them; it does not
choose between them. What the measurements mean, and which reading therefore plays,
belongs to `takes`. The same division holds for what is left over: alignment measures
how much of a leftover is an adjacent line's own words, and `offscript` decides whether
that makes it a restart worth removing.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from roughcut.analysis import Word
from roughcut.script import ScriptLine
from roughcut.takes import Matched, Take, disfluencies_in
from roughcut.tokens import Transcript, tokenize

# How much of a line has to be heard in one stretch before that stretch counts as a
# reading of it. Below this it is a coincidence — a "the" and an "and" in common.
MINIMUM_COVERAGE = 0.5

# How much of a line a leftover has to contain before it is called another take of it
# rather than something else that was said. Higher than the spine's bar: a leftover
# is judged against a line the spine already had its pick of.
RETAKE_COVERAGE = 0.6

# The shortest run of unheard words that separates two readings of a line rather than
# sitting inside one. A stumble mid-sentence is a few words; a restart is most of the
# line again, which is why the real bar scales with the line.
SPAN_GAP_TOKENS = 4


@dataclass(frozen=True)
class SpokenLine:
    """A script line located in the recording: every reading of it that was found."""

    line: ScriptLine
    takes: list[Take]
    """In the order recorded, which is the order take selection reasons about."""


@dataclass(frozen=True)
class Leftover:
    """Speech no script line accounts for: material off the script."""

    start_seconds: float
    end_seconds: float
    text: str
    nearest: ScriptLine | None = None
    """The adjacent script line this most reads like, if it reads like one at all."""
    likeness: float = 0.0
    """How much of what was said here is that line's own words, in order.

    Containment, not coverage — the measurement the other way up. An attempt abandoned
    four words into a twenty-word line holds a fifth of the line and would be nobody's
    reading of it, but everything it said *was* the line, which is what an abandoned
    attempt sounds like. Measuring that belongs here, beside the token streams; what it
    means for a leftover belongs to `offscript`.
    """

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


@dataclass(frozen=True)
class Alignment:
    """Where every script line went, and what was said that no line accounts for."""

    spoken: list[SpokenLine]
    """The located lines, in script order — which is not always the order spoken."""
    missing: list[ScriptLine]
    leftovers: list[Leftover]
    heard: Transcript
    """The recording as tokens, which is what every take's matches index into.

    Carried out of the alignment rather than reduced again downstream: a take says
    which of the transcript's words it was heard to say, and those positions mean
    nothing without the stream they were counted in.
    """


def align(words: Sequence[Word], script: Sequence[ScriptLine]) -> Alignment:
    """Locate every script line in a transcript, and label what is left over."""
    return _Aligner(words, script).run()


@dataclass(frozen=True)
class _Run:
    """A stretch of transcript tokens, named by its ends — both inclusive."""

    first: int
    last: int

    def outside(self, span: "_Span") -> list["_Run"]:
        """What is left of this run once a span of it is taken away."""
        return [
            _Run(first, last)
            for first, last in ((self.first, span.first - 1), (span.last + 1, self.last))
            if first <= last
        ]


@dataclass(frozen=True)
class _Span:
    """A run of matched tokens: transcript position paired with position in a line."""

    pairs: list[tuple[int, int]]

    @property
    def first(self) -> int:
        return self.pairs[0][0]

    @property
    def last(self) -> int:
        return self.pairs[-1][0]

    def covers(self, tokens: int) -> float:
        return len(self.pairs) / tokens if tokens else 0.0


@dataclass(frozen=True)
class _Match:
    """A leftover read as one script line, and how much of that line it holds."""

    line: ScriptLine
    span: _Span
    coverage: float


class _Aligner:
    """One alignment in progress: the two passes, sharing the token streams."""

    def __init__(self, words: Sequence[Word], script: Sequence[ScriptLine]) -> None:
        self._script = list(script)
        self._heard = Transcript.of(words)
        self._tokens = {line.number: tokenize(line.text) for line in self._script}
        self._takes: dict[int, list[_Span]] = {}

    def run(self) -> Alignment:
        self._takes = self._spine()
        leftovers = self._label(self._unclaimed())
        return Alignment(
            spoken=[
                self._spoken_line(line) for line in self._script if line.number in self._takes
            ],
            missing=[line for line in self._script if line.number not in self._takes],
            leftovers=sorted(leftovers, key=lambda leftover: leftover.start_seconds),
            heard=self._heard,
        )

    def _spine(self) -> dict[int, list[_Span]]:
        """The monotonic reading of the script: every span of it that reads as a line.

        A line read twice has its matches scattered across both attempts, so the spans
        are split apart before they are judged — otherwise a line's region would run
        from the first attempt to the last and swallow every reading in between.
        """
        matched = self._matched_by_line()
        located = {}
        for line in self._script:
            tokens = len(self._tokens[line.number])
            spans = [
                span
                for span in _split(matched[line.number], _gap_for(tokens))
                if span.covers(tokens) >= MINIMUM_COVERAGE
            ]
            if spans:
                located[line.number] = spans
        return located

    def _matched_by_line(self) -> dict[int, list[tuple[int, int]]]:
        """Every transcript token the script accounts for, grouped by its line."""
        script_tokens: list[str] = []
        owner: list[ScriptLine] = []
        offset: list[int] = []
        for line in self._script:
            for index, token in enumerate(self._tokens[line.number]):
                script_tokens.append(token)
                owner.append(line)
                offset.append(index)

        matched: dict[int, list[tuple[int, int]]] = {line.number: [] for line in self._script}
        for heard, script_index in matched_pairs(self._heard.texts, script_tokens):
            matched[owner[script_index].number].append((heard, offset[script_index]))
        return matched

    def _unclaimed(self) -> list[_Run]:
        """The runs of transcript tokens no line's take covers, in the order heard."""
        claimed = sorted(
            (span.first, span.last) for spans in self._takes.values() for span in spans
        )
        runs = []
        cursor = 0
        for first, last in claimed:
            if first > cursor:
                runs.append(_Run(cursor, first - 1))
            cursor = max(cursor, last + 1)
        if cursor <= len(self._heard) - 1:
            runs.append(_Run(cursor, len(self._heard) - 1))
        return runs

    def _label(self, runs: list[_Run]) -> list[Leftover]:
        """Take every leftover that reads as a script line; call the rest off-script.

        A leftover reading as a line the spine already placed is another take of it,
        and one reading a line the spine could not place *is* that line — which is what
        puts a pickup recorded out of order back in its written place. Either way only
        the part of the run that reads as the line is taken: whatever was said either
        side of it goes back on the pile and is labelled in its own right, because a
        retake is usually introduced by a mutter and nothing said may vanish unreported.
        """
        leftovers = []
        pending = list(reversed(runs))
        while pending:
            run = pending.pop()
            match = self._best_match(run)
            if match is not None:
                self._takes.setdefault(match.line.number, []).append(match.span)
                pending.extend(reversed(run.outside(match.span)))
                continue
            leftovers.append(self._leftover(run))
        return leftovers

    def _leftover(self, run: _Run) -> Leftover:
        """What was said across a run no line claimed, and what it most reads like."""
        nearest, likeness = self._likeness(run)
        return Leftover(
            start_seconds=self._heard.start_of(run.first),
            end_seconds=self._heard.end_of(run.last),
            text=self._heard.said_between(run.first, run.last),
            nearest=nearest,
            likeness=likeness,
        )

    def _likeness(self, run: _Run) -> tuple[ScriptLine | None, float]:
        """Which line beside this run it most reads like, and how much of it is that line.

        The same matcher the retake pass used, with the fraction taken the other way
        up: not how much of the line was said, but how much of what was said is the
        line. That is the reading a run has already failed to be a take of, so it is
        the only reading left that can name it.

        Only the lines the run sits *between* are asked — not, as the retake pass also
        asks, every line the spine placed nowhere. A line picked up at the far end of
        the session is worth recovering wherever it turns up, but a fragment that
        happens to echo a line written minutes away is not an attempt at it, and this
        measurement only ever removes material.
        """
        heard = self._heard.texts[run.first : run.last + 1]
        if not heard:
            return None, 0.0
        nearest: ScriptLine | None = None
        likeness = 0.0
        for line in self._between(run.first):
            share = len(matched_pairs(heard, self._tokens[line.number])) / len(heard)
            if share > likeness:
                nearest, likeness = line, share
        return nearest, likeness

    def _best_match(self, run: _Run) -> _Match | None:
        """The line this leftover reads as, if it reads as one at all.

        The lines it sits between are asked first. Only if it reads like none of them
        is the rest of the script asked, because a line re-recorded at the end of the
        session sits nowhere near where it is written — and calling that off-script
        would throw away the take the writer went back for.
        """
        heard = self._heard.texts[run.first : run.last + 1]
        return self._closest(heard, run, self._neighbours(run.first)) or self._closest(
            heard, run, self._script
        )

    def _closest(
        self, heard: list[str], run: _Run, candidates: list[ScriptLine]
    ) -> _Match | None:
        """Whichever candidate this leftover contains most of, if it contains enough."""
        best: _Match | None = None
        for line in candidates:
            tokens = self._tokens[line.number]
            pairs = matched_pairs(heard, tokens, offset=run.first)
            if not pairs:
                continue
            span = _Span(pairs)
            coverage = span.covers(len(tokens))
            if coverage >= RETAKE_COVERAGE and (best is None or coverage > best.coverage):
                best = _Match(line, span, coverage)
        return best

    def _neighbours(self, first: int) -> list[ScriptLine]:
        """The lines a leftover could be a take of: the ones it sits between, and any
        line the spine placed nowhere at all.

        A located line can only be repeated near where it sits, but a line that was
        never found could have been picked up anywhere in the recording — most likely
        at the end, which is nowhere near where it is written.
        """
        between = {line.number for line in self._between(first)}
        return [
            line
            for line in self._script
            if line.number in between or line.number not in self._takes
        ]

    def _between(self, first: int) -> list[ScriptLine]:
        """The lines a run sits between: the ones located either side of it in the
        recording, and everything written between those two."""
        numbers = [line.number for line in self._script]
        if not numbers:
            return []
        before = [
            number
            for number, spans in self._takes.items()
            if max(span.last for span in spans) < first
        ]
        after = [
            number
            for number, spans in self._takes.items()
            if min(span.first for span in spans) > first
        ]
        low = max(before, default=min(numbers))
        high = min(after, default=max(numbers))
        return [
            line for line in self._script if min(low, high) <= line.number <= max(low, high)
        ]

    def _spoken_line(self, line: ScriptLine) -> SpokenLine:
        """Every reading of one line, numbered in the order it was recorded."""
        spans = sorted(self._takes[line.number], key=lambda span: span.first)
        return SpokenLine(
            line=line,
            takes=[
                self._take(line, number, span)
                for number, span in enumerate(spans, start=1)
            ],
        )

    def _take(self, line: ScriptLine, number: int, span: _Span) -> Take:
        """One reading, measured — what it held, where it stopped, how it stumbled."""
        tokens = len(self._tokens[line.number])
        end = self._heard.end_of(span.last)
        return Take(
            line=line,
            number=number,
            start_seconds=self._heard.start_of(span.first),
            end_seconds=end,
            token_seconds=self._token_seconds(span, tokens, end),
            tokens=tokens,
            matched=tuple(Matched(token, offset) for token, offset in span.pairs),
            disfluencies=disfluencies_in(self._heard.texts[span.first : span.last + 1]),
        )

    def _token_seconds(self, span: _Span, tokens: int, end: float) -> tuple[float, ...]:
        """When the reading reached each of the line's tokens.

        A token that was never matched — misheard, or swallowed — takes the time of
        the next one that was, so a marker is never placed before its words.
        """
        times = []
        cursor = 0
        for index in range(tokens):
            while cursor < len(span.pairs) and span.pairs[cursor][1] < index:
                cursor += 1
            reached = cursor < len(span.pairs)
            times.append(self._heard.start_of(span.pairs[cursor][0]) if reached else end)
        return tuple(times)


def matched_pairs(
    heard: Sequence[str], written: Sequence[str], *, offset: int = 0
) -> list[tuple[int, int]]:
    """Every token two streams say in common, as a pair of positions, one in each.

    The one measurement this module is built on, exposed because deciding what may be
    taken out of a take asks it too: how much of a line a reading holds is the same
    question before and after a stretch of that reading is dropped.

    Monotonic, so a match can only ever move forward through both streams and a
    repeated phrase cannot steal an earlier one's match.

    `autojunk` off: it discards any element appearing in more than 1% of a sequence
    longer than 200, which over a transcript means "the", "a", "we" — the connective
    tissue that holds a sentence match together.
    """
    matcher = SequenceMatcher(None, list(heard), list(written), autojunk=False)
    return [
        (offset + block.a + step, block.b + step)
        for block in matcher.get_matching_blocks()
        for step in range(block.size)
    ]


def _gap_for(tokens: int) -> int:
    """How many unheard words separate two readings of a line of this length."""
    return max(SPAN_GAP_TOKENS, tokens // 2)


def _split(pairs: list[tuple[int, int]], gap: int) -> list[_Span]:
    """Break a line's matches wherever too much unheard speech sits between them."""
    spans: list[list[tuple[int, int]]] = []
    for pair in pairs:
        if spans and pair[0] - spans[-1][-1][0] - 1 <= gap:
            spans[-1].append(pair)
        else:
            spans.append([pair])
    return [_Span(span) for span in spans]
