from pathlib import Path

import pytest

from roughcut.errors import RoughCutError
from roughcut.script import ScriptLine, parse_script, read_script


def test_each_non_blank_line_becomes_a_numbered_line() -> None:
    assert parse_script("First one.\nSecond one.\n") == [
        ScriptLine(1, "First one."),
        ScriptLine(2, "Second one."),
    ]


def test_carriage_returns_are_stripped() -> None:
    assert parse_script("First one.\r\nSecond one.\r\n") == [
        ScriptLine(1, "First one."),
        ScriptLine(2, "Second one."),
    ]


def test_blank_lines_are_ignored_and_do_not_consume_a_number() -> None:
    # The fixture script separates every sentence with a blank line, so numbering
    # that counted them would put line 5 of the script at number 9.
    assert parse_script("First one.\n\n   \nSecond one.\n\n") == [
        ScriptLine(1, "First one."),
        ScriptLine(2, "Second one."),
    ]


def test_surrounding_whitespace_is_trimmed_but_the_text_is_otherwise_kept() -> None:
    assert parse_script("  Part 2 — we'll build it.  \n") == [
        ScriptLine(1, "Part 2 — we'll build it.")
    ]


def test_reading_a_missing_script_names_the_path(tmp_path: Path) -> None:
    missing = tmp_path / "nope.txt"

    with pytest.raises(RoughCutError, match=f"Script not found: {missing}"):
        read_script(missing)


def test_reading_an_empty_script_says_so_rather_than_planning_nothing(tmp_path: Path) -> None:
    empty = tmp_path / "empty.txt"
    empty.write_text("\n  \n", encoding="utf-8")

    with pytest.raises(RoughCutError, match="no lines"):
        read_script(empty)


def test_reading_a_script_decodes_utf8(tmp_path: Path) -> None:
    path = tmp_path / "script.txt"
    path.write_bytes("Part 2 — “vibe coding”.\r\n\r\nThe end.\r\n".encode("utf-8"))

    assert read_script(path) == [
        ScriptLine(1, "Part 2 — “vibe coding”."),
        ScriptLine(2, "The end."),
    ]
