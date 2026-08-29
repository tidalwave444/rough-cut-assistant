"""The media stage — the only code in the project that opens the recording.

It probes the container, detects the silent regions and transcribes the speech, and
writes the three of them as one analysis artifact. Everything downstream reads that
artifact, so this module is also the only place that needs ffmpeg, a model or a GPU.

Its result is cached against a fingerprint of what produced it: the recording's bytes
and the settings that shaped the run. Iterating on cut heuristics therefore costs a
file read rather than a transcription.
"""

import ctypes
import hashlib
import importlib.util
import json
import re
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from roughcut.analysis import (
    DEFAULT_AUDIO_CHANNELS,
    DEFAULT_BIT_DEPTH,
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    Analysis,
    Silence,
    SourceMedia,
    Word,
    load_analysis,
    save_analysis,
)
from roughcut.errors import RoughCutError

# What to assume when the container declares nothing usable. A recording with no
# picture still needs a sequence format, and 30fps non-drop is the safe default.
FALLBACK_FPS = 30.0
DEFAULT_SAMPLE_RATE = 48000

# How near a rate must be to a nameable one to count as it.
NTSC_TOLERANCE = 0.001

FINGERPRINT_VERSION = 1
HASH_CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True)
class AnalysisSettings:
    """Everything that changes what the media stage produces.

    All of it feeds the fingerprint, so touching any of it re-analyzes rather than
    quietly serving a result the settings no longer describe.
    """

    model: str = "large-v3"
    device: str = "cuda"
    compute_type: str = "int8_float16"
    language: str = "en"
    silence_threshold_db: float = -35.0
    silence_min_seconds: float = 0.2
    """The shortest quiet worth writing down: what the cut may leave behind.

    Quiet the cut is willing to leave at a splice is quiet it has to be able to see —
    a stretch shorter than this is one the plan can neither find nor take off an edge,
    however plainly it is heard. So this follows the pause floor down rather than
    standing on its own, and `tests/test_analyze.py` holds the two together.
    """
    buried_speech_seconds: float = 1.0
    """The most speech one word may bury before the stretch is decoded again.

    A word's declared span less the quiet heard inside it is the speech it buries. A
    second of it is the bar `work/rough-cut-assistant/facts.md` measures the recordings
    at, and above it the token is not a long word but an attempt the transcriber
    collapsed into one — `part` buries 2.53 s of `Sequence 07` line 1.
    """


@dataclass(frozen=True)
class AnalysisRun:
    """An analysis, and whether it cost a transcription to get."""

    analysis: Analysis
    reused: bool


Analyzer = Callable[[Path, AnalysisSettings], Analysis]


def analyze_recording(recording: Path, settings: AnalysisSettings) -> Analysis:
    """Open the recording and learn everything the rest of the tool works from.

    Ordered cheapest-first: a recording with no audio stream, or an ffmpeg that isn't
    installed, fails in milliseconds rather than after a transcription.
    """
    if not recording.is_file():
        raise _missing(recording)
    source = probe_source(recording)
    silences = detect_silences(recording, source.duration_seconds, settings)
    words = transcribe(recording, settings)
    return Analysis(source=source, words=words, silences=silences)


def analysis_for(
    recording: Path,
    artifact: Path,
    settings: AnalysisSettings,
    *,
    analyze: Analyzer = analyze_recording,
) -> AnalysisRun:
    """Return the analysis of a recording, transcribing only if nothing usable exists.

    A cached artifact is reused only when it records the fingerprint of exactly this
    recording and these settings. Anything else — a hand-written fixture parked at the
    cache path, a truncated file, a changed threshold — is analyzed afresh.

    The fingerprint is stamped here rather than by the analyzer: what an analysis was
    derived from is the cache's business, not the transcriber's.
    """
    key = fingerprint(recording, settings)
    cached = _reusable(artifact, key)
    if cached is not None:
        return AnalysisRun(cached, reused=True)
    analysis = replace(analyze(recording, settings), fingerprint=key)
    save_analysis(analysis, artifact)
    return AnalysisRun(analysis, reused=False)


