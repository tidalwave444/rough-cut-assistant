"""Take selection: which reading of a line reaches the cut, and why the rest did not.

**The last complete take wins.** The rule is the recording behaviour rather than a
score: a person re-records a line until they are satisfied and then stops, so recency
carries the strongest signal there is — and it is the only signal that *selects*.

Scoring never promotes a take. It only disqualifies one, and selection then falls back
to the take before it, and so on. When every take is disqualified the least bad plays
and the line is flagged, because a cut missing a line is worse than a cut holding a
poor reading of it that the report names.

A weighted multi-signal score was rejected for v1: with no labelled data the weights
would be invented, and a wrong choice would be unexplainable. Everything decided here
is explainable in one sentence — "take 2 of 3; take 3 truncated" — because that
sentence is what the report prints.

The thresholds below are provisional. The recordings this was built against hold few
genuine retakes, so they are tuned against synthetic fixtures and should be expected
to move once a longer, messier recording exists.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from roughcut.script import ScriptLine

# How much of a line a take has to hold before it counts as a complete reading of it.
# Not 1.0: a transcriber drops the occasional word, and disqualifying every take of
# every line would make the veto meaningless.
COMPLETE_COVERAGE = 0.85

# How many of a line's closing words a take may leave unsaid before it is truncated.
# One is a word the transcriber dropped; more than one is a reading that stopped. Flat
# rather than scaled with the line: on both recordings to hand every take either reaches
# the last word or stops five short, so a proportional allowance would decide nothing.
TOLERATED_UNREAD_TOKENS = 1

# Ums and uhs a take may hold and still stand. Two is a person thinking; more is a
# reading worth passing over while a cleaner one exists.
DISFLUENCY_LIMIT = 2

DISFLUENCIES = frozenset(
    {"um", "umm", "uhm", "uh", "uhh", "erm", "er", "ah", "eh", "hm", "hmm", "mm", "mmm"}
)
"""What a stumble sounds like once normalised. Deliberately a short, closed list:
a word wrongly on it silently disqualifies good takes."""

PASSED_OVER = "a later take was also complete"


@dataclass(frozen=True)
class Matched:
    """One word of the line, and the transcript token it was heard as.

    The way back from a reading to the recording it was heard in. It is what says
    which of the words inside a take the line accounts for — and therefore which of
    them it does not, which is the whole of what a false start is found by.
    """

    token: int
    """Where the word sits in the transcript this reading was aligned against."""
    offset: int
    """Which word of the line it was heard as, counting from 0."""


@dataclass(frozen=True)
class Take:
    """One reading of a script line, as the recording holds it.

    Everything here is a fact about what was heard — which of the line's words it
    held, where it stopped, how many stumbles are in it. What those facts *mean* is
    decided below, so that the judgement lives in one place and can be re-tuned there.
    """

    line: ScriptLine
    number: int
    """Which attempt this was, counting from 1 in the order they were recorded."""
    start_seconds: float
    end_seconds: float
    token_seconds: tuple[float, ...]
    """When each of the line's tokens was reached — how a beat becomes a time."""
    tokens: int
    """How many words the line has to say."""
    matched: tuple[Matched, ...]
    """Every word of the line this reading was heard to say, in the order heard."""
    disfluencies: int
    """How many ums and uhs were heard inside it."""

    @property
    def name(self) -> str:
        """How a marker names this reading: its line, and which attempt it was."""
        return f"Line {self.line.number} take {self.number}"

    @property
    def heard_tokens(self) -> int:
        """How many of the line's words this reading was heard to say."""
        return len(self.matched)

    @property
    def unread_at_end(self) -> int:
        """How many of the line's closing words this reading never reached."""
        return self.tokens - 1 - max((word.offset for word in self.matched), default=-1)

    @property
    def coverage(self) -> float:
        """How much of the line this reading holds, from 0 to 1."""
        return self.heard_tokens / self.tokens if self.tokens else 0.0

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds

    def time_of_token(self, offset: int) -> float:
        """When the reading had got as far as its `offset`-th token."""
        if not self.token_seconds:
            return self.start_seconds
        return self.token_seconds[min(max(offset, 0), len(self.token_seconds) - 1)]


