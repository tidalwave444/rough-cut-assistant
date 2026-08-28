"""What the cut did with the pauses, driven by hand-written recordings.

Every fixture here is one script line read with quiet somewhere in it, so that what is
asserted is the cut — where the clips fall and how long the timeline runs — rather
than the arithmetic that placed them.

A pause is a stretch of detected silence, not a gap in the transcript, so several of
these fixtures put the quiet *underneath* a word rather than between two of them: that
is where it sits on real material, and the cut has to find it there (decision 0001).

The gaps between lines are a different thing entirely and are already gone: the cut
is butt-spliced, so only quiet *inside* a kept stretch has anything to shorten.
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
    """Line 1, read with `gap` seconds of nothing in the middle of it.

    A gap the transcript admits to, which real transcripts hardly ever leave. It is
    the silence passed beside it that decides what comes out; the gap is only here so
    that a fixture reads as a line with a pause in the middle of it.
    """
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
    # Two seconds of quiet: 1.7 s comes out and the 0.3 s floor is left behind, so the
    # line still breathes where it was read to.
    plan = plan_for(paused_read(gap=2.0), [Silence(3.0, 5.0)])

    assert cut_times(plan) == [(0.0, 3.15, 0.0), (4.85, 6.5, 3.15)]
    assert [round(pause.remaining_seconds, 3) for pause in plan.shortened] == [0.3]
    assert round(timeline_duration_seconds(rough_cut(plan)), 3) == 4.8


def test_a_pause_below_the_threshold_is_left_exactly_as_it_was_spoken() -> None:
    plan = plan_for(paused_read(gap=0.6), [Silence(3.0, 3.6)])

    assert cut_times(plan) == [(0.0, 5.1, 0.0)]
    assert plan.shortened == []


def test_a_gap_in_the_transcript_the_detector_heard_nothing_quiet_in_is_left_alone() -> None:
    # The transcript has nothing said for two seconds, but the detector heard sound
    # all through them: a mumble, or a word the transcriber dropped. The transcript
    # is not asked and the room says there was no pause here, so nothing is cut.
    plan = plan_for(paused_read(gap=2.0), [])

    assert cut_times(plan) == [(0.0, 6.5, 0.0)]
    assert plan.shortened == []


def test_a_silence_lying_wholly_under_one_word_is_collapsed_all_the_same() -> None:
    # The transcriber left no gap to find: it stretched `part` over the pause that
    # followed it, two and a half seconds for one syllable. The detector heard two of
    # them as quiet, and those two are what comes out — the word's declared span is
    # not a rail (decision 0001), so the cut lands inside it.
    words = spoken(OPENING + " coding,", at=0.0) + [
        Word("part", 3.5, 6.0, 0.34),
        Word("two.", 6.0, 6.5, 0.9),
    ]

    plan = plan_for(words, [Silence(3.7, 5.7)])

    assert cut_times(plan) == [(0.0, 3.85, 0.0), (5.55, 6.5, 3.85)]
    assert [round(pause.remaining_seconds, 3) for pause in plan.shortened] == [0.3]


def test_only_the_quiet_gives_up_time_and_not_the_gap_around_it() -> None:
    # Two seconds of gap, but the room was only quiet through one of them. What is
    # measured is that one: it keeps the floor, and the rest of the gap plays on.
    plan = plan_for(paused_read(gap=2.0), [Silence(3.5, 4.5)])

    assert cut_times(plan) == [(0.0, 3.65, 0.0), (4.35, 6.5, 3.65)]
    assert [round(pause.remaining_seconds, 3) for pause in plan.shortened] == [0.3]


def test_a_pad_wider_than_half_the_quiet_leaves_nothing_of_it_safe_to_cut() -> None:
    # The cut sits inside the quiet with a pad off both edges. Where the two pads meet
    # before they have anything between them, the whole region plays.
    plan = plan_for(
        paused_read(gap=2.0), [Silence(3.0, 5.0)], settings=PauseSettings(padding_seconds=1.5)
    )

    assert cut_times(plan) == [(0.0, 6.5, 0.0)]
    assert plan.shortened == []


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


def test_quiet_at_the_head_of_a_take_is_removed_in_full_rather_than_floored() -> None:
    # The room stays quiet a second past where the first word was declared to start.
    # A take begins where sound begins, so the take begins at 3.0 — no floor is held
    # there, because a floor is a beat between two words and this is the outside of a
    # splice. The 0.15 s in front of it is the splice pad, measured from that
    # corrected boundary rather than from the timestamp.
    plan = plan_for(spoken(LINE_1, at=2.0), [Silence(0.0, 3.0)])

    assert cut_times(plan) == [(2.85, 6.5, 0.0)]
    assert plan.shortened == []


def test_quiet_at_the_tail_of_a_take_is_removed_in_full_rather_than_floored() -> None:
    # The mirror of it: the transcriber ran the last word on for a second after the
    # room went quiet, and the take ends where the sound did.
    plan = plan_for(spoken(LINE_1, at=0.0), [Silence(3.5, 8.0)])

    assert cut_times(plan) == [(0.0, 3.65, 0.0)]
    assert plan.shortened == []


def test_quiet_at_a_take_s_edge_that_stops_where_the_words_do_is_only_padded_into() -> None:
    # Nothing to trim: the detector and the transcriber agree about where the line
    # starts and stops. All that happens to the quiet either side is the splice pad
    # taking a tenth and a half of it.
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


def test_a_marker_whose_word_begins_inside_a_collapsed_region_lands_on_the_splice() -> None:
    # The quiet runs half a second into `who`, so the moment that marker names no
    # longer exists in the cut. It sits on the splice rather than in the hole where
    # the silence was.
    script = [ScriptLine(1, "It asks: what it is about, who it is for, and which stack we need.")]
    words = spoken("It asks: what it is about,", at=0.0) + spoken(
        "who it is for, and which stack we need.", at=5.0
    )

    plan = plan_for(words, [Silence(3.0, 5.5)], script=script)

    assert cut_times(plan) == [(0.0, 3.15, 0.0), (5.35, 9.5, 3.15)]
    assert [
        round(marker.timeline_position_seconds, 3) for marker in rough_cut(plan).markers
    ] == [0.0, 3.15, 4.8]


def test_a_kept_off_script_region_collapses_its_own_quiet_on_the_same_rule() -> None:
    # An aside nobody scripted is still a stretch of the cut that plays, so the dead
    # air inside it comes out exactly as it would inside a line.
    aside = "Sorry, my microphone was unplugged the whole time again."
    plan = plan_for(
        spoken(LINE_1, at=0.0) + spoken(aside, at=6.0) + spoken(LINE_2, at=13.0),
        [Silence(7.0, 9.0)],
        script=SCRIPT[:2],
    )

    assert cut_times(plan) == [
        (0.0, 4.5, 0.0),
        (6.0, 7.15, 4.5),
        (8.85, 10.5, 5.65),
        (13.0, 17.5, 7.3),
    ]
    assert [round(pause.remaining_seconds, 3) for pause in plan.shortened] == [0.3]


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
