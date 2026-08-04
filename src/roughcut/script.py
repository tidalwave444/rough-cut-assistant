"""The script: one sentence per line, no markup.

Line numbers count non-blank lines only. They are the stable identifier used in the
plan, the report and every marker, so a blank line between sentences — which is how
the fixture script is written — must not consume one.
"""

from dataclasses import dataclass
from pathlib import Path

from roughcut.errors import RoughCutError


@dataclass(frozen=True)
class ScriptLine:
    """One spoken sentence, numbered from 1 among the non-blank lines."""

    number: int
    text: str


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