@dataclass(frozen=True)
class Decision:
    """One take and what became of it.

    The fault is the judgement; the reason is that judgement written as the words a
    marker comment and the report's outcome column both carry.
    """

    take: Take
    selected: bool
    fault: str | None
    """What disqualified this take, or None if nothing did."""
    reason: str


@dataclass(frozen=True)
class Chosen:
    """Every take of one line, which of them plays, and why the others do not."""

    decisions: list[Decision]
    """In the order recorded, so take numbers and rows read the same way."""
    flagged: bool
    """Whether every take was disqualified and the least bad had to do."""

    @property
    def selected(self) -> Decision:
        return next(decision for decision in self.decisions if decision.selected)

    @property
    def take(self) -> Take:
        """The reading that plays."""
        return self.selected.take

    @property
    def alternates(self) -> list[Decision]:
        """The readings that lost, in the order recorded."""
        return [decision for decision in self.decisions if not decision.selected]

    @property
    def summary(self) -> str:
        """Why this line's cut is what it is, in one sentence.

        Only the takes disqualified by a fault of their own are named. A take that
        lost merely by being earlier than the winner needs no explaining — that is the
        rule itself — so naming it would bury the one thing the sentence is for.
        """
        of = f"take {self.take.number} of {len(self.decisions)}"
        if self.flagged:
            return f"{of}, the least bad — every take was disqualified"
        faulted = [
            decision
            for decision in self.decisions
            if decision.fault is not None and not decision.selected
        ]
        return "; ".join(
            [of, *(f"take {decision.take.number} {decision.fault}" for decision in faulted)]
        )


def choose(takes: Sequence[Take]) -> Chosen:
    """Pick the take that plays: the most recent one nothing disqualifies."""
    if not takes:
        raise ValueError("A line with no takes has nothing to choose between")

    faults = {take.number: _fault(take) for take in takes}
    standing = [take for take in takes if faults[take.number] is None]
    flagged = not standing
    winner = standing[-1] if standing else _least_bad(takes)
    return Chosen(
        decisions=[
            _decision(take, faults[take.number], take is winner, flagged) for take in takes
        ],
        flagged=flagged,
    )


def disfluencies_in(tokens: Iterable[str]) -> int:
    """How many of these normalised tokens are stumbles rather than words."""
    return sum(1 for token in tokens if token in DISFLUENCIES)


def _fault(take: Take) -> str | None:
    """What disqualifies this take, or None if nothing does.

    Truncation is tested before coverage even though a truncated take is usually short
    of coverage too: "stopped four words early" says what happened, where "eight of
    twelve words" leaves the reader to work out whether the missing four were the end.
    """
    if take.unread_at_end > TOLERATED_UNREAD_TOKENS:
        return f"truncated — stopped {take.unread_at_end} words short"
    if take.coverage < COMPLETE_COVERAGE:
        return f"incomplete — {take.heard_tokens} of {take.tokens} words"
    if take.disfluencies > DISFLUENCY_LIMIT:
        return f"disfluent — {take.disfluencies} ums and uhs"
    return None


def _least_bad(takes: Sequence[Take]) -> Take:
    """Of takes that all fail, the one holding most of the line.

    Coverage first because a line half said is the fault that shows; then the fewest
    stumbles; then the most recent, so the tie-break is the rule that selects anyway.
    """
    return max(takes, key=lambda take: (take.coverage, -take.disfluencies, take.number))


def _decision(take: Take, fault: str | None, selected: bool, flagged: bool) -> Decision:
    return Decision(
        take=take, selected=selected, fault=fault, reason=_outcome(fault, selected, flagged)
    )


def _outcome(fault: str | None, selected: bool, flagged: bool) -> str:
    if selected:
        return f"selected as the least bad — {fault}" if flagged and fault else "selected"
    return fault or PASSED_OVER
