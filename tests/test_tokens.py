"""Normalisation is the only place a spelling difference can decide a match.

These are the one exception to asserting on decisions rather than internals: two
readings of the same sentence only compare if they reduce to the same tokens, so the
reduction itself is the contract.
"""

from roughcut.analysis import Word
from roughcut.tokens import Transcript, tokenize


def test_words_are_lowercased_and_stripped_of_punctuation() -> None:
    assert tokenize("Building a real project — with vibe coding!") == [
        "building",
        "a",
        "real",
        "project",
        "with",
        "vibe",
        "coding",
    ]


def test_apostrophes_close_a_word_rather_than_splitting_it() -> None:
    # Straight and curly alike: the script is typed and the transcript is generated,
    # so the same contraction arrives spelled two ways.
    assert tokenize("we're") == tokenize("we’re") == ["were"]


def test_digits_are_spelled_out_so_that_a_script_matches_a_transcript() -> None:
    # The script writes "Part 2."; Whisper writes "part two".
    assert tokenize("Part 2.") == tokenize("Part two.") == ["part", "two"]


def test_larger_numbers_are_spelled_the_way_they_are_read() -> None:
    assert tokenize("21") == ["twenty", "one"]
    assert tokenize("305") == ["three", "hundred", "five"]
    assert tokenize("1200") == ["one", "thousand", "two", "hundred"]


def test_a_number_too_long_to_be_a_count_is_read_digit_by_digit() -> None:
    assert tokenize("1234567") == [
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
    ]


def test_a_transcript_turns_a_matched_token_back_into_a_time() -> None:
    heard = Transcript.of([Word("Part", 0.0, 0.4, 0.9), Word("2.", 0.4, 0.8, 0.9)])

    assert heard.texts == ["part", "two"]
    assert (heard.start_of(1), heard.end_of(1)) == (0.4, 0.8)
    assert heard.said_between(0, 1) == "Part 2."


def test_a_word_the_transcriber_heard_as_nothing_contributes_no_tokens() -> None:
    heard = Transcript.of([Word("—", 0.0, 0.4, 0.9), Word("Part", 0.4, 0.8, 0.9)])

    assert heard.texts == ["part"]
    assert heard.start_of(0) == 0.4
