# AGENTS.md

Rough Cut Assistant: a recording plus its script in, an FCP7 XML for Premiere out.

## Where things live

- **`settled/`** — what is agreed and outlives any ticket. Read before working in an area.
  - `words.md` — the vocabulary. Use its words; it exists because several pairs of terms
    here look alike and are opposites.
  - `how-we-work.md` — how work is written down and accepted.
  - `decisions/` — what the project has already decided, each file titled as its claim.
    Contradicting one is allowed; doing it silently is not.
- **`work/<feature>/`** — the live work: `what-it-does.md`, `facts.md`, `open/`, `closed.md`.
- **`src/`, `tests/`** — the tool itself. `tests/committed/` holds what is committed by
  hand rather than produced: the reference XML, the real recording's analysis, the goldens.
- **`recordings/`** — the recordings and the scripts read from them. The tool's input.
- **`running/`** — for the person operating it: getting a recording in and an XML back out
  to Windows. Nothing here is imported by the tool.
- **`out/`** — what a run writes. Disposable, and git-ignored.

## Skills

Skills from `~/.claude/skills` (a third-party set) are forbidden in this project, and so
are their conventions — no `.scratch/` tracker, no `docs/agents/`, no `CONTEXT.md`. The
full rule and the list of names is in `CLAUDE.md`.

## Commands

```bash
uv run pytest              # everything below the seam — fast, no hardware
uv run pytest -m slow      # the media stage — needs ffmpeg, the model and a GPU
uv run pytest --update-golden
uv run mypy                # strict, over src and tests
```

Python is pinned to 3.12 and everything runs through `uv`. Lines wrap at 99.

## The seam

`analyze` is the only stage that opens the recording. `plan` and `render` are pure
functions over its artifact. This is the project's single test seam and the reason the
suite runs in half a second without a GPU.

- Nothing below the seam may read media, call a model, or touch the network.
- Tests below the seam drive `plan` and `render` with hand-written analysis JSON. Build
  them from `tests/conftest.py`, which describes one recording in one place.
- Assert on what the tool **decided** — a selected take, a collapsed pause, an emitted
  timebase — never on alignment internals, scores, or how many passes something makes.
- Never assert exact transcription text anywhere. Model output is not a contract.

## Two things that are not regenerable

- `tests/committed/minimal2.xml` is the hand-verified import contract. It is never produced by the
  renderer; regenerating it would make its test circular.
- `tests/committed/sequence.analysis.json` is the committed real recording. Re-running
  `analyze` over the fixture invalidates every golden below it.

`--update-golden` applies to the rendered outputs only, and a golden diff is meant to be
read: an alignment change should show up in the report as a line moving.

## Closing work

`Status: done` means a person confirmed the behaviour with their own senses. **Never
write it, and never write under `## Heard`** — that section is dictation of what someone
heard, not a summary of what shipped. An agent's last act on a ticket is
`Status: awaiting-listen`.
