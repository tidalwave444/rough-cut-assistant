# Spike findings — FCP7 XML import into Premiere Pro

Verified by hand on 2026-08-04 against the real fixture recording. **The renderer must reproduce this structure.** A working reference file is committed at `tests/committed/minimal2.xml` — read it before writing the renderer.

## Verdict

Premiere Pro imports hand-authored FCP7 XML correctly. Frame arithmetic, cut placement, sequence markers, and the empty video track all survive import. The format is viable.

## Fixture media facts

| Property | Value |
|---|---|
| Container | MP4, 86.250000 s, 3.99 MB |
| Video | h264, 1920x1080, **60/1 fps**, fully black |
| Audio | AAC, **48000 Hz, 2 channels** |
| Total frames at 60 fps | **5175** (exactly, no remainder) |

The recording is genuinely black-screen as the spec assumes. Frame rate is **60**, not the 30 the spec named as a fallback — read it from the file, never assume.

## What was verified

A sequence removing one 1.25 s pause (source 55.312562 s – 56.563917 s):

- Clip 1: source in 0, out 3319 → timeline 0–3319
- Clip 2: source in 3394, out 5175 → timeline 3319–5100
- Sequence duration 5100 frames = **00:01:25:00** exactly, against a source of 00:01:26:15

Premiere reported exactly 00:01:25:00. Rounding seconds to frames with `round(seconds * fps)` is correct; the splice at frame 3319 (00:00:55:19) is seamless on playback with no audible gap or click.

## Structural requirements

**One audio track, not two.** The first attempt modelled the stereo source as two mono channels on separate tracks, with `sourcetrack/trackindex` of 1 and 2. The result imported and looked right but was **silent**. Premiere sees one stereo stream, so `trackindex` 2 points at a source track that does not exist. Use a single track whose clipitems all declare `trackindex` 1.

**The `<file>` element must describe the media truthfully.** Declaring only `<audio>` while the file also contains video appears to confuse stream mapping. Declare both `<video>` and `<audio>` under `<file><media>`, with `<channelcount>2</channelcount>` and one `<audiochannel><sourcechannel>` entry per channel.

**Use `masterclipid`.** Every clipitem drawn from the same source carries the same `masterclipid`, so Premiere treats them as instances of one master clip rather than unrelated files.

**Declare `<file>` fully once.** The first clipitem carries the full `<file id="...">` element; every later clipitem references it as `<file id="..."/>`. This works.

**The empty video track survives.** A `<track>` element containing only `<enabled>` and `<locked>` imports as an empty V1, ready to receive visuals.

**Sequence markers work.** `<marker>` elements with `<name>`, `<comment>`, `<in>` and `<out>-1</out>`, placed as direct children of `<sequence>`, appear on the timeline with readable comments.

## Media linking — settled

`<pathurl>file://localhost/sequence.mp4</pathurl>` does **not** resolve, even with the XML sitting in the same folder as the media. Premiere imports the sequence with an offline placeholder: the clip shows a question mark and the track renders red and silent.

Manual relink works and takes seconds: right-click the offline clip → **Link Media…** → **Locate** → select the file. After relinking, audio plays correctly.

So the accepted v1 flow is: put the XML next to the media, import, relink once.

**Worth revisiting during implementation:** embedding a real absolute Windows path in `<pathurl>` should make Premiere link automatically and remove the manual step. This was not tested during the spike because the Windows path was not known. If the tool gains a `--media-path` flag, this becomes trivial to try.

**Still open after ticket 04, and now testable.** The Windows path is known: the recording is copied to `C:\Users\<USER>\Downloads\`, so the line to try is

```xml
<pathurl>file://localhost/C:/Users/<USER>/Downloads/sequence.mp4</pathurl>
```

(forward slashes, drive as `C:/`; the fallback spelling to try if that fails is `file:///C:/Users/<USER>/Downloads/sequence.mp4`, without `localhost`).

A ready-to-import file is generated at `out/sequence-winpath.xml` by copying `out/sequence.xml` and substituting that one line — nothing else differs. The test is one import: if the clip arrives **online** — waveform visible, audio playing, no Link Media dialog — then the tool should gain a `--media-path` flag that writes the Windows path itself, and the manual relink disappears from every future run. If the clip still arrives **offline**, the bare filename is the ceiling; record that here and stop spending time on it.

