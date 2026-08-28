# The detector decides where the quiet is

Where the silence detector and the transcriber disagree about whether someone was
speaking, the detector wins: a pause is found from the detected silence regions and may
be cut out from inside a word's declared span. The transcriber's word boundaries no
longer bound a cut.

## Context

The original design read a pause off the transcript — the gap between one word's end
time and the next one's start time — and used the silence regions only to confirm it and
to place the cut point. It also held a hard rule: *pauses are never cut inside a word*.

On real Whisper output there are almost no such gaps. 97% of consecutive word pairs on
`sequence.mp4` and 94% on `Sequence 07.mp4` butt straight up against each other, because
the transcriber stretches a word over the pause that follows it rather than leaving a
hole. The silence is therefore not *between* the words but *underneath* them: of the
16.71 s and 31.67 s of detected quiet lying inside selected takes, 93% and 98% sits under
some word's declared span. One word, `claim`, is declared at 27.28–29.70 — 2.42 s for a
single syllable — with 2.14 s of silence inside it.

So the rule was not acting as a safety rail. It was the sole reason thirty seconds of
dead air survived into the cut.

## Consequences

A collapse can now swallow most of a transcribed word's declared span — thirteen words on
`Sequence 07.mp4` lose over 40% of theirs, several at confidence above 0.95. This reads
worse than it is: the percentage measures a span the word never occupied, and the cut is
still placed inside the corroborated quiet with a pad off both edges, so audible sound
cannot be removed however long the word claiming that time says it is.

A structural rail — *a transcribed word keeps some part of itself in the cut* — was
written and dropped. It leans on precisely the timestamps this decision declares
untrustworthy, and in the case it exists for (the detector swallowing a genuinely quiet
word) it would preserve an unhearable fragment. The defences that remain are the
detector's own threshold, exposed as an option on `analyze`, and listening to the result.

The same reasoning settles the ends of a take: a take begins where sound begins, not
where the transcriber declared its first word, so quiet at the head or tail of a take is
removed in full rather than collapsed to the floor.
