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

Nine faults, from one listen of `Sequence 07` on 28 August, every one of them inside the first
fifteen seconds of the cut. They come to five problems: several of the nine are one fault heard
in several places, and one of them is already fixed and only looks broken. Problem 6 is not from
that listen — it is what problem 5 did to the cut when it landed. Each problem names the check
that is red for it.

1. **Quiet the detector heard inside a line plays exactly as it was recorded.** Heard as blank
   sections at 01:42, 04:47 and 14:05 — 0.507 s, 0.565 s and 0.632 s of nothing, every one of
   them under the 0.7 s threshold and so left whole.

   Red: `tests/test_pauses.py`, three cases, one per length the listen named —
   `test_quiet_the_detector_heard_inside_a_line_does_not_play_as_recorded`.

2. **What a shortened pause leaves behind is still heard as a hole.** Heard at 11:52: 1.168 s of
   quiet collapsed exactly as the rule says, and a blank section there afterwards all the same,
   because what it collapsed to is 0.3 s long.

   Red: `tests/test_pauses.py`, `test_what_a_shortened_pause_leaves_behind_is_not_heard_as_a_hole`.

   1 and 2 are one bar read from its two sides, and a listen is the only thing that moves it —
   decision 0003 says so, and names the acceptance listen on ticket 10 as the first evidence
   that could. This is that listen, and it went the opposite way to the one 0003 expected: not
   breathless, still loose. What the two checks ask for is a threshold under 0.5 s and a floor
   of 0.2 s or less; `A_BEAT_AT_MOST_SECONDS` in `tests/test_pauses.py` carries the evidence
   behind the second number. The fixtures either side of them now name the bar they were
   written at, so moving the defaults does not move them — if one of those does move, you have
   changed how a pause is collapsed and not where the bar sits.

3. **A removal's two edges are word timestamps, so one clips a word and the other admits quiet.**
   Heard at 14:37, where `we prepared the project` played as `the proj`: the removal begins on
   the timestamp that ended the word before it, and a word goes on sounding after the
   transcriber stops recognising it. And heard at 03:04, where a blank section opens what plays
   after a removal: the removal stops where the transcriber declared the next word to start,
   which is before the room stopped being quiet. Every other splice the cut makes is trimmed to
   the sound and then padded back into the quiet — decisions 0001 and 0006. These two edges are
   the only ones that are neither.

   Red, both in `tests/test_stumbles.py`:
   `test_a_word_beside_a_removal_keeps_the_tail_the_transcriber_stopped_short_of` and
   `test_the_quiet_a_removal_ends_in_does_not_play_after_the_splice`. Both read at the
   defaults, so the quiet beside the removal is a pause like any other — which is the
   world this fix has to work in. A rule handed only the quiet no pause claimed is handed
   nothing, and the first version of these two hid that by pinning the bar out of the way.

4. **The detector is asked for half a second and up, so the cut cannot see the quiet it is meant
   to take off a splice.** The blank section at 03:04 is 0.376 s long and the artifact holds no
   record of it. Fixing 3 on its own will not take it out of the operator's XML.

   Red: `tests/test_analyze.py`,
   `test_the_detector_hears_quiet_as_short_as_the_cut_may_leave_behind`.

   The bar is an `AnalysisSettings` field and therefore in the fingerprint. The check goes green
   here; the XML changes only when the operator re-runs `analyze` over both recordings. Say that
   in your last message rather than reporting the blank section gone.

5. **Speech the transcriber wrote no word for is thrown away as though it were nothing.** Heard
   at 02:24, where the reading that plays is the abandoned `vibe co` and the finished one is
   buried under the single word `part` — 2.53 s of speech under one token, removed as part of a
   stumble. And heard at 07:13–10:33, where 3.3 s of junk plays because four attempts at the end
   of line 2 sit under the single word `development.` What separates both from an ordinary long
   word is not length: it is how much of the stretch the detector heard sound in. A word
   stretched over *quiet* is the ordinary case decision 0001 is about and must stay.

   Red: `tests/test_analyze.py`,
   `test_a_word_stretched_over_speech_is_decoded_again_and_replaced`, two cases — `part`
   and `development.` as the recording actually holds them.

   This is ticket 14; read it before starting. The check drives `analyze_recording` with a
   model that hears a stretch differently when handed that stretch alone, which is the
   finding the ticket rests on, and it counts the calls. A span-finder nothing calls does
   not pass it — that was the first version of this check, and a function sitting unused is
   exactly what satisfied it.

