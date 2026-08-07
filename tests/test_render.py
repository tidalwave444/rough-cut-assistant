import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

from conftest import FIXTURE_SOURCE

from roughcut.analysis import SourceMedia
from roughcut.plan import Clip, Marker, Plan, Sequence
from roughcut.render import render_fcp7

# Hand-authored and confirmed to import into Premiere. It is the contract, so it is
# never regenerated from the renderer — that would make the golden test circular.
REFERENCE_XML = Path(__file__).resolve().parents[1] / "media" / "minimal2.xml"


def spike_plan() -> Plan:
    """The cut that was hand-authored and verified in Premiere: one 1.25s pause removed."""
    return Plan(
        sequences=[
            Sequence(
                id="spike-roughcut-2",
                name="SPIKE_RoughCut_v2",
                source=FIXTURE_SOURCE,
                clips=[
                    Clip(
                        source_in_seconds=0.0,
                        source_out_seconds=55.312562,
                        timeline_start_seconds=0.0,
                    ),
                    Clip(
                        source_in_seconds=56.563917,
                        source_out_seconds=86.250000,
                        timeline_start_seconds=55.312562,
                    ),
                ],
                markers=[
                    Marker(
                        name="L1 START",
                        comment="Building a real project with vibe coding - Part 2.",
                        timeline_position_seconds=0.0,
                    ),
                    Marker(
                        name="CUT 01",
                        comment=(
                            "Pause removed here: 1.25s cut from source 55.31s-56.56s"
                        ),
                        timeline_position_seconds=55.312562,
                    ),
                ],
            )
        ]
    )


def test_renders_the_verified_reference_file_exactly() -> None:
    assert render_fcp7(spike_plan()) == REFERENCE_XML.read_text(encoding="utf-8")


def one_sequence(
    source: SourceMedia,
    clips: list[Clip],
    markers: list[Marker] | None = None,
) -> Plan:
    return Plan(
        sequences=[
            Sequence(
                id="seq-1",
                name="RoughCut",
                source=source,
                clips=clips,
                markers=markers or [],
            )
        ]
    )


def rendered(plan: Plan) -> ET.Element:
    return ET.fromstring(render_fcp7(plan))


def test_a_plan_with_no_markers_renders_a_sequence_carrying_none() -> None:
    plan = one_sequence(
        FIXTURE_SOURCE,
        clips=[Clip(0.0, 86.250000, 0.0)],
        markers=[],
    )

    sequence = rendered(plan).find("sequence")
    assert sequence is not None
    assert sequence.findall("marker") == []
    assert sequence.findtext("duration") == "5175"


def test_a_single_clip_occupies_the_whole_timeline() -> None:
    source = replace(FIXTURE_SOURCE, filename="take.mp4", duration_seconds=10.0, fps=30)
    plan = one_sequence(source, clips=[Clip(2.0, 5.0, 0.0)])

    root = rendered(plan)
    clipitems = root.findall("./sequence/media/audio/track/clipitem")
    assert len(clipitems) == 1
    assert _timings(clipitems[0]) == {"start": 0, "end": 90, "in": 60, "out": 150}
    assert root.findtext("./sequence/duration") == "90"


def test_media_properties_are_taken_from_the_plan() -> None:
    # Every property differs from the fixture, so anything hardcoded shows up here.
    source = replace(
        FIXTURE_SOURCE,
        filename="mono take.mp4",
        duration_seconds=4.0,
        fps=24,
        width=1280,
        height=720,
        audio_sample_rate=44100,
        audio_channels=1,
        audio_bit_depth=24,
    )

    root = rendered(one_sequence(source, clips=[Clip(0.0, 4.0, 0.0)]))

    assert {rate.findtext("timebase") for rate in root.iter("rate")} == {"24"}
    assert {rate.findtext("ntsc") for rate in root.iter("rate")} == {"FALSE"}
    assert {e.text for e in root.iter("width")} == {"1280"}
    assert {e.text for e in root.iter("height")} == {"720"}
    assert {e.text for e in root.iter("samplerate")} == {"44100"}
    assert {e.text for e in root.iter("depth")} == {"24"}
    assert root.findtext("./sequence/media/audio/numOutputChannels") == "1"
    assert len(root.findall("./sequence/media/audio/outputs/group/channel")) == 1
    assert len(list(root.iter("audiochannel"))) == 1
    assert root.findtext(".//pathurl") == "file://localhost/mono%20take.mp4"