def fingerprint(recording: Path, settings: AnalysisSettings) -> str:
    """Identify the inputs of an analysis: the recording's bytes and the settings.

    The bytes rather than the modification time, so that copying a recording around
    or touching it doesn't force a re-transcription — and so that a recording replaced
    by a different one of the same size does.
    """
    digest = hashlib.sha256()
    digest.update(f"v{FINGERPRINT_VERSION}\n".encode())
    digest.update(json.dumps(asdict(settings), sort_keys=True).encode())
    try:
        with recording.open("rb") as stream:
            while chunk := stream.read(HASH_CHUNK_BYTES):
                digest.update(chunk)
    except FileNotFoundError:
        raise _missing(recording) from None
    except OSError as error:
        raise RoughCutError(f"Could not read the recording at {recording}: {error}") from None
    return digest.hexdigest()


def _missing(recording: Path) -> RoughCutError:
    return RoughCutError(f"Recording not found: {recording}")


def _reusable(artifact: Path, key: str) -> Analysis | None:
    if not artifact.is_file():
        return None
    try:
        cached = load_analysis(artifact)
    except RoughCutError:
        return None  # An unreadable cache is a cache miss, not a failure.
    return cached if cached.fingerprint == key else None


def probe_source(recording: Path) -> SourceMedia:
    """Read the container's own account of itself."""
    document = _run_json(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(recording),
        ],
        what=f"probe {recording}",
    )
    return parse_probe(document, filename=recording.name)


def parse_probe(document: Mapping[str, Any], *, filename: str) -> SourceMedia:
    """Turn ffprobe's report into the source properties the sequence is authored at.

    The frame rate comes from the file. The fallback exists for a container that
    declares nothing usable, and is never reached by a normal screen recording.
    """
    streams = document.get("streams") or []
    audio = _first_stream(streams, "audio")
    if audio is None:
        raise RoughCutError(
            f"{filename} has no audio stream, so there is nothing to cut. "
            "Check that the recording captured your microphone."
        )
    duration = _duration(document, filename)
    video = _first_stream(streams, "video")
    rate = _frame_rate(video)
    return SourceMedia(
        filename=filename,
        duration_seconds=duration,
        fps=rate.fps,
        ntsc=rate.ntsc,
        audio_sample_rate=int(audio.get("sample_rate") or DEFAULT_SAMPLE_RATE),
        width=int(video.get("width") or DEFAULT_WIDTH) if video else DEFAULT_WIDTH,
        height=int(video.get("height") or DEFAULT_HEIGHT) if video else DEFAULT_HEIGHT,
        audio_channels=int(audio.get("channels") or DEFAULT_AUDIO_CHANNELS),
        audio_bit_depth=_bit_depth(audio),
    )


def _first_stream(streams: Iterable[Any], kind: str) -> Mapping[str, Any] | None:
    for stream in streams:
        if isinstance(stream, dict) and stream.get("codec_type") == kind:
            return stream
    return None


def _duration(document: Mapping[str, Any], filename: str) -> float:
    declared = (document.get("format") or {}).get("duration")
    unreadable = RoughCutError(
        f"{filename} declares no duration, so it cannot be cut. "
        "The file may be truncated or still being written."
    )
    if not isinstance(declared, (str, int, float)):
        raise unreadable
    try:
        duration = float(declared)
    except ValueError:
        raise unreadable from None
    if duration <= 0:
        raise RoughCutError(f"{filename} declares a duration of {declared}, which is not usable.")
    return duration


@dataclass(frozen=True)
class _FrameRate:
    """A rate the sequence can be authored at: whole, or a broadcast rate flagged NTSC."""

    fps: float
    ntsc: bool


FALLBACK_RATE = _FrameRate(FALLBACK_FPS, ntsc=False)


