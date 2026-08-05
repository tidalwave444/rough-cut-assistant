from pathlib import Path

import pytest

from roughcut.errors import RoughCutError
from roughcut.script import Beat, ScriptLine, beats, parse_script, read_script


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


def beat_texts(text: str) -> list[str]:
    return [beat.text for beat in beats(ScriptLine(1, text))]


def test_an_ordinary_line_is_one_beat_carrying_the_whole_line() -> None:
    line = ScriptLine(3, "Today, we're moving from setup to actual development.")

    assert beats(line) == [Beat(line.text, 0)]


def test_a_line_listing_three_things_is_split_into_a_beat_per_item() -> None:
    assert beat_texts(
        "Here it asks: what it is about, who it is for, and which tech stack we need."
    ) == [
        "Here it asks: what it is about,",
        "who it is for,",
        "and which tech stack we need.",
    ]


def test_a_run_of_questions_enumerates_as_readily_as_a_run_of_clauses() -> None:
    assert beat_texts(
        "It asks: What problem does it solve? Who is it for? And which stack do we need?"
    ) == [
        "It asks: What problem does it solve?",
        "Who is it for?",
        "And which stack do we need?",
    ]


def test_a_word_opening_the_sentence_is_not_an_item_of_the_list_it_introduces() -> None:
    # "Here," is where the sentence starts, not the first thing it lists.
    assert beat_texts(
        "Here, it asks about the website: what it is, who it is for, and which stack we need."
    ) == [
        "Here, it asks about the website: what it is,",
        "who it is for,",
        "and which stack we need.",
    ]


def test_a_beat_knows_how_far_into_the_line_it_starts() -> None:
    # The offset is in tokens, because that is what the recording is located by.
    line = ScriptLine(1, "It asks: what it is, who it is for, and which stack we need.")

    assert [beat.token_offset for beat in beats(line)] == [0, 5, 9]


def test_a_line_with_one_aside_is_not_an_enumeration() -> None:
    # Two clauses and a conjunction is how ordinary sentences are written; splitting
    # them would put a marker mid-sentence on nearly every line.
    assert beat_texts("In the previous part, we prepared the project and installed it.") == [
        "In the previous part, we prepared the project and installed it."
    ]


def test_a_list_without_a_conjunction_is_not_an_enumeration() -> None:
    assert beat_texts("Today, before we start, we need a plan.") == [
        "Today, before we start, we need a plan."
    ]


def test_reading_a_script_decodes_utf8(tmp_path: Path) -> None:
    path = tmp_path / "script.txt"
    path.write_bytes("Part 2 — “vibe coding”.\r\n\r\nThe end.\r\n".encode("utf-8"))

    assert read_script(path) == [
        ScriptLine(1, "Part 2 — “vibe coding”."),
        ScriptLine(2, "The end."),
    ]
