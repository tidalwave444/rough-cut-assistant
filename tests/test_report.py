from conftest import (
    FIXTURE_SOURCE,
    LINE_1,
    LINE_2,
    LINE_2_STOPS_SHORT,
    LINE_3,
    SCRIPT,
    clean_read,
    retakes,
    spoken,
)

from roughcut.analysis import Analysis, Silence, Word
from roughcut.plan import Clip, Plan, Sequence, build_plan
from roughcut.report import render_report

CLEAN_READ = clean_read()


def analysis(words: list[Word]) -> Analysis:
    """A recording the detector heard no quiet in — so no clip is padded or shortened.

    The report is a pure function of the plan, so what it says about a cut is the same
    whatever moved the cut's edges. Leaving the quiet out keeps the times below the
    round numbers the fixtures were written with.
    """
    return Analysis(source=FIXTURE_SOURCE, words=words, silences=[])


def report_for(words: list[Word]) -> str:
    described = analysis(words)
    return render_report(described, SCRIPT, build_plan(described, SCRIPT))


def report_with_a_pause() -> str:
    """Line 1 read with two seconds of quiet in the middle of it."""
    words = spoken("Building a real project with vibe", at=0.0) + spoken(
        "coding, part two.", at=5.0
    )
    described = Analysis(source=FIXTURE_SOURCE, words=words, silences=[Silence(3.0, 5.0)])
    return render_report(described, SCRIPT[:1], build_plan(described, SCRIPT[:1]))


def test_the_report_names_the_recording_it_describes() -> None:
    assert "sequence.mp4" in report_for(CLEAN_READ)


def test_the_report_states_the_source_and_output_durations() -> None:
    report = report_for(CLEAN_READ)

    assert "Source duration    00:01:26.250" in report
    assert "Output duration    00:00:13.500" in report
    assert "Removed            00:01:12.750" in report


def test_the_report_states_the_word_count_and_the_script_size() -> None:
    report = report_for(CLEAN_READ)

    assert "Words transcribed  27" in report
    assert "Script lines       3" in report
    assert "Lines found        3" in report
    assert "Lines not found    0" in report


def test_the_report_gives_the_source_time_each_line_was_found_at() -> None:
    report = report_for(CLEAN_READ)

    assert "   1  00:00:00.000   00:00:00.000   Building a real project" in report
    assert "   2  00:00:06.000   00:00:04.500   Today we are moving" in report
    assert "   3  00:00:13.000   00:00:09.000   In the next part" in report


def test_a_line_the_recording_does_not_contain_is_flagged_rather_than_timed() -> None:
    report = report_for(spoken(LINE_1, at=0.0) + spoken(LINE_3, at=6.0))

    assert "Lines not found    1" in report
    assert "   2  not found      —              Today we are moving" in report


def test_a_second_reading_of_a_line_is_a_take_of_it_rather_than_off_script_material() -> None:
    report = report_for(CLEAN_READ + spoken(LINE_2, at=20.0))

    assert "Takes considered   4" in report
    assert "Off-script material" not in report


def test_every_take_considered_is_listed_with_its_coverage_and_its_outcome() -> None:
    # The line number is written once and its takes hang below it, so a line read
    # three times reads as one block rather than as three rows to match up by eye.
    report = report_for(retakes(LINE_2, LINE_2, LINE_2_STOPS_SHORT))

    assert "Line  Take  Source         Coverage  Disfluencies  Outcome" in report
    assert "   2     1  00:00:06.000   100%      0             a later take" in report
    assert "         2  00:00:13.000   100%      0             selected" in report
    assert "         3  00:00:20.000   67%       0             truncated — stopped 3" in report


def test_a_line_read_more_than_once_has_its_choice_explained_in_one_sentence() -> None:
    report = report_for(retakes(LINE_2, LINE_2, LINE_2_STOPS_SHORT))

    assert "  Line 2  take 2 of 3; take 3 truncated — stopped 3 words short" in report


def test_a_line_read_only_once_needs_no_sentence_explaining_the_choice() -> None:
    report = report_for(CLEAN_READ)

    assert "Which take was used" not in report


def test_a_line_whose_every_take_was_disqualified_is_flagged_for_re_recording() -> None:
    report = report_for(
        retakes(LINE_2_STOPS_SHORT, f"{LINE_2_STOPS_SHORT} to", LINE_2_STOPS_SHORT)
    )

    assert "Lines flagged      1" in report
    assert "Lines whose best take was poor" in report
    assert "  Line 2  take 2 of 3, the least bad — every take was disqualified" in report


