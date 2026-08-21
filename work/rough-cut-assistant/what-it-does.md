# Rough Cut Assistant — v1

Status: ready-for-agent

## Problem Statement

I record short scripted videos: a black-screen MP4 capturing voiceover against a script I wrote beforehand. Before I can do any real editing, I have to do a mechanical pass that takes far longer than the finished video:

- Scrub the whole recording to find and delete the long dead air between attempts.
- Find every line I flubbed and re-read, listen to each attempt, and decide which one to keep.
- Delete the muttering between attempts — the "ugh", the "sorry, again", the half-finished restarts.
- Then, once the audio is finally assembled, go back through and work out where each visual belongs, because I need to lay screen recordings over the voiceover and I have nothing marking where each script line starts.

None of this is editorial judgement. It is bookkeeping I already did in my head while recording, thrown away the moment I stopped, and reconstructed by hand in Premiere. On a 45-second video it is disproportionately expensive, and it is the reason the gap between finishing a recording and starting the actual edit is measured in hours.

## Solution

A command-line tool that reads the raw MP4 and the script, and emits a single XML file I import into Premiere Pro. The import gives me two sequences:

- **RoughCut** — my selected takes, butt-spliced in script order, with long pauses shortened, restarts and mutters removed, and an empty video track ready for me to drop screen recordings onto. A marker sits at the start of every script line carrying that line's text, so scrubbing the timeline tells me exactly which visual belongs where.
- **RoughCut_Alternates** — every take the tool rejected, laid end to end, each marked with the script line and take number it belongs to. If I disagree with a choice, the alternative is seconds away instead of buried in a two-hour source.

Alongside it, a readable report explaining every decision: which take won each line and why the others lost, how much time each pause removal saved, and what off-script material was kept or dropped.

Nothing is destroyed. The XML references the original MP4 by in/out points, so every frame of the source remains available.

The tool is fully deterministic and fully offline. No API keys, no network, no model calls. The same inputs always produce the same XML.

## Implementation Decisions

### Pipeline shape and the single seam

Three stages, with all media I/O confined to the first:

- **analyze** — the only stage that opens the MP4. Probes the container, transcribes with word-level timestamps, and detects silence regions. Writes one analysis artifact.
- **plan** — a pure function over the analysis artifact and the script text. Produces the complete set of cut decisions.
- **render** — a pure function over the plan. Produces the XML text and the report text.

The boundary between `analyze` and `plan` is the project's single test seam. Everything below it is deterministic and hardware-free.

This supersedes an earlier four-stage design (transcribe / align / cuts / emit); `align` and `cuts` had no reason to touch the media file, and leaving frame-rate probing and silence detection embedded in them would have forced every test of the cut logic to depend on real audio.

### The analysis artifact

The shape of this artifact is the contract that makes the seam work, so it is fixed deliberately. Trimmed to the decision-bearing parts:

```
Analysis {
  source: { filename, duration_seconds, fps, ntsc, audio_sample_rate }
  words:  [ { text, start_seconds, end_seconds, confidence } ]
  silences: [ { start_seconds, end_seconds } ]
}
```

Times are seconds as floats throughout; conversion to frames happens only in `render`. `filename` is the bare basename, not a path — see the media-reference decision below.

**The cache stamps the fingerprint, not the analyzer.** Describing a recording and recording what that description was derived from are two jobs: the analysis says nothing about where it came from, and the cache records the settings it was produced under. Every media setting feeds the fingerprint, so changing the silence threshold re-analyzes rather than serving a result those settings no longer describe. A hand-written fixture parked at the cache path carries no fingerprint and is therefore never mistaken for a cache hit.

Only `--device` and the two silence thresholds are flags. The model, its quantisation and the language are fixed by the spec; they are settings because they belong in the fingerprint, not because a run should choose them.

### Transcription