def _frame_rate(video: Mapping[str, Any] | None) -> _FrameRate:
    """Read `r_frame_rate` — `60/1`, or `30000/1001` for a broadcast rate.

    Only two kinds of rate can be authored: a whole one, and a broadcast one, which
    FCP7 writes as the whole timebase plus the NTSC flag. Anything else — a variable
    frame rate container averaging out at 30.303, say — is nonsensical for a timeline
    and takes the fallback rather than being flagged NTSC, which it isn't.
    """
    if video is None:
        return FALLBACK_RATE
    numerator, _, denominator = str(video.get("r_frame_rate", "")).partition("/")
    try:
        rate = float(numerator) / float(denominator)
    except (ValueError, ZeroDivisionError):
        return FALLBACK_RATE
    if rate <= 0:
        return FALLBACK_RATE
    if abs(rate - round(rate)) <= NTSC_TOLERANCE:
        return _FrameRate(rate, ntsc=False)
    # A broadcast rate is a whole rate slowed by 1000/1001: 30 becomes 29.97.
    broadcast = round(rate * 1001 / 1000) * 1000 / 1001
    if abs(rate - broadcast) <= NTSC_TOLERANCE:
        return _FrameRate(rate, ntsc=True)
    return FALLBACK_RATE


def _bit_depth(audio: Mapping[str, Any]) -> int:
    for key in ("bits_per_raw_sample", "bits_per_sample"):
        try:
            depth = int(audio.get(key) or 0)
        except (TypeError, ValueError):
            continue
        if depth > 0:
            return depth
    return DEFAULT_BIT_DEPTH


def detect_silences(
    recording: Path, duration_seconds: float, settings: AnalysisSettings
) -> list[Silence]:
    """Find the regions the room was quiet through, as ffmpeg hears them."""
    reported = _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(recording),
            "-map",
            "0:a:0",
            "-af",
            f"silencedetect=noise={settings.silence_threshold_db}dB"
            f":d={settings.silence_min_seconds}",
            "-f",
            "null",
            "-",
        ],
        what=f"detect silence in {recording}",
    )
    # The detector reports on stderr, alongside ffmpeg's own progress commentary.
    return parse_silences(reported.stderr, duration_seconds)


SILENCE_START = re.compile(r"silence_start:\s*(-?[\d.]+)")
SILENCE_END = re.compile(r"silence_end:\s*(-?[\d.]+)")


def parse_silences(output: str, duration_seconds: float) -> list[Silence]:
    """Pair up the detector's running commentary into regions.

    A recording that ends while still quiet reports a start with no end; that region
    runs to the end of the file.
    """
    silences: list[Silence] = []
    start: float | None = None
    for line in output.splitlines():
        if (opening := SILENCE_START.search(line)) is not None:
            start = float(opening.group(1))
        elif (closing := SILENCE_END.search(line)) is not None and start is not None:
            silences.append(Silence(start, float(closing.group(1))))
            start = None
    if start is not None and start < duration_seconds:
        silences.append(Silence(start, duration_seconds))
    return silences


def stretched_over_speech(
    words: Sequence[Word], silences: Sequence[Silence], settings: AnalysisSettings
) -> list[Word]:
    """The words the transcriber ran across speech it wrote nothing down for.

    What separates one of these from an ordinary long word is not its length but how
    much of it was audible: a word stretched over *quiet* is the ordinary case decision
    0001 is about and stays as it is, while one burying more than the bar is several
    attempts collapsed into a single token — on `Sequence 07` line 1 the reading the
    operator wanted is inside such a word, and the cut removes it without ever knowing
    it was speech.

    The stretches named here are what a second decode pass is handed (ticket 14).
    """
    return [
        word for word in words if _buried_seconds(word, silences) > settings.buried_speech_seconds
    ]


def _buried_seconds(word: Word, silences: Sequence[Silence]) -> float:
    """How much of a word's declared span the detector heard sound in."""
    quiet = sum(
        max(
            0.0,
            min(word.end_seconds, silence.end_seconds)
            - max(word.start_seconds, silence.start_seconds),
        )
        for silence in silences
    )
    return word.end_seconds - word.start_seconds - quiet


