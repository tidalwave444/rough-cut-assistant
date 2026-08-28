# Accepted work

Tickets 01–08, closed. Each was confirmed by a person: `## Heard` carries their verdict,
or the one-line reason the ticket had nothing for them to hear. Live tickets stay one to
a file under `open/` and fold in here once they close.

The 60-line ceiling is a rule about a ticket while it is being worked and accepted. This
file is the sum of eight of them and has no ceiling of its own.

---

## 01 — Capture the fixture recording and script

**What to build:** A real recording of the 8-line script, committed to the repo, that every other ticket is verified against. It must contain the defects the tool exists to remove — deliberate flubs with retakes, long pauses, and muttering between attempts — because a clean first-take recording proves nothing.

**Blocked by:** None — can start immediately.

**Status:** done

### Listen for

Nothing the tool produces. What this ticket delivers is source material, and the claims made about it — 60 fps, 48 kHz stereo, 86.25 s, 29 silent regions, longest 1.91 s — are read off the file rather than judged by ear.

- [x] Black-screen MP4 with a single audio track committed to the repo
- [x] Script committed alongside it, one sentence per line
- [x] Recording contains long pauses (29 silent regions found, longest 1.91 s)
- [x] Media properties documented (60 fps, 48 kHz stereo, 86.25 s)

### Comments

Delivered as `recordings/sequence.mp4` and `recordings/textt.txt`. Full media properties in
`facts.md`.

Two things differ from what the spec assumed: the frame rate is **60**, not 30, and the
script file uses **CRLF** line endings with blank lines between sentences.

**The brief was not fully met, and it took until 07 to find out.** The recording was
asked to contain retakes and it contains none — its alternates sequence comes out empty
because no take is ever rejected. So take selection, the most intricate logic in the
tool, is exercised on this recording by nothing at all. `Sequence 07.mp4` was added later
and does have multiple takes of a line, but they are transcription-loop artefacts rather
than genuine retakes. A recording with real flubs and re-reads is still owed.

### Heard

Exempt, per the reason above.

---

## 02 — Verify Premiere accepts a hand-authored FCP7 XML

**What to build:** Proof that the chosen output format actually works, obtained before any code exists. A hand-written XML describing two pieces of the fixture recording butt-spliced together with one pause removed, plus markers and an empty video track, imported into Premiere and checked by eye.

This is first because the FCP7 schema is the only part of the project that cannot be discovered from code, and everything else is built on the assumption that it works.

**Blocked by:** 01

**Status:** done

### Listen for

1. The file imports into Premiere without error, and the sequence duration is exactly as computed — that is the frame arithmetic proved.
2. Two clips visible with the pause removed between them, and the splice seamless on playback: no gap, no click.
3. Sequence markers visible with readable comments, an empty video track present, and audio playing at all.

- [x] XML imports into Premiere without error
- [x] Sequence duration is exactly as computed, proving the frame arithmetic
- [x] Two clips visible with the pause removed between them
- [x] Splice is seamless on playback — no gap, no click
- [x] Sequence markers visible with readable comments
- [x] Empty video track present
- [x] Audio plays

### Comments

All findings, including the exact structural requirements the renderer must reproduce,
are written up in `facts.md`. The verified file is committed at
`tests/committed/minimal2.xml`.

### Heard

Two rounds were needed.

The first attempt modelled the stereo source as two mono tracks and imported **silent**.
Corrected to a single audio track with a truthful `<file>` media declaration.

The second attempt played correctly, but only after manually relinking the media —
`file://localhost/<name>` does not resolve, so the clip imports offline (question mark
icon, red track). Manual relink takes seconds and matches the workflow agreed during
grilling.

---

## 03 — Scaffold, and render a plan into the verified XML

**What to build:** A Python project, and a renderer that turns a plan object — a list of clips with source in/out points, plus a list of markers — into FCP7 XML. Its first job is to reproduce the file that was verified by hand in ticket 02, so that a generated file imports into Premiere identically to one a human wrote.

