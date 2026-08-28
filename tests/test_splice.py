"""What the cut did with the ends of every clip, driven by hand-written recordings.

Every splice is widened into the quiet either side of it, so that a last consonant
still plays and a join sounds like a join rather than a word cut short. What is
asserted is therefore the cut — which piece of the recording each clip plays — and the
only thing that moves it is where the detector says the room was quiet.
"""

from conftest import FIXTURE_SOURCE, LINE_1, LINE_2, LINE_3, SCRIPT, cut_times, retakes, spoken

from roughcut.analysis import Analysis, Silence, Word
from roughcut.pauses import PauseSettings
from roughcut.plan import Clip, Plan, alternates, build_plan, rough_cut
from roughcut.script import ScriptLine
from roughcut.splice import SpliceSettings

ONE_LINE = [SCRIPT[0]]
"""Line 1 alone — the line every fixture below reads first, and some read only."""

QUIET_EITHER_SIDE = [Silence(0.0, 2.0), Silence(6.5, 10.0)]
"""The room before and after a line read from 2.0 to 6.5."""


def plan_for(
    words: list[Word],
    silences: list[Silence],
    *,
    settings: SpliceSettings | None = None,
    script: list[ScriptLine] | None = None,
    pauses: PauseSettings | None = None,
) -> Plan:
    analysis = Analysis(source=FIXTURE_SOURCE, words=words, silences=silences)
    return build_plan(
        analysis,
        script or ONE_LINE,
        pauses=pauses or PauseSettings(),
        splice=settings or SpliceSettings(),
    )


def test_a_take_with_quiet_either_side_is_widened_into_both() -> None:
    # The line was read from 2.0 to 6.5 and the room is quiet on both sides of it, so
    # both ends grow by the pad and the whole of the speech survives the splice.
    plan = plan_for(spoken(LINE_1, at=2.0), QUIET_EITHER_SIDE)

    assert cut_times(plan) == [(1.85, 6.65, 0.0)]


def test_speech_resuming_immediately_leaves_that_side_of_the_splice_unpadded() -> None:
    # Nothing quiet was detected between the two lines — a breath, a mutter, a word the
    # transcriber dropped — so neither line may grow into it. Only line 2's tail, where
    # the room does go quiet, gets a pad.
    plan = plan_for(
        spoken(LINE_1, at=0.0) + spoken(LINE_2, at=5.0),
        [Silence(9.5, 12.0)],
        script=SCRIPT[:2],
    )

    assert cut_times(plan) == [(0.0, 4.5, 0.0), (5.0, 9.65, 4.5)]


def test_two_takes_separated_by_a_short_gap_share_it_rather_than_both_claiming_it() -> None:
    # Two tenths of quiet between the lines and a pad of 0.15 s wanted either side of
    # it: each takes half. Both clips still play, and no frame of the recording is laid
    # down twice — the first clip ends exactly where the second one begins.
    plan = plan_for(
        spoken(LINE_1, at=0.0) + spoken(LINE_2, at=4.7),
        [Silence(4.5, 4.7)],
        script=SCRIPT[:2],
    )

    assert cut_times(plan) == [(0.0, 4.6, 0.0), (4.6, 9.2, 4.6)]


def test_a_take_at_either_end_of_the_recording_is_padded_only_on_the_inside() -> None:
    # Line 1 starts on the first frame and line 3 ends on the last: there is no
    # recording outside either of them to pad into, and the pad is refused rather than
    # reaching past the file.
    plan = plan_for(
        spoken(LINE_1, at=0.0) + spoken(LINE_3, at=81.75),
        [Silence(4.5, 81.75)],
        script=[SCRIPT[0], SCRIPT[2]],
    )

    assert cut_times(plan) == [(0.0, 4.65, 0.0), (81.6, 86.25, 4.65)]


def test_a_pad_never_reaches_past_the_end_of_the_recording() -> None:
    # The detector rounds its last region up to just past the end of the file, and a
    # pad wide enough to want all of it still stops on the last frame there is.
    plan = plan_for(
        spoken(LINE_1, at=80.0),
        [Silence(84.5, 86.3)],
        settings=SpliceSettings(padding_seconds=5.0),
    )

    assert cut_times(plan) == [(80.0, 86.25, 0.0)]


