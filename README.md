# Rough Cut Assistant

Turns a black-screen recording and its script into a sequence you can import into
Premiere Pro. See `.scratch/rough-cut-assistant/spec.md` for what it is for and why it
is built this way.

## Setup

```bash
uv sync --extra gpu
```

The `gpu` extra installs the CUDA runtime CTranslate2 needs (cuBLAS and cuDNN). Leave
it off to work on the cut logic alone — everything below the analysis seam runs on the
pure stages and needs no GPU. The Whisper model downloads once on first use.

`ffmpeg` and `ffprobe` must be on PATH.

## Running

```bash
# The whole tool: probe, transcribe, detect silence, plan, render.
uv run roughcut cut media/sequence.mp4 media/textt.txt -o out

# The media stage alone.
uv run roughcut analyze media/sequence.mp4 -o out

# Plan and render from an existing analysis — no media, instant.
uv run roughcut render out/sequence.analysis.json media/textt.txt -o out
```

`cut` writes three files into the output directory: the analysis artifact, the FCP7
XML, and the report. Re-running reuses the analysis unless the recording or a media
setting changed, so iterating on the cut costs no transcription.

The cut is one clip per script line, butt-spliced in the order the script writes them
— not the order they were recorded — with a marker at each line carrying its text, and
one marker per item where a line enumerates. The report says where each line was found
in the recording, names any line the recording does not contain, and lists the speech
no line accounts for.

Where a line was read more than once, **the last complete reading plays**: a person
re-records until satisfied and then stops, so recency selects and scoring only vetoes
— a take that stops short of the end of the line, holds too little of it, or stumbles
too often is passed over for the one before it. When no take survives, the least bad
plays and the line is flagged as worth recording again. Every reading passed over is
laid end to end in a second sequence, `RoughCut_Alternates`, each marked with its line,
its take number and the reason it lost, so overruling a choice is a drag rather than a
hunt. The report tabulates every take considered with its coverage and its outcome.

Anything you said that the script does not account for is **kept in place and marked**
unless something says it should go: it runs shorter than 2.5 s, or it is an abandoned
attempt at the line beside it — nearly every word of it that line's own — or it is on
the stop-phrase list. The asymmetry is deliberate: deleting a kept line in Premiere is
one keystroke, while recovering a deleted one means knowing it was ever there. What
survives plays between the same two lines it was said between, under an `Off-script`
marker quoting it, and the report lists every region with its duration and whether it
was kept or cut. `--off-script-keep-seconds`, `--off-script-restart-likeness` and
`--stop-phrases` move those bars; each of them only ever removes more, and
`--stop-phrases` with nothing after it turns that rule off.

A long pause *inside* a line is shortened rather than removed: a stretch of detected
quiet running over 0.7 s collapses to 0.3 s, so the read still breathes. A pause is
what the detector heard, not what the transcript shows — the transcriber stretches a
word over the pause that follows it rather than leaving a gap, so the quiet sits
underneath the words and a cut may land inside a word's declared span (ADR-0001). At
the head or the tail of a take that quiet is removed in full instead of collapsed: a
take begins where sound begins. `--pause-threshold-seconds`, `--pause-floor-seconds`
and `--pause-padding-seconds` tighten or loosen the whole cut in one run. They decide
the plan rather than the analysis, so `render` takes them too and trying a different
floor costs no transcription. The report says what each pause gave up.

Every splice keeps 0.15 s of the quiet either side of it, because a word goes on
sounding after the transcriber has stopped recognising it and a cut on the timestamp
lands on the last consonant. The pad is only ever taken from quiet the detector heard,
and two pieces either side of one gap split it rather than both claiming it, so nothing
is played twice. `--splice-padding-seconds` sets it — its own number rather than the
pause pad's, which does the opposite job of holding a cut inside the quiet.

Import the XML into Premiere and relink the clip once when prompted — the XML
references the recording by bare filename, so it arrives offline by design.

Transcription needs a GPU by default. `--device cpu` works everywhere and is slow.

## Testing

```bash
uv run pytest              # everything below the seam: fast, no hardware
uv run pytest -m slow      # the media stage against the real recording: needs a GPU
uv run pytest --update-golden   # rewrite the golden files after an intended change
uv run mypy
```

The fixture recording's analysis is committed at
`tests/fixtures/sequence.analysis.json`, so the golden test runs the real recording's
timings without the MP4 or a GPU. Both the XML and the report are golden: a change to
how lines are located reads as a line moving rather than as a frame count changing.
