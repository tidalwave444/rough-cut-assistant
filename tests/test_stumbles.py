"""What came out from inside a take, driven by hand-written recordings.

Every fixture here is line 1 read once with something in the middle of it that the
line does not account for, and the whole subject is which of those things comes out.
A stumble must go; a word the transcriber merely misheard was spoken perfectly well,
so deleting it would delete real speech and it stays.

Nearly all of them hold no silence at all, because nothing here is decided by the room:
a removal is triggered by the words and guarded by the line's own coverage. What the
quiet does to a clip is `test_pauses.py`'s subject and `test_splice.py`'s. The two
fixtures that do describe quiet are about the one place the two meet — a stretch a
pause and a removal would otherwise both claim to have taken.
"""

from conftest import FIXTURE_SOURCE, LINE_1, SCRIPT, cut_times, spoken

from roughcut.analysis import Analysis, Silence, Word
from roughcut.plan import Plan, build_plan, rough_cut, timeline_duration_seconds
from roughcut.script import ScriptLine

ONE_LINE = [SCRIPT[0]]
"""`Building a real project with vibe coding — Part 2.`, which is what is read below."""

STUMBLED = "Building a real project with vibe coding part no part two."
"""Line 1 with `part` said, abandoned and said again — `part no` is what comes out."""


def plan_for(
    words: list[Word],
    script: list[ScriptLine] | None = None,
    silences: list[Silence] | None = None,
) -> Plan:
    return build_plan(
        Analysis(source=FIXTURE_SOURCE, words=words, silences=silences or []),
        script or ONE_LINE,
    )


def read(text: str, silences: list[Silence] | None = None) -> Plan:
    """One reading of line 1, as the transcriber heard it, from the top of the file."""
    return plan_for(spoken(text, at=0.0), silences=silences)


def test_a_stumble_that_repeats_a_word_of_the_line_comes_out() -> None:
    # `part` is said, abandoned and said again. The stretch between the two utterances
    # is what the speaker threw away, so it is what the cut throws away: the line plays
    # as `…vibe coding, part two.`
    plan = read(STUMBLED)

    assert cut_times(plan) == [(0.0, 3.5, 0.0), (4.5, 5.5, 3.5)]
    assert [removal.text for removal in plan.removed] == ["part no"]


def test_a_word_the_transcriber_misheard_is_left_where_it_was_spoken() -> None:
    # `the wipe` is `vibe` misheard, and the script word it displaced sits opposite it.
    # Nothing was said twice and nothing stands unaccounted for, so the take reaches
    # the timeline in one piece — this is speech, not a stumble.
    plan = read("Building a real project with the wipe coding part two.")

    assert cut_times(plan) == [(0.0, 5.0, 0.0)]
    assert plan.removed == []


def test_a_repetition_that_would_cost_the_line_a_word_of_its_own_is_refused() -> None:
    # `a` was said twice, so the repeat test fires — and the stretch between the two
    # utterances is `a real project with`, three of which are the line's own words. The
    # line either keeps all of them or the removal does not happen.
    plan = read("Building a real project with a wipe coding part two.")

    assert cut_times(plan) == [(0.0, 5.0, 0.0)]
    assert plan.removed == []


def test_a_run_with_no_script_words_left_opposite_it_comes_out() -> None:
    # `wipe` stands where the line has already been fully accounted for: `coding` was
    # said before it and `part` after it, with nothing of the line in between. So it
    # cannot be the line misheard, which is the only reason there is to keep it.
    plan = read("Building a real project with vibe coding wipe part two.")

    assert cut_times(plan) == [(0.0, 3.5, 0.0), (4.0, 5.0, 3.5)]
    assert [removal.text for removal in plan.removed] == ["wipe"]


def test_two_stumbles_in_one_line_both_come_out() -> None:
    # The second is weighed against a take the first has already been taken out of,
    # because what a removal costs the line depends on what has gone already: the word
    # a stumble displaced is only back in the line's hands once the stumble is gone.
    plan = read("Building a real project with vibe wipe coding part no part two.")

    assert cut_times(plan) == [(0.0, 3.0, 0.0), (3.5, 4.0, 3.0), (5.0, 6.0, 3.5)]
    assert [removal.text for removal in plan.removed] == ["wipe", "part no"]


def test_a_clean_take_is_left_whole() -> None:
    plan = read(LINE_1)

    assert cut_times(plan) == [(0.0, 4.5, 0.0)]
    assert plan.removed == []


def test_every_removal_says_where_it_was_how_long_it_ran_and_what_was_said() -> None:
    # The report is the only record that a removed stretch was ever spoken, so the plan
    # carries everything a person needs in order to go back and listen to it.
    plan = read(STUMBLED)

    removal = plan.removed[0]
    assert (removal.start_seconds, removal.end_seconds) == (3.5, 4.5)
    assert removal.line.number == 1
    assert removal.text == "part no"
    assert removal.fault == '"part" said twice'


def test_a_run_removed_for_having_nothing_opposite_it_says_so() -> None:
    plan = read("Building a real project with vibe coding wipe part two.")

    assert plan.removed[0].fault == "nothing of the line opposite it"


def test_quiet_a_removal_takes_with_it_is_not_also_a_shortened_pause() -> None:
    # The speaker stumbled and paused in the middle of the stumble. The whole stretch
    # goes, so the second inside it is removed once and reported once — as a removal,
    # which is the thing that took it.
    plan = read(STUMBLED, [Silence(3.6, 4.4)])

    assert cut_times(plan) == [(0.0, 3.5, 0.0), (4.5, 5.5, 3.5)]
    assert [removal.text for removal in plan.removed] == ["part no"]
    assert plan.shortened == []


def test_quiet_a_removal_only_reaches_into_is_left_to_the_removal_as_well() -> None:
    # Half of this pause is inside the stumble and half is not. Collapsing what is left
    # would have the pause and the removal each report taking the same half second, so
    # the removal keeps the whole stretch and the pause table says nothing about it.
    plan = read(STUMBLED, [Silence(4.2, 5.1)])

    assert cut_times(plan) == [(0.0, 3.5, 0.0), (4.5, 5.5, 3.5)]
    assert plan.shortened == []


def test_a_marker_after_a_removal_moves_with_the_words_it_names() -> None:
    # The line enumerates, so its third beat is marked where `and which stack` is
    # reached — and the speaker stumbled on `and` a second before reaching it.
    script = [ScriptLine(1, "It asks: what it is about, who it is for, and which stack we need.")]
    words = spoken(
        "It asks: what it is about, who it is for, and no and which stack we need.", at=0.0
    )

    plan = plan_for(words, script)

    assert [removal.text for removal in plan.removed] == ["and no"]
    assert [
        round(marker.timeline_position_seconds, 3) for marker in rough_cut(plan).markers
    ] == [0.0, 3.0, 5.0]


def test_a_take_the_cut_passed_over_reaches_the_alternates_exactly_as_recorded() -> None:
    # An alternate is there to be auditioned and dragged into the cut rather than used
    # as it stands, so nothing is taken out of the middle of one.
    plan = plan_for(spoken(STUMBLED, at=0.0) + spoken(LINE_1, at=8.0))

    assert cut_times(plan) == [(8.0, 12.5, 0.0)]
    assert plan.removed == []
    assert timeline_duration_seconds(rough_cut(plan)) == 4.5
