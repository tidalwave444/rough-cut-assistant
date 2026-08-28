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
Splitting that set wherever too much unheard speech sits between matches is what makes
the attempts separable at all — otherwise a line's region stretches from the first
attempt to the last, swallows every retake, and retakes can never be identified. The
break scales with the line: a stumble mid-sentence is a few words, a restart is half the
line again.

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
