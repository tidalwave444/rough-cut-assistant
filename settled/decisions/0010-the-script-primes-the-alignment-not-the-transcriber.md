# The script primes the alignment, not the transcriber

The transcriber is never told what the script says. It is given the recording, sensible
decoding settings and nothing else, and what it writes down is what it heard. Where its
words and the script's words differ by a hair — `wipe` against `vibe`, `rail` against
`real` — the difference is reconciled where the two texts are compared, not by leaning on
the model until it produces the expected word.

## Context

Both recordings hear `vibe coding` as `wipe coating`. Priming Whisper with the script line
as `initial_prompt` fixes it outright: `Building a real project with vibe coding — Oh no,
vibe coding — Part 1.` where the unprimed run gives `Building a rail project with a wipe
coating part 1.` It is the only thing tried that recovers the phrase — a generic
vocabulary list, as `hotwords` or as a prompt, does not. It also recovers the 2.53 s of
speech buried under the word `part`, which no decoding setting reaches.

So the rejected alternative is the one that works, and it is rejected on what it costs
rather than on what it fails to do.

**Priming writes the script over speech that was not the script.** On `sequence.mp4` it
turned `we'll build a website like this` into `we'll build a vibe coding project. website
like this`. With `vad_filter=True` alongside it, line 1 disappeared from the transcript
altogether and the recording opened on line 2. This tool's job includes noticing that a
line was *not* read: a transcript biased towards the script is a transcript that agrees
with the script, and take selection, coverage and every disqualification downstream read
that agreement as evidence. The one failure mode that cannot be caught by looking at the
report is the one priming introduces.

Nothing else in the pipeline has this shape. `analyze` is the only stage that opens the
recording, and it takes a recording and settings — not a script. Priming would make the
seam's own contract depend on the script, so the artifact could no longer be read as "what
was heard", only as "what was heard while being told what to expect".

**Accuracy was measured first and is not the lever.** `float16`, level normalisation and a
high-pass were each tried against the fixed decoding settings, and none of them moves
`wipe` to `vibe`; the numbers are in `facts.md`. The model decodes this audio about as
well as it can. What it lacks is a phrase that postdates its training data, and precision
does not supply one.

## Consequences

Three routes take the place of priming, and they are separable — each is worth having on
its own.

- **A word stretched over speech is decoded again.** The buried stretch is recoverable by
  handing that span to the same model alone, with no prompt: 3.3–9.2 s of `Sequence 07`
  transcribed on its own gives `oh no white coating part` where the whole file gives
  `part`. This is the fix for speech the transcriber collapsed, and it needs no script.
- **A near miss is read as the word it displaced.** Alignment compares exactly-equal
  tokens, so `wipe` against `vibe` is a total miss and line 1 reports 67% coverage for a
  take read correctly start to finish. Matching near misses fixes the figure and the false
  flag with the transcript left exactly as the model wrote it — and it is the same
  structural test decision 0002 already rests on, since a mishearing is defined there as a
  word with the script word it displaced sitting opposite it.
- **A substitution list**, applied after transcription rather than before it. Auditable,
  deterministic, reversible, and the report can say what it changed. Priming can offer
  none of those.

The first two leave the transcript alone, which is why they are preferred to the third.
The third is where a phrase the model simply does not hold can still be corrected, and it
stays a last resort for that reason.

**What would reopen this.** A recording whose vocabulary the model gets wrong often enough
that near-miss matching cannot recover the lines, and where the substitution list has grown
past the point of being read at a glance. Priming would then be the honest answer, and the
guard it needs is the one this decision is worried about: a way to tell that a line the
transcript agrees with was actually spoken.