Local Whisper via `faster-whisper`, model `large-v3`, compute type `int8_float16`, on GPU. Word-level timestamps are required — they are the substrate for alignment, take detection, and marker placement.

Whisper's own VAD filtering is disabled: pause handling is the tool's job and Whisper's silence suppression would destroy the gaps the tool needs to reason about.

Runs under a Python 3.12 environment managed by `uv`, because the CUDA backend has no wheels for the system Python. At the target recording length (2–4 minutes) transcription takes seconds, which is why the most accurate model is chosen over faster distilled variants.

CPU fallback is supported but not optimised for.

### Silence detection

`ffmpeg`'s silence detection filter, run once over the whole file during `analyze`, producing a list of silent regions. Thresholds for silence level and minimum duration are configurable but have defaults tuned for a quiet room.

### Alignment

Both the script and the transcript are normalised to token streams (lowercased, punctuation stripped, numbers expanded). Longest-matching-block sequence alignment produces the spine: the monotonic mapping of transcript regions to script lines representing the good read of each line.

A line's take is a **span** of its matched tokens rather than all of them, split wherever too much unheard speech sits between matches — otherwise a restarted line stretches from its first attempt to its last and swallows every retake.

Transcript regions not claimed by the spine are then scored against the script lines their neighbours map to, and the score is **coverage** — how much of the line the region accounts for — not similarity:

- Coverage of 0.6 of an adjacent line → a **retake** of that line.
- Below that → **off-script** material.

If no neighbour reads like the leftover, the rest of the script is asked, and a leftover matching a line that has no take yet becomes that line's take. Only the part of it that reads as the line is taken; what was said either side goes back on the pile and is labelled in its own right.

Alignment finds **every** reading of a line, not the first adequate one — a second reading is a take of that line, bound for the cut or the alternates, and not "unused speech". So a leftover means exactly one thing: material off the script.

The ordering and the measure are both load-bearing — see decision 0005 and decision 0004.

### Take selection

**Rule: the last complete take wins.** Scoring acts only as a veto, never as the primary selector.

A take is disqualified if it fails to cover the whole script line, is truncated, or exceeds a disfluency threshold. If the most recent take is disqualified, the tool falls back to the previous one, and so on. If every take is disqualified, the least-bad is selected and the line is flagged in the report.

The rationale is that the recording behaviour itself carries the strongest signal — a person re-records until satisfied and then stops. A weighted multi-signal score was rejected for v1: with no labelled data the weights would be invented, and a wrong choice would be unexplainable.

Every take considered is recorded in the plan with its coverage, its disfluency count, and the reason it won or lost. The one-sentence explanation names only the takes that lost by a fault of their own — a take that lost by being earlier than the winner needs no explaining, since that is the rule itself. So `take 3 of 3; take 1 truncated — stopped 3 words short`, never a recital of every take.

Truncation is tested before coverage, though a truncated take is nearly always short of coverage too: "stopped 5 words short" says what happened, where "18 of 23 words" leaves the reader to work out whether the missing five were the end.

The tolerance for a truncated take is **flat, not scaled with the line**. A proportional allowance was written first and removed: across both real recordings every take either reaches the last word or stops five short, so scaling decided nothing and would have been a threshold invented to look careful — see decision 0003.

A fourth veto — disqualifying a take whose duration is implausible for the number of words it claims — is deliberately **not** added, for the same reason. It would fix one real symptom on the second recording, but the threshold would be invented and the fault it compensates for belongs to the analysis stage.

### Pause handling

Pauses are located from the detected silence regions, not from the transcript. A region longer than the threshold is eligible; the cut is placed inside it with a small pad off both edges, so that speech is never clipped.

Eligible pauses are **collapsed to a floor, not eliminated**. Default: quiet running over 0.7 s is shortened to 0.3 s. Both values are configurable, and the defaults are held deliberately rather than tuned — see decision 0003.