This is a manual acceptance step, like the import verification itself. Nothing in the tool depends on the answer — v1 works either way, with one relink — so it does not block any ticket.

**Answered — the absolute Windows path links.** The import was run during the manual
acceptance of tickets 05–08. The clip arrives **online**: waveform visible, audio
playing, no Link Media dialog. The `file://localhost/C:/...` spelling above is the one
that worked, so the `file:///C:/...` fallback was never needed.

So the ceiling is not the bare filename, and the relink is not inherent to FCP7 XML —
it is a consequence of the tool writing a path Premiere cannot resolve. The consequence
for the tool is the `--media-path` flag this section anticipated: given the folder the
recording sits in on the Windows side, the renderer writes the absolute path itself and
the manual relink disappears from every future run. Without the flag the bare filename
stays the default, because the tool cannot know a Windows path from inside WSL.

Two things worth carrying into that work. The path has to be **percent-encoded** — the
tested file was `Sequence%2007.mp4`, and a raw space is the obvious way to get this
wrong. And the flag decides the *rendering*, not the analysis, so it belongs beside the
other render-time options and must not touch the analysis fingerprint.

## What the fixture does and does not exercise

`sequence.mp4`: 163 words, 29 silent regions, 8 script lines all located, 10 markers. A cold run takes 55 s and a cached one 0.15 s.

**It contains no retakes.** Ticket 01 left this unconfirmed and take selection answered it: the fixture's alternates sequence is empty, because nothing was ever rejected. So the disqualification thresholds are exercised by fixtures alone on this recording, and the only real material with multiple takes of a line is `Sequence 07.mp4`, where they are loop artefacts rather than genuine retakes.

Coverage on real material runs **89–100%**, so the 85% completeness bar has about four points of headroom. It is the threshold most likely to want moving first, and — like every other threshold here — it wants moving on a listen, not on this distribution. See decision 0003.

## Running the analysis stage

**The CUDA libraries installed by pip must be preloaded in-process.** CTranslate2 asks the dynamic loader for `libcublas.so.12` and `libcudnn.so.9` by name, and the loader does not look inside site-packages, so a GPU environment fails in exactly the way a machine with no GPU does. `_preload_cuda_libraries` does in-process what an `LD_LIBRARY_PATH` export would do outside it. Without it the tool reports a missing GPU on a machine that has one.

## Script file facts

`recordings/textt.txt` uses **CRLF** line endings and separates sentences with **blank lines**. The parser must strip carriage returns and ignore blank lines. Line numbering for markers and reports should count only non-blank lines.

Note the actual filenames differ from the spec's examples: the recording is `sequence.mp4` and the script is `textt.txt`. Filenames are CLI arguments; nothing should hardcode them.

## Silence profile of the fixture

At `-35dB` with a 0.5 s minimum, `ffmpeg silencedetect` finds **29 silent regions**, 8 of them longer than 1 s, the longest 1.91 s. There is substantial material to cut, so the fixture will genuinely exercise pause collapsing.

## The transcription loop in `Sequence 07.mp4` — diagnosed on the GPU, not yet fixed

The committed analysis of the second recording has Whisper looping: from 01:42 to the end it emits "You can find this skill…" twelve times over ~21 s of real speech (10.9 words per second, which is not a rate a person talks at), and the last three script lines are nowhere in it.

Alignment behaves correctly on a transcript that is wrong — those three lines are genuinely absent from *this transcript*, and the loop is correctly reported as a retake of line 6. The consequences are visible downstream: 6 of 9 lines located on that recording, and line 6's take is seventeen words at confidence 0.01 hallucinated over 2.65 s of detected silence, which ticket 10's tail trim now cuts to 0.36 s.

**The three lines are in the recording.** `condition_on_previous_text=False` alone recovers them: "After answering the questions, the skill turns everything into a detailed development plan. Now we can start building the website step by step without getting lost. In the next part we will begin the inflammation." The loop ate the last 21 s of the file, and with the loop gone the speech is simply there. Nothing about the recording was ever missing; the earlier reading of this section — that the lines were not spoken — was wrong.

`sequence.mp4` has the same defect in miniature: its one off-script region is 0.1 s holding 150 characters of "we're going to go ahead and get started with the first step" three times over.

