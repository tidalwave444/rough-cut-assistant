# A region of repeated attempts is measured attempt by attempt

Containment is not taken across an off-script region in one pass. The region is cut into
attempts at the line beside it — greedily, in the order heard, each the longest run still
made mostly of that line's own words — and what those attempts cover is the fraction
decision 0007 reads against the bar. One bar, read twice: it says what counts as an
attempt, and then how much of the region they have to cover.

## Context

Decision 0007 settled the direction of the fraction and left its grain unstated, which in
practice meant one pass over the whole region. `matched_pairs` is monotonic, so a pass can
claim the line's words exactly once. A region holding the same restart three times over
therefore scores a third of what one attempt scores, five times over a fifth, and the
measure falls as the evidence rises: the plainer it is that a passage is nothing but
restarts, the surer it was to survive.

`Sequence 07` is where this showed. The region at 00:00:40.460 is 15.5 s of line 3
attempted again and again — 61 of its 63 tokens are line 3's own words — and it scored
**0.206** against a bar of 0.8 and played in the cut, marked. Measured attempt by attempt
it scores **1.000**.

This is the same dilution `settled/words.md` records as the reason "similarity" was
rejected, arriving by the other route: containment inherits it through its denominator,
which counts every repetition while the numerator can only pay for one.

Two alternatives were measured and rejected:

- **Repeated passes over what is left unclaimed**, until a pass claims nothing. Scores the
  region 0.968, but the last passes scavenge scattered function words rather than finding
  another attempt, so part of the answer is built from evidence of nothing.
- **Comparing the two as bags of words**, dropping order entirely. Scores 0.968 as well,
  and would call "we need a tool" three quarters of line 3. Order within an attempt is
  most of what distinguishes a restart from a sentence sharing its vocabulary.

Attempt segmentation separates further than either: on the same five cases the restarts
score 1.000 and the improvised sentences 0.118 to 0.368.

## Consequences

Whatever no attempt accounts for counts against the region, so a restart with a real
sentence tacked onto it is still kept — the sentence is the part that would be lost, and
this rule can only ever remove.

A region holding a single attempt is measured exactly as it was, so nothing about a
recording without repeats moves. `sequence.mp4`'s goldens are untouched by this change.

The bar can no longer be applied where the leftover is built: it belongs to the user, and
the measurement now needs it to say what an attempt is. So `align` names the adjacent line
a leftover most reads like and stops there, `offscript` takes the fraction, and
`Leftover.likeness` is gone rather than being computed at a grain nothing can use.
