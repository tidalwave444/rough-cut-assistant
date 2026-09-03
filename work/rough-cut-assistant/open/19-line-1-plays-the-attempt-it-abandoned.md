# 19 — Line 1 plays the attempt it abandoned

**What to build:** The abandoned reading of line 1 out of the cut. It plays in full today —
7.67 s of `a wipe coating / oh no / white coating / one no no` before the finished
`part 2` — and the report calls the line complete while it does so.

**Blocked by:** None

**Status:** ready-for-agent

## Listen for

1. `Sequence 07` at `00:00` — line 1 plays once, ending on `vibe coding, part 2`. It should
   run about 3 s, not 7.67 s. If the `oh no` is still there the removal still is not firing.
2. `Sequence 07` line 1 in the report — `Stumbles cut` counts the removal. A line at 100%
   coverage with nothing removed from it is the exact shape of this fault.
3. `sequence.mp4` line 1 at `00:00` — `the wipe` is still there and still audible. It is
   `vibe` misheard across two words, and the rule this ticket narrows is what keeps it.

- [ ] A run beside a near miss is judged by what it is, not spared for standing next to one
- [ ] The `the wipe` case keeps working — one word of a two-word mishearing, not seven
- [ ] `Sequence 07`'s golden moves and line 1's clip count falls
- [ ] Tests: a two-word mishearing keeps its other half; a long run beside a near miss goes

## Comments

Found by the operator's listen of 31 August, on the XML that had been reported to them as
fixed. What they heard: everything but the blank sections is much as it was.

The cause is `_beside_a_near_miss` in `stumbles.py`, added so that near-miss matching would
not break `test_a_word_the_transcriber_misheard_is_left_where_it_was_spoken`. It spares any
unmatched run with a near miss on either side of it. For `the wipe` — the transcriber
writing two words where the line has one — that is right. It has no bound, so the seven
words and 6.5 s of `oh no white coating one no no` are spared too, because `coating` before
them was matched as `coding`.

Nothing else fires on that run. `_repeats` compares text for equality, so the second
`coating` does not read as the line's `coding`; `_unaccounted` would have taken it and is
what `_beside_a_near_miss` overrules.

Why the checks did not see it: coverage was 100% and every check asserted coverage, flags
or off-script regions. **Decision 0011** is what that cost. The `Sequence 07` golden now
holds the 11 clipitems, so this fault is committed and any fix shows as a diff.

## Heard
