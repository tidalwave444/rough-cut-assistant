# A mishearing has the word it displaced sitting opposite it

Words inside a take that the line does not account for are two opposite things, and what
separates them is structural rather than a matter of degree. A **mishearing** always has
the script word it displaced sitting opposite it — that is what makes it a mishearing,
and it stays. A run with **nothing opposite it** sits where the line has already been
fully accounted for, so it cannot be the line said wrong, and it comes out. A **stumble**
that does have script words opposite it is found the other way, by the word the speaker
went back to and said again, and it comes out only if the line can spare what goes with
it.

## Context

A line's clip runs from its first matched word to its last, so an abandoned attempt
sitting between the two plays in the cut and appears nowhere in the report. "It did not
match the line, so it is junk" is the obvious rule and it is wrong: most of what is
unmatched inside a take was spoken perfectly well and merely misheard, and deleting it
deletes real speech.

The corpus that makes this decidable is every unmatched run inside every take of both
recordings — thirteen of them, recorded in the feature's `facts.md`. Eight are
purely a mishearing, three have nothing opposite them at all, and two are both a
mishearing and a stumble at once. Read down the column of what stands opposite each run
and the split is structural, so the second mechanism above needs no number.

The two mixed runs are the ones that need the first mechanism, and they are the ones
actually audible. On `Sequence 07` line 1, `a wipe coating` is `vibe coding` misheard and
must stay, while `part 1. No, no,` is the stumble — the speaker says `part`, abandons it,
and says `part` again. On line 3, `claim plan` is `clear plan` misheard; the speaker
jumps to the end of the line, says "No", and restarts from `and`, which is a word already
spoken. So the trigger is the repeat, and the cut runs from the first utterance to the
second.

That alone is not safe. The same test fires on `a` and on `the`, and each of those
removals eats several of the line's own words. Coverage is what stops it, and no
threshold could — run over both recordings, with coverage measured before and after each
candidate:

| | line | would remove | coverage | |
| --- | --- | --- | --- | --- |
| `sequence` | 4 | `along the` | 19 → 19 | removed |
| `Sequence 07` | 1 | `part one no no` | 6 → 6 | removed |
| `Sequence 07` | 3 | `and claim plan no` | 17 → 17 | removed |
| `sequence` | 3 | `the skill to follow analyze` | 23 → 20 | refused |
| `sequence` | 3 | `the implementation well use` | 23 → 20 | refused |
| `sequence` | 7 | `the project based on` | 9 → 6 | refused |
| `Sequence 07` | 1 | `a rail project with` | 6 → 4 | refused |

Every refusal was triggered by a function word and every one of them would have destroyed
the line. Nothing separates the two halves of that table by degree: the line either keeps
all of its own words or it does not.

**Coverage is measured by reading the survivors against the line again**, not by counting
the matched words inside the proposed cut. That distinction is the mechanism rather than a
detail. The removal that takes `and claim plan. No,` starts on a matched `and`, and the
take keeps all seventeen of its words only because the *second* `and` — the one the
speaker restarted on — takes over the match the first one gave up. Counting matched words
inside the cut calls that 17 → 16 and refuses it; read the other way it reproduces the
table above exactly, refusals included.

Two consequences of measuring it that way, both deliberate. The guard is asked of
everything taken out of a take so far rather than of one candidate at a time, because what
a removal costs depends on what has already gone. And both sides of the comparison are
counted the same way — the take read against its line, before and after — rather than the
"before" being the figure the whole-script alignment arrived at. The two agree on every
take of both recordings, so nothing moves; they are kept separate anyway, because a guard
whose two halves are measured differently can be loosened by a change somewhere else that
was never about it.

## Consequences

**Most mishearings no longer reach these two mechanisms at all.** The corpus above was
read against an alignment that compares exactly-equal tokens, where every mishearing is a
run the line does not account for. A transcript word one sound away from the script word
facing it is now matched as that word — the same structural test as this decision's,
applied where the two texts are first compared instead of afterwards — so it sits inside
the line's coverage and is never a candidate for removal. What still arrives here is a
mishearing too far off to match, and a stumble. The split the table shows is structural
and holds; its coverage figures are the alignment's own and move when the alignment does.

**A run standing beside a near miss is not a run with nothing opposite it.** Near-miss
matching steps over a word neither side accounts for, exactly as exact matching does, so
where the transcriber wrote two words where the line has one — `the wipe` for `vibe`, on
`sequence.mp4` line 1 — the near miss takes `vibe` and leaves `the` sitting between two
consecutive words of the line. Read by the second mechanism alone that is a run with
nothing opposite it, and it came out: a 0.3 s butt splice mid-phrase, deleting half of one
mishearing, on the reasoning that the mishearing beside it was the line said right. So the
mechanism asks first whether a near miss stands against the run, and leaves the run alone
if one does. That is the same structural test as this decision's, read once more: what
stands opposite the pair is the word the near miss already claimed. Nothing else moves —
the two removals of this kind on `sequence.mp4`, `wipe` on line 2 and `skills` on line 6,
both sit between exactly-matched words.

Where both signals name the same run, the stronger claim wins: a repeat says which word
the speaker went back to, where "nothing opposite it" only says nothing accounts for it.
`along the` is named by both, and the report calls it `"along" said twice`.

**A silence precondition was considered and left out.** Only one of the five removals is
corroborated by quiet at both ends — `and claim plan. No,`. `wipe` (0.30 s) and `skills`
(0.54 s) have no silence anywhere near them: the speaker corrected themselves without
pausing, so these are hard butt splices in the middle of running speech, and the padding
of decision 0001's neighbour decision — which only ever extends into detected silence — gives
them nothing. Requiring a silence at one end would drop exactly those two and keep the
three large ones. It was left out because the evidence for removal here is the repetition
and the coverage, not the quiet, and a cut that is right should not need the room to
agree.

That leaves the risk concentrated in two sub-second, mid-flow, unpadded splices, which is
where an audible artefact would show up first. If either clicks or swallows a consonant,
the answer is the precondition this decision left out, and it is a one-line change.
