"""The script: one sentence per line, no markup.

Line numbers count non-blank lines only. They are the stable identifier used in the
plan, the report and every marker, so a blank line between sentences — which is how
the fixture script is written — must not consume one.

A line is also read for its *beats*: the moments in it that deserve a marker of their
own. Most lines have one. A line that enumerates has one per item, because a sentence
listing three things is three visual beats and a single marker would hide two of them.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from roughcut.errors import RoughCutError
from roughcut.tokens import tokenize

# An item runs to the next comma, semicolon or question mark, and keeps it: the
# punctuation belongs to the item it ends, so a marker reads as it was written.
_ITEM = re.compile(r"[^,;?]+[,;?]*")

# Two clauses joined by "and" is how ordinary sentences are written. Three or more is
# a list, and a list closed by a conjunction is one the writer meant as a list.
MINIMUM_ITEMS = 3
CONJUNCTIONS = ("and", "or")

# A sentence that opens "Here," or "Now, first," is not listing those. A single word
# before the first real item belongs to the item, not beside it.
MINIMUM_ITEM_TOKENS = 2


@dataclass(frozen=True)
class ScriptLine:
    """One spoken sentence, numbered from 1 among the non-blank lines."""

    number: int
    text: str


@dataclass(frozen=True)
class Beat:
    """A moment in a line that gets its own marker, and where it starts.

    The offset counts tokens rather than characters, because the recording is located
    by tokens: it is what turns "the third item of line 6" into a time.
    """

    text: str
    token_offset: int


def beats(line: ScriptLine) -> list[Beat]:
    """Split a line into the beats it should be marked at — usually just itself."""
    items = _lead_folded(_items(line.text))
    if len(items) < MINIMUM_ITEMS or items[-1][1][0] not in CONJUNCTIONS:
        return [Beat(line.text, 0)]

    found = []
    offset = 0
    for text, tokens in items:
        found.append(Beat(text, offset))
        offset += len(tokens)
    return found


def _items(text: str) -> list[tuple[str, list[str]]]:
    """The comma-separated pieces of a line, each with its tokens.

    A piece that says no words — a stray separator — is dropped rather than counted,
    so it can neither become a beat nor make a sentence look like a list.
    """
    pieces = [match.group().strip() for match in _ITEM.finditer(text)]
    return [(piece, tokenize(piece)) for piece in pieces if tokenize(piece)]


def _lead_folded(items: list[tuple[str, list[str]]]) -> list[tuple[str, list[str]]]:
    """Fold an opening fragment into the item it introduces."""
    while len(items) > 1 and len(items[0][1]) < MINIMUM_ITEM_TOKENS:
        (lead, lead_tokens), (first, first_tokens) = items[0], items[1]
        items = [(f"{lead} {first}", lead_tokens + first_tokens), *items[2:]]
    return items


def parse_script(text: str) -> list[ScriptLine]:
    """Number the non-blank lines of a script, regardless of how it wraps them.

    Carriage returns are stripped rather than kept, so a CRLF file and an LF file
    parse identically — the fixture script is CRLF, and a trailing `\\r` would ride
    into every marker comment.
    """
    stripped = (line.strip() for line in text.replace("\r", "").split("\n"))
    spoken = [line for line in stripped if line]
    return [ScriptLine(number, line) for number, line in enumerate(spoken, start=1)]


def read_script(path: Path) -> list[ScriptLine]:
    """Read a script file, failing clearly when it is missing or says nothing."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise RoughCutError(f"Script not found: {path}") from None
    except OSError as error:
        raise RoughCutError(f"Could not read the script at {path}: {error}") from None
    except UnicodeDecodeError:
        raise RoughCutError(f"The script at {path} is not valid UTF-8 text.") from None

    lines = parse_script(text)
    if not lines:
        raise RoughCutError(f"The script at {path} has no lines — it is empty or all blank.")
    return lines
