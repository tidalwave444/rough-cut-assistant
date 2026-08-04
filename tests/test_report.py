from conftest import FIXTURE_SOURCE

from roughcut.analysis import Analysis, Silence, Word
from roughcut.plan import Clip, Plan, Sequence, build_plan
from roughcut.report import render_report
from roughcut.script import ScriptLine

SCRIPT = [ScriptLine(1, "Part 2."), ScriptLine(2, "The end.")]

ANALYSIS = Analysis(
    source=FIXTURE_SOURCE,
    words=[Word("Part", 0.5, 0.8, 0.9), Word("two.", 0.8, 1.2, 0.9)],
    silences=[Silence(1.2, 4.0)],
)


def report_for(plan: Plan) -> str:
    return render_report(ANALYSIS, SCRIPT, plan)


def test_the_report_names_the_recording_it_describes() -> None:
    assert "sequence.mp4" in report_for(build_plan(ANALYSIS, SCRIPT))


def test_the_report_states_the_source_and_output_durations() -> None:
    report = report_for(build_plan(ANALYSIS, SCRIPT))

    assert "Source duration    00:01:26.250" in report
    assert "Output duration    00:01:26.250" in report


def test_the_report_states_what_a_cut_removed() -> None:
    plan = Plan(
        sequences=[
            Sequence("sequence-1", "RoughCut", FIXTURE_SOURCE, clips=[Clip(0.0, 80.25, 0.0)]),
        ]
    )

    report = report_for(plan)

    assert "Output duration    00:01:20.250" in report
    assert "Removed            00:00:06.000" in report


def test_the_report_states_the_word_count_and_the_script_size() -> None:
    report = report_for(build_plan(ANALYSIS, SCRIPT))

    assert "Words transcribed  2" in report
    assert "Script lines       2" in report


def test_the_output_duration_is_the_cut_alone_not_the_alternates_beside_it() -> None:
    plan = Plan(
        sequences=[
            Sequence("sequence-1", "RoughCut", FIXTURE_SOURCE, clips=[Clip(0.0, 80.25, 0.0)]),
            Sequence(
                "sequence-2", "RoughCut_Alternates", FIXTURE_SOURCE, clips=[Clip(0.0, 6.0, 0.0)]
            ),
        ]
    )

    report = report_for(plan)

    assert "Output duration    00:01:20.250" in report
    assert "Removed            00:00:06.000" in report


def test_a_cut_longer_than_its_source_reads_as_a_negative_rather_than_as_nonsense() -> None:
    plan = Plan(
        sequences=[
            Sequence("sequence-1", "RoughCut", FIXTURE_SOURCE, clips=[Clip(0.0, 87.75, 0.0)])
        ]
    )

    assert "Removed            -00:00:01.500" in report_for(plan)


def test_the_report_ends_with_a_newline() -> None:
    assert report_for(build_plan(ANALYSIS, SCRIPT)).endswith("\n")