def test_a_pad_stops_where_the_room_stops_being_quiet() -> None:
    # A mutter was said half a second after the line and dropped for its length. A pad
    # of a whole second still stops dead where the quiet does: playing the head of
    # something nobody kept is the fault the corroboration is here to prevent.
    plan = plan_for(
        spoken(LINE_1, at=0.0) + spoken("Ugh sorry", at=5.0) + spoken(LINE_2, at=9.0),
        [Silence(4.5, 5.0), Silence(6.0, 9.0)],
        settings=SpliceSettings(padding_seconds=1.0),
        script=SCRIPT[:2],
        # Half a second of quiet, and the subject here is the pad that stops in it
        # rather than anything collapsed out of it.
        pauses=PauseSettings(threshold_seconds=0.7),
    )

    assert cut_times(plan) == [(0.0, 5.0, 0.0), (8.0, 13.5, 5.0)]


def test_a_pad_may_cross_a_word_the_transcriber_stretched_over_the_quiet() -> None:
    # The detector decides where the quiet is (decision 0001). A transcriber declares a
    # mutter to last two seconds when it was over in a moment, and the pad reaches into
    # that declared span because the audio under it is quiet — which is the only reason
    # a pad is ever possible, since almost every word butts against the next.
    plan = plan_for(
        spoken(LINE_1, at=0.0) + [Word("Ugh", 4.5, 6.5, 0.4)] + spoken(LINE_2, at=7.0),
        [Silence(5.0, 7.0)],
        script=SCRIPT[:2],
    )

    assert cut_times(plan) == [(0.0, 4.65, 0.0), (6.85, 11.5, 4.65)]


def test_a_kept_off_script_region_is_padded_on_the_same_rule_as_a_line() -> None:
    # Both take their bounds from word timestamps, so both bite off the same ends
    # without a pad. The aside grows at both ends like the lines either side of it.
    aside = "Sorry, my microphone was unplugged the whole time again."
    plan = plan_for(
        spoken(LINE_1, at=0.0) + spoken(aside, at=6.0) + spoken(LINE_2, at=13.0),
        [Silence(4.5, 6.0), Silence(10.5, 13.0)],
        script=SCRIPT[:2],
    )

    assert cut_times(plan) == [
        (0.0, 4.65, 0.0),
        (5.85, 10.65, 4.65),
        (12.85, 17.5, 9.45),
    ]


def test_a_marker_still_lands_on_the_words_it_names_once_the_clip_has_grown() -> None:
    # The clip now starts a pad before the first word, so the line's marker sits a pad
    # into it rather than on its front edge.
    plan = plan_for(spoken(LINE_1, at=2.0), QUIET_EITHER_SIDE)

    assert [
        round(marker.timeline_position_seconds, 3) for marker in rough_cut(plan).markers
    ] == [0.15]


def test_an_alternate_still_plays_exactly_as_it_was_recorded() -> None:
    # A rejected take is there to be auditioned and dragged into the cut, not used as
    # it stands, so nothing pads it — including where the cut beside it was padded.
    plan = plan_for(
        retakes(LINE_2, LINE_2),
        [Silence(4.5, 6.0), Silence(10.5, 13.0), Silence(17.5, 20.0)],
        script=SCRIPT,
    )

    assert alternates(plan).clips == [Clip(6.0, 10.5, 0.0)]


def test_the_padding_is_a_setting() -> None:
    plan = plan_for(
        spoken(LINE_1, at=2.0), QUIET_EITHER_SIDE, settings=SpliceSettings(padding_seconds=0.5)
    )

    assert cut_times(plan) == [(1.5, 7.0, 0.0)]


def test_a_padding_of_nothing_leaves_every_splice_on_the_words() -> None:
    plan = plan_for(
        spoken(LINE_1, at=2.0), QUIET_EITHER_SIDE, settings=SpliceSettings(padding_seconds=0.0)
    )

    assert cut_times(plan) == [(2.0, 6.5, 0.0)]
