from conftest import FIXTURE_SOURCE, LINE_1, LINE_2, LINE_3, SCRIPT, clean_read, spoken

from roughcut.analysis import Analysis, Silence, Word
from roughcut.plan import Clip, Plan, Sequence, build_plan
from roughcut.report import render_report

CLEAN_READ = clean_read()


def analysis(words: list[Word]) -> Analysis:
    return Analysis(source=FIXTURE_SOURCE, words=words, silences=[Silence(4.5, 6.0)])


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


def test_a_retake_is_listed_with_the_line_it_repeats() -> None:
    report = report_for(CLEAN_READ + spoken(LINE_2, at=20.0))

    assert "00:00:20.000–00:00:24.500  retake of line 2" in report


def test_off_script_material_is_listed_as_such_with_what_was_said() -> None:
    report = report_for(
        spoken(LINE_1, at=0.0)
        + spoken("Sorry, my microphone was unplugged the whole time again.", at=6.0)
        + spoken(LINE_2, at=13.0)
        + spoken(LINE_3, at=20.0)
    )

    assert "00:00:06.000–00:00:10.500  off-script" in report
    assert "Sorry, my microphone was unplugged" in report


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


def test_a_cut_that_uses_all_of_the_recording_lists_nothing_as_unused() -> None:
    assert "Not used" not in report_for(CLEAN_READ)


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
