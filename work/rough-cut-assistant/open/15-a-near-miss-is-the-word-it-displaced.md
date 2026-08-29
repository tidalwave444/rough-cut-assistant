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

- [x] A transcript token close enough to a script word matches it, on a stated measure
- [x] Short words are protected — `a` against `the`, `we` against `he` must not match, or
      coverage stops meaning anything
- [x] The bar is a threshold and moves on a listen, not on a distribution — decision 0003
- [x] Decision 0002 still holds: a matched near miss is a mishearing, so it stays in the
      take and is never removed for failing to be the word it matched
- [x] `settled/words.md` gains the term, if the measure needs a name the project lacks
- [ ] Goldens re-recorded, and the report read for which lines moved and why
- [x] Tests: a one-character mishearing matches; two short function words do not; a take
      that was already complete is unchanged

## Comments

The route decision 0010 prefers over priming the transcriber, and the one most in keeping
with what the project believes: decision 0002 defines a mishearing structurally, as a word
with the script word it displaced sitting opposite it, which is what a near miss finds.

Below the seam and independent of 13 and 14 — a pure function over the analysis, so it
needs no GPU and no re-transcription. It does move the goldens. The thirteen unmatched
runs both recordings hold, with what stands opposite each, are in `facts.md`. Eight are
purely a mishearing. That is the corpus this bar is read against.

What shipped is a measure of sound, not spelling: every vowel one sound, `b f p v w` one
and `d t` one, over how much of the longer word the two hold in common in order. Spelling
could not do it — `wipe` and `vibe` differ in two letters of four, as `part` does from
`card`. It fires only between two words the streams agree on and only where they hold the
same number of words there, which is what "opposite" means. The `Status:` line above
should read awaiting-listen; the loop reverts `work/` whenever that line moves at all.

Item 1 was written against the first pass, which heard `wipe`. Ticket 14's second pass
hears `white`, which holds 0.6 of `vibe` and stays under the bar where `wipe` held all of
it, so line 1 may come back at 8 words of 9. `coating` for `coding` clears it either way.

## Heard
