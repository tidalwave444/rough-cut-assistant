"""False starts inside a take: the stumble in the middle of a line, and only that.

A line's clip runs from its first matched word to its last, so an abandoned attempt
sitting between the two plays in the cut. The words inside a take that the line does
not account for are two opposite things wearing the same clothes, and only one of them
may be removed: a **stumble**, which must go, and a word the transcriber **misheard**,
which was spoken perfectly well and whose removal deletes real speech. "It did not
match the line, so it is junk" is the obvious rule and it is wrong.

Two signals separate them, neither of them a threshold.

A **repeated word** marks a false start: an unmatched word that reads as a word of the
line spoken elsewhere in that take, before it or after it. The speaker said the word,
abandoned the sentence and said it again, so the stretch between the two utterances is
what they threw away — and the second utterance is the one that survives.

That test alone is not safe, because it fires just as readily on "a" and on "the", and
each of those removals eats several of the line's own words. **Coverage guards it**:
the surviving words are read against the line again, and a removal that leaves the
line holding fewer of its own words than before is refused. No threshold separates the
two halves of that judgement — the line either keeps all of its words or it does not.

**Words with nothing left opposite them** come out too, and need no guard: a
mishearing always has the script word it displaced sitting opposite it, so a run in a
place where the line has already been fully accounted for cannot be the line said
wrong. Everything else stays whole.

Every removal is quoted in full in the report, on the same reasoning as a removed
off-script region: nothing else records that it was ever spoken.

Only the take that plays is examined. An alternate is there to be auditioned and
dragged into the cut rather than used as it stands, so nothing is taken out of one.
"""

from dataclasses import dataclass

from roughcut.align import matched_pairs
from roughcut.pauses import Cut
from roughcut.script import ScriptLine
from roughcut.takes import Take
from roughcut.tokens import Transcript, tokenize


REPEATED = '"{word}" said twice'
UNACCOUNTED = "nothing of the line opposite it"


@dataclass(frozen=True)
class FalseStart:
    """One stretch taken out from inside a take, and why it went.

    The fault is the judgement; what was said is quoted beside it because the report
    is the only record a removed stretch ever existed, and a person who does not know
    it existed cannot go looking for it.
    """

    line: ScriptLine
    cut: Cut
    text: str
    """What was said across it, in the transcriber's own words."""
    fault: str
    """What removed it — a word said twice, or nothing of the line left opposite it."""

    @property
    def start_seconds(self) -> float:
        return self.cut.start_seconds

    @property
    def end_seconds(self) -> float:
        return self.cut.end_seconds

    @property
    def duration_seconds(self) -> float:
        return self.cut.seconds


def false_starts(take: Take, heard: Transcript) -> list[FalseStart]:
    """Everything inside this reading that the line did not mean to say."""
    return _Reader(take, heard).removals()


@dataclass(frozen=True)
class _Candidate:
    """A run of the take proposed for removal, before coverage has had its say."""

    first: int
    """Where the run begins, counted in transcript tokens."""
    last: int
    """Where it ends, inclusive."""
    fault: str

    @property
    def taken(self) -> set[int]:
        """The tokens this removal would take out."""
        return set(range(self.first, self.last + 1))


