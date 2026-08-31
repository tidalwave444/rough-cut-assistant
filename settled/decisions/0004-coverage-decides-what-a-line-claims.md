# Coverage decides what a line claims

A stretch of transcript is a reading of a script line when it contains enough of that
line, not when it looks like it. Similarity is not the measure; how much of the line the
stretch accounts for is. And what a line claims is a *span* of its matches rather than
every match it has, and only the part of a leftover that reads as the line.

## Context

Similarity answers the wrong question. A leftover holding eleven repeats of one line
scores ~2/13 by `SequenceMatcher.ratio()` — the repeats dilute it — but 1.0 by "how much
of the line does this contain", which is what is actually being asked. The same measure
then answers both gates: whether a span is a reading of a line at all (half the line),
and whether a leftover is a retake of one (0.6 of it).

**A line's take is a span of its matches, not all of them.** The spine gives each line a
set of matched tokens, which for a restarted line is scattered across every attempt.
Splitting that set wherever a reading of the line was left behind is what makes the
attempts separable at all — otherwise a line's region stretches from the first attempt
to the last, swallows every retake, and retakes can never be identified. How much
unheard speech sits between two matches is the first thing that says so, and the break
scales with the line: a stumble mid-sentence is a few words, a restart is half the line
again.

**But how much was said between two matches is not on its own what left a reading
behind.** Amended 31 August, on `Sequence 07` line 1. It reads `…with a wipe coating /
oh no white coating one no no / part two`, and the run in the middle is one abandoned
attempt — the same one that, before the transcriber was asked again over the stretch it
was buried in, was written down as the four words `part one no no` and sat inside the
bar. Seven words pushed it over, so the take ended at `coating` and the line's own last
words played beside it as a leftover. A count of unheard words was deciding a stumble
from a restart on how well the transcriber heard, which is the one thing it cannot
mean; and no count that admits seven words of a nine-word line can go on refusing a
restart, which is nine.

So the count is read against which of the *line's* words stand either side of the run.
A reading that goes on to the very next word of the line did not stop and start again,
however much was said in between — the abandoned attempt is then something said in the
middle of a reading, which is what `stumbles` exists to take out. The count still
bounds it: an attempt abandoned mid-line is at most the line said over again, and two
matches further apart than that have a reading left behind between them whatever the
line does across it.

**A take is the part of a run that reads as the line, not the run it arrived in.** Only
that part becomes the take; what was said either side goes back on the pile and is
labelled in its own right. This began as the rule for recovering a pickup and now applies
to every match, because a retake is usually introduced by a mutter, and swallowing the
whole run would delete that mutter from a report whose job is that nothing vanishes
unreported.

## Consequences

`autojunk` must be off. `SequenceMatcher` discards elements appearing in more than 1% of
a sequence longer than 200 elements, which over a transcript means "the", "a", "we". Left
on, it drops the connective tissue that holds a sentence match together, and coverage is
measured on whatever survives that discarding.

Coverage is a measure the project keeps rather than computes once, which is what lets it
be re-asked after a cut is proposed inside a take — see decision 0002, where the same
arithmetic is what stops removing a stumble costing a line its own words.