def test_a_cut_whose_every_line_stands_flags_nothing() -> None:
    report = report_for(CLEAN_READ)

    assert "Lines flagged      0" in report
    assert "Lines whose best take was poor" not in report


def test_off_script_material_kept_is_listed_with_its_duration_and_what_was_said() -> None:
    report = report_for(
        spoken(LINE_1, at=0.0)
        + spoken("Sorry, my microphone was unplugged the whole time again.", at=6.0)
        + spoken(LINE_2, at=13.0)
        + spoken(LINE_3, at=20.0)
    )

    assert "Off-script kept    1" in report
    assert "Off-script cut     0" in report
    assert "  00:00:06.000   00:00:04.500   kept — marked in place" in report
    assert "Sorry, my microphone was unplugged" in report


def test_off_script_material_dropped_says_so_and_why_it_went() -> None:
    # The section is the only record that a dropped region was ever there, so it says
    # what was said as well as what became of it.
    report = report_for(CLEAN_READ + spoken("Ugh", at=20.0))

    assert "Off-script kept    0" in report
    assert "Off-script cut     1" in report
    assert "  00:00:20.000   00:00:00.500   cut — a fragment, under 2.5 s" in report
    assert report.rstrip().endswith("Ugh")


def test_the_report_counts_the_pauses_it_shortened() -> None:
    assert "Pauses shortened   1" in report_with_a_pause()


def test_each_shortened_pause_is_listed_with_what_it_gave_up() -> None:
    # Two seconds of gap three seconds in, cut back to the floor.
    assert (
        "  00:00:03.000   00:00:02.000   00:00:00.300   00:00:01.700" in report_with_a_pause()
    )


def test_a_cut_with_no_pause_worth_shortening_says_so_and_tabulates_nothing() -> None:
    report = report_for(CLEAN_READ)

    assert "Pauses shortened   0" in report
    assert "What each pause gave up" not in report


def report_with_a_false_start() -> str:
    """Line 1 read with `part` said, abandoned and said again."""
    words = spoken("Building a real project with vibe coding part no part two.", at=0.0)
    described = analysis(words)
    return render_report(described, SCRIPT[:1], build_plan(described, SCRIPT[:1]))


def test_the_report_counts_the_false_starts_it_cut() -> None:
    assert "False starts cut   1" in report_with_a_false_start()


def test_each_removal_from_inside_a_take_says_when_it_was_why_it_went_and_what_was_said() -> None:
    # The one thing in the cut that leaves no silence behind it, so the row is the only
    # way of knowing the words were ever spoken.
    report = report_with_a_false_start()

    assert "Line  At             Duration       Why" in report
    assert (
        '   1  00:00:03.500   00:00:01.000   "part" said twice                 part no'
        in report
    )


def test_a_cut_with_no_false_start_in_it_tabulates_nothing() -> None:
    report = report_for(CLEAN_READ)

    assert "False starts cut   0" in report
    assert "What came out from inside a take" not in report


def test_a_cut_with_nothing_said_off_the_script_tabulates_nothing() -> None:
    report = report_for(CLEAN_READ)

    assert "Off-script kept    0" in report
    assert "Off-script cut     0" in report
    assert "Off-script material" not in report


def test_the_output_duration_is_the_cut_alone_not_the_alternates_beside_it() -> None:
    plan = Plan(
        sequences=[
            Sequence("sequence-1", "RoughCut", FIXTURE_SOURCE, clips=[Clip(0.0, 80.25, 0.0)]),
            Sequence(
                "sequence-2", "RoughCut_Alternates", FIXTURE_SOURCE, clips=[Clip(0.0, 6.0, 0.0)]
            ),
        ]
    )

    report = render_report(analysis(CLEAN_READ), SCRIPT, plan)

    assert "Output duration    00:01:20.250" in report
    assert "Removed            00:00:06.000" in report


def test_a_cut_longer_than_its_source_reads_as_a_negative_rather_than_as_nonsense() -> None:
    plan = Plan(
        sequences=[
            Sequence("sequence-1", "RoughCut", FIXTURE_SOURCE, clips=[Clip(0.0, 87.75, 0.0)])
        ]
    )

    assert "Removed            -00:00:01.500" in render_report(analysis([]), SCRIPT, plan)


def test_the_report_ends_with_a_newline() -> None:
    assert report_for(CLEAN_READ).endswith("\n")
