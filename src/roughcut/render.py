"""Renders a plan as Final Cut Pro 7 XML, the format Premiere Pro imports natively.

The structure here is not free invention: it reproduces a file that was hand-authored
and confirmed to import correctly, and the deviations that were tried and failed are
recorded in `.scratch/rough-cut-assistant/spike-findings.md`. Two of them matter most:
a stereo source is one audio track and not two, and the `<file>` element has to declare
both the video and the audio stream even though the picture is never used.
"""

from dataclasses import dataclass
from urllib.parse import quote

from roughcut.analysis import SourceMedia
from roughcut.plan import Clip, Marker, Plan, Sequence
from roughcut.xmlwriter import Element, el, leaf, to_xml

MARKER_HAS_NO_DURATION = -1


def render_fcp7(plan: Plan) -> str:
    """Render a plan as an FCP7 XML document, one `<sequence>` per timeline."""
    ids = _Ids()
    return to_xml(
        el("xmeml", *(_sequence(s, ids) for s in plan.sequences), version=4),
        doctype="xmeml",
    )


def to_frames(seconds: float, fps: float) -> int:
    """Convert seconds to a frame count by rounding — the arithmetic proven in the spike.

    Counted at the source's real rate, not at the whole-number timebase: an hour of
    29.97fps material is 107892 frames, which is the whole reason drop-frame timecode
    exists. Quantisation error is at most half a frame, well below audibility.
    """
    return round(seconds * fps)


@dataclass(frozen=True)
class _SourceIds:
    file: str
    masterclip: str
    is_first_use: bool
    """Whether this clipitem must carry the full `<file>` declaration or just a reference."""


class _Ids:
    """Element ids, unique across the whole document.

    Clips drawn from the same recording share a `masterclipid` and a `file` id, so
    Premiere treats them as instances of one master clip rather than unrelated files.
    """

    def __init__(self) -> None:
        self._sources: dict[str, int] = {}
        self._clipitems = 0

    def claim_source(self, filename: str) -> _SourceIds:
        first_use = filename not in self._sources
        if first_use:
            self._sources[filename] = len(self._sources) + 1
        number = self._sources[filename]
        return _SourceIds(f"file-{number}", f"masterclip-{number}", first_use)

    def next_clipitem(self) -> str:
        self._clipitems += 1
        return f"clipitem-{self._clipitems}"


def _sequence(sequence: Sequence, ids: _Ids) -> Element:
    source = sequence.source
    return el(
        "sequence",
        leaf("name", sequence.name),
        leaf("duration", _timeline_duration(sequence)),
        _rate(source),
        _timecode(source),
        el(
            "media",
            el(
                "video",
                el("format", _video_characteristics(source)),
                el("track", *_track_state()),
            ),
            el(
                "audio",
                leaf("numOutputChannels", source.audio_channels),
                el("format", _audio_characteristics(source)),
                _outputs(source),
                el(
                    "track",
                    *_track_state(),
                    *(_clipitem(clip, source, ids) for clip in sequence.clips),
                ),
            ),
        ),
        *(_marker(marker, source.fps) for marker in sequence.markers),
        id=sequence.id,
    )


def _timeline_duration(sequence: Sequence) -> int:
    fps = sequence.source.fps
    return max((_frames(clip, fps).end for clip in sequence.clips), default=0)


@dataclass(frozen=True)
class _ClipFrames:
    source_in: int
    source_out: int
    start: int
    end: int


def _frames(clip: Clip, fps: float) -> _ClipFrames:
    """A clip's source range and its timeline placement, all in frames.

    The end is derived from the start rather than rounded on its own, so a clip always
    occupies exactly as many frames as it takes from the source and successive clips
    can't drift apart by a frame.
    """
    source_in = to_frames(clip.source_in_seconds, fps)
    source_out = to_frames(clip.source_out_seconds, fps)
    start = to_frames(clip.timeline_start_seconds, fps)
    return _ClipFrames(
        source_in=source_in,
        source_out=source_out,
        start=start,
        end=start + (source_out - source_in),
    )


