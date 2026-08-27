# 16 — Words the model does not hold

**What to build:** A short list of corrections applied to the transcript after it is
written, for phrases the model gets wrong every time because it does not have them.
`vibe coding` is heard as `wipe coating` or `wipe coding` on both recordings — a term that
postdates the model's training data, which no decoding setting reaches.

**Blocked by:** 15

**Status:** ready-for-agent

## Listen for

1. `Sequence 07` line 1 — the report names every substitution it made, with what was heard
   and what replaced it. A correction nothing records is a transcript that cannot be
   checked against the recording.
2. Both recordings, whole — nothing outside the list moved.
3. Line 1 of each recording, with the list and without it. If 15 already carries these
   lines, this ticket is not needed and should be closed saying so. Read that comparison
   before building anything.

- [ ] The list is given by the operator and is not built into the tool — the words a
      recording gets wrong belong to the recording, not to the project
- [ ] Where it applies is stated and reasoned: in `analyze`, and therefore in the
      fingerprint; or below the seam as a render-time option. Not both
- [ ] Every substitution reaches the report, on the same reasoning as a removed stretch —
      nothing else records that the model said something different
- [ ] A substitution changes words, never timings
- [ ] Tests: a listed phrase is corrected; an unlisted near miss is left to 15; an empty
      list changes nothing

## Comments

Last of the three routes decision 0010 puts in place of priming the transcriber, and
deliberately the least preferred: 14 and 15 both leave the transcript exactly as the model
wrote it, and this one does not. It earns its place only where a phrase is simply absent
from the model and near-miss matching cannot reach it.

What it has over priming, and the reason it is on the list at all: it is auditable,
deterministic, reversible, and it cannot invent agreement with the script in a place the
script was never read. Priming offers none of those — see decision 0010 for what it did to
`sequence.mp4` when it was tried.

Expect this ticket to shrink after 15 lands. Do not build it before measuring what is left.

## Heard
