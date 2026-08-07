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
the cut is not using: retakes, and material that is off the script.

A long pause *inside* a line is shortened rather than removed: a gap over 0.7 s
collapses to 0.3 s, and only as far as a detected silence corroborates it, so the read
still breathes and the cut never lands inside a word. `--pause-threshold-seconds`,
`--pause-floor-seconds` and `--pause-padding-seconds` tighten or loosen the whole cut
in one run. They decide the plan rather than the analysis, so `render` takes them too
and trying a different floor costs no transcription. The report says what each pause
gave up.

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