def test_an_ntsc_source_declares_the_whole_timebase_and_the_ntsc_flag() -> None:
    source = replace(
        FIXTURE_SOURCE, filename="ntsc.mp4", duration_seconds=100.0, fps=29.97, ntsc=True
    )

    root = rendered(one_sequence(source, clips=[Clip(0.0, 100.0, 0.0)]))

    assert {rate.findtext("timebase") for rate in root.iter("rate")} == {"30"}
    assert {rate.findtext("ntsc") for rate in root.iter("rate")} == {"TRUE"}
    # 100s holds 2997 frames at the real rate, not the 3000 the timebase alone implies.
    assert root.findtext("./sequence/duration") == "2997"


def test_seconds_are_converted_to_frames_by_rounding() -> None:
    source = replace(FIXTURE_SOURCE, filename="take.mp4", duration_seconds=3.0, fps=30)
    # 1.01s is 30.3 frames and rounds down; the 1.98s the clip runs for is 59.4 and
    # rounds down too; 1.99s of timeline is 59.7 and rounds up.
    plan = one_sequence(
        source,
        clips=[
            Clip(
                source_in_seconds=1.01,
                source_out_seconds=2.99,
                timeline_start_seconds=0.0,
            )
        ],
        markers=[Marker(name="M", comment="", timeline_position_seconds=1.99)],
    )

    root = rendered(plan)
    clipitem = root.findall("./sequence/media/audio/track/clipitem")[0]
    assert _timings(clipitem) == {"start": 0, "end": 59, "in": 30, "out": 89}
    assert root.findtext("./sequence/marker/in") == "60"


def test_butt_spliced_clips_meet_on_a_frame_rather_than_overlapping() -> None:
    # Source times that land between frames, laid end to end — what a shortened pause
    # produces. Two clipitems overlapping on one audio track is a sequence Premiere
    # cannot lay out, and a frame of hole between them is a click.
    plan = one_sequence(
        FIXTURE_SOURCE,
        clips=[
            Clip(3.64, 6.546625, 3.64),
            Clip(7.635021, 12.28, 6.546625),
            Clip(12.28, 26.12, 11.191604),
        ],
    )

    timings = [
        _timings(item) for item in rendered(plan).findall("./sequence/media/audio/track/clipitem")
    ]

    assert [frames["start"] for frames in timings[1:]] == [
        frames["end"] for frames in timings[:-1]
    ]


def test_each_sequence_in_a_plan_is_rendered_with_its_own_clip_ids() -> None:
    plan = Plan(
        sequences=[
            Sequence("seq-1", "RoughCut", FIXTURE_SOURCE, clips=[Clip(0.0, 10.0, 0.0)]),
            Sequence(
                "seq-2", "RoughCut_Alternates", FIXTURE_SOURCE, clips=[Clip(10.0, 20.0, 0.0)]
            ),
        ]
    )

    root = rendered(plan)
    # One file, both sequences, each named for the project panel.
    assert [s.findtext("name") for s in root.findall("sequence")] == [
        "RoughCut",
        "RoughCut_Alternates",
    ]
    assert [s.get("id") for s in root.findall("sequence")] == ["seq-1", "seq-2"]
    clip_ids = [c.get("id") for c in root.iter("clipitem")]
    assert clip_ids == ["clipitem-1", "clipitem-2"]
    # One recording, so both sequences point at one master clip and one file.
    assert {c.text for c in root.iter("masterclipid")} == {"masterclip-1"}
    assert {f.get("id") for f in root.iter("file")} == {"file-1"}


def _timings(clipitem: ET.Element) -> dict[str, int]:
    return {
        field: int(clipitem.findtext(field) or "")
        for field in ("start", "end", "in", "out")
    }
