# CONTEXT

The words this project uses, and the distinctions they carry. Where a term names a type,
that type's docstring is its definition — this file exists for the boundaries between
terms, which no single docstring can state.

## The three places a sentence lives

A sentence exists in three forms and they are never interchangeable.

- **line** — a sentence *in the script*. Numbered from 1 among the non-blank lines, and
  that number is the stable identifier in the plan, the report and every marker.
- **reading** / **take** — a sentence *in the recording*. One attempt at a line. A line
  read three times has three takes, of which one plays and the rest become alternates.
- **clip** — a piece of source *on the timeline*. What Premiere receives.

"Line 6 is 2.68 s long" is a category error: a line has no duration, a take does.

## What is on the script and what is not

- **take** — a reading of a line, however poor. A retake is a take, bound for the cut or
  the alternates.
- **leftover** — speech no line accounts for. It means exactly one thing: material off
  the script. A retake is *not* a leftover, and not "unused speech" — that phrasing was
  used early and dropped, because it made a second reading look like waste.
- **off-script** — a leftover the cut has judged: kept in place and marked, or removed as
  short, as a failed restart, or as a stop phrase.
- **spine** — the monotonic mapping of transcript to script lines, established before
  anything else is classified. Everything not on the spine is a leftover until judged.

## Two words inside a take that look alike

Both are transcript words the line does not account for. They are opposites.

- **stumble** — an abandoned attempt. It goes.
- **mishearing** — a word spoken perfectly well and transcribed wrong. It stays. What
  identifies it is structural: the script word it displaced sits opposite it (decision 0002).

"It did not match the line, so it is junk" is the rule this vocabulary exists to prevent.

## The two directions of one fraction

- **coverage** — how much *of the line* a stretch accounts for. Decides what a line
  claims (decision 0004), and guards every removal inside a take.
- **likeness** — how much *of what was said* is the line. Decides whether a leftover is a
  failed restart (decision 0007).

They are not interchangeable and neither is "similarity", which was measured first and
rejected: repeats dilute it, so it scores an obvious restart near zero.

## Quiet, and what is done to it

- **silence** / **quiet** — a region the detector heard as quiet. The authority on where
  sound is, over the word timestamps (decision 0001).
- **pause** — a stretch of quiet together with the piece of it the cut takes out.
- **threshold** — the length above which quiet is shortened. **floor** — what it is
  shortened to. **pad** — hundredths kept off a cut so speech is not clipped.

A pad does two opposite jobs and so has two settings: held *inside* the quiet at a pause
cut, extended *into* it at a splice (decision 0006).

## Three stretches that are not one type

Each is a start and an end, and collapsing them would say nothing:

- **span** — a stretch that plays: a take, or a kept off-script region.
- **segment** — a piece that survives the shortening and reaches a clip.
- **cut** — a stretch taken *out* of something that plays.

**tightened** — a stretch with everything the cut removes from it already gone.

## The pipeline

- **analysis** — what the media stage learned about a recording. The seam's contract.
- **plan** — every decision, as data, before any XML exists.
- **render** — plan to XML and report.
- **golden** — a committed expected output the tests assert against.
- **alternates** — the second sequence, holding every reading that lost.
- **marker** — a note on the timeline: a script line, a **beat** within one, or a record
  of what was removed.

## Accepting work

- **listen** — a person playing the cut to judge it. The only thing that closes a ticket.
- **sitting** — one playthrough, which may close several tickets at once.
- **heard** — what that person reported, in their words. Nothing else says whether an
  acceptance happened. See `settled/how-we-work.md`.

## Words this project avoids

"similarity" (use coverage or likeness), "unused speech" (a retake is a take), "junk"
(nothing is junk until a rule names why), "the cut is wrong" (say which take, which line,
which splice).