**It also breaks take selection on that recording.** The loop produces 13 takes of line 6, all scoring 100% coverage because the transcript genuinely repeats the line thirteen times, so recency selects take 13 — a 2.68 s fragment — over take 1, the real 7 s reading. The report explains it and the alternates hold the good take, so overruling costs one drag. Selection is working as designed on a transcript that is wrong.

**The consequence for tuning: no threshold about off-script material has met real material yet.** Both off-script regions across both recordings are loops rather than speech. The 0.1 s one is removed by the duration rule — the right answer for the wrong reason — and the 15.5 s one is line 3 attempted over and over: 61 of its 63 tokens are that line's own words. It was kept until ticket 12, not because it sits close to no adjacent line but because containment was taken across the whole region in one pass, which scored it 0.206 against a bar of 0.8. Measured attempt by attempt it scores 1.000 and goes. So both removal rules that matter are still carried entirely by fixtures, and their thresholds should be expected to move once a recording exists with real restarts in it. Fix the loop before tuning anything against real material.

## What each decoding setting is worth

Measured on `Sequence 07.mp4`, large-v3 / cuda / int8_float16, each row adding to the one above it. "Buried" is audible time inside a word's own declared span — its duration less the quiet the detector hears inside it — summed over words holding more than a second of it. It is the measure of speech the transcriber collapsed rather than wrote down.

| what `transcribe()` was given | words | longest 4-gram repeat | buried | wall clock |
| --- | --- | --- | --- | --- |
| as shipped, `temperature=0.0` | 393 | ×13 | 11.8 s | 60 s |
| `temperature=[0.0 … 1.0]` | 268 | ×6 | 10.8 s | 61 s |
| `condition_on_previous_text=False` | 162 | ×2 | 12.4 s | 19 s |
| `chunk_length=10` | 177 | ×2 | 6.2 s | 35 s |
| the script as `initial_prompt` | 183 | ×2 | 4.9 s | 36 s |

`temperature=0.0` is a single value where `faster-whisper` defaults to a ladder, and passing one disables the fallback loop entirely (`transcribe.py:1432`). `compression_ratio_threshold` and `log_prob_threshold` still fire; there is no higher temperature to retry at, so the bad decode is kept. Every safety net in the library is wired to a re-decode that cannot happen. Separately, at `transcribe.py:1226` a window whose `no_speech_prob` exceeds 0.6 with `avg_logprob` under −1.0 is skipped by `seek += segment_size`, silently — a whole 30 s discarded with nothing recorded to say so.

The artifact keeps none of the evidence. `Word` holds text, start, end and confidence; the segment's `avg_logprob`, `compression_ratio`, `no_speech_prob` and the temperature it settled at are all dropped at `analyze.py:333-340`, so a collapsed segment cannot be told from a real one after the fact. It has to be inferred from word span against detected silence, which is how the table above was built. `confidence` is stored and read by nothing.

## The speech that reaches no word

`Sequence 07` line 1: the word `part` is declared at 3.48–8.64 — 5.16 s for one syllable at confidence 0.22 — and the detector hears 2.63 s of that as quiet, leaving **2.53 s of audible speech with no word against it**.

Cut that stretch out and hand it to the same model on its own, with `language="en"` and nothing else — no prompt, no vocabulary:

| what was transcribed | result |
| --- | --- |
| the whole file | `part` |
| 3.3–9.2 s alone | `oh no white coating part` |
| 3.3–9.2 s alone, script line as prompt | `Oh, no, vibe coding, part 2.` |

The speech was always recoverable. Whisper cannot see it inside a 30 s window that is mostly silence, and the word-timestamp DTW then stretches the neighbouring word over the gap. **This span survives every decoding setting**, `chunk_length=10` included, where it still reads 3.52–8.34 with 2.50 s buried. Shortening the window halves the buried total across the recording without touching this one.

The operator hears `with vibe co… tuu… oh no… vibe coding` here. The cut keeps the failed attempt and loses the good one, because the stumble rule reads `part` said twice and takes 3.480–10.500 out — and the retake is inside that span, in the part of it no word was ever written for.

## Levers that were tried and did nothing

Each measured against the fixed decoding settings, so that a later run does not pay for them again.

