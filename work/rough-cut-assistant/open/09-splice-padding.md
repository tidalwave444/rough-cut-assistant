# 09 — Padding around every splice

**What to build:** A cut that does not bite off the ends of words. Every splice is widened into the quiet either side, so a last consonant still plays and a join sounds like a join rather than a word cut short.

**Blocked by:** None — can start immediately.

**Status:** awaiting-listen

## Listen for

1. `sequence.xml`, line 5 into line 6 — the only mid-recording splice both sides of which grew. It is one of the three the manual pass of 05–08 called out as clipping a word; the word's tail should now finish before the join.
2. `sequence.xml`, line 8's out point — the recording's other grown end. Nothing should sound cut short at the tail.
3. Any of the three — a pad that reached too far plays a fragment of something the cut dropped. Up to a pad's width of the wrong sound is the known cost; more than that means the sharing rail failed.

- [x] A clip's in point moves earlier and its out point later by a padding amount, so the speech at both ends is whole
- [x] The pad is bounded by the detected silence: it crosses the fading consonant between a word's declared end and the start of the quiet, and stops at the quiet's far edge. A join the detector heard no quiet in gets no pad
- [x] A pad never reaches into another piece's words: two pieces of source that both play cannot claim the same audio, and a quiet gap short enough for only one of them is shared rather than double-claimed
- [x] Kept off-script regions are padded on the same rule as line takes — both take their bounds from word timestamps today
- [x] Padding is exposed as a command-line option
- [x] The option decides the plan rather than the analysis, so `render` takes it too and trying a value costs no transcription
- [x] Consecutive clips still meet on the same frame number after quantisation — no one-frame overlaps and no one-frame holes on the audio track
- [x] Report totals stay a pure function of the plan: output duration grows and time removed shrinks by exactly what the pads gave back
- [x] Goldens are re-recorded and the change reads as expected — no source time moves by more than the padding, and no line changes which reading it was found at
- [x] Tests: a take with silence on both sides is padded on both; a take with speech immediately after gets no pad on that side; two takes separated by a gap too short for both pads split it without overlapping; a take at the very start and one at the very end of the recording

## Comments

06 named this and left it undone on purpose — widening the splices moves every line's in
and out point and re-opens 05's and 06's goldens. The manual acceptance of 05–08 then
confirmed it as an audible fault rather than a theoretical one: a transcriber's word-end
timestamp lands where the word stops being *recognisable*, which is before it stops being
*audible*.

What bounds a pad, why the acceptance line above had to be rewritten, and why the option
is separate from `--pause-padding-seconds`: **decision 0006**.

What shipped: three clip ends moved, not sixteen, each by the full 0.15 s — +0.450 s of
output and −0.450 s removed. The rest of `sequence.mp4` has no splices to pad, because
consecutive takes are contiguous in the source; `facts.md` records why.

10 and 11 both changed the cut after this ticket, so all three are one sitting: the cut
is played once and each records its own verdict.

## Heard
