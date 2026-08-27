# 13 — What the transcriber was told to do

**What to build:** The decoding settings `transcribe()` passes fixed, both committed
analyses re-run against them, and every golden below them re-recorded. The repetition loop
goes, the fallback ladder comes back, and lines 7, 8 and 9 of `Sequence 07` — reported
`not found` today — are in the transcript, because they were always in the recording.

**Blocked by:** None

**Status:** ready-for-agent

## Listen for

1. `Sequence 07` at the end of the timeline — lines 7, 8 and 9 play, in order. They were
   hidden by a loop that ate the last 21 s of the file. If they are still missing, the
   loop was not the whole cause and the recording is short of them after all.
2. `Sequence 07` line 6, one reading rather than thirteen — the report should say take 1
   of 1. Thirteen takes was the loop being read as thirteen retakes.
3. `Sequence 07` line 1 at `00:03` of the source — still one continuous sentence ending on
   `part 2`, with `a wipe coating` still in it. It is `vibe coding` misheard and stays.
4. `sequence.mp4`, whole — it plays as it did. Its report was already right; anything that
   moves there is the new settings taking something they should not.

- [ ] `temperature` is the full ladder, not a single `0.0` — one value disables the
      fallback loop entirely, so every threshold in the library is wired to a re-decode
      that cannot happen
- [ ] `condition_on_previous_text=False`
- [ ] `chunk_length=10`
- [ ] All three live on `AnalysisSettings` and therefore in the fingerprint
- [ ] `FINGERPRINT_VERSION` bumped, so a stale artifact is a cache miss and not a wrong
      answer served quietly
- [ ] Both committed analyses re-run on the GPU and re-committed, and every golden below
      them re-recorded — the report diff read line by line, not skimmed
- [ ] The `vad_filter` comment in `transcribe()` corrected: `False` is already the library
      default in `faster-whisper` 1.2.1, so passing it states intent and changes nothing
- [ ] `tests/test_analyze_smoke.py`'s word band still holds, or moves with a reason

## Comments

What each setting is worth, measured row by row on `Sequence 07`, and the four levers that
were tried and did nothing — `float16`, `loudnorm`, a high-pass, a generic vocabulary — are
in `facts.md`. Do not pay for those again.

`AGENTS.md` calls the committed analyses "not regenerable", and this ticket regenerates
them. That is the point of it and the reason the whole golden set moves at once. Re-running
`analyze` is the only way to fix a defect that lives in the artifact.

This ticket does not touch the 2.53 s of speech buried under `part` on line 1 — no decoding
setting reaches it. That is ticket 14.

## Heard