Nothing analyses media yet. The renderer takes a plan it is handed and turns it into XML; where the plan comes from is the next ticket's problem.

**Blocked by:** 02

**Status:** done

### Listen for

Nothing to hear or see. The renderer reproduces `tests/committed/minimal2.xml` **byte for byte**, so the import criterion is met by identity: the bytes it emits for the spike plan are the bytes already imported and confirmed in ticket 02. A fresh import is not meaningful until a plan diverges from the spike, which first happens in 04.

- [x] Project set up under `uv` with a Python 3.12 environment, because the CUDA transcription backend has no wheels for the system Python
- [x] Renderer produces XML from a plan describing clips (source in/out, timeline position) and markers (position, name, comment)
- [x] Given a plan equivalent to the verified spike, output is structurally identical to `tests/committed/minimal2.xml`
- [x] Generated file imports into Premiere with audio playing, correct duration, and visible markers
- [x] Timebase, frame rate, resolution, sample rate and channel count are taken from the plan, not hardcoded
- [x] Seconds are converted to frames by rounding, matching the arithmetic proven in the spike
- [x] Test asserts the rendered XML against the committed reference file
- [x] Test covers a plan with zero markers and a plan with a single clip

### Comments

**Read `facts.md` before writing any of this.** It records structural
requirements that are not guessable and cost two rounds of manual testing to discover —
in particular that a stereo source needs one audio track rather than two, and that the
`<file>` element must declare both video and audio media. `tests/committed/minimal2.xml` is the
contract, and it is never regenerated from the renderer; `spec.md` records why.

Why the serializer is hand-rolled, and how NTSC rates are authored: `spec.md`.

Two things were carried further than the checklist required. `Plan` wraps a list of
sequences rather than the renderer taking one, because the spec fixes the output as "one
file, two sequences" — clipitem ids are unique document-wide and clips from one recording
share a `masterclipid` and a `file` id across sequences. The cross-sequence `<file>`
reference was plausible but unverified here; **07's import confirmed it.** And NTSC was
handled early because `<ntsc>` is a required element and could not be avoided.

`pathurl` percent-encodes the filename, so a name with a space produces a syntactically
valid file URL. It is still a bare filename here and still arrives offline; 05 settled
what an absolute path does.

### Heard

Exempt, per the reason above.

---

## 04 — End-to-end tracer: MP4 and script to importable XML

**What to build:** The first version that does something useful from a single command. Point it at the recording and the script, and get a sequence you can import into Premiere.

The cutting logic is deliberately trivial: the whole recording as one clip, no pauses removed, no takes chosen. The point is that the complete path exists and every later ticket makes the cut better rather than making it exist.

This ticket also establishes the project's single test seam. All media I/O — probing the container, transcribing, detecting silence — lives in one analysis step that writes a JSON artifact. Everything after that seam is pure and testable with hand-written JSON, no GPU and no media file.

**Blocked by:** 03

**Status:** done

### Listen for

Nothing to hear or see. The emitted XML is structurally the file already verified by hand in ticket 02 — one clip, no markers — and the golden test locks it to that structure, so a fresh import would prove nothing it does not already prove. The first output that genuinely diverges is 05's, and that is the one worth importing.

- [x] Analysis step probes the container for duration, frame rate and audio properties
- [x] Analysis step transcribes with word-level timestamps using local Whisper on GPU
- [x] Analysis step detects silent regions
- [x] All three results land in one JSON artifact holding source properties, words with start/end times, and silence regions
- [x] Analysis is cached — re-running without changing the input does not re-transcribe
- [x] Planning and rendering run against an existing analysis artifact without touching the media
- [x] One command turns the fixture recording plus script into an importable XML
- [x] A first report is written, stating source duration, output duration, and word count
- [x] Script parsing strips carriage returns and ignores blank lines
- [x] Clear failure when the audio stream, the script, or the GPU is unavailable
- [x] Smoke test over the analysis step, marked slow and excluded from the default run: timestamps are monotonic and within the file duration, frame rate is plausible, known silences are present
- [x] The fixture's analysis artifact is committed so later tickets can be tested without hardware

