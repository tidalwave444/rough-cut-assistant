# 15 — A near miss is the word it displaced

**What to build:** `wipe` read as the `vibe` it displaced. Alignment compares
exactly-equal tokens, so a one-character mishearing is a total miss: `Sequence 07` line 1
holds 6 of its 9 words, reports 67% coverage and carries a `least bad — incomplete` flag,
for a take that was read correctly from start to finish.

**Blocked by:** None

**Status:** ready-for-agent

## Listen for

1. `Sequence 07` line 1 — reported at full coverage with no flag, and still one clip. The
   flag is the fault being fixed; a line that gains a take instead has been matched too
   loosely.
2. `Sequence 07` line 1 at `00:03` of the source — the stumble removal now rests on
   `vibe`/`coding` said twice rather than on `part`, and the reading that plays is the
   complete one.
3. `sequence.mp4` line 1 at `00:00` — `the wipe` is still in the take and still audible. A
   near miss that now matches must not then be removed as something the line accounts for
   twice.
4. Both recordings, every line — no line gains a take it did not have, and no off-script
   region is absorbed into one. Coverage is what disqualifies a take, so loosening it
   loosens every judgement downstream at once.

- [ ] A transcript token close enough to a script word matches it, on a stated measure
- [ ] Short words are protected — `a` against `the`, `we` against `he` must not match, or
      coverage stops meaning anything
- [ ] The bar is a threshold and moves on a listen, not on a distribution — decision 0003
- [ ] Decision 0002 still holds: a matched near miss is a mishearing, so it stays in the
      take and is never removed for failing to be the word it matched
- [ ] `settled/words.md` gains the term, if the measure needs a name the project lacks
- [ ] Goldens re-recorded, and the report read for which lines moved and why
- [ ] Tests: a one-character mishearing matches; two short function words do not; a take
      that was already complete is unchanged

## Comments

This is the route decision 0010 prefers over priming the transcriber, and it is the one
most in keeping with what the project already believes: decision 0002 defines a mishearing
structurally, as a word with the script word it displaced sitting opposite it, which is
exactly what a near-miss match finds.

Below the seam and independent of 13 and 14 — a pure function over the analysis, so it
needs no GPU and no re-transcription. It does move the goldens, so land it in a known
order with 13 rather than alongside it.

The thirteen unmatched runs both recordings hold, with what stands opposite each, are in
`facts.md`. Eight are purely a mishearing. That is the corpus this bar is read against.

## Heard