def transcribe(recording: Path, settings: AnalysisSettings) -> list[Word]:
    """Transcribe the speech with a word-level timestamp on every word.

    Whisper's own voice-activity filtering is off: pause handling is this tool's job,
    and the filter would remove the very gaps the cut is decided from.
    """
    model = _load_model(settings)
    try:
        segments, _ = model.transcribe(
            str(recording),
            language=settings.language,
            word_timestamps=True,
            vad_filter=False,
            temperature=0.0,
        )
        return [
            Word(
                text=spoken.word.strip(),
                start_seconds=float(spoken.start),
                end_seconds=float(spoken.end),
                confidence=float(spoken.probability),
            )
            for segment in segments
            for spoken in (segment.words or ())
            if spoken.word.strip()
        ]
    except RuntimeError as error:
        raise describe_model_failure(error, settings) from None


def _load_model(settings: AnalysisSettings) -> Any:
    from faster_whisper import WhisperModel  # Imported late: it costs seconds to load.

    if settings.device != "cpu":
        _preload_cuda_libraries()
    try:
        return WhisperModel(
            settings.model, device=settings.device, compute_type=settings.compute_type
        )
    except Exception as error:
        raise describe_model_failure(error, settings) from None


def _preload_cuda_libraries() -> None:
    """Open the CUDA libraries that came from pip, so CTranslate2 can find them.

    CTranslate2 asks the dynamic loader for `libcublas.so.12` and `libcudnn.so.9` by
    name, and the loader does not search inside site-packages — so an environment that
    installed them with `--extra gpu` fails exactly as if there were no GPU. Loading
    them here, globally, puts them where the later `dlopen` will find them, which is
    what the alternative `LD_LIBRARY_PATH` export achieves outside the process.

    Silent when there is nothing to preload: a system CUDA install needs none of this.
    """
    spec = importlib.util.find_spec("nvidia")
    if spec is None:
        return
    pending = sorted(
        library
        for root in (spec.submodule_search_locations or ())
        for library in Path(root).glob("*/lib/*.so.*")
    )
    # Twice over: a library whose own dependency has not been loaded yet fails the
    # first pass and succeeds the second.
    for _ in range(2):
        for library in list(pending):
            try:
                ctypes.CDLL(str(library), mode=ctypes.RTLD_GLOBAL)
            except OSError:
                continue
            pending.remove(library)


GPU_SYMPTOMS = ("cuda", "cudnn", "cublas", "gpu", "libdevice")


def describe_model_failure(error: Exception, settings: AnalysisSettings) -> RoughCutError:
    """Turn a driver or download failure into something a person can act on."""
    if settings.device != "cpu" and any(
        symptom in str(error).lower() for symptom in GPU_SYMPTOMS
    ):
        return RoughCutError(
            f"The transcriber could not start on the GPU: {error}\n"
            "Check that the driver is visible (nvidia-smi), or re-run with "
            "--device cpu — slower, but it needs no GPU."
        )
    return RoughCutError(
        f"Could not load the Whisper model {settings.model!r} on {settings.device}: {error}\n"
        "The model is downloaded once on first use and cached; a first run needs network access."
    )


def _run(command: list[str], *, what: str) -> subprocess.CompletedProcess[str]:
    """Run a media tool, failing with its own words when it can't do the job."""
    try:
        finished = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        raise RoughCutError(
            f"{command[0]} was not found on PATH, so the tool cannot {what}. "
            f"Install ffmpeg and try again."
        ) from None
    if finished.returncode != 0:
        raise RoughCutError(f"{command[0]} could not {what}:\n{finished.stderr.strip()}")
    return finished


def _run_json(command: list[str], *, what: str) -> Mapping[str, Any]:
    try:
        document = json.loads(_run(command, what=what).stdout)
    except json.JSONDecodeError:
        raise RoughCutError(f"{command[0]} produced no readable report when asked to {what}.")
    if not isinstance(document, dict):
        raise RoughCutError(f"{command[0]} produced an unexpected report when asked to {what}.")
    return document