### Comments

The analysis artifact is the project's most important contract — every subsequent ticket
is tested by hand-writing one. Its shape, what feeds the cache fingerprint, which
settings are flags, and how NTSC rates are judged are all in `spec.md`. Never assert
exact transcription text anywhere: model output is not a stable contract.

Frame rate comes from the file. The fixture is 60 fps; the 30 fps in the spec is only the
fallback for a container that declares nothing usable.

Three commands rather than one, because the seam is worth exposing: `cut` is the whole
tool, `analyze` is the media stage alone, and `render` plans and renders from an existing
artifact without opening the recording. `render`'s tests prove the media is never touched
— the analysis they drive names an MP4 that does not exist anywhere near the test.

Run figures for the fixture and the CUDA preloading the analysis stage needs are in
`facts.md`.

### Heard

Exempt, per the reason above.

---

## 05 — Script alignment: per-line clips and markers

**What to build:** A timeline you can read. Each script line is located in the recording, the sequence is assembled from one clip per line in script order, and a marker sits at each line's start carrying that line's text — so scrubbing the timeline tells you which visual belongs where without replaying the audio.

**Blocked by:** 04

**Status:** done

### Listen for

1. `out/Sequence 07.xml` in Premiere — 6 clips, 9 markers. The marker comments should be readable and carry the script's own text. This is the file that proves the ticket.
2. `out/Sequence 07.xml`, line 5 — four of the nine markers are that line's enumerated items. This is the part most likely to arrive as one marker, or as three wrong ones.
3. `out/sequence.xml` — the clean case, 8 clips and 10 markers, every line of that script found. Splices should land where `out/sequence.report.txt` says.
4. `out/sequence-winpath.xml` or `out/Sequence 07-winpath.xml` — same file with the `<pathurl>` naming an absolute Windows path. If the clip arrives online with no Link Media dialog, the manual relink is not inherent to the format. Record the answer in `facts.md`.

- [x] Script and transcript are normalised to token streams before comparison — lowercased, punctuation stripped, numbers expanded
- [x] Sequence alignment produces the spine: the monotonic mapping of transcript regions to script lines
- [x] Transcript regions not claimed by the spine are scored against neighbouring script lines and labelled as either a retake of that line or off-script material
- [x] The sequence is assembled in script order, regardless of the order lines were spoken
- [x] One marker per script line, positioned at that line's start, with the line's text as the comment
- [x] Lines containing an enumeration produce one marker per enumerated item
- [x] Script lines not found in the recording are flagged in the report and skipped without aborting
- [x] Report lists each line with the source time it was found at
- [x] Tests drive planning with hand-written analysis fixtures: a clean read, a line spoken out of order, a line missing entirely, a line containing an enumeration

### Comments

This ticket only identifies retakes and labels them; choosing between them is 07.

What a line claims and why the score is coverage rather than similarity: **decision 0004**.
Why a leftover asks its neighbours before it asks the whole script: **decision 0005**.

What shipped: on `sequence.mp4` all 8 lines located, 10 markers, 9.45 s of dead air gone.
On `Sequence 07.mp4` 6 of 9 located — the three missing ones are the transcription loop
recorded in `facts.md`, which is the analysis stage's fault and still wants a
ticket of its own.

### Heard

Both files went into Premiere and the ticket holds. The markers arrive where the report
says, their comments read cleanly, and the text in them is the script's — including the
enumerated items of line 5 (items 1 and 2).

Item 4 is answered and the question is closed: an absolute Windows path links
automatically, with no Link Media dialog. What follows from it is in `facts.md`.

Faults were found in what the cut *sounds* like. None of them is alignment's — the lines
are located correctly — so they are not recorded here; they became 06, 09, 10 and 11.

---

## 06 — Pause collapsing

