"""Normalisation: reducing a script and a transcript to comparable words.

The script is typed and the transcript is generated, so the same sentence arrives
spelled two ways — "Part 2." against "part two", "we're" against "we’re". Everything
that compares the two compares the token streams produced here: lowercased, stripped
of punctuation, with digits spelled out the way they are read aloud.

A transcript's tokens keep the word they came from alongside them, because a match is
only useful once it can be turned back into a time.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from roughcut.analysis import Word

# Anything that is not a letter or a digit separates words. Apostrophes are removed
# first rather than treated as separators, so "we're" is one token and not two.
_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_APOSTROPHES = re.compile(r"['’`]")

_ONES = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
_SCALES = ((1000, "thousand"), (100, "hundred"))

# Above this a number is a year, a version or an identifier rather than a count, and
# there is no single way it is read aloud — so it is read digit by digit.
SPELLED_LIMIT = 1_000_000


@dataclass(frozen=True)
class SpokenToken:
    """One normalised transcript token, and the word it was spoken as."""

    text: str
    word: int
    """Index into the analysis's word list — the way back to a time."""


@dataclass(frozen=True)
class Transcript:
    """A recording's words and the token stream they reduce to, kept together.

    Comparison happens over the tokens and every answer is wanted in seconds, so the
    two are only useful side by side: this is what turns "the fourth token matched"
    back into "at 12.56 s, and here is what was said".
    """

    words: Sequence[Word]
    tokens: list[SpokenToken]

    @staticmethod
    def of(words: Sequence[Word]) -> "Transcript":
        """Reduce a transcript to tokens, each remembering which word produced it.

        A word can produce none — the transcriber sometimes emits bare punctuation —
        or several, when it produces a number.
        """
        return Transcript(
            words,
            [
                SpokenToken(token, index)
                for index, word in enumerate(words)
                for token in tokenize(word.text)
            ],
        )

    def __len__(self) -> int:
        return len(self.tokens)

    @property
    def texts(self) -> list[str]:
        """The tokens alone, as the sequence matcher wants them."""
        return [token.text for token in self.tokens]

    def start_of(self, token: int) -> float:
        """When the word this token came from began."""
        return self.words[self.tokens[token].word].start_seconds

    def end_of(self, token: int) -> float:
        """When the word this token came from ended."""
        return self.words[self.tokens[token].word].end_seconds

    def said_between(self, first: int, last: int) -> str:
        """What was said across a run of tokens, in the transcriber's own words."""
        return " ".join(
            word.text.strip()
            for word in self.words[self.tokens[first].word : self.tokens[last].word + 1]
        )


def tokenize(text: str) -> list[str]:
    """Reduce text to the words another reading of it can be compared against."""
    return [
        token
        for word in _WORD.findall(_APOSTROPHES.sub("", text.lower()))
        for token in _expanded(word)
    ]


def _expanded(word: str) -> list[str]:
    if not word.isdigit():
        return [word]
    if int(word) >= SPELLED_LIMIT:
        return [_ONES[int(digit)] for digit in word]
    return _spelled(int(word))


def _spelled(value: int) -> list[str]:
    for size, name in _SCALES:
        if value >= size:
            count, rest = divmod(value, size)
            return _spelled(count) + [name] + (_spelled(rest) if rest else [])
    if value >= 20:
        tens, unit = divmod(value, 10)
        return [_TENS[tens]] + ([_ONES[unit]] if unit else [])
    return [_ONES[value]]