- **`vad_filter=True`** — line 1 vanished from the transcript entirely. Note that `False` is already the library default in `faster-whisper` 1.2.1, so passing it documents intent rather than changing behaviour.
- **`compute_type="float16"`** — the same transcript to the word on both recordings, at 4.5–5× the wall clock: `sequence.mp4` 24 s → 107 s, `Sequence 07` 34 s → 173 s. The GTX 1650 Ti has 4 GB and large-v3 in fp16 spills. Quantisation was costing nothing.
- **`loudnorm=I=-16:TP=-1.5:LRA=11`** — `Sequence 07` gains 10.7 dB (mean −31.3 → −20.6). It clears three of the four stretched words but not `part`, which stays 3.48–8.32 with 2.53 s buried at confidence 0.36 rather than 0.24. On `sequence.mp4` buried time gets worse, 7.4 → 8.4 s, and the text is flat to slightly worse. If it is ever adopted anyway, silence detection must keep running on the original: normalisation lifts the noise floor and the −35 dB threshold would no longer mean what it means today.
- **`highpass=f=80` before `loudnorm`** — identical to the raw file, benefit cancelled.
- **a generic vocabulary** as `hotwords` or as `initial_prompt` (`"vibe coding, Telegram, tech stack, skill"`) — does not recover `vibe coding`. Only the script line itself did.

So recognition accuracy is not the bottleneck. The model decodes this audio about as well as it can; what it lacks is the phrase, and no amount of precision or level supplies one.

## `vibe` against `wipe` is a matching problem

Both recordings hear `vibe coding` as `wipe coating` or `wipe coding`, and `Sequence 07` hears `real` as `rail`. Alignment compares exactly-equal tokens — `difflib.SequenceMatcher` over the normalised streams from `tokens.py` — so a one-character difference is a total miss. `Sequence 07` line 1 therefore holds 6 of its 9 words, reports 67% coverage and is flagged `least bad — incomplete`, for a take that was read correctly start to finish.

Decision 0002 already says a mishearing stays, and it is right: the audio in the cut is correct today. What the wrong transcript costs is the coverage figure, the false flag, and — on this line — which attempt the stumble rule removes. That is an alignment problem wearing a transcription problem's clothes. See decision 0010.

## Where the quiet actually sits

The transcriber does not leave holes between words — it stretches a word over the pause that follows it. **97% of consecutive word pairs on `sequence.mp4` and 94% on `Sequence 07.mp4` butt straight up against each other.** So the silence inside a take is not between the words but underneath them:

| silence lying inside a selected take | `sequence.mp4` | `Sequence 07.mp4` |
| --- | --- | --- |
| total | 16.71 s (24 regions) | 31.67 s (37 regions) |
| under a word's own timestamps | 15.52 s (93%) | 31.16 s (98%) |
| in a real transcript gap | 1.19 s | 0.51 s |

`Sequence 07` line 3 is the clearest case: the word `claim` is declared at 27.28–29.70 — 2.42 s for one syllable, confidence 0.34 — and the detector hears 2.14 s of that as silence. Line 1's `part` is declared at 3.48–8.64, 5.16 s, with three separate silence regions inside it.

**A consequence worth knowing before predicting how a change will look: consecutive takes are usually contiguous in the source.** 157 of `sequence.mp4`'s 162 consecutive word pairs butt straight together, so line 1's clip ends at 3.640 and line 2's begins at 3.640 — there is no gap between them at all. That recording has **three real splices**, not sixteen: line 5's out point, line 6's in point and line 8's out point. Any change that acts on splices will move far less of the golden than a per-line count suggests.

This is the measurement decision 0001 rests on. Re-derive it before changing how pauses are found.

## Unmatched runs inside takes

Every unmatched run inside every take of both recordings — thirteen of them, with what stands opposite each one in the script:

| what was heard | opposite it in the script | |
| --- | --- | --- |
| `rail` | `real` | misheard |
| `we are` | `were` | misheard |
| `project` | `product` | misheard |
| `the wipe` | `vibe` | misheard |
| `the` | `a` | misheard |
| `follow` | `fully` | misheard |
| `results` | `resources` | misheard |
| `the` | `that` | misheard |
| `a wipe coating part one no no` | `vibe coding` | misheard **and** stumble |
| `claim plan no and install` | `installed` | stumble **and** spoken fine |
| `wipe` | — | stumble |
| `along the` | — | stumble |
| `skills` | — | stumble |

Eight are purely a mishearing, three have nothing opposite them, and two are both at once. The right-hand column is the whole corpus the stumble rules were derived from and the thing to re-derive them against if those rules are ever changed — see decision 0002.
