"""The analysis artifact — the project's single test seam.

`analyze` is the only stage that opens the recording; everything downstream reads this
artifact instead. That is what lets the cut logic be tested with a few hand-written
JSON documents rather than a GPU and a real MP4, so the shape below is a contract:
a hand-written fixture supplies `source`, `words` and `silences`, and within `source`
only the decision-bearing properties. Everything else has a default and nothing else
may become mandatory.

Times are seconds as floats throughout. Conversion to frames happens only in `render`.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from roughcut.errors import RoughCutError

# Enough decimals to hold a sample-accurate time, few enough that the file reads and
# diffs like a document rather than a float dump.
TIME_PRECISION = 6

# What a recording is assumed to be where it doesn't say otherwise: a fixture
# describing a cut cares about times, not about the picture it never had.
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
DEFAULT_AUDIO_CHANNELS = 2
# AAC and friends declare no sample depth; 16-bit is what the sequence is authored at.
DEFAULT_BIT_DEPTH = 16


@dataclass(frozen=True)
class SourceMedia:
    """The recording, as probed from the container.

    The first five properties decide the cut and the sequence's timebase; the rest
    only describe the format the sequence is authored at, and default.

    Referenced by bare filename: the tool and Premiere run in different filesystem
    namespaces, so the user relinks once on import.
    """

    filename: str
    duration_seconds: float
    fps: float
    ntsc: bool
    audio_sample_rate: int
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    audio_channels: int = DEFAULT_AUDIO_CHANNELS
    audio_bit_depth: int = DEFAULT_BIT_DEPTH


@dataclass(frozen=True)
class Word:
    """One transcribed word with the times it was spoken between."""

    text: str
    start_seconds: float
    end_seconds: float
    confidence: float


@dataclass(frozen=True)
class Silence:
    """A region the audio was quiet through, as heard by the detector.

    Cuts are placed against these rather than against the word timings: a gap in the
    transcript says roughly where nothing was said — and hardly ever appears, since a
    word is stretched over the pause that follows it — while a silence says where
    nothing was heard. Where the two disagree the detector wins (ADR-0001).
    """

    start_seconds: float
    end_seconds: float


@dataclass(frozen=True)
class Analysis:
    """Everything the media stage learned about one recording."""

    source: SourceMedia
    words: list[Word] = field(default_factory=list)
    silences: list[Silence] = field(default_factory=list)
    fingerprint: str | None = None
    """What this was derived from — the cache's record of its own inputs.

    Absent in hand-written fixtures, which describe a recording that never existed.
    """


def save_analysis(analysis: Analysis, path: Path) -> None:
    """Write an artifact as readable JSON, so a surprising cut can be read back."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_as_json(analysis), encoding="utf-8")


def load_analysis(path: Path) -> Analysis:
    """Read an artifact, naming the file and the field when it doesn't hold up."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise RoughCutError(f"Analysis not found: {path}") from None
    except OSError as error:
        raise RoughCutError(f"Could not read the analysis at {path}: {error}") from None

    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise RoughCutError(f"{path.name} is not valid JSON: {error}") from None

    try:
        return _analysis(_Fields.of(document, "the document"))
    except _MalformedField as error:
        raise RoughCutError(f"{path.name} is not a valid analysis artifact: {error}") from None


def _as_json(analysis: Analysis) -> str:
    document: dict[str, object] = {
        "source": {
            "filename": analysis.source.filename,
            "duration_seconds": _time(analysis.source.duration_seconds),
            "fps": analysis.source.fps,
            "ntsc": analysis.source.ntsc,
            "audio_sample_rate": analysis.source.audio_sample_rate,
            "width": analysis.source.width,
            "height": analysis.source.height,
            "audio_channels": analysis.source.audio_channels,
            "audio_bit_depth": analysis.source.audio_bit_depth,
        },
        "words": [
            {
                "text": word.text,
                "start_seconds": _time(word.start_seconds),
                "end_seconds": _time(word.end_seconds),
                "confidence": round(word.confidence, 4),
            }
            for word in analysis.words
        ],
        "silences": [
            {
                "start_seconds": _time(silence.start_seconds),
                "end_seconds": _time(silence.end_seconds),
            }
            for silence in analysis.silences
        ],
    }
    if analysis.fingerprint is not None:
        document["fingerprint"] = analysis.fingerprint
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def _time(seconds: float) -> float:
    return round(seconds, TIME_PRECISION)


class _MalformedField(Exception):
    """Internal: a field that is missing or the wrong type, named by where it sits."""


@dataclass(frozen=True)
class _Fields:
    """One object in the document, and the path that leads to it.

    Every read carries the path along, so a fault is reported as `words[1].start_seconds`
    rather than as a type error about a string.
    """

    values: Mapping[str, object]
    where: str

    @staticmethod
    def of(value: object, where: str) -> "_Fields":
        if not isinstance(value, dict):
            raise _MalformedField(f"{where} must be an object")
        return _Fields(value, where)

    def child(self, key: str) -> "_Fields":
        return _Fields.of(self.required(key), key)

    def children(self, key: str) -> list["_Fields"]:
        value = self.required(key)
        if not isinstance(value, list):
            raise _MalformedField(f"{key} must be a list")
        return [_Fields.of(entry, f"{key}[{index}]") for index, entry in enumerate(value)]

    def required(self, key: str) -> object:
        if key not in self.values:
            raise _MalformedField(f"{self.where} is missing {key!r}")
        return self.values[key]

    def number(self, key: str) -> float:
        value = self.required(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise _MalformedField(f"{self.where}.{key} must be a number")
        return float(value)

    def whole(self, key: str, *, default: int | None = None) -> int:
        if default is not None and key not in self.values:
            return default
        value = self.required(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise _MalformedField(f"{self.where}.{key} must be a whole number")
        return value

    def text(self, key: str) -> str:
        value = self.required(key)
        if not isinstance(value, str):
            raise _MalformedField(f"{self.where}.{key} must be text")
        return value

    def optional_text(self, key: str) -> str | None:
        return self.text(key) if key in self.values else None

    def flag(self, key: str) -> bool:
        value = self.required(key)
        if not isinstance(value, bool):
            raise _MalformedField(f"{self.where}.{key} must be true or false")
        return value


def _analysis(document: _Fields) -> Analysis:
    return Analysis(
        source=_source(document.child("source")),
        words=[_word(fields) for fields in document.children("words")],
        silences=[_silence(fields) for fields in document.children("silences")],
        fingerprint=document.optional_text("fingerprint"),
    )


def _source(fields: _Fields) -> SourceMedia:
    return SourceMedia(
        filename=fields.text("filename"),
        duration_seconds=fields.number("duration_seconds"),
        fps=fields.number("fps"),
        ntsc=fields.flag("ntsc"),
        audio_sample_rate=fields.whole("audio_sample_rate"),
        width=fields.whole("width", default=DEFAULT_WIDTH),
        height=fields.whole("height", default=DEFAULT_HEIGHT),
        audio_channels=fields.whole("audio_channels", default=DEFAULT_AUDIO_CHANNELS),
        audio_bit_depth=fields.whole("audio_bit_depth", default=DEFAULT_BIT_DEPTH),
    )


def _word(fields: _Fields) -> Word:
    return Word(
        text=fields.text("text"),
        start_seconds=fields.number("start_seconds"),
        end_seconds=fields.number("end_seconds"),
        confidence=fields.number("confidence"),
    )


def _silence(fields: _Fields) -> Silence:
    return Silence(
        start_seconds=fields.number("start_seconds"),
        end_seconds=fields.number("end_seconds"),
    )
