# The standing prompt for the XML fix loop

`running/xml-fix-loop/loop.sh` hands this file to a fresh `claude -p` on every iteration, together
with the output of the checks that are red. Nothing else carries over between iterations: no
memory of what the last one tried, no conversation. Whatever the next iteration needs to know
has to be in this file, in the repo, or in the check output — so when you learn something
that outlives your iteration, put it in your commit message.

## What is being fixed

*The operator fills this in before starting the loop, one numbered problem per fault seen in
the XML Premiere received. Every problem here must be paired with a check that is red today.
A problem with no red check is not in this loop — if you spot one, say so and leave it.*

1. …
2. …

## What decides that you are done

`uv run pytest` and `uv run mypy`, both green, in a tree where nothing under `tests/`,
`settled/`, `recordings/`, `running/` or `work/` has changed. That is the whole criterion.

Your own reading of your work does not enter into it. Neither does a closing summary that
says the fix is complete — the loop re-runs the checks itself and will not take your word.
Finishing an iteration with checks still red is a normal outcome, not a failure: say what you
changed and what you now know, and stop. The next iteration starts from your commit.

## What you may change

`src/roughcut/` only.

These are locked. The loop reverts them after your turn and counts the iteration as wasted:

- **`tests/`** — the checks are the contract being worked against. An agent that edits the
  contract to satisfy it has proved nothing. This includes `tests/committed/`, which holds
  the hand-verified import contract and the committed analysis of the real recording.
- **`settled/`** — the vocabulary and the decisions. Contradicting a decision is allowed;
  doing it silently is not, and a loop is not the place to do it at all. If your fix needs a
  decision overturned, stop and name the decision.
- **`recordings/`** — the input material.
- **`work/`** — the tickets. Their `Status:` and `## Heard` belong to the person who listens.
- **`running/`** — the operator's side of the tool, this loop and its prompt among it. A run
  that rewrites its own instructions is not a run anyone can read afterwards.

**Never run `pytest --update-golden`.** It is the single command that turns every check green
without fixing anything, and using it here would end the loop on a lie. If your change is
genuinely meant to move `sequence.golden.xml` or `sequence.golden.report.txt`, that is a
golden diff a human has to read. Say in your last message which lines move and why, and stop
there — the loop sees a red golden with nothing else red, stops on the spot rather than
spending its remaining turns, and hands the diff to the operator.

## Read before you change anything

- `AGENTS.md` — the seam above all. `analyze` is the only stage that opens the recording;
  `plan` and `render` are pure functions over its artifact and may not read media, call a
  model or touch the network.
- `settled/words.md` — several pairs of terms here look alike and are opposites. *line* vs
  *take* vs *clip*; *stumble* vs *mishearing*; *coverage* vs *likeness*. Using the wrong one
  in a name or a comment is a real defect in this repo, not a style point.
- `settled/decisions/` — one file per decision, each titled as its claim. Skim the titles;
  read in full any that touch what you are changing.
- Lines wrap at 99. Assert on what the tool decided, never on alignment internals or scores.

## Working one iteration

1. Read the red check output first and reproduce the failure before theorising about it.
   `uv run pytest -q <path>::<test>` is cheap; the whole suite runs in about half a second.
2. Make the smallest change that turns a red check green. The loop scores you on the number
   of red checks, so a change that fixes one and breaks two is worse than doing nothing.
3. Fix one problem completely rather than four partly. Partial fixes across several files are
   what make the next iteration unable to tell what is load-bearing.
4. Do not widen the scope. Refactoring you were not asked for, renaming, and tidying nearby
   code all cost the next iteration its ability to read the diff.
5. End by saying what you changed, why, and what is still red. Keep it short.

## The two ways this loop ends early and wrongly

- **The check gets adjusted to the code.** Editing a test, relaxing an assertion, or
  regenerating a golden. The loop reverts it, but the iteration is spent.
- **The fixture gets special-cased.** A branch keyed to a filename, a duration, or a line
  number that happens to appear in `tests/committed/sequence.analysis.json` will pass every
  check and fix nothing. If a change only makes sense for this one recording, it is wrong.
