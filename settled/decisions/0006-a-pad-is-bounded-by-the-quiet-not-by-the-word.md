# A pad is bounded by the quiet, not by the word

A splice pad is stopped by the quiet the detector heard, not by the neighbouring word's
declared edge. It crosses the stretch between a word's declared end and the start of that
quiet — because that stretch is the fading consonant the pad exists to save — and stops
at the far edge of the quiet beyond it.

## Context

The first implementation stopped a pad at the neighbouring word's declared edge. It was
wrong for exactly the reason decision 0001 exists: with the transcriber butting words straight
together, that rail is hit everywhere and no pad is ever possible.

The acceptance criterion as written — *the pad only ever extends into detected silence* —
is true of where a pad **stops** and not of where it **starts**, and it cannot be both.
The stretch between a word's declared end and the start of the detected quiet is the
fading consonant itself: 0.19 s, 0.28 s and 0.63 s at the fixture recording's three real
splices. A pad required to land inside silence to be allowed would have been refused at
every one of them, and the change would have shipped as a no-op.

What bounds a pad instead is the quiet, plus one rule between pieces that both play:
neither may reach past the middle of the gap between them, so a gap wide enough for only
one pad is shared rather than double-claimed. A join the detector heard no quiet in gets
no pad at all.

The cost is stated where it is paid, in `splice.py`. Where the sound beside a clip
belongs to something the cut dropped rather than to the clip's own word, up to a pad's
width of it plays. The pad is small because that width is the bound on how wrong this can
be.

## Consequences

`--splice-padding-seconds` is a separate option from `--pause-padding-seconds`, and the
reason is not symmetry. A pause pad holds a cut *inside* the corroborated quiet, so
raising it makes the cut looser and eventually refuses to cut at all. A splice pad extends
a clip *into* the quiet, so raising it makes the cut longer. They move the output in
opposite directions from the same number, and one option meaning both could be tuned for
neither.

This gives a take back up to a pad's width of the quiet that decision 0001 removes in full at
a take's head and tail. It is not a reopening of that decision: a floor is a beat held
*between two words*, and nothing here restores one. A pad is the same hundredths decision 0001
already keeps around every cut it makes, applied outward instead of inward.
