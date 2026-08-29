# 17 — The two edges of a removal, and the check that blocks one of them

**What to build:** A removal's two edges placed against the sound like every other splice.
The head is done; the tail waits on a decision from the operator, because the two checks
that ask for it cannot both be satisfied.

**Blocked by:** A locked check only a person may move — see the finding below.

**Status:** ready-for-agent

## Listen for

1. `Sequence 07` at `14:37` — `we prepared the project` played as `the proj`. The tail of
   the word before a removal should finish before the cut.
2. `Sequence 07` at `03:04` — a blank section opening what plays after a removal. The word
   after the splice should arrive on time.

- [x] The head of what plays after a removal is trimmed to its sound and padded back
- [ ] The tail of what plays before one reaches the sound the transcriber stopped short of
- [ ] `tests/test_stumbles.py` no longer holds two checks that contradict each other

## Comments

The head half shipped on 29 August. The rule is the one the green check beside it is named
for: **an edge may move only into quiet the removal does not itself reach into.**
`Silence(4.2, 5.1)` against a removal at (3.5, 4.5) begins before the removal ends, so the
removal owns that quiet and the head stays at 4.5 —
`test_quiet_a_removal_only_reaches_into_is_left_to_the_removal_as_well`, green. `Silence(
4.5, 5.1)` begins exactly where the removal ends, so the head trims to 5.1 and pads back
to 4.95 — `test_the_quiet_a_removal_ends_in_does_not_play_after_the_splice`, now green too.
`bounded_by_sound` is handed every silence and filters to the ones outside the removal;
`quiet_left_whole` is gone, since at the 0.2 s bar it was empty beside every removal.

The tail half is not reachable, and this is the finding.
`test_quiet_a_removal_takes_with_it_is_not_also_a_shortened_pause` is green with
`Silence(3.6, 4.4)` and pins the first clip's out point at 3.5.
`test_a_word_beside_a_removal_keeps_the_tail_the_transcriber_stopped_short_of` is red with
`Silence(3.6, 4.2)` and asks for 3.6 or later. Both stretches of quiet lie wholly inside
the same removal at (3.5, 4.5), both are pauses at the defaults, and they differ in
nothing but 0.2 s of length. No rule that reads where the sound is can answer them
differently; handing every silence to `bounded_by_sound` gives 3.65 for both, turning one
red check green and one green check red.

The two were written apart. The green one dates from ticket 11, where the subject was that
a pause and a removal never report the same second twice, and it asserts a whole cut to say
so — the out point at 3.5 is incidental to what it is about. The red one is the listen of
28 August, and by its reasoning the green one's fixture has the same fault in it: the tail
of `coding` runs to 3.6 there too, and 3.5 clips it.

So the question for the operator is whether that green check should go on asserting a whole
cut. If it asserted `plan.shortened == []` and the clip count, both could hold at once.
That is an edit to `tests/`, which is locked to the loop and not to a person.

## Heard