6. **A near miss is a total miss, so recovering buried speech lowers a line's coverage.**
   Not from the 28 August listen: this is what problem 5 did when it landed. Cutting
   `Sequence 07` on 29 August recovered the words under `part` — `oh no white coating`,
   which is `vibe coding` misheard — and the cut got worse for it. Line 1 stopped having
   its abandoned attempt removed at all, because `white coating` repeats no word of the
   line it was misheard from; lines flagged went 2 → 3; line 2 fell from 88% coverage and
   clean to 75% and flagged. Alignment compares tokens for equality, so every word the
   second pass hands back that the model heard slightly wrong counts against the line.

   Red: `tests/test_plan.py`,
   `test_a_line_the_transcriber_misheard_is_still_a_complete_reading_of_it`.

   This is ticket 15; read it, and decision 0002 with it — a mishearing is identified
   structurally, by the script word it displaced sitting opposite it, which is what a
   near-miss match finds. `test_two_short_words_a_letter_apart_are_not_the_same_word` is
   green beside it and is the rail: `a` is not `the`, and a measure loose enough to match
   them makes coverage stop meaning anything. Coverage is what disqualifies a take, so
   loosening it loosens every judgement downstream at once.

   Ticket 14's own `## Listen for` predicted the report would *quote* the re-decoded words
   in place of `part 1. No, no,`. It does not — the removal stopped happening instead.
   Correct that item where it stands rather than appending to it.

   **A first near-miss measure shipped on 29 August and made line 1 worse, not better.**
   It fires only where the two words sit exactly opposite each other, and exact matching
   has always stepped over a word the line does not account for. Line 1 reads `with a
   wipe coating`: the `a` is the transcriber's own, near-miss matching stops at it, and
   the line now reaches `with` and hands its last four words to a kept off-script region
   that plays beside it — 56% coverage where equality alone scored 67%. Second red check,
   `tests/test_plan.py`,
   `test_a_near_miss_is_found_past_a_word_the_line_does_not_account_for`. Whether an
   intruder is stepped over is not the mishearing's business; decision 0002 identifies one
   by the script word it displaced sitting opposite it, and `vibe` is opposite `wipe` once
   the `a` is passed.

7. **A line loses its own ending because the attempt it abandoned was written down more
   fully.** The last of the 02:24 fault, and what is left of it after 5 and 6 both landed.
   Line 1 now reads `…with a wipe coating / oh no white coating one no no / part 2.` The
   run in the middle is seven words the line does not account for; `SPAN_GAP_TOKENS`
   tolerates four and not five, so the take ends at `coating` and `part 2` — the line's
   own last words — become a kept off-script region playing beside it. Line 1 is at 78%
   and flagged where equality alone scored 67%, so this is better than it was and still
   not right.

   Red: `tests/test_plan.py`,
   `test_a_line_keeps_its_ending_across_an_attempt_it_abandoned`.

   **A first answer shipped on 30 August and merged three retakes into one take.** It kept
   the bar and added an escape from it: a run longer than the bar is still one reading if
   the match after it is the *very next word of the line*, bounded by the line's own
   length. That is right on the recording — line 1 reaches 100% and unflagged, nothing of
   it is handed to a leftover, and the 15.5 s restart of line 3 is still cut — and it is
   wrong on a retake that gets one word further than the attempt before it, which is
   exactly what the two red checks describe. Three readings of line 2 that each stop short,
   the second reaching one word past the first, now come back as a single take beginning at
   the first. Retake selection and the alternates sequence both go with it.

   The escape cannot be read off the run's length, which is the whole point of this
   problem, and it cannot be read off what follows the run either. What separates the two
   cases is inside the run: a restart re-says words of the line already spoken, and a
   stumble does not. `stumbles.py` already tells a repeat from a mishearing on that signal,
   and decision 0009 measures a region of repeated attempts attempt by attempt for the same
   reason. Neither is a prescription — but an answer that reads only the run's ends has
   both of these cases looking identical, and that is why this one does.

   Nothing about the recording changed. Before the second pass that run was `part one no
   no` — four words, inside the bar. The same abandoned attempt, written down more fully,
   is what pushed it over: a rule for telling a stumble from a restart is now deciding it
   on how well the transcriber heard, which is the one thing it cannot mean. Whether that
   is answered by moving the bar, by scaling it as the comment beside it says the real one
   does, or by judging the run for what it is rather than how long it is, is yours — but a
   number moved far enough to swallow this run will also swallow restarts, so say in your
   commit what you measured it against. Decision 0003 governs if you move it.