The pad is a rail underneath the floor, not an inset the threshold is measured through: a region longer than the threshold gives up everything but the floor, and what remains of it is `max(floor, 2 × pad)`, which at the defaults is the floor by 0.2 s.

A collapse gives up only what the audio corroborates, so a pause does not always reach the floor. A 1.76 s gap of which only 1.19 s registered as silent collapses to 0.67 s, not to 0.3 s. That is the cut boundary coming from the silence regions rather than from the word timestamps, working as intended — not an undershoot.

An earlier design read a pause off the transcript — the gap between consecutive word end and start times — and used silence only to corroborate it. It was replaced because the transcriber leaves almost no such gaps: it stretches a word over the pause that follows it, so on real material the quiet sits underneath the words rather than between them and the rule almost never fired. A cut may therefore fall inside a word's declared span; the word's timestamps bound nothing. See decision 0001.

Quiet at the very start or end of a take is removed in full rather than collapsed: a take begins where sound begins, and a floor exists to hold a beat between two words, which is not what sits on the outside of a splice.

Trimming a take to the sound and padding the splice back into the quiet are one decision in two steps, taken in that order — trim first, then pad — so that the two never move the same in point against each other.

### Splice padding

Every clip's in point moves earlier and its out point later, by default 0.15 s, so a last consonant still plays and a join sounds like a join rather than a word cut short. The pad is bounded by the quiet the detector heard rather than by the neighbouring word's declared edge — see decision 0006 — and a join with no detected quiet gets no pad at all.

Two pieces of source that both play may not claim the same audio: neither pad reaches past the middle of the gap between them, so a gap wide enough for only one of them is shared rather than double-claimed. Kept off-script regions are padded on the same rule as line takes.

`--splice-padding-seconds` is separate from `--pause-padding-seconds`. Like every option that decides the plan rather than the analysis, `render` takes it too, so trying a value costs no transcription.

### Off-script material

A leftover region is removed if it is shorter than a duration threshold (default ~2.5 s), or if it is a near-duplicate of an adjacent script line (a failed restart), or if it matches a configurable stop-phrase list.

Anything else is **kept in place and marked** as off-script. This is deliberately asymmetric: deleting a kept line in Premiere is one keystroke, whereas recovering a deleted line requires knowing it existed. "In place" means between the two lines it was spoken between rather than at the time it was said — see decision 0008 — and "near-duplicate" is containment rather than coverage, see decision 0007. Containment is taken attempt by attempt, so one restart said five times reads as a restart rather than as a fifth of one, see decision 0009.

All three removal rules are bars a region has to fail, so every one of them only ever removes more and leaving them alone keeps everything not plainly a mutter. That property is worth preserving if a fourth rule is ever added.

The stop-phrase list ships short and blunt: only phrases that say "start over" outright. A bare "sorry" was considered and left off — it appears inside sentences people mean, and a default that eats those is the exact failure the asymmetry exists to prevent. Phrases given on the command line **replace** the list rather than adding to it, so what a run drops is exactly what was asked for.

A kept region is cut material like any other: the pauses inside it collapse to the floor on the same rule as a take's.

The report quotes a removed region **in full**, never as an excerpt. Elsewhere a truncated quote is a convenience; here it is the only record that the region existed, and someone who does not know it existed cannot go looking for it.

An empty script keeps the whole recording rather than planning nothing: without a script to read it against, nothing said can be shown to be a restart. This is a degenerate case — `read_script` rejects an empty file — but it is the honest consequence of the rule.

### Stumbles inside a take

A line's clip runs from its first matched word to its last, so an abandoned attempt sitting between the two plays in the cut. Words inside a take that the line does not account for are two opposite things, and only one of them may be removed: a **stumble**, which must go, and a word the transcriber **misheard**, which was spoken perfectly well and whose removal would delete real speech.

Two signals separate them, neither of them a threshold.

