"""What the cut did with the pauses, driven by hand-written recordings.

Every fixture here is one script line read with a gap in the middle of it, so that
what is asserted is the cut — where the clips fall and how long the timeline runs —
rather than the arithmetic that placed them.

The gaps between lines are a different thing entirely and are already gone: the cut
is butt-spliced, so only a pause *inside* a kept line has anything to shorten.
"""

from conftest import FIXTURE_SOURCE, LINE_1, LINE_2, SCRIPT, cut_times, spoken

from roughcut.analysis import Analysis, Silence, Word
from roughcut.pauses import PauseSettings
from roughcut.plan import Plan, build_plan, rough_cut, timeline_duration_seconds
from roughcut.script import ScriptLine

ONE_LINE = [SCRIPT[0]]
"""Line 1 alone — the fixtures below are all one line read in two halves."""

OPENING = "Building a real project with vibe"
CLOSING = "coding, part two."
OPENING_ENDS = 3.0
"""Six words at half a second each: the first half of line 1 runs out here."""


def paused_read(gap: float) -> list[Word]:
    """Line 1, read with `gap` seconds of nothing in the middle of it."""
    return spoken(OPENING, at=0.0) + spoken(CLOSING, at=OPENING_ENDS + gap)


def plan_for(
    words: list[Word],
    silences: list[Silence],
    *,
    settings: PauseSettings | None = None,
    script: list[ScriptLine] | None = None,
) -> Plan:
    analysis = Analysis(source=FIXTURE_SOURCE, words=words, silences=silences)
    return build_plan(analysis, script or ONE_LINE, settings or PauseSettings())


def test_a_long_pause_is_shortened_to_the_floor_rather_than_closed() -> None:
    # Two seconds of gap: 1.7 s comes out and the 0.3 s floor is left behind, so the
    # line still breathes where it was read to.
    plan = plan_for(paused_read(gap=2.0), [Silence(3.0, 5.0)])

    assert cut_times(plan) == [(0.0, 3.15, 0.0), (4.85, 6.5, 3.15)]
    assert [round(pause.remaining_seconds, 3) for pause in plan.shortened] == [0.3]
    assert round(timeline_duration_seconds(rough_cut(plan)), 3) == 4.8


def test_a_pause_below_the_threshold_is_left_exactly_as_it_was_spoken() -> None:
    plan = plan_for(paused_read(gap=0.6), [Silence(3.0, 3.6)])

    assert cut_times(plan) == [(0.0, 5.1, 0.0)]
    assert plan.shortened == []


def test_a_gap_no_silence_corroborates_is_left_alone() -> None:
    # The transcript heard nothing said, but the detector heard something: a mumble
    # between the words, or a word the transcriber dropped. Not a pause to cut.
    plan = plan_for(paused_read(gap=2.0), [])

    assert cut_times(plan) == [(0.0, 6.5, 0.0)]
    assert plan.shortened == []


def test_a_silence_running_into_the_words_either_side_cannot_move_the_cut_into_one() -> None:
    # The detector calls the fade of a last consonant quiet, so a silence region
    # overlaps the words. The cut is bounded by the gap regardless.
    plan = plan_for(paused_read(gap=2.0), [Silence(2.4, 5.6)])

    assert cut_times(plan) == [(0.0, 3.15, 0.0), (4.85, 6.5, 3.15)]


def test_only_the_corroborated_part_of_a_gap_is_taken_out() -> None:
    # Two seconds of gap, but the room was only quiet through 0.6 s of it.
    plan = plan_for(paused_read(gap=2.0), [Silence(3.7, 4.3)])

    assert cut_times(plan) == [(0.0, 3.75, 0.0), (4.25, 6.5, 3.75)]
    assert [round(pause.remaining_seconds, 3) for pause in plan.shortened] == [1.5]


def test_a_silence_too_short_to_pad_away_from_the_words_is_not_cut_at_all() -> None:
    plan = plan_for(paused_read(gap=2.0), [Silence(3.9, 3.95)])

    assert cut_times(plan) == [(0.0, 6.5, 0.0)]


def test_a_pause_after_the_very_first_word_is_shortened_like_any_other() -> None:
    words = spoken("Building", at=0.0) + spoken(
        "a real project with vibe coding, part two.", at=2.5
    )

    plan = plan_for(words, [Silence(0.5, 2.5)])

    assert cut_times(plan) == [(0.0, 0.65, 0.0), (2.35, 6.5, 0.65)]


def test_a_pause_before_the_very_last_word_is_shortened_like_any_other() -> None:
    words = spoken("Building a real project with vibe coding, part", at=0.0) + spoken(
        "two.", at=6.0
    )

    plan = plan_for(words, [Silence(4.0, 6.0)])

    assert cut_times(plan) == [(0.0, 4.15, 0.0), (5.85, 6.5, 4.15)]


def test_quiet_before_the_first_word_and_after_the_last_is_not_a_pause_to_shorten() -> None:
    # There are no two words either side of it, so there is no gap to collapse. What
    # happens to that quiet instead is the splice pad taking a tenth and a half of it.
    plan = plan_for(spoken(LINE_1, at=2.0), [Silence(0.0, 2.0), Silence(6.5, 10.0)])

    assert cut_times(plan) == [(1.85, 6.65, 0.0)]
    assert plan.shortened == []


def test_the_threshold_the_floor_and_the_padding_are_all_settings() -> None:
    plan = plan_for(
        paused_read(gap=2.0),
        [Silence(3.0, 5.0)],
        settings=PauseSettings(threshold_seconds=1.0, floor_seconds=1.0, padding_seconds=0.25),
    )

    assert cut_times(plan) == [(0.0, 3.5, 0.0), (4.5, 6.5, 3.5)]
    assert [round(pause.remaining_seconds, 3) for pause in plan.shortened] == [1.0]


def test_a_threshold_raised_past_the_gap_leaves_the_read_as_it_was() -> None:
    plan = plan_for(
        paused_read(gap=2.0),
        [Silence(3.0, 5.0)],
        settings=PauseSettings(threshold_seconds=3.0),
    )

    assert cut_times(plan) == [(0.0, 6.5, 0.0)]


def test_a_marker_after_a_shortened_pause_moves_with_the_words_it_names() -> None:
    script = [ScriptLine(1, "It asks: what it is about, who it is for, and which stack we need.")]
    words = spoken("It asks: what it is about,", at=0.0) + spoken(
        "who it is for, and which stack we need.", at=5.0
    )

    plan = plan_for(words, [Silence(3.0, 5.0)], script=script)

    # Without the pause the beats fall at 0.0, 5.0 and 7.0; 1.7 s came out before them.
    assert [
        round(marker.timeline_position_seconds, 3) for marker in rough_cut(plan).markers
    ] == [0.0, 3.3, 5.3]


def test_a_pause_in_the_dead_air_between_two_lines_is_not_shortened_but_removed() -> None:
    # Nothing to collapse: the splice already takes the whole of it out, bar the pad
    # each line keeps of the quiet on its own side.
    plan = plan_for(
        spoken(LINE_1, at=0.0) + spoken(LINE_2, at=8.0),
        [Silence(4.5, 8.0)],
        script=SCRIPT[:2],
    )

    assert cut_times(plan) == [(0.0, 4.65, 0.0), (7.85, 12.5, 4.65)]
    assert plan.shortened == []