class _Reader:
    """One take read against the line it says and the transcript it was heard in."""

    def __init__(self, take: Take, heard: Transcript) -> None:
        self._take = take
        self._heard = heard
        self._first = take.matched[0].token
        self._last = take.matched[-1].token
        self._offsets = {word.token: word.offset for word in take.matched}
        self._line = tokenize(take.line.text)

    def removals(self) -> list[FalseStart]:
        """What comes out, in the order it was spoken.

        Coverage is asked of everything taken out so far and not of one candidate at a
        time, because a removal changes how the rest of the take reads against the
        line: the word a stumble displaced is only recovered once the stumble is gone.
        """
        taken: set[int] = set()
        removals = []
        for candidate in self._candidates():
            cut = self._cut(candidate)
            if cut is None or candidate.taken & taken:
                continue
            if not self._still_holds(taken | candidate.taken):
                continue
            taken |= candidate.taken
            removals.append(
                FalseStart(
                    line=self._take.line,
                    cut=cut,
                    text=self._heard.said_between(candidate.first, candidate.last),
                    fault=candidate.fault,
                )
            )
        return removals

    def _candidates(self) -> list[_Candidate]:
        """Everything either signal proposes, in the order it was spoken.

        A repeat is proposed before a run standing in the same place is, so that where
        both signals name the same stretch it is the repeat that names it: that is the
        stronger claim, since it says which word the speaker went back to.
        """
        return sorted(
            self._repeats() + self._unaccounted(), key=lambda found: (found.first, found.last)
        )

    def _repeats(self) -> list[_Candidate]:
        """Every unmatched word that reads as a word of the line said elsewhere in it.

        Both directions, and the nearest utterance in each: a speaker who stumbles
        goes back to the word they just said or forward to the one they are about to,
        not to the same word four sentences away.
        """
        words = set(self._line)
        found = []
        for token in self._unmatched():
            text = self._heard.texts[token]
            if text not in words:
                continue
            for other in self._nearest_saying(text, token):
                found.append(
                    _Candidate(
                        min(token, other), max(token, other) - 1, REPEATED.format(word=text)
                    )
                )
        return found

    def _unaccounted(self) -> list[_Candidate]:
        """Every run of unmatched words with no word of the line left opposite it."""
        return [
            _Candidate(first, last, UNACCOUNTED)
            for first, last in self._runs()
            if self._offsets[last + 1] == self._offsets[first - 1] + 1
        ]

    def _unmatched(self) -> list[int]:
        """The tokens inside this take that the line does not account for."""
        return [
            token
            for token in range(self._first, self._last + 1)
            if token not in self._offsets
        ]

    def _runs(self) -> list[tuple[int, int]]:
        """Those tokens grouped into runs, each named by its ends — both inclusive.

        Every run is interior: a take begins and ends on a word the line accounts for,
        so a run always has a matched word on either side of it to be read against.
        """
        runs: list[tuple[int, int]] = []
        for token in self._unmatched():
            if runs and token == runs[-1][1] + 1:
                runs[-1] = (runs[-1][0], token)
            else:
                runs.append((token, token))
        return runs

    def _nearest_saying(self, text: str, token: int) -> list[int]:
        """The nearest word of this take either side of `token` that says the same."""
        said = [
            other
            for other in range(self._first, self._last + 1)
            if other != token and self._heard.texts[other] == text
        ]
        before = [other for other in said if other < token]
        after = [other for other in said if other > token]
        return [*before[-1:], *after[:1]]

    def _still_holds(self, taken: set[int]) -> bool:
        """Whether the line keeps all of its own words once these tokens are gone.

        Both sides of that comparison are counted the same way — the words left,
        read against the line — so the judgement cannot be quietly loosened or
        tightened by how the alignment reached its own figure. It is the alignment's
        figure on both recordings to hand, on every take of both of them; it is the
        truer of the two where they ever differ, since a take realigned on its own is
        exactly the question being asked here.
        """
        return self._holds(taken) >= self._holds(set())

    def _holds(self, taken: set[int]) -> int:
        """How many of the line's words this take still says once these are gone."""
        survivors = [
            self._heard.texts[token]
            for token in range(self._first, self._last + 1)
            if token not in taken
        ]
        return len(matched_pairs(survivors, self._line))

    def _cut(self, candidate: _Candidate) -> Cut | None:
        """When this run was spoken: from its first word to the one that follows it.

        Bounded by where the next word *starts* rather than by where the transcriber
        declared this one to end, so that nothing is left of a stumble between the two
        — the transcriber runs a word on over whatever follows it (ADR-0001), and the
        word that follows is the one the cut is being made to reach. There is always
        one: a run ends before the word it was found by, and a take ends on a word the
        line accounts for.

        None where the two ends meet, which is a run inside a single spoken word — a
        number the transcriber wrote once and the script reads as several. There is no
        stretch of recording there to take out.
        """
        start = self._heard.start_of(candidate.first)
        end = self._heard.start_of(candidate.last + 1)
        return Cut(start, end) if end > start else None
