# 12 — A restart said more than once

**What to build:** The 15.5 s of line 3 attempted over and over at `00:00:40.460` of
`Sequence 07` out of the cut. It plays today, marked as off-script, because containment
was taken across the whole region in one pass: the matcher is monotonic, so a restart said
five times scores a fifth of what it scores said once, and the measure falls as the
evidence rises.

**Blocked by:** None

**Status:** awaiting-listen

## Listen for

1. `Sequence 07` at `00:21` on the timeline — line 3 ends and line 4 begins, with no
   "we need a previous part" between them. A click there means the splice needs padding
   the removal did not ask for.
2. `Sequence 07` line 3, ending at `00:21.703` — it still ends on the words it ended on
   before. The removed region begins with line 3's own tail, so if the line lost its
   ending, the region was cut wider than what was said.
3. `sequence.mp4`, whole — nothing about it moves. Its one off-script region is 0.1 s and
   goes on length; if anything else there changed, the new measure is removing on its own.

- [x] Containment is measured attempt by attempt: the region is cut into the longest runs
      that are each mostly the adjacent line's own words, and what they cover is the
      fraction the bar is read against
- [x] One bar does both jobs — `--off-script-restart-likeness` still means "how much of
      what was said has to be the line", and still keeps the region when raised to 0.95
- [x] A region no attempt fully accounts for is still kept: a restart with a real sentence
      after it stays, because the sentence is the part that would be lost
- [x] `Leftover.likeness` is gone — `align` names the adjacent line, `offscript` measures
- [x] `sequence.mp4`'s goldens are unchanged, and re-recorded goldens are not needed
- [x] Tests: the same restart three times over is cut where one pass scored it 0.381 and
      kept it; a restart talked out of into a sentence is kept

## Comments

Found by reading the `Sequence 07` report: the region was the only off-script material the
tool has ever kept, and it is 61 tokens of line 3's own words out of 63.

Why the grain of the fraction is a decision and not a tuning, with the two alternatives
measured and rejected: **decision 0009**. Decision 0007 is amended where it named where
the measurement lives.

`Sequence 07` goes 48.586 s → 39.484 s, and five of its nineteen shortened pauses go with
the region, which is why the count drops to fourteen.

## Heard