A **repeated word** marks a stumble: an unmatched word that reads as a word of the line already spoken in that take, or spoken later in it. The stretch between the two utterances is removed. This is guarded by coverage — a removal is refused if it would cost the line one of its own words, which is what stops the same test firing on "a" and "the" and eating half a sentence.

**Words with nothing left opposite them** are removed too. A mishearing always has the script word it displaced sitting opposite it; a run in a place the line has already fully accounted for cannot be the line said wrong.

Everything else stays. A run standing opposite unmatched script words is the line misheard, and it is kept whole.

Every removal is named in the report and quoted in full, on the same reasoning as a removed off-script region: the report is the only record that it existed.

A pause and a removal can cover the same moment, so the report accounts for the time once. Everything cut out of a stretch is merged before that stretch is measured — a second removed twice is still one second — and a pause a removal reaches into at all is dropped from the pause table rather than reported, because it is not a pause in the cut any more. Otherwise the two tables would each claim to have taken the same second while the cut takes it once.

### Markers

One marker per script line, positioned at the start of that line's selected take on the rough-cut timeline, with the line's script text as the comment.

A marker's word may begin at a time the cut no longer contains — inside a collapsed region, or inside the head trim of its own take. The marker is clamped to the nearest end of the stretch that carries it: nothing is placed at a time that does not exist.

Lines containing enumerations are split into one marker per enumerated item, so a line listing three subjects yields three visual beats. Enumeration is a **written** signal, not a semantic one: three or more comma- or question-mark-separated items whose last begins "and" or "or". The bar is three because two clauses joined by "and" is how ordinary sentences are written. A one-word opener ("Here,") is folded into the item it introduces rather than becoming a marker of its own.

The alternates sequence carries one marker per alternate, naming the script line, the take number, and the reason it lost.

Chapter markers are **not** produced — at the target video length they carry no information.

### Output format

Final Cut Pro 7 XML, chosen because it is the richest format Premiere Pro imports natively: it carries clip instances with source in/out points, multiple sequences, and markers with comments, and it is plain text that can be generated and tested without any Adobe software present.

One file, two sequences: the rough cut and the alternates.

The rough-cut sequence declares one audio track carrying the selected takes and one **empty** video track, ready to receive screen recordings. The MP4's black picture stream is not referenced — it carries no information and would only need to be deleted.

Both sequences are always emitted, even when nothing was rejected. Omitting an empty alternates timeline as clutter was considered: an empty timeline that is *there* says "nothing was rejected", where a missing one says nothing at all.

The serializer is hand-rolled rather than `xml.etree`, because the output is a byte-level contract — `etree` writes `<file id="file-1" />` with a space, and post-processing its output to match is uglier than a 50-line writer.

All timings are integer frame counts against the sequence timebase. **Both ends of a clip are quantised on the timeline** and the source out point derived from them, so consecutive clips meet on the same frame number with no one-frame overlaps or holes — a sequence with either is one Premiere cannot lay out. The half-frame of quantisation error therefore lands in the source range, where it is inaudible.

The timebase is read from the source file. A whole rate is authored as-is; a whole rate slowed by 1000/1001 (29.97, 23.976, 59.94) is flagged NTSC and its frame *counts* are counted at the real rate, so 100 s is 2997 frames rather than 3000. **NTSC is a broadcast rate, not merely a fractional one** — a variable-rate container averaging 30.303 is not 29.97, and flagging it as such would conform every clip in the sequence, so anything else nonsensical gets the 30 fps non-drop fallback. `displayformat` stays `NDF` even for NTSC, because drop-frame affects only how a timecode is displayed and every sequence here starts at 00:00:00:00.

### Media reference

The XML references the media by bare filename only. Premiere prompts to relink once on import, and the user points at the file.

This deliberately removes cross-filesystem path translation from v1's scope: the tool runs in one filesystem namespace and Premiere runs in another, and a one-time relink dialog is a smaller cost than a path-rewriting layer that can silently produce an offline sequence.

### Determinism