**What to build:** A cut that is actually tighter than the raw recording. Long silences are shortened — not eliminated — so the result still sounds like a person speaking rather than a machine-gun read.

**Blocked by:** 05

**Status:** done

### Listen for

1. `out/sequence.xml` — every clip's frame numbers moved, so the sequence wants re-importing once. It must lay out on a single audio track with no clip on top of another.
2. The line-3 splice in that file — the one place a clip is split mid-line, where the collapsed pause is. It should neither overlap the next clip nor leave a hole.
3. The same splice by ear: this ticket pads the pause cuts but not the joins between lines, so a clipped word tail here is expected rather than a fault of the collapse.

- [x] A gap between consecutive words longer than the threshold is eligible for shortening; gaps below it are left untouched
- [x] Eligible gaps are collapsed to a floor, never removed entirely
- [x] Defaults: threshold 0.7 s, floor 0.3 s
- [x] Threshold, floor and padding are exposed as command-line options
- [x] The exact cut boundary comes from the silence regions overlapping the gap, not from the word timestamps, with padding so speech is not clipped
- [x] A transcript gap with no corroborating silence region is left alone
- [x] Cuts are never placed inside a word
- [x] Report states how many pauses were shortened and how much time each removed
- [x] Tests: a long pause collapses to the floor, a pause below threshold is untouched, a gap with no matching silence region is untouched, a gap at the very start and at the very end are both handled

### Comments

**Two of the criteria above were later reversed and are kept as the record of what was
accepted here, not as current behaviour.** Ticket 10 replaced the transcript-gap rule
with the silence regions themselves, and removed "cuts are never placed inside a word"
outright — on this material that rule was the sole reason thirty seconds of dead air
survived into the cut. See decision 0001.

Collapsing rather than eliminating is a product decision, not an implementation shortcut:
removing all silence makes the read breathless, and restoring pacing afterwards means
re-trimming every edit point by hand.

This ticket and 07 are siblings — both depend only on 05 and neither on the other.

Splitting a line into two clips exposed a latent renderer bug: clip starts were quantised
from the timeline and lengths from the source, so butt-spliced clips could disagree by a
frame. Both ends are now quantised on the timeline; `spec.md` records the rule.

Padding the joins between lines was left undone here on purpose, and became 09.

### Heard

The re-import was run and the renderer fix holds: the sequence lays out on a single audio
track with no clip on top of another, and the one mid-line splice — the collapsed pause —
neither overlaps nor leaves a hole.

The listen-through confirmed the deferral above as a real fault rather than a theoretical
one: unpadded splices audibly clip the tail of a word. That is its own ticket, not a
reopening of this one.

---

## 07 — Take selection and the alternates sequence

**What to build:** The tool choosing for you. Where a line was read more than once, the best attempt goes into the rough cut and the rest go into a second sequence — so overruling a choice takes seconds instead of scrubbing the source.

**Blocked by:** 05

**Status:** done

### Listen for

1. `out/Sequence 07.xml` — both sequences should arrive, named `RoughCut` and `RoughCut_Alternates` in the project panel. This is the only real material with more than one take of a line.
2. The alternates timeline of that file — 12 clips end to end, each marked `Line 6 take N` with the reason it lost. Two of them are frames long, so check they do not break the layout.
3. `out/sequence.xml` — its alternates sequence is **empty**, because nothing was rejected. An empty sequence has never been put in front of Premiere. If it is refused on import, emitting the sequence only when something lost is a one-line change.

- [x] Default rule: the most recent complete attempt at each line wins
- [x] Scoring acts only as a veto — a take is disqualified for failing to cover the whole line, being truncated, or exceeding a disfluency threshold
- [x] When the most recent take is disqualified, selection falls back to the previous one, and so on
- [x] When every take is disqualified, the least-bad is selected and the line is flagged in the report
- [x] Output contains two sequences in one file: the rough cut, and the alternates
- [x] Alternates are laid end to end, each with a marker naming its script line, take number, and the reason it lost
- [x] Report lists every take considered per line with its coverage, its disfluency count, and why it won or lost
- [x] Tests: three takes with the last complete, three with the last truncated, all takes incomplete, a line with exactly one take

