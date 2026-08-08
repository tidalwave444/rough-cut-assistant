"""Off-script material: what becomes of speech no script line accounts for.

A restart has to go and an unplanned sentence you meant has to stay, and nothing here
can tell the two apart with certainty. So the rule is deliberately asymmetric: a region
goes only when something positively says it should, and **everything else is kept in
place and marked**.

The asymmetry is the whole design. Deleting a kept line in Premiere is one keystroke;
recovering a deleted one requires knowing it existed — which is precisely what a person
who has stopped recording no longer does. A cut that leaves a mutter in costs a
keystroke. A cut that eats the one line you improvised and meant costs the recording.

Three things say a region should go, in the order they are asked:

- **It is too short to be a sentence.** Half a second of speech between two lines is a
  mutter, not an idea. This is the rule that removes almost everything.
- **It is a failed restart.** Not "it reads like the line beside it" — an attempt
  abandoned four words in holds a fifth of the line — but "everything in it is that
  line's own words". Containment, not coverage; `align` measures it.
- **It is on the stop-phrase list.** The list is the user's, because "sorry, again" is
  a restart in one person's recording and a sentence in another's.

The built-in list is short and holds only phrases that say "start over" outright.
Anything vaguer — a bare "sorry", a "wait" — is left off deliberately: it appears
inside sentences people mean, and a default that eats those is the failure this module
is shaped to avoid. Add them per-recording if your own restarts sound like that.

Nothing is destroyed either way. The XML references the source by in and out points,
so a removed region is still in the recording, and the report names every one of them.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from roughcut.align import Leftover
from roughcut.tokens import tokenize

# How long a region has to run before it is treated as something that was meant. Below
# this it is a mutter or a fragment of a restart. Provisional, like every threshold
# here: it is tuned against synthetic fixtures and a recording with few retakes.
DEFAULT_KEEP_SECONDS = 2.5

# How much of what was said has to be an adjacent line's own words before the region is
# an abandoned attempt at that line rather than something else. Not 1.0: a restart
# usually carries a stray word — the "so" or the "okay" it was launched with.
DEFAULT_RESTART_LIKENESS = 0.8

DEFAULT_STOP_PHRASES = (
    "let me try that again",
    "let me try again",
    "let me do that again",
    "one more time",
    "from the top",
    "scratch that",
    "take two",
)
"""Phrases that say "start over" outright, and nothing vaguer than that."""

KEPT = "kept — marked in place"


@dataclass(frozen=True)
class OffScriptSettings:
    """What the cut removes without asking. Everything else it keeps and marks."""

    keep_seconds: float = DEFAULT_KEEP_SECONDS
    restart_likeness: float = DEFAULT_RESTART_LIKENESS
    stop_phrases: tuple[str, ...] = DEFAULT_STOP_PHRASES


@dataclass(frozen=True)
class OffScript:
    """One region of speech off the script, and what the cut does with it.

    The fault is the judgement; the reason is that judgement written as the words the
    report's outcome column carries — the same split `takes` makes over a take, for the
    same reason: one place decides, and the wording of the decision lives beside it.
    """

    leftover: Leftover
    fault: str | None
    """What removed this region, or None if nothing did."""
    reason: str

    @property
    def kept(self) -> bool:
        """Whether the region plays in the cut, marked, rather than being removed."""
        return self.fault is None

    @property
    def start_seconds(self) -> float:
        return self.leftover.start_seconds

    @property
    def end_seconds(self) -> float:
        return self.leftover.end_seconds

    @property
    def duration_seconds(self) -> float:
        return self.leftover.duration_seconds

    @property
    def text(self) -> str:
        """What was said, in the transcriber's own words."""
        return self.leftover.text


def judge(
    leftovers: Sequence[Leftover], settings: OffScriptSettings = OffScriptSettings()
) -> list[OffScript]:
    """Decide what becomes of every region the script does not account for."""
    return [_judged(leftover, settings) for leftover in leftovers]


def _judged(leftover: Leftover, settings: OffScriptSettings) -> OffScript:
    fault = _fault(leftover, settings)
    return OffScript(
        leftover=leftover, fault=fault, reason=KEPT if fault is None else f"cut — {fault}"
    )


def _fault(leftover: Leftover, settings: OffScriptSettings) -> str | None:
    """What removes this region, or None — which is the answer that keeps it.

    Length is asked first because it is what removes nearly everything, and because a
    fragment short enough to be a mutter is one whichever line it half-echoes.
    """
    if leftover.duration_seconds < settings.keep_seconds:
        return f"a fragment, under {settings.keep_seconds:g} s"
    if leftover.nearest is not None and leftover.likeness >= settings.restart_likeness:
        return f"a restart of line {leftover.nearest.number}"
    said = tokenize(leftover.text)
    for phrase in settings.stop_phrases:
        if _contains(said, tokenize(phrase)):
            return f'a stop phrase, "{phrase}"'
    return None


def _contains(said: list[str], phrase: list[str]) -> bool:
    """Whether a stop phrase was said, as its own run of words.

    Compared as tokens rather than as text so that a phrase matches however the
    transcriber punctuated it — which is the same reason everything else in the tool
    compares tokens.
    """
    if not phrase:
        return False
    return any(
        said[start : start + len(phrase)] == phrase
        for start in range(len(said) - len(phrase) + 1)
    )
