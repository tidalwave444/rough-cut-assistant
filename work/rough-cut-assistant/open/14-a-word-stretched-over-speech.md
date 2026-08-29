# 14 — A word stretched over speech

**What to build:** Speech the transcriber collapsed into one long word written down, by
handing that stretch back to the model on its own. `Sequence 07` line 1 holds 2.53 s of
audible speech under the single word `part`, declared 3.48–8.64 at confidence 0.22. The
cut removes that speech as part of a stumble without ever knowing it was speech.

**Blocked by:** 13

**Status:** ready-for-agent

## Listen for

1. `Sequence 07` line 1 at `00:03` of the source — the operator hears `with vibe co… tuu…
   oh no… vibe coding`. The second pass recovers them as `oh no white coating`, and the
   report does not quote them in the removal: on 29 August the removal stopped happening
   at all, because the rule keys on a repeat and `white coating` repeats no word of the
   line. So this listen is for the words being *there* — in the transcript and in what
   plays — and the removal is ticket 15's to bring back.
2. `Sequence 07` line 1 on the timeline — the reading that plays is the finished one, not
   the abandoned one. This is the whole point of the ticket: today the good take is inside
   the removed stretch, in the part no word was ever written for.
3. `sequence.mp4`, whole — unchanged. Nothing there buries more than 2 s under one word,
   so any movement means the trigger fires too easily.
4. Anywhere a re-decoded stretch meets its neighbours — no click, and no word landing
   outside the span it was decoded from.

- [ ] A word whose audible span — its duration less the quiet the detector hears inside it
      — exceeds a bar is decoded again on its own, and the words that come back replace it
- [ ] The bar is a setting on `AnalysisSettings`, and therefore in the fingerprint
- [ ] The second pass is given no prompt and no vocabulary — decision 0010
- [ ] Times from the second pass are offset back onto the recording's own timeline, and a
      word from it never falls outside the stretch it was decoded from
- [ ] The seam holds: this is `analyze`'s work, and nothing below it learns a new field
- [ ] Goldens re-recorded
- [ ] Tests: a stretched low-confidence word is re-decoded; an ordinary long word is not;
      the replacement words keep the order and the timeline of what they replaced

## Comments

Proved before the ticket was written. The same model, `language="en"`, no prompt: the
whole file gives `part` for that stretch; 3.3–9.2 s handed over alone gives `oh no white
coating part`. Whisper cannot see the speech inside a 30 s window that is mostly silence,
and the word-timestamp DTW then stretches the neighbouring word across the gap.
`facts.md` has the table.

`chunk_length=10` from ticket 13 halves buried time across the recording — 11.8 s to
6.2 s — and leaves this span untouched at 2.50 s. The two fixes do not overlap.

No schema change is needed to find the spans: word timings and the detected silences are
both in the artifact already.

## Heard