No stage calls a language model or any network service. Given identical inputs and configuration, output is byte-identical. This is a hard constraint, not a preference — it is what makes the golden-file test meaningful and what makes a surprising cut diagnosable.

Everything below the seam is deterministic by construction. Transcription is not: `temperature=0.0` and a fixed model make it reproducible in practice, and a fresh run has reproduced the committed artifact byte for byte, but that is an observation on one machine rather than a guarantee. The committed analysis artifact is what the rest of the project is deterministic against.

An earlier design placed a model-driven semantic stage between planning and rendering to propose chapters and visual beats. It was dropped: chapters are meaningless at this video length, and with a one-sentence-per-line script the visual beats fall out of the line structure deterministically.

### Script format

One sentence per line, no markup. Blank lines ignored — the fixture script separates sentences with them, so line numbering counts **non-blank lines only**. That number is the stable identifier used in the plan, the report, and every marker.

## Testing Decisions

### What makes a good test here

Tests assert on **what the tool decided**, never on how it decided it. A test may assert that line 4's selected take starts at a given source time, that a 1.8 s pause was reduced to 0.3 s, that a restart was excluded, or that the emitted XML declares a given timebase. A test must not assert on alignment block counts, similarity scores, intermediate data structures, or the number of passes an algorithm makes — those are free to change.

The unit of observation is the plan and the rendered output, not the internals of alignment or scoring. Alignment therefore has no tests of its own — everything it decides is asserted through `build_plan` and `render_report`. The one exception is token normalisation: it is the only place a spelling difference can decide a match, so the reduction itself is a contract and is tested directly.

The plan carries the decisions and not just the geometry, which is what keeps this possible: the report is a pure function of the plan and cannot describe a cut other than the one rendered.

### Testing at the seam

Nearly all tests drive `plan` and `render` with hand-authored analysis fixtures — small JSON documents describing a synthetic recording word by word. This is possible precisely because the seam exists, and it is what keeps the suite fast and hardware-free.

Fixtures are written to isolate one behaviour each:

- A clean read with no retakes and no pauses — the baseline.
- A single long pause — asserts collapse to the floor, and that the floor is preserved rather than eliminated.
- A pause below threshold — asserts it is left untouched.
- A silence lying wholly under one word's declared span — asserts it is collapsed anyway.
- Silence at the head and at the tail of a take — asserts both are removed in full rather than collapsed to the floor.
- A stumble that repeats a word of the line — asserts the stretch between the two utterances is removed, and that a misheard word standing opposite the script word it displaced is kept.
- A repetition whose removal would cost the line one of its own words — asserts it is refused.
- Three attempts at one line, the last complete — asserts the last wins.
- Three attempts, the last truncated — asserts fallback to the previous complete take.
- All attempts at a line incomplete — asserts the least-bad is selected and the line is flagged.
- A short off-script fragment — asserts removal.
- A long off-script sentence — asserts it is kept in place and marked.
- An off-script fragment that near-duplicates an adjacent line — asserts removal as a restake.
- A script line missing from the recording entirely — asserts it is flagged, and that the tool still produces a usable cut.
- A line containing an enumeration — asserts one marker per item.
- A recording whose lines were spoken out of script order — asserts script-order assembly.

### Golden-file test

One golden test captures the real recording's analysis artifact once and asserts the complete rendered XML against a committed expected output. This catches unintended changes to the schema, the timebase handling, marker placement, and sequence structure in a single assertion — and because the analysis artifact is committed, it needs neither the GPU nor the MP4 to run.

The report is golden-tested alongside the XML, and it is the artifact actually reviewed: an alignment change shows up there as a line moving, which is reviewable, where in the XML alone it shows up as a frame count changing, which is not.

The hand-verified reference file from the import spike is **never regenerated from the renderer**. It is the independent source of truth, and regenerating it would make the test circular. Regeneration applies only to the rendered-output goldens, which are derived from a committed analysis artifact.

