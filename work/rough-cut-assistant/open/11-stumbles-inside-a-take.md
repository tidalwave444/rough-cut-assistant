# 11 — Stumbles inside a take

**What to build:** The stumble in the middle of a line gone, without touching the words the transcriber merely misheard. A line's clip runs from its first matched word to its last, so an abandoned attempt sitting between them plays in the cut today and appears nowhere in the report — the one place material is allowed to vanish unmentioned.

**Blocked by:** 10

**Status:** awaiting-listen

## Listen for

1. `Sequence 07.mp4` line 1, where `part 1. No, no,` stood at `00:03` of the source — one continuous sentence, and `a wipe coating` still in it. That is `vibe coding` misheard; if it went, the rule is deleting real speech.
2. `Sequence 07.mp4` line 3, where `and claim plan. No,` stood at `00:26` — one continuous sentence. If the line lost a word of its own, the coverage guard failed.
3. `sequence.mp4` line 4, where `along the` stood at `00:30` — one continuous sentence.
4. `sequence.mp4` at `00:09` (`wipe`, 0.30 s) and `01:00` (`skills`, 0.54 s) — the riskiest splices the tool makes: sub-second, mid-flow, unpadded. A click or a swallowed consonant means the silence precondition decision 0002 left out is needed after all.

- [x] A take exposes which transcript words matched the line, which it does not do today
- [x] A repeated word marks a stumble: an unmatched word inside the take that reads as a word of the line already spoken there, or spoken later in it, and the stretch between the two utterances comes out
- [x] A removal is refused if it would drop the take's coverage — the line may not lose one of its own words to it
- [x] Unmatched words with no script words left opposite them come out as well: the line has nothing to say there, so they cannot be anything it said
- [x] Nothing else is removed — a run standing opposite unmatched script words is the line misheard and stays whole
- [x] Report: a new section names every removal, with its time, its length, and what was said, quoted in full
- [x] `spec.md`'s "Filler-word removal inside a kept take" is narrowed to filler words, leaving an abandoned restart inside a take in scope
- [x] Goldens are re-recorded — five clips lose an interior stretch and every other clip is untouched
- [x] Tests: a stumble that repeats a word of the line is removed; a misheard word standing opposite the script word it displaced is kept; a repetition that would cost the line one of its own words is refused; a run with nothing opposite it is removed; a clean take is untouched

## Comments

Ticket 08's listen-through found this and declined it: it sits *inside* a take, between
two matched words, where `align` never raises a leftover and nothing there ever sees it —
work no ticket had covered yet.

How a stumble is told from a mishearing, why the guard is coverage rather than a
threshold, and the silence precondition that was considered and left out: **decision 0002**.
The corpus of thirteen unmatched runs it was all derived from is in `facts.md`.

Five removals shipped, three on `sequence.mp4` and two on `Sequence 07.mp4`. Lines only,
`sequence.mp4` goes 72.76 s → 70.46 s and `Sequence 07.mp4` 47.35 s → 39.48 s.

Only `sequence.mp4` has a golden, so three of the five removals are locked by it. The
other two — items 1 and 2 above, which are also the two largest — rest on the listen
alone.

## Heard
