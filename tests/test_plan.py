"""What the plan decided, driven by hand-written recordings.

Each fixture isolates one thing the cut has to get right: a clean read, a line
recorded out of order, a line never recorded at all, a line that enumerates, and a
line read several times over.
"""

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

from roughcut.analysis import Analysis, Silence, SourceMedia, Word
from roughcut.plan import (
    ALTERNATES,
    ROUGH_CUT,
    Clip,
    Marker,
    Sequence,
    alternates,
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
    assert len(plan.leftovers) == 1
    assert plan.leftovers[0].text.startswith("Ugh sorry")


def test_a_recording_with_no_script_to_compare_it_to_plans_nothing() -> None:
    plan = build_plan(analysis(clean_read()), [])

    assert rough_cut(plan).clips == []
    assert len(plan.leftovers) == 1


def test_the_last_complete_reading_of_a_line_is_the_one_that_plays() -> None:
    # The recording behaviour is the selector: a person re-records until satisfied and
    # then stops, so the third attempt is the one they meant to keep.
    plan = build_plan(analysis(retakes(LINE_2, LINE_2, LINE_2)), SCRIPT)

    assert rough_cut(plan).clips[1] == Clip(20.0, 24.5, 4.5)


def test_a_truncated_last_reading_is_passed_over_for_the_complete_one_before_it() -> None:
    plan = build_plan(analysis(retakes(LINE_2, LINE_2, LINE_2_STOPS_SHORT)), SCRIPT)

    assert rough_cut(plan).clips[1] == Clip(13.0, 17.5, 4.5)


def test_when_every_reading_falls_short_the_least_bad_plays_and_the_line_is_flagged() -> None:
    # Six words, then seven, then six again: the middle attempt is neither the most
    # recent nor the first, so only "the one that covers most of the line" selects it.
    plan = build_plan(
        analysis(
            retakes(LINE_2_STOPS_SHORT, f"{LINE_2_STOPS_SHORT} to", LINE_2_STOPS_SHORT)
        ),
        SCRIPT,
    )

    assert rough_cut(plan).clips[1] == Clip(13.0, 16.5, 4.5)
    assert [line.line.number for line in plan.flagged] == [2]


def test_a_line_read_once_plays_and_leaves_the_alternates_sequence_empty() -> None:
    # Both sequences are always emitted, so one import gives both: a line read once
    # simply contributes nothing to the second.
    plan = build_plan(analysis(clean_read()), SCRIPT)

    assert [sequence.name for sequence in plan.sequences] == [ROUGH_CUT, ALTERNATES]
    assert alternates(plan).clips == []
    assert [len(line.chosen.decisions) for line in plan.lines] == [1, 1, 1]
    assert plan.flagged == []


def test_the_readings_that_lost_are_laid_end_to_end_in_a_second_sequence() -> None:
    plan = build_plan(analysis(retakes(LINE_2, LINE_2, LINE_2)), SCRIPT)

    assert alternates(plan).clips == [
        Clip(source_in_seconds=6.0, source_out_seconds=10.5, timeline_start_seconds=0.0),
        Clip(source_in_seconds=13.0, source_out_seconds=17.5, timeline_start_seconds=4.5),
    ]


def test_each_alternate_is_marked_with_its_line_its_take_number_and_why_it_lost() -> None:
    plan = build_plan(analysis(retakes(LINE_2, LINE_2, LINE_2_STOPS_SHORT)), SCRIPT)

    assert alternates(plan).markers == [
        Marker("Line 2 take 1", "a later take was also complete", 0.0),
        Marker("Line 2 take 3", "truncated — stopped 3 words short", 4.5),
    ]


def test_a_reading_that_stumbles_too_often_is_passed_over_for_a_cleaner_one() -> None:
    plan = build_plan(
        analysis(
            retakes(LINE_2, "Today we um are uh moving from um setup to actual development.")
        ),
        SCRIPT,
    )

    assert rough_cut(plan).clips[1] == Clip(6.0, 10.5, 4.5)
    assert plan.lines[1].chosen.decisions[1].fault == "disfluent — 3 ums and uhs"


def test_a_line_whose_earlier_attempt_fell_short_says_so_in_one_sentence() -> None:
    plan = build_plan(analysis(retakes(LINE_2_STOPS_SHORT, LINE_2)), SCRIPT)

    assert (
        plan.lines[1].chosen.summary
        == "take 2 of 2; take 1 truncated — stopped 3 words short"
    )


def test_every_take_of_a_line_is_recorded_with_what_became_of_it() -> None:
    plan = build_plan(analysis(retakes(LINE_2, LINE_2, LINE_2_STOPS_SHORT)), SCRIPT)

    chosen = plan.lines[1].chosen
    assert [decision.take.number for decision in chosen.decisions] == [1, 2, 3]
    assert [decision.take.start_seconds for decision in chosen.decisions] == [6.0, 13.0, 20.0]
    assert chosen.selected.take.number == 2
    assert chosen.summary == "take 2 of 3; take 3 truncated — stopped 3 words short"


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
