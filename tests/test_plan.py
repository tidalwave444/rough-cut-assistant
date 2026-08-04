from conftest import FIXTURE_SOURCE

from roughcut.analysis import Analysis, Silence, SourceMedia, Word
from roughcut.plan import Clip, Sequence, build_plan, timeline_duration_seconds
from roughcut.script import ScriptLine

SCRIPT = [ScriptLine(1, "Part 2."), ScriptLine(2, "The end.")]


def analysis(source: SourceMedia = FIXTURE_SOURCE) -> Analysis:
    return Analysis(
        source=source,
        words=[Word("Part", 0.5, 0.8, 0.9), Word("two.", 0.8, 1.2, 0.9)],
        silences=[Silence(1.2, 4.0)],
    )


def rough_cut() -> Sequence:
    sequences = build_plan(analysis(), SCRIPT).sequences
    assert len(sequences) == 1
    return sequences[0]


def test_the_whole_recording_plays_as_one_clip() -> None:
    # The trivial cut of ticket 04: nothing removed, nothing chosen. Later tickets
    # make this cut better; this one makes it exist.
    assert rough_cut().clips == [
        Clip(source_in_seconds=0.0, source_out_seconds=86.25, timeline_start_seconds=0.0)
    ]


def test_the_rough_cut_is_named_for_the_project_panel() -> None:
    assert rough_cut().name == "RoughCut"


def test_the_sequence_draws_on_the_recording_the_analysis_describes() -> None:
    assert rough_cut().source == FIXTURE_SOURCE


def test_a_recording_of_any_length_is_cut_to_its_own_length() -> None:
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

    plan = build_plan(analysis(source), SCRIPT)

    assert plan.sequences[0].clips[0].source_out_seconds == 12.5


def test_the_output_lasts_as_long_as_the_source_while_nothing_is_removed() -> None:
    assert timeline_duration_seconds(rough_cut()) == 86.25


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
