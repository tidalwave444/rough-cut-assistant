# Containment, not coverage, marks a failed restart

An off-script region is a failed restart when most of what was *said* is the line, not
when most of the line was said. And it is compared only against the lines it sits
between, never against the whole script.

## Context

Coverage — the measure decision 0004 settles for deciding what a line claims — answers the
wrong question here. An attempt abandoned four words into a twenty-word line holds a
fifth of the line, so coverage calls it nothing. But every word it said *was* the line,
and that is what a restart sounds like. So the fraction is measured the other way up —
how much of what was said is the line — by `offscript`, which owns the bar it is read
against. At what grain it is taken, when the region holds more than one attempt, is
settled by decision 0009.

The two measures cannot fight over the same region, because they sit on opposite sides of
one bar: anything scoring above 0.6 coverage is already a *take*, and only what falls
below that is ever asked whether it is a restart.

"Adjacent" is also narrower here than it is for a retake. The retake pass of decision 0005
goes on to ask every line the spine placed nowhere, because a pickup recorded at the end
of a session is worth recovering wherever it turns up. This pass asks only the lines the
region sits between: a fragment that happens to echo a line written minutes away is not
an attempt at it.

## Consequences

The difference in scope follows from the direction each measurement can move the cut. The
retake pass can only ever *recover* material, so it is worth asking widely. This one can
only ever *remove*, so it is asked narrowly. A measurement that deletes is scoped tighter
than one that restores — which is the same asymmetry that keeps a long off-script region
in place and marked rather than cut.
