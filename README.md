# Rough Cut Assistant

A black-screen recording and the script that was read from it go in; an FCP7 XML you can
import into Premiere Pro comes out. One clip per script line, in script order, with the
abandoned attempts taken out and every removal written down in a report beside it.

It works, and it is about 4,300 lines of Python with another 3,000 in tests. But the part
of this repository worth a reader's time is the other half: what is written down, why, and
what it cost to learn. The recording is the authority here, not the test suite, and nearly
every convention below exists because that distinction turned out to be expensive.

## Where to look

| | |
| --- | --- |
| [`settled/decisions/`](settled/decisions/) | Eleven decisions, each file **titled as the claim it settles** rather than its topic: "A cut is described from its clips, not from its report", not "Reporting". Each carries the alternatives rejected to reach it and the evidence that makes the choice checkable. Scanning the directory tells you what the project believes without opening anything. |
| [`settled/how-we-work.md`](settled/how-we-work.md) | The discipline. What shape a ticket has, why nothing may be inserted above `## Listen for`, why a ticket has a hard 60-line ceiling, and why `Status: done` is the one thing an agent may never write. |
| [`work/rough-cut-assistant/open/`](work/rough-cut-assistant/open/) | The live tickets in that shape — each one a thing that can be built and *heard* in a single pass. |
| [`running/xml-fix-loop/`](running/xml-fix-loop/) | The loop that runs an agent against the checks until they pass. Read it next to "Two checks are red" below, which is what the loop did when nobody was watching the checks it wasn't aiming at. |
| [`AGENTS.md`](AGENTS.md) | The test seam, and the two files in this repo that are never regenerated because regenerating them would make their tests circular. |

## What this project learned the hard way

Between 28 and 31 August four changes went in with every check green and every one of them
wrong on the recording: a span-finder nothing called, a rule that could never fire at the
bar it shipped with, a measure that lowered the coverage it was built to raise, and a line
playing seven seconds of the attempt it abandoned. All four were found by cutting the messy
recording and listening to it. None was caught by a hand-written fixture, and none could
have been — a fixture holds one thing at a time, and each of those faults was two rules
meeting.

Four things came out of that, and they live in the repository rather than in a
retrospective nobody would reread:

- **A cut is described from its clips, not from its report** — [decision 0011](settled/decisions/0011-a-cut-is-described-from-its-clips-not-from-its-report.md). The report called line 1 complete at 100% coverage while eleven clips beneath it played the whole abandoned attempt. A summary can describe a cut as healthier than it is; a clip list cannot.
- **A check that cannot disagree with the code is not evidence.** An expected value computed the way the code computes it, or a golden regenerated from the run it is meant to judge, agrees by construction and would have passed whatever the code did. The expected value has to come from somewhere the code cannot reach.
- **Two goldens, not one.** `sequence.mp4` is the small clean read. `Sequence 07.mp4` is the messy one — three lines never found, a line read thirteen times, an attempt abandoned mid-line — and it is the one that catches things. Its golden records the fault rather than hiding it, so a fix shows up as a diff.
- **`Status: done` is a person's word.** It means someone confirmed the behaviour with their own senses. It does not mean the tests pass, and an agent never writes it.

## Two checks are red

`uv run pytest` reports 189 passing and two failing:

    tests/test_plan.py::test_when_every_reading_falls_short_the_least_bad_plays_and_the_line_is_flagged
    tests/test_report.py::test_a_line_whose_every_take_was_disqualified_is_flagged_for_re_recording

Both were green until commit `6af3c50`, "xml fix loop, iteration 2 (was 1 red)". That
iteration replaced the token-count gap rule in `align.py` with `_one_reading`, which asks
which of the line's own words sit either side of an unheard run rather than counting the
run. It turned the check it was aiming at green, turned these two red, and said nothing
about either.

They are not written ahead of a fix, and nothing is waiting on them on purpose. Three
attempts at a line — six words, then seven, then six — should select the middle one because
it covers most of the line; the aligner now selects the first. The behaviour the checks
describe is what the tool is supposed to do, so they are left standing and red rather than
adjusted into agreeing with the code.

That is the point of leaving it written down. Adjusting a check until it agrees with the
code is exactly how those four changes shipped green and wrong. A red check whose cause is
known and named costs less than a green one that was talked into passing.

## What the tool does

One clip per script line in script order — where a line was read more than once, the last
complete reading plays. A marker at each line carrying its text, and one per item where a
line enumerates. Long pauses shortened. Abandoned attempts removed from inside a line.
Off-script speech kept and marked unless it is short or a failed restart. Every rejected
reading laid end to end in a second sequence, `RoughCut_Alternates`. The report says where
each line was found, which take won and why, and quotes everything removed.

Import the XML and relink the clip once when prompted — it references the recording by bare
filename, so it arrives offline by design.

Why it is built this way: [`work/rough-cut-assistant/what-it-does.md`](work/rough-cut-assistant/what-it-does.md).

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
uv run roughcut cut your-recording.mp4 your-script.txt -o out

# The media stage alone.
uv run roughcut analyze your-recording.mp4 -o out

# Plan and render from an existing analysis — no media, instant.
uv run roughcut render out/your-recording.analysis.json your-script.txt -o out
```

`cut` writes the analysis artifact, the FCP7 XML and the report into the output directory.
Re-running reuses the analysis unless the recording or a media setting changed, so
iterating on the cut costs no transcription.

The two recordings this project was built against are the author's own footage and are not
in the repository. They are not needed: each one's transcript and script are committed
under `tests/committed/`, so the whole cut can be planned, rendered and asserted from an
artifact. Getting a recording in from Windows and the XML back out again, with the mounts
fenced so an agent cannot reach past them:
[`running/getting-it-to-windows.md`](running/getting-it-to-windows.md).

```bash
uv run python running/dashboard.py        # out/dashboard.html — where the project stands
```

The dashboard reads what is already written down: the pipeline and where each artifact
lands, every run of the fix loop with its red count falling, the open tickets and what they
are waiting on, and the newest cut in `out/` described from its clip list beside what its
report claims. It scores nothing and decides nothing — a single number standing in for the
state of the cut is the proxy this project has already been burned by.

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
uv run mypy                # strict, over src and tests
```

`analyze` is the only stage that opens the recording; `plan` and `render` are pure
functions over its artifact. That seam is why 189 tests run in about a second without a
GPU, and why both real recordings can be asserted end to end from committed transcripts.
Both the XML and the report are golden, so a change to how lines are located reads as a
line moving rather than as a frame count changing.
