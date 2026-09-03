# Rough Cut Assistant

Turns a black-screen recording and its script into a sequence you can import into
Premiere Pro. What it is for and why it is built this way:
`work/rough-cut-assistant/what-it-does.md`. The decisions behind the cut: `settled/decisions/`.

## Setup

```bash
uv sync --extra gpu
```

The `gpu` extra installs the CUDA runtime CTranslate2 needs. Leave it off to work on the
cut logic alone — everything below the analysis seam needs no GPU. The Whisper model
downloads once on first use. `ffmpeg` and `ffprobe` must be on PATH.

## Running

```bash
# The whole tool: probe, transcribe, detect silence, plan, render.
uv run roughcut cut recordings/sequence.mp4 recordings/textt.txt -o out

# The media stage alone.
uv run roughcut analyze recordings/sequence.mp4 -o out

# Plan and render from an existing analysis — no media, instant.
uv run roughcut render out/sequence.analysis.json recordings/textt.txt -o out
```

`cut` writes the analysis artifact, the FCP7 XML and the report into the output
directory. Re-running reuses the analysis unless the recording or a media setting
changed, so iterating on the cut costs no transcription.

Recordings live in `recordings/` and results land in `out/`. Getting a recording in from
Windows and the XML back out again: `running/getting-it-to-windows.md`.

```bash
uv run python running/dashboard.py        # out/dashboard.html — where the project stands
```

The dashboard reads what is already written down: the pipeline and where each artifact
lands, every run of the fix loop with its red count falling, the open tickets and what
they are waiting on, and the newest cut in `out/` described from its clip list beside
what its report claims. It scores nothing and decides nothing.

What lands in the XML: one clip per script line in script order — where a line was
read more than once, the last complete reading plays — a marker at each line
carrying its text and one per item where a line enumerates, long pauses shortened,
abandoned attempts removed from inside a line, off-script speech kept and marked unless
it is short or a failed restart, and every rejected reading laid end to end in a second
sequence, `RoughCut_Alternates`. The report says where each line was found, which take
won and why, and quotes everything removed.

Import the XML and relink the clip once when prompted — it references the recording by
bare filename, so it arrives offline by design.

## Options

Everything below the seam decides the plan rather than the analysis, so `render` takes
these too and trying a value costs no transcription.

| | default | |
| --- | --- | --- |
| `--pause-threshold-seconds` | 0.7 | quiet longer than this is shortened |
| `--pause-floor-seconds` | 0.3 | what it is shortened to |
| `--pause-padding-seconds` | 0.05 | held off the words either side of a pause cut |
| `--splice-padding-seconds` | 0.15 | given back into the quiet at every splice |
| `--off-script-keep-seconds` | 2.5 | off-script speech shorter than this is dropped |
| `--off-script-restart-likeness` | 0.8 | how much of it must be the line beside it to count as a failed restart |
| `--stop-phrases` | short list | replaces the list; pass it empty to turn the rule off |

Analysis-stage settings feed the cache fingerprint, so changing one re-transcribes:
`--silence-threshold-db` (−35), `--silence-min-seconds` (0.5), `--device` (`cuda`;
`--device cpu` works everywhere and is slow).

## Testing

```bash
uv run pytest              # everything below the seam: fast, no hardware
uv run pytest -m slow      # the media stage against the real recording: needs a GPU
uv run pytest --update-golden   # rewrite the goldens after an intended change
uv run mypy
```

The fixture recording's analysis is committed at `tests/committed/sequence.analysis.json`,
so the golden test runs the real recording's timings without the MP4 or a GPU. Both the
XML and the report are golden: a change to how lines are located reads as a line moving
rather than as a frame count changing.
