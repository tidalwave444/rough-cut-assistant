"""What the plan decided, driven by hand-written recordings.

Each fixture isolates one thing the cut has to get right: a clean read, a line
recorded out of order, a line never recorded at all, a line that enumerates, a line
read several times over, and something said that the script never asked for.
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

from roughcut.analysis import Analysis, SourceMedia, Word
from roughcut.offscript import OffScriptSettings
from roughcut.plan import (
    ALTERNATES,
    OFF_SCRIPT,
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
    """A recording the detector heard no quiet in.

    Not because a real one is like that, but because quiet is what moves a splice: a
    fixture with silence between its lines pads every clip in the file, and each
    assertion below would then be about two things at once. Where the quiet goes is
    `test_splice.py`'s subject, and shortening it is `test_pauses.py`'s.
    """
    return Analysis(source=source, words=words, silences=[])


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
    assert len(plan.off_script) == 1
    assert plan.off_script[0].text.startswith("Ugh sorry")


def test_a_recording_with_no_script_to_compare_it_to_keeps_all_of_it_as_off_script() -> None:
    # Nothing said can be shown to be a restart or a mutter without a script to read
    # it against, so the asymmetry does the only thing it can: keep it and mark it.
    plan = build_plan(analysis(clean_read()), [])

    assert [region.kept for region in plan.off_script] == [True]
    assert [marker.name for marker in rough_cut(plan).markers] == [OFF_SCRIPT]


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


UNPLANNED = "Sorry, my microphone was unplugged the whole time again."
"""Four and a half seconds of something not in the script, and meant."""


def session_with(aside: str) -> list[Word]:
    """The three lines read cleanly, with something else said between one and two."""
    return (
        spoken(LINE_1, at=0.0)
        + spoken(aside, at=6.0)
        + spoken(LINE_2, at=13.0)
        + spoken(LINE_3, at=20.0)
    )


def test_a_short_off_script_fragment_is_dropped_from_the_cut() -> None:
    # Half a second of speech after the last line: a mutter, not an idea.
    plan = build_plan(analysis(clean_read() + spoken("Ugh", at=20.0)), SCRIPT)

    assert timeline_duration_seconds(rough_cut(plan)) == 13.5
    assert [region.kept for region in plan.off_script] == [False]


def test_a_long_off_script_sentence_is_kept_where_it_was_said_and_marked() -> None:
    # Deleting a kept line in Premiere is one keystroke; recovering a deleted one
    # means knowing it existed. So it plays between the same two lines it was said
    # between, with a marker on it.
    plan = build_plan(analysis(session_with(UNPLANNED)), SCRIPT)

    assert rough_cut(plan).clips == [
        Clip(source_in_seconds=0.0, source_out_seconds=4.5, timeline_start_seconds=0.0),
        Clip(source_in_seconds=6.0, source_out_seconds=10.5, timeline_start_seconds=4.5),
        Clip(source_in_seconds=13.0, source_out_seconds=17.5, timeline_start_seconds=9.0),
        Clip(source_in_seconds=20.0, source_out_seconds=24.5, timeline_start_seconds=13.5),
    ]
    assert rough_cut(plan).markers[1] == Marker(OFF_SCRIPT, UNPLANNED, 4.5)


def test_a_kept_region_between_two_attempts_at_a_line_follows_that_line() -> None:
    # The mutter that introduces a retake was said after the line, not before it —
    # even though the reading that plays is the one on the far side of it.
    plan = build_plan(
        analysis(
            spoken(LINE_1, at=0.0)
            + spoken(UNPLANNED, at=6.0)
            + spoken(LINE_1, at=13.0)
            + spoken(LINE_2, at=20.0)
            + spoken(LINE_3, at=27.0)
        ),
        SCRIPT,
    )

    assert [marker.name for marker in rough_cut(plan).markers] == [
        "Line 1",
        OFF_SCRIPT,
        "Line 2",
        "Line 3",
    ]


def test_a_kept_region_follows_whatever_was_read_last_before_it() -> None:
    # Recorded 3, 2, an aside, 1. The aside was said after line 2, so it plays after
    # line 2 — not at the end, where line 3 being read first would otherwise put it.
    plan = build_plan(
        analysis(
            spoken(LINE_3, at=0.0)
            + spoken(LINE_2, at=6.0)
            + spoken(UNPLANNED, at=13.0)
            + spoken(LINE_1, at=20.0)
        ),
        SCRIPT,
    )

    assert [marker.name for marker in rough_cut(plan).markers] == [
        "Line 1",
        "Line 2",
        OFF_SCRIPT,
        "Line 3",
    ]


def test_a_failed_restart_of_the_line_beside_it_is_dropped() -> None:
    # Seven seconds in — far too long to be dropped for its length — but every word of
    # it is the line's own, which is what an abandoned attempt sounds like.
    script = [ScriptLine(1, "In the previous video we set up the project and got it running.")]
    restarted = "In the previous video we set up"
    words = spoken(restarted, at=0.0) + spoken(
        f"{restarted} the project and got it running.", at=10.0
    )

    plan = build_plan(analysis(words), script)

    assert rough_cut(plan).clips == [Clip(10.0, 16.5, 0.0)]
    assert [region.kept for region in plan.off_script] == [False]
    assert plan.off_script[0].reason == "cut — a restart of line 1"


def test_one_restart_said_over_and_over_is_still_one_restart() -> None:
    # The same abandoned attempt three times over, in one region. Measured in a single
    # pass it scores a third of what one attempt scores — the matcher is monotonic, so
    # the line's words can be claimed once — and the plainer the restart, the surer it
    # survived. Measured attempt by attempt it is what it sounds like. Decision 0009.
    script = [ScriptLine(1, "In the previous video we set up the project and got it running.")]
    restarted = "In the previous video we set up"
    words = spoken(" ".join([restarted] * 3), at=0.0) + spoken(
        f"{restarted} the project and got it running.", at=30.0
    )

    plan = build_plan(analysis(words), script)

    assert [region.kept for region in plan.off_script] == [False]
    assert plan.off_script[0].reason == "cut — a restart of line 1"


def test_a_restart_with_a_sentence_after_it_is_kept_for_the_sake_of_the_sentence() -> None:
    # What no attempt at the line accounts for counts against the region, so a restart
    # someone talked their way out of stays: the sentence is the part that would be lost.
    script = [ScriptLine(1, "In the previous video we set up the project and got it running.")]
    words = spoken(
        "In the previous video we set up, no, hold on, I want to say something else "
        "here about where all of this is actually going.",
        at=0.0,
    ) + spoken("In the previous video we set up the project and got it running.", at=30.0)

    plan = build_plan(analysis(words), script)

    assert [region.kept for region in plan.off_script] == [True]
    assert plan.off_script[0].reason == "kept — marked in place"


def test_an_off_script_region_on_the_stop_phrase_list_is_dropped() -> None:
    plan = build_plan(
        analysis(session_with("Let me try that again, I keep getting this line wrong.")),
        SCRIPT,
    )

    assert [region.kept for region in plan.off_script] == [False]
    assert plan.off_script[0].reason == 'cut — a stop phrase, "let me try that again"'


def test_how_long_an_off_script_region_must_run_to_survive_is_an_option() -> None:
    described = analysis(clean_read() + spoken("Well anyway.", at=20.0))

    assert [region.kept for region in build_plan(described, SCRIPT).off_script] == [False]
    assert [
        region.kept
        for region in build_plan(
            described, SCRIPT, off_script=OffScriptSettings(keep_seconds=0.5)
        ).off_script
    ] == [True]


def test_how_much_of_a_restart_has_to_be_the_line_is_an_option() -> None:
    # Seven of its eight words are the line's, which the default calls a restart.
    script = [ScriptLine(1, "In the previous video we set up the project and got it running.")]
    described = analysis(
        spoken("In the previous video we set up, sorry", at=0.0)
        + spoken("In the previous video we set up the project and got it running.", at=10.0)
    )

    assert [region.kept for region in build_plan(described, script).off_script] == [False]
    assert [
        region.kept
        for region in build_plan(
            described, script, off_script=OffScriptSettings(restart_likeness=0.95)
        ).off_script
    ] == [True]


def test_the_stop_phrase_list_is_an_option() -> None:
    described = analysis(session_with("Honestly this whole section needs rewriting later."))

    assert [region.kept for region in build_plan(described, SCRIPT).off_script] == [True]
    assert [
        region.kept
        for region in build_plan(
            described, SCRIPT, off_script=OffScriptSettings(stop_phrases=("needs rewriting",))
        ).off_script
    ] == [False]


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


def test_only_the_last_attempt_at_a_line_s_ending_reaches_the_cut() -> None:
    # Green on purpose, and the one thing the listen of 28 August asked for that the
    # tool already does: the ending of line 2 tried three times inside one reading, and
    # only the third reaching the timeline. What the listen heard at 07:13–11:02 is this
    # rule never firing, because the transcriber wrote one long word where the three
    # attempts were and there was nothing for it to find. Pinned here so that giving it
    # the words back is the whole of that fix.
    words = spoken(
        "Today we are moving from setup to actual to actual to actual development.", at=0.0
    )

    assert cut_of(words, [SCRIPT[1]]).clips == [
        Clip(source_in_seconds=0.0, source_out_seconds=3.0, timeline_start_seconds=0.0),
        Clip(source_in_seconds=5.0, source_out_seconds=6.5, timeline_start_seconds=3.0),
    ]


# The two below are ticket 15, and the evidence for it is the cut made on 29 August after
# the second pass of ticket 14 landed. Recovering the speech buried under one long word
# means recovering the model's mishearings with it, and alignment compares tokens for
# equality — so every word the second pass hands back that the model heard slightly wrong
# lowers the line's coverage instead of raising it. `Sequence 07` came back with three
# lines flagged where it had two, and line 1 stopped having its abandoned attempt removed
# at all, because `white coating` repeats no word of the line it was misheard from.


def test_a_line_the_transcriber_misheard_is_still_a_complete_reading_of_it() -> None:
    # `rail` for `real`, `wipe` for `vibe`, `coating` for `coding` — one character each,
    # and the line is reported at 67% and flagged as the least bad, for a reading that was
    # read correctly from start to finish. What identifies a mishearing is structural: the
    # script word it displaced sits opposite it (decision 0002), which is exactly what a
    # near-miss match finds.
    misheard = spoken("Building a rail project with wipe coating, part two.", at=0.0)

    plan = build_plan(analysis(misheard), [SCRIPT[0]])

    assert plan.flagged == []
    assert rough_cut(plan).clips == [Clip(0.0, 4.5, 0.0)]


def test_two_short_words_a_letter_apart_are_not_the_same_word() -> None:
    # Green, and the rail under the one above: `a` is not `the` and `we` is not `he`. A
    # measure loose enough to match them makes coverage stop meaning anything, and
    # coverage is what disqualifies a take — so loosening it loosens every judgement
    # downstream at once. This reading really is two words short and must go on saying so.
    swapped = spoken("In a next part we will begin a implementation.", at=0.0)

    plan = build_plan(analysis(swapped), [SCRIPT[2]])

    assert [line.line.number for line in plan.flagged] == [3]


def test_a_near_miss_is_found_past_a_word_the_line_does_not_account_for() -> None:
    # `Sequence 07` line 1 as the second pass leaves it: `with a wipe coating`, where the
    # `a` is the transcriber's own and `wipe coating` is `vibe coding`. Exact matching
    # steps over a word the line does not account for and goes on; near-miss matching
    # stops at it, so the line reaches `with` and everything after it — its own ending
    # included — becomes an off-script region that plays beside it.
    #
    # Which is decision 0002 read at half strength. A mishearing is identified by the
    # script word it displaced sitting opposite it, and `vibe` is opposite `wipe` once
    # the intruder is stepped over. Whether it is stepped over is not the mishearing's
    # business.
    heard = spoken("Building a real project with a wipe coating part two.", at=0.0)

    plan = build_plan(analysis(heard), [SCRIPT[0]])

    assert plan.flagged == []
    assert plan.off_script == []


def test_a_line_keeps_its_ending_across_an_attempt_it_abandoned() -> None:
    # `Sequence 07` line 1 once the second pass has written the buried attempt down:
    # `oh no white coating one no no` sits between `coding` and `part two`, and the take
    # ends before it. The line's own last two words become a leftover that plays beside
    # it, and the line is flagged for stopping two words short of an ending it reached.
    #
    # `SPAN_GAP_TOKENS` tolerates four such words and not five, and until the second pass
    # landed the run here was `part one no no` — four. Nothing about the recording
    # changed; the same abandoned attempt written down more fully is what pushed it over.
    # So a rule for telling a stumble from a restart is now deciding it on how well the
    # transcriber heard, which is the one thing it cannot mean.
    heard = spoken(
        "Building a real project with a wipe coating oh no white coating one no no part two.",
        at=0.0,
    )

    plan = build_plan(analysis(heard), [SCRIPT[0]])

    assert plan.flagged == []
    assert plan.off_script == []
