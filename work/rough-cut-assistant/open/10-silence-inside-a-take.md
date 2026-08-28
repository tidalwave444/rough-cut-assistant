# 10 — Silence inside a take

**What to build:** A cut as tight as the room actually was. The quiet inside a line comes out whether or not the transcriber left a gap for it — because on real material it almost never does, and thirty seconds of dead air is currently riding into the timeline underneath the words.

**Blocked by:** 09

**Status:** awaiting-listen

## Listen for

1. `Sequence 07.xml` as a whole — it loses a quarter of its length, so this is the ticket most likely to have made the cut too tight. Do the lines now run into each other without room to breathe? If they do, the handback is `--pause-threshold-seconds 0.8` (decision 0003), not a new number.
2. `Sequence 07.xml` line 3, around `00:27` of the source — seven regions collapse inside it, including 2.14 s from under the single word `claim`. Listen for a word losing its head or its tail where a collapse landed on top of it.
3. `Sequence 07.xml` line 6 — the take now plays 0.36 s instead of 2.68 s after the tail trim. It should sound truncated: that take's selection is wrong for a reason this ticket does not touch, see 05's note on the transcription loop.

- [x] A pause is found from the detected silence regions themselves, not from the gap between one word's end time and the next one's start time
- [x] The transcript-gap rule goes rather than gaining a second source beside it
- [x] A cut may land inside a word's declared span — word timestamps bound nothing any more
- [x] Quiet at the very start or end of a take is removed in full, not collapsed to the floor
- [x] The padding from 09 is measured from that corrected boundary, so the two tickets do not move the same in point in opposite directions
- [x] The threshold and the floor keep their current defaults and their current job: a region longer than the threshold gives up everything but the floor
- [x] Kept off-script regions collapse on the same rule — they already go through `tighten`
- [x] The alternates sequence stays untightened, as 07 decided
- [x] Report: the pause table's `Was` and `Now` describe the quiet, and `HOW_THE_CUT_WAS_MADE` no longer says pauses are read off the transcript
- [x] `settled/decisions/0001` records why a cut may now fall inside a word
- [x] `spec.md`'s "Pause handling" is rewritten and its "never cut inside a word" sentence removed
- [x] Goldens are re-recorded, and the report is the artifact reviewed — every line should keep the source time it was found at
- [x] Tests: a silence lying wholly under one word's declared span is collapsed; a silence at the head of a take is removed with nothing left behind, and likewise at the tail; a silence under the threshold is untouched; a transcript gap no silence corroborates is untouched; a marker whose word begins inside a collapsed region lands on the splice; a kept off-script region's internal silence collapses on the same rule

## Comments

Ticket 08's listen-through found the cut "looser than it should be" and could not place
the fault. Half of it was this ticket; the other half was 11.

Why a cut may now fall inside a word, and the structural rail that was written and
dropped: **decision 0001**. Why the threshold stays at 0.7 s: **decision 0003**. The measurement
both rest on — where the quiet actually sits — is in `facts.md`.

What shipped: `sequence.mp4` 76.16 s → 72.76 s, 7 regions collapsed. `Sequence 07.mp4`
79.78 s → 56.45 s for the whole cut, 47.35 s lines only, 23 regions across the cut. The
kept 15.52 s off-script region plays for 9.10 s after tightening.

The head and tail trim does nothing on `sequence.mp4` — it has no quiet at any take
boundary — so the committed golden evidences the collapse rule and not the trim.
`Sequence 07` is the only place the trim acts, and it has no golden.

## Heard
