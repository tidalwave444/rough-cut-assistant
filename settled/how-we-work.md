# How we work

The discipline this repo actually runs on. It assumes no external skill set and no
orchestration — read this file and you know how work is written down, how it is accepted,
and where the things that outlive a ticket go.

The reader of everything here is **the person who has to accept the work**. That is the
constraint the rest of this file is derived from.

## Where work is written down

- One feature per directory: `work/<feature-slug>/`
- What the tool does and why: `work/<feature-slug>/what-it-does.md`
- Facts about the material or the environment: `work/<feature-slug>/facts.md`
- A live ticket is one file at `work/<feature-slug>/open/<NN>-<slug>.md`, numbered from `01` — never a single combined file while work is open
- A closed ticket folds into `work/<feature-slug>/closed.md`, whole, in number order. `open/` holds only what is still open
- Decisions that outlive a ticket: `settled/decisions/<NNNN>-<claim>.md`, one file per decision
- Domain vocabulary: `settled/words.md`

This repo is **single-context**: one `settled/words.md` and one `settled/decisions/`. If
it ever grows into several bounded contexts, switch to a `settled/words-map.md` pointing
at one `words.md` per context.

## The shape of a ticket

Fixed, in this order, and nothing may be inserted above `## Listen for`:

```markdown
# NN — Title

**What to build:** the outcome in two or three lines, in the user's terms.
**Blocked by:** NN, or None
**Status:** ready-for-agent | awaiting-listen | done

## Listen for
1. `file` at `mm:ss` — what should be true. If it is not: what that means.

- [ ] Acceptance criteria

## Comments
## Heard
```

Those three `Status:` values are the whole vocabulary. Comments and conversation history
append to the bottom under `## Comments`.

## `## Listen for`

The section immediately under `Status:`, above the acceptance criteria, because it is the
only part someone else has to act on.

- At most **five** numbered items, one line each: which file, where in it, what should be true, and what it means if it is not.
- A timecode wherever one exists, so an item is scrubbed to rather than hunted for.
- More than five items means the ticket is too big to accept in one pass. Split it.
- When implementation changes what to listen for, **edit the item in place**. Never append a second, truer copy further down the file.

## Closing a ticket

`Status: done` means a human confirmed the behaviour with their own senses. It does not
mean the tests pass. **An agent never writes it.**

- An agent's last act on a ticket is `Status: awaiting-listen` and an empty `## Heard` heading. The code may be finished, reviewed and committed; the ticket is not closed.
- Only the person who ran the listen writes under `## Heard`, and only they set `done`. An agent at the keyboard there is taking dictation: every line is that person's answer to a numbered `## Listen for` item, in their words, and it says which item it answers.
- `## Heard` lands in its own commit, after the one that shipped the code. An acceptance arriving in the same commit as the work it accepts is not one.
- One sitting may close several tickets — the cut is played once and each ticket records its own verdict. Say in each which sitting it was.
- A listen that finds a fault still closes the ticket, on what shipped, with the fault written down under `## Heard`. The fault then becomes its own ticket. 06 → 09 and 08 → 10, 11 are what this looks like when it works.
- Nothing else may say whether the acceptance happened. No `Outstanding for a human`, no `Imported`, no `Listened to`. If it is not in `## Heard` and the `Status:` line, it did not happen.

**Exemption.** A ticket that changes nothing a human can see or hear writes, as the whole
of its `## Listen for`, one line giving the reason, and may then close on tests. That
claim is made when the ticket is written and a human is still reading it — an agent may
not grant itself the exemption at the end of the work it has just done.

## Ticket length

**60 lines, hard**, per ticket, including its `## Comments` and `## Heard`. Roughly: brief
and criteria in 30, comments in 15, verdict in 10. Over the ceiling the ticket is not
filed — it is cut down, or split into two that each fit.

The ceiling is a rule about a ticket while it is open. `closed.md` is the sum of the
closed ones and has none of its own.

Where the material goes instead:

- **A decision whose consequences outlive the ticket, with the alternatives rejected to reach it** → `settled/decisions/`, one file, titled as the claim it settles. The ticket keeps a one-line pointer.
- **Behaviour that is now true of the tool** → `what-it-does.md`. **Facts about the material or the environment** → the feature's `facts.md`.
- **A narrative of what the agent did and why its work was sound** → nowhere. The commit message carries what a reader needs; the code, the tests, the goldens and the report already state what shipped, and each of those is checkable in a way the narrative is not.
- **A prediction the work proved wrong** → correct it where it stands. Do not append the correction. A ticket that argues with its own earlier paragraphs holds two answers and the reader cannot tell which is live.

Writing past the person who has to accept the ticket, to persuade the next agent, is the
failure this ceiling exists to stop.

## Decisions

One file per decision under `settled/decisions/`, **titled as the claim it settles** — a sentence,
not a topic. "The detector decides where the quiet is", not "Silence detection". A reader
scanning the directory should be able to see what the project believes without opening
anything.

A decision carries the alternatives that were rejected to reach it, and the evidence that
makes the choice checkable. Evidence that is a fact about the material lives in
`facts.md` and is pointed at, not copied — one fact, one home.

If your output contradicts an existing decision, surface it explicitly rather than silently
overriding:

> _Contradicts decision 0007 — but worth reopening because…_

## Vocabulary

Before working in an area, read `settled/words.md` and any decision that touches it. If either does
not exist yet, proceed silently — they are written when a term or a decision actually
needs settling, not upfront.

When your output names a domain concept — in a ticket title, a refactor proposal, a
hypothesis, a test name — use the term as `settled/words.md` defines it. Don't drift to
synonyms the glossary avoids. If the concept you need isn't there yet, that is a signal:
either you are inventing language the project doesn't use, or there is a real gap worth
filling.