A hand-written analysis fixture needs only the five decision-bearing source properties — filename, duration, fps, ntsc, sample rate. Width, height, channel count and bit depth describe the format the sequence is authored at rather than the cut, so they default; no fixture cares about the picture.

The golden files are regenerable by an explicit command, so that intentional changes are a deliberate, reviewable diff rather than a chore.

### Analysis stage

`analyze` gets one smoke test, marked slow and excluded from the default run: given the fixture recording, it produces the expected number of words within a tolerance, timestamps that are monotonically increasing and within the file's duration, a plausible frame rate, and at least the silences that are known to be present. It does not assert exact transcription text — model output is not a stable contract.

This is the only test requiring hardware, and it is the only place where a Whisper or driver regression can be caught.

### Premiere import verification

Not automatable, and deliberately treated as a manual acceptance step rather than pretended otherwise. It is also the **first** thing done, before any pipeline code exists: a hand-authored minimal XML — two clips of the fixture recording with a gap removed, one marker, one empty video track — is imported into Premiere and checked for correct timings and a visible marker.

That hand-verified file then becomes the template the renderer must reproduce, and the golden test locks it in. The reasoning is that the FCP7 schema is the highest-risk unknown in the project and the only one that cannot be discovered from code; every other component uses well-understood libraries.

## Out of Scope

- **Chapter markers.** Meaningless at the target video length. Revisit for longer content.
- **Any language model in the pipeline.** Editorial judgement about visual beats, chapter boundaries, or whether an off-script line is worth keeping is deferred.
- **Languages other than English.**
- **Multiple source files.** One recording per run. Pickups recorded in a separate session are not pooled.
- **Multiple camera angles or multicam sequences.**
- **Video content.** The source's black picture stream is ignored; the rough cut is audio plus an empty video track.
- **Filler-word removal inside a kept take.** Cutting "um" out of the middle of a good sentence joins two words the speaker meant to say in one breath, which is a much higher risk of an audible artefact than removing a whole region between lines. An abandoned restart inside a take is *not* covered by this: it is bounded by the speaker stopping and starting again, which is where a splice belongs, and it is removed — see "Stumbles inside a take" above.
- **Crossfades, level matching, noise reduction, or any audio processing.** Every splice is a hard butt cut. The tool makes edit decisions, not audio decisions.
- **Cross-filesystem path translation.** The XML carries a bare filename and the user relinks on import.
- **Round-tripping.** The tool does not read back an edited Premiere project or learn from which takes the user overrode.
- **A Premiere panel, plugin, or any in-application integration.**
- **Scripts with headings, stage directions, or non-spoken annotations.**
- **Unattended or batch operation.**

## Further Notes

### Known weakness of the first real run

The intended first recording is a 45-second script with few retakes, so take selection — the most intricate logic in the tool — will barely be exercised by real material. The synthetic fixtures compensate for correctness, but the *heuristics* (the disqualification thresholds especially) will be undertuned until a longer, messier recording exists. Expect to revisit the thresholds rather than treating v1's defaults as settled.

### Why the recording is committed

The fixture recording is committed to the repo rather than generated. A synthetic text-to-speech fixture was considered and rejected: it has no breaths, no room tone, and unnaturally clean word boundaries, so any threshold tuned against it would be wrong on real audio. A few minutes of black-screen MP4 is small enough that committing it is cheaper than the alternative.

### Environment constraints worth knowing

The target GPU has 4 GB of VRAM, which fits the chosen model at the chosen quantisation with headroom but would not fit it at half precision. System RAM is 6 GB, so CPU fallback is viable at the target recording length but would not be at feature length.

### Direction this leaves open

The single seam is what makes the rest cheap to change later. A model-driven planner, a different output format, chapter inference, or a longer-form take-scoring model can all be introduced as alternative implementations of `plan` or `render` without touching transcription or silence detection — and the existing fixtures keep working, because they describe recordings rather than algorithms.
