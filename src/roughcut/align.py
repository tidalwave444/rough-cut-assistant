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
belongs to `takes`. The same division holds for what is left over: alignment names the
adjacent line a leftover most reads like, and `offscript` measures how much of it is
attempts at that line and decides whether that makes it a restart worth removing.
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
#
# Length is not the whole of it, and cannot be: how long a run is, is how well the
# transcriber heard the attempt buried in it, and that is the one thing this question
# may not turn on. What the length is read against is `_one_reading` below.
SPAN_GAP_TOKENS = 4

# Letters a transcriber trades for one another, each group heard as one sound. Every
# vowel together, and the consonants both recordings are actually caught confusing:
# `wipe` for `vibe` trades w for v and p for b, `coating` for `coding` trades t for d.
# Spelling on its own cannot do this. `wipe` and `vibe` differ in two letters of four —
# exactly as `part` differs from `card` — so no measure that reads letters as letters
# can call one pair the same word and the other two words.
SAME_SOUND = ("aeiouy", "bfpvw", "dt")

# How much of the longer word's sound the two have to hold in common, in order, before
# one reads as the other misheard. Heard this way `wipe` for `vibe` and `rail` for `real`
# hold all four of four and `coating` for `coding` six of seven, where `white` for `vibe`
# holds three of five and stays a word the line does not account for. A threshold, so a
# listen moves it and not a distribution (decision 0003).
A_NEAR_MISS_SHARES_AT_LEAST = 0.7

# No word shorter than this is ever a near miss, however it sounds. `to` against `too`
# is the whole of one word inside the other and they are different words; there has to
# be enough of a word for the measure above to be saying anything about it.
SHORTEST_NEAR_MISS_LETTERS = 4


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
    """The adjacent script line this most reads like, if it reads like one at all.

    Naming it is as far as alignment goes. How much of what was said here is that
    line's own words — containment, the measurement decision 0007 turns the other way
    up — is asked by `offscript`, which owns the bar that answer is read against and
    therefore the only place it can be taken at the right grain.
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
                for span in _split(matched[line.number], tokens)
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
        return Leftover(
            start_seconds=self._heard.start_of(run.first),
            end_seconds=self._heard.end_of(run.last),
            text=self._heard.said_between(run.first, run.last),
            nearest=self._nearest(run),
        )

    def _nearest(self, run: _Run) -> ScriptLine | None:
        """Which line beside this run it most reads like, if it reads like one at all.

        Naming the line is alignment's half of the question decision 0007 settles;
        `offscript` measures how much of the run is that line and decides. The two are
        split because the measurement is read against a bar the user can move, and a
        bar cannot reach in here without dragging every off-script setting with it.

        The neighbour is picked on one pass of the same matcher the retake pass used —
        enough to say which line is even in the running, which is all a name has to do.

        Only the lines the run sits *between* are asked — not, as the retake pass also
        asks, every line the spine placed nowhere. A line picked up at the far end of
        the session is worth recovering wherever it turns up, but a fragment that
        happens to echo a line written minutes away is not an attempt at it, and this
        measurement only ever removes material.
        """
        heard = self._heard.texts[run.first : run.last + 1]
        if not heard:
            return None
        nearest: ScriptLine | None = None
        best = 0.0
        for line in self._between(run.first):
            share = len(matched_pairs(heard, self._tokens[line.number])) / len(heard)
            if share > best:
                nearest, best = line, share
        return nearest

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

    Two words the transcriber heard a hair apart are the same word, and the near misses
    below are how that is said. They are found only between two words the streams
    already agree on, so nothing they add can displace an exact match.
    """
    said = _said_the_same(heard, written)
    found = sorted(said + _near_misses(heard, written, said))
    return [(offset + token, index) for token, index in found]


def _said_the_same(heard: Sequence[str], written: Sequence[str]) -> list[tuple[int, int]]:
    """Every position at which the two streams hold exactly the same word.

    `autojunk` off: it discards any element appearing in more than 1% of a sequence
    longer than 200, which over a transcript means "the", "a", "we" — the connective
    tissue that holds a sentence match together.
    """
    matcher = SequenceMatcher(None, list(heard), list(written), autojunk=False)
    return [
        (block.a + step, block.b + step)
        for block in matcher.get_matching_blocks()
        for step in range(block.size)
    ]