### Comments

Recency is the selector and scoring only a veto because the recording behaviour carries
the strongest signal — a person re-records until satisfied and then stops. A weighted
multi-signal score was rejected: with no labelled data the weights would be invented, and
a wrong choice would be unexplainable. Every decision must be explainable in one sentence.

Alignment now finds every reading of a line rather than the first adequate one, so a
retake is a take and `Leftover.retake_of` is gone — a leftover means exactly one thing.
What a take is a part of: **decision 0004**.

What shipped: `sequence.golden.xml` changed only by gaining the alternates sequence, every
line's frames untouched — finding all the takes moved no take that was already in use.

Where this behaves badly is on `Sequence 07`, where the transcription loop produces 13
takes of line 6 and recency picks a 2.68 s fragment over the real 7 s reading. A fourth
veto would fix it and is deliberately not added; both the numbers and the reasoning are
in `facts.md` and `spec.md`.

### Heard

Both files imported, so both shapes of the second sequence are ones Premiere accepts: the
empty one from the fixture and the twelve-clip one from `Sequence 07`, frames-long loop
artefacts included. Emitting the empty timeline unconditionally stays, and the one-line
fallback in item 3 is not needed.

---

## 08 — Off-script material handling

**What to build:** Restarts and mutters gone from the cut, without risk of silently losing something you actually meant to say. Short fragments and failed restarts are removed; anything longer survives in place with a marker, so a sentence you improvised is never deleted without you seeing it.

**Blocked by:** 07

**Status:** done

### Listen for

1. `out/Sequence 07.xml` — it now runs 14 s longer, and those 14 s are one kept stretch spliced between two script lines. Play the splices either side of it: they should land where the report says.
2. The same file's `Off-script` marker — it should read clearly enough to decide from without scrubbing. If it does not, the keep-and-mark asymmetry costs more than the deletion it was meant to avoid.
3. Deleting that region in Premiere should be one keystroke. That is the assumption the whole asymmetry rests on, and it has not been tested by hand before.

- [x] An off-script region is removed if it is shorter than a duration threshold, defaulting to about 2.5 s
- [x] An off-script region is removed if it near-duplicates an adjacent script line — a failed restart
- [x] An off-script region is removed if it matches a configurable stop-phrase list
- [x] Everything else is kept in place and marked as off-script
- [x] Thresholds and the stop-phrase list are exposed as options
- [x] Report lists every off-script region with its duration, its text, and whether it was kept or cut
- [x] Tests: a short fragment is cut, a long off-script sentence is kept and marked, a near-duplicate of an adjacent line is cut, a stop-phrase is cut

### Comments

The asymmetry is deliberate. Deleting a kept line in Premiere is one keystroke;
recovering a deleted line requires knowing it existed. When in doubt, keep and mark.
Nothing is ever destroyed in any case — the XML references the source by in/out points.

Why a restart is measured by containment rather than coverage, and why "adjacent" is
narrower here than for a retake: **decision 0007**. What "in place" anchors to, and the two
anchors that were tried and are wrong: **decision 0008**.

What shipped: `sequence.golden.xml` is byte-identical — only the report gained a section.
Neither recording exercises this ticket properly; both off-script regions found are
Whisper loops rather than speech, and `facts.md` records what that means for the
thresholds.

### Heard

Played through. The kept region sits where it was said, the `Off-script` marker quotes it
well enough to judge without scrubbing, and deleting it is the single keystroke the
asymmetry is built on.

The listen-through also found the cut looser than it should be — but what is still
audible is not off-script material in this ticket's sense. It sits *inside* a take,
between two matched words, where `align` never raises a leftover and nothing here ever
sees it. So it is not this ticket's rules failing or its thresholds being wrong; it is
work no ticket had covered, and it became 10 and 11.

---