def _clipitem(clip: Clip, source: SourceMedia, ids: _Ids) -> Element:
    frames = _frames(clip, source.fps)
    source_ids = ids.claim_source(source.filename)
    return el(
        "clipitem",
        leaf("masterclipid", source_ids.masterclip),
        leaf("name", source.filename),
        leaf("enabled", "TRUE"),
        leaf("duration", to_frames(source.duration_seconds, source.fps)),
        _rate(source),
        leaf("start", frames.start),
        leaf("end", frames.end),
        leaf("in", frames.source_in),
        leaf("out", frames.source_out),
        (
            _file(source, source_ids.file)
            if source_ids.is_first_use
            else el("file", id=source_ids.file)
        ),
        # One track, not two: Premiere sees a stereo source as a single stream, and
        # pointing a clipitem at trackindex 2 imports silent.
        el("sourcetrack", leaf("mediatype", "audio"), leaf("trackindex", 1)),
        id=ids.next_clipitem(),
    )


def _file(source: SourceMedia, file_id: str) -> Element:
    """The full media declaration, carried by the first clipitem that uses the source.

    `file://localhost/<name>` does not resolve on import — the clip arrives offline and
    the user relinks once. That is the accepted v1 flow: the tool and Premiere run in
    different filesystem namespaces, so there is no path that would work for both.
    """
    return el(
        "file",
        leaf("name", source.filename),
        leaf("pathurl", f"file://localhost/{quote(source.filename)}"),
        _rate(source),
        leaf("duration", to_frames(source.duration_seconds, source.fps)),
        _timecode(source),
        el(
            "media",
            el("video", _video_characteristics(source)),
            el(
                "audio",
                _audio_characteristics(source),
                leaf("channelcount", source.audio_channels),
                *(
                    el("audiochannel", leaf("sourcechannel", channel))
                    for channel in range(1, source.audio_channels + 1)
                ),
            ),
        ),
        id=file_id,
    )


def _marker(marker: Marker, fps: float) -> Element:
    return el(
        "marker",
        leaf("name", marker.name),
        leaf("comment", marker.comment),
        leaf("in", to_frames(marker.timeline_position_seconds, fps)),
        leaf("out", MARKER_HAS_NO_DURATION),
    )


def _rate(source: SourceMedia) -> Element:
    """The whole-number timebase plus the NTSC flag that qualifies it.

    FCP7 has no fractional timebase: 29.97 is written as timebase 30 with `ntsc` TRUE,
    which means the frames are played back at 30000/1001. Frame *counts* are therefore
    counted at the real rate — see `to_frames`.
    """
    return el(
        "rate",
        leaf("timebase", round(source.fps)),
        leaf("ntsc", _flag(source.ntsc)),
    )


def _timecode(source: SourceMedia) -> Element:
    """Every timeline starts at zero.

    Non-drop-frame regardless of NTSC: drop-frame is a way of *displaying* timecode so
    that it tracks wall clock, and it only matters once a start timecode other than
    00:00:00:00 is authored. Nothing here does.
    """
    return el(
        "timecode",
        _rate(source),
        leaf("string", "00:00:00:00"),
        leaf("frame", 0),
        leaf("displayformat", "NDF"),
    )


def _video_characteristics(source: SourceMedia) -> Element:
    return el(
        "samplecharacteristics",
        _rate(source),
        leaf("width", source.width),
        leaf("height", source.height),
        leaf("anamorphic", "FALSE"),
        leaf("pixelaspectratio", "square"),
        leaf("fielddominance", "none"),
    )


def _audio_characteristics(source: SourceMedia) -> Element:
    return el(
        "samplecharacteristics",
        leaf("depth", source.audio_bit_depth),
        leaf("samplerate", source.audio_sample_rate),
    )


def _outputs(source: SourceMedia) -> Element:
    return el(
        "outputs",
        el(
            "group",
            leaf("index", 1),
            leaf("numchannels", source.audio_channels),
            leaf("downmix", 0),
            *(
                el("channel", leaf("index", channel))
                for channel in range(1, source.audio_channels + 1)
            ),
        ),
    )


def _track_state() -> tuple[Element, Element]:
    return leaf("enabled", "TRUE"), leaf("locked", "FALSE")


def _flag(value: bool) -> str:
    return "TRUE" if value else "FALSE"