def _near_misses(
    heard: Sequence[str], written: Sequence[str], said_the_same: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Every word the transcriber heard wrong, paired with the word it displaced.

    A mishearing is identified structurally, by the script word sitting opposite it
    (decision 0002), and what is read against what, between two words the streams agree
    on, is settled by `_facing` below.
    """
    found: list[tuple[int, int]] = []
    for before, after in zip(said_the_same, said_the_same[1:]):
        found += _facing(
            heard, written, range(before[0] + 1, after[0]), range(before[1] + 1, after[1])
        )
    return found


def _facing(
    heard: Sequence[str], written: Sequence[str], left_over: range, facing: range
) -> list[tuple[int, int]]:
    """Which of two stretches of unmatched words stand opposite each other, and match.

    "Opposite" cannot mean position for position: a stretch usually holds a word one
    side does not account for at all — `with a wipe coating` for `with vibe coding`,
    where the `a` is the transcriber's own — and reading position for position stops
    at that word and leaves `vibe` unfound. Whether an intruder is stepped over is not
    the mishearing's business; exact matching steps over one and goes on, and this does
    the same, one grain further out.

    So the pairing is the longest run of near misses that moves forward through both
    stretches at once, exactly as the exact match does, with whatever neither side
    accounts for left unpaired. A stretch that is an abandoned attempt rather than a
    mishearing still pairs nothing: what makes it one is that its words are not the
    line's words, and no monotonic pairing can make them so.
    """
    left = list(left_over)
    right = list(facing)
    empty: list[tuple[int, int]] = []
    best = [[empty for _ in range(len(right) + 1)] for _ in range(len(left) + 1)]
    for row in reversed(range(len(left))):
        for column in reversed(range(len(right))):
            token, index = left[row], right[column]
            stepped_over = max(best[row + 1][column], best[row][column + 1], key=len)
            paired = (
                [(token, index)] + best[row + 1][column + 1]
                if _a_near_miss(heard[token], written[index])
                else []
            )
            best[row][column] = max(paired, stepped_over, key=len)
    return best[0][0]


def _a_near_miss(heard: str, written: str) -> bool:
    """Whether one word is the other misheard — the same word, heard a hair off.

    Measured as how much of the longer word's sound the two hold in common, in order:
    coverage read at the grain of a word, and read the same way round as everywhere
    else — how much of the one the other accounts for.
    """
    if min(len(heard), len(written)) < SHORTEST_NEAR_MISS_LETTERS:
        return heard == written
    shared = _letters_in_common(_as_sounds(heard), _as_sounds(written))
    return shared / max(len(heard), len(written)) >= A_NEAR_MISS_SHARES_AT_LEAST


def _as_sounds(word: str) -> str:
    """A word with every letter written as the sound it is one of the spellings of."""
    return "".join(
        next((group[0] for group in SAME_SOUND if letter in group), letter) for letter in word
    )


def _letters_in_common(one: str, other: str) -> int:
    """How many letters two words hold in common, in order though not side by side.

    The measurement this module is built on, one grain down: the same matcher, run over
    letters rather than over words. A mishearing lands in the middle of a word as often
    as at either end — `coating` for `coding` — so it has to be able to step over a
    letter and go on counting, which is exactly what it does over a word.
    """
    matcher = SequenceMatcher(None, one, other)
    return sum(block.size for block in matcher.get_matching_blocks())


def _gap_for(tokens: int) -> int:
    """How much unheard speech says two readings of a line of this length, not one."""
    return max(SPAN_GAP_TOKENS, tokens // 2)


def _split(pairs: list[tuple[int, int]], tokens: int) -> list[_Span]:
    """Break a line's matches wherever a reading of it was left behind."""
    spans: list[list[tuple[int, int]]] = []
    for pair in pairs:
        if spans and _one_reading(spans[-1][-1], pair, tokens):
            spans[-1].append(pair)
        else:
            spans.append([pair])
    return [_Span(span) for span in spans]


def _one_reading(before: tuple[int, int], after: tuple[int, int], tokens: int) -> bool:
    """Whether one reading of the line runs from one of its matches on to the next.

    A short run of unheard words between them is a stumble inside a reading, and the
    bar above says how short. What a count of them cannot see is which of the *line's*
    own words sit either side of the run: a reading that goes on to the very next word
    of the line did not stop and start again, however much was said in between.

    That is what `Sequence 07` line 1 needed. It reads `…with a wipe coating / oh no
    white coating one no no / part two`, and the seven words in the middle are one
    abandoned attempt written down more fully than the four the same attempt was
    written as before the transcriber was asked again. Nothing about the recording
    changed, so nothing about where the reading ends may change either — and no count
    that admits seven words of it can refuse a restart, which is nine.

    Bounded by the line all the same, because two matches can also be far apart with
    nothing of any line between them. An attempt abandoned mid-line is at most the line
    said over again; longer than that and what sits between is not something said in
    the middle of a reading, whatever the line does across it.
    """
    unheard = after[0] - before[0] - 1
    if unheard <= _gap_for(tokens):
        return True
    return after[1] == before[1] + 1 and unheard <= tokens
