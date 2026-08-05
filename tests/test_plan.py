"""What the plan decided, driven by hand-written recordings.

Each fixture isolates one thing the cut has to get right: a clean read, a line
recorded out of order, a line never recorded at all, and a line that enumerates.
"""

from conftest import FIXTURE_SOURCE, LINE_1, LINE_2, LINE_3, SCRIPT, clean_read, spoken

from roughcut.analysis import Analysis, Silence, SourceMedia, Word
from roughcut.plan import (
    Clip,
    Marker,
    Sequence,
    build_plan,
    rough_cut,
    timeline_duration_seconds,
)
from roughcut.script import ScriptLine


def analysis(words: list[Word], source: SourceMedia = FIXTURE_SOURCE) -> Analysis:
    return Analysis(source=source, words=words, silences=[Silence(4.5, 6.0)])


def cut_of(words: list[Word], script: list[ScriptLine] | None = None) -> Sequence:
    return rough_cut(build_plan(analysis(words), script if script is not None else SCRIPT))


def test_each_line_becomes_a_clip_of_the_stretch_it_was_read_in() -> None:
    assert cut_of(clean_read()).clips == [
        Clip(source_in_seconds=0.0, source_out_seconds=4.5, timeline_start_seconds=0.0),
        Clip(source_in_seconds=6.0, source_out_seconds=10.5, timeline_start_seconds=4.5),
        Clip(source_in_seconds=13.0, source_out_seconds=17.5, timeline_start_seconds=9.0),
    ]


def test_the_clips_are_butt_spliced_so_the_dead_air_between_lines_is_gone() -> None:
    # 22.5s of recording, 13.5s of it speech.
    assert timeline_duration_seconds(cut_of(clean_read())) == 13.5


def test_a_marker_at_each_line_carries_that_line_s_text() -> None:
    assert cut_of(clean_read()).markers == [
        Marker(name="Line 1", comment=SCRIPT[0].text, timeline_position_seconds=0.0),
        Marker(name="Line 2", comment=SCRIPT[1].text, timeline_position_seconds=4.5),
        Marker(name="Line 3", comment=SCRIPT[2].text, timeline_position_seconds=9.0),
    ]


def test_the_sequence_is_assembled_in_script_order_not_in_the_order_spoken() -> None:
    # Line 2 was re-recorded after line 3 — a pickup take at the end of the session.
    out_of_order = spoken(LINE_1, at=0.0) + spoken(LINE_3, at=6.0) + spoken(LINE_2, at=13.0)

    assert cut_of(out_of_order).clips == [
        Clip(source_in_seconds=0.0, source_out_seconds=4.5, timeline_start_seconds=0.0),
        Clip(source_in_seconds=13.0, source_out_seconds=17.5, timeline_start_seconds=4.5),
        Clip(source_in_seconds=6.0, source_out_seconds=10.5, timeline_start_seconds=9.0),
    ]


def test_a_line_that_was_never_read_is_skipped_rather_than_aborting_the_cut() -> None:
    plan = build_plan(analysis(spoken(LINE_1, at=0.0) + spoken(LINE_3, at=6.0)), SCRIPT)

    assert [line.line.number for line in plan.lines] == [1, 3]
    assert plan.missing == [SCRIPT[1]]
    assert [marker.name for marker in rough_cut(plan).markers] == ["Line 1", "Line 3"]


def test_a_line_that_enumerates_gets_a_marker_for_each_item() -> None:
    script = [ScriptLine(1, "It asks: what it is about, who it is for, and which stack we need.")]
    words = spoken("It asks: what it is about, who it is for, and which stack we need.", at=0.0)

    assert cut_of(words, script).markers == [
        Marker("Line 1.1", "It asks: what it is about,", 0.0),
        Marker("Line 1.2", "who it is for,", 3.0),
        Marker("Line 1.3", "and which stack we need.", 5.0),
    ]


def test_what_was_muttered_before_a_pickup_take_is_still_reported() -> None:
    # The pickup is recovered as line 2's take, but the run it arrived in held more
    # than the line — and nothing said is allowed to vanish unreported.
    session = (
        spoken(LINE_1, at=0.0)
        + spoken(LINE_3, at=6.0)
        + spoken("Ugh sorry let me try that one once more", at=13.0)
        + spoken(LINE_2, at=20.0)
    )

    plan = build_plan(analysis(session), SCRIPT)

    assert [line.source_in_seconds for line in plan.lines] == [0.0, 20.0, 6.0]
    assert [leftover.retake_of for leftover in plan.leftovers] == [None]
    assert plan.leftovers[0].text.startswith("Ugh sorry")


def test_a_recording_with_no_script_to_compare_it_to_plans_nothing() -> None:
    plan = build_plan(analysis(clean_read()), [])

    assert rough_cut(plan).clips == []
    assert [leftover.retake_of for leftover in plan.leftovers] == [None]


def test_the_first_reading_of_a_line_is_the_one_that_plays() -> None:
    # Choosing between takes is ticket 07; until then the second reading is only
    # recorded as a retake, so nothing is lost and nothing is silently preferred.
    retaken = (
        spoken(LINE_1, at=0.0)
        + spoken(LINE_2, at=6.0)
        + spoken(LINE_2, at=13.0)
        + spoken(LINE_3, at=20.0)
    )

    plan = build_plan(analysis(retaken), SCRIPT)

    assert rough_cut(plan).clips[1] == Clip(6.0, 10.5, 4.5)
    assert [leftover.retake_of for leftover in plan.leftovers] == [SCRIPT[1]]


def test_the_rough_cut_is_named_for_the_project_panel() -> None:
    assert cut_of(clean_read()).name == "RoughCut"


def test_the_sequence_draws_on_the_recording_the_analysis_describes() -> None:
    assert cut_of(clean_read()).source == FIXTURE_SOURCE


def test_a_recording_of_any_length_is_cut_from_the_source_it_describes() -> None:
    source = SourceMedia(
        filename="other.mp4",
        duration_seconds=12.5,
        fps=30.0,
        ntsc=False,
        width=1280,
        height=720,
        audio_sample_rate=44100,
        audio_channels=1,
    )

    plan = build_plan(analysis(spoken(LINE_1, at=0.0), source), SCRIPT)

    assert rough_cut(plan).source == source


def test_a_recording_with_nothing_in_it_plans_an_empty_cut_rather_than_failing() -> None:
    plan = build_plan(analysis([]), SCRIPT)

    assert rough_cut(plan).clips == []
    assert plan.missing == SCRIPT


def test_the_output_duration_is_the_end_of_the_last_clip() -> None:
    sequence = Sequence(
        id="seq-1",
        name="RoughCut",
        source=FIXTURE_SOURCE,
        clips=[Clip(0.0, 10.0, 0.0), Clip(12.0, 20.0, 10.0)],
    )

    assert timeline_duration_seconds(sequence) == 18.0


def test_a_sequence_with_no_clips_lasts_no_time() -> None:
    assert timeline_duration_seconds(Sequence("seq-1", "RoughCut", FIXTURE_SOURCE)) == 0.0