One thing the listen asked for is **not** in this loop, because nothing is red for it. At
10:33–11:02 the operator wants the last attempt at line 2's ending to be the one that plays. It
already is, wherever the attempts are words at all: `tests/test_plan.py`,
`test_only_the_last_attempt_at_a_line_s_ending_reaches_the_cut`, green, pins exactly that. What
the listen heard is problem 5 and nothing besides — the rule never fired because the transcriber
wrote one long word where the three attempts were. Do not build a second rule for it.

`Sequence 07` has a golden of its own as of 31 August, and it is the one that will catch
you. Its cut is locked the same way `sequence.mp4`'s is, so any change to `plan` or
`render` now moves two sets of expected output and the messy recording is in both. Read
its **XML** golden rather than its report when you want to know what a change did: the
report says line 1 is found at 100% coverage and selected, and the clips beneath it play
all 7.67 s of the attempt the speaker abandoned. That gap is the reason the golden exists.

Expect `tests/test_golden.py` to be the last thing standing. Problems 1 and 2 move every
collapsed pause in `sequence.mp4`, and that is a diff for a person to read: the loop stops there
on purpose and hands it over.

## What decides that you are done

`uv run pytest` and `uv run mypy`, both green, in a tree where nothing under `tests/`,
`settled/`, `recordings/`, `running/` or `work/` has changed. That is the whole criterion.

Your own reading of your work does not enter into it. Neither does a closing summary that
says the fix is complete — the loop re-runs the checks itself and will not take your word.
Finishing an iteration with checks still red is a normal outcome, not a failure: say what you
changed and what you now know, and stop. The next iteration starts from your commit.

## What you may change

`src/roughcut/`, `settled/` and `work/`.

The last two opened up on 29 August. A loop that may change the code but not the documents
describing it produces one thing reliably: a decision still naming the number the code has
moved, and a ticket still open on work that shipped. That is what happened on the first run
of this loop — read `settled/decisions/0003` against `src/roughcut/pauses.py` for the shape
of it. A document nobody may edit goes stale, and a stale document is worse than none.

What that permission is for, and what it is not:

- **`settled/`** — bring a decision forward when your change contradicts it. Not silently,
  and not by deleting it: a decision carries the alternatives rejected to reach it and the
  evidence that makes the choice checkable, and an amended one says what moved it. Amend
  the claim in its title too if the claim has changed — a file titled as something the
  project no longer believes is worse than the stale number inside it. If you cannot name
  the evidence that overturns a decision, that is the signal to stop rather than to edit.
- **`work/`** — edit a ticket that your change has made untrue. Correct a prediction where
  it stands rather than appending the correction, keep to the 60-line ceiling, and move
  anything that outgrows it to `settled/decisions/` or to `what-it-does.md` and `facts.md`.
  You may open a ticket for something you found and are not fixing.

**What you may never write is a ticket's own verdict.** The `Status:` line and everything
under `## Heard` are the record of a person having played the cut and judged it, and an
agent writing either invents an acceptance that never happened. Your last act on a ticket
is `Status: awaiting-listen` and an empty `## Heard`; `Status: done` is not yours to write
at all. The loop checks this against the previous commit rather than trusting the prompt:
touch either and it reverts the whole of `work/` and counts the iteration as wasted.

These stay locked, and the loop reverts them after your turn:

- **`tests/`** — the checks are the contract being worked against. An agent that edits the
  contract to satisfy it has proved nothing. This includes `tests/committed/`, which holds
  the hand-verified import contract and the committed analysis of the real recording.
- **`recordings/`** — the input material.
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
