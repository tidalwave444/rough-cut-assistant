# A cut is described from its clips, not from its report

Anyone saying what a change did to a recording — an agent reporting to the operator, a
commit message, a ticket comment — reads the clip list first and the report second. Source
in, source out, and how long each line plays. The report's summary may be quoted after
that and never instead of it.

## Context

Between 28 and 31 August four changes went in with every check green and were wrong on the
recording. The last of them was reported to the operator as fixed. It was not, and the
words used to say it was fixed came from the report:

> Line 1 — 100%, selected, no flag.

All three are true. Coverage says the line's *words were found*; it says nothing about the
seven and a half seconds of abandoned attempt still playing between them. `Stumbles cut 1`
sat four lines above in the same report and went unread. The operator imported the XML,
listened, and found the fault that had been declared fixed — after fifteen commits had
landed on that reading.

The clip list could not have been read that way:

```
src 0.43-1.98   Building a rail project with
src 2.35-3.17   with a wipe coating
src 4.85-5.90   oh no
src 7.03-8.05   white coating
src 10.12-11.60 No, no, part 2.
    line 1 plays 7.67s of source
```

## Consequences

The `Sequence 07` golden is the XML as well as the report, and `AGENTS.md` says to read the
XML one. A report golden alone would have shown `100%` moving to `100%` and nothing else.

This is not a rule about honesty. Every figure in that report was correct, produced by the
tool, and freshly generated. It is a rule about altitude: a summary is a claim about a cut,
the clips are the cut, and the two come apart precisely where a heuristic has gone wrong —
which is the only time anyone is reading either.

The cost is that describing a change takes a script rather than a `head` of the report.
That is thirty seconds against fifteen commits.

## What was rejected

**Trusting the report and checking the clips when suspicious.** This was the working
practice, and it failed four times out of four: the clips were opened only after the
operator said it sounded wrong. Suspicion arrives after the report has already been
believed.

**Adding what-plays lines to the report.** It would make the summary honest for this one
fault and leave the altitude problem where it is — the next thing to go wrong will be
something the report does not have a column for.
