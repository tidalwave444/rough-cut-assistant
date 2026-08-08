"""Tests for the command line, all of them below the seam.

Nothing here opens a recording: `render` works from an analysis artifact, and the
failure paths are reached before the media stage would start.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from roughcut.cli import main

ANALYSIS = {
    "source": {
        "filename": "sequence.mp4",
        "duration_seconds": 86.25,
        "fps": 60,
        "ntsc": False,
        "width": 1920,
        "height": 1080,
        "audio_sample_rate": 48000,
        "audio_channels": 2,
    },
    "words": [
        {"text": "Building", "start_seconds": 0.5, "end_seconds": 0.9, "confidence": 0.98},
        {"text": "a", "start_seconds": 0.9, "end_seconds": 1.1, "confidence": 0.98},
        {"text": "real", "start_seconds": 1.1, "end_seconds": 1.5, "confidence": 0.98},
        {"text": "project.", "start_seconds": 1.5, "end_seconds": 2.0, "confidence": 0.9},
        {"text": "The", "start_seconds": 4.0, "end_seconds": 4.2, "confidence": 0.98},
        {"text": "end.", "start_seconds": 4.2, "end_seconds": 4.6, "confidence": 0.9},
    ],
    "silences": [{"start_seconds": 2.0, "end_seconds": 4.0}],
}

PAUSED = {
    "source": ANALYSIS["source"],
    # One line read with two seconds of nothing in the middle of it: 3.5s of recording.
    "words": [
        {"text": "Building", "start_seconds": 0.5, "end_seconds": 0.9, "confidence": 0.98},
        {"text": "a", "start_seconds": 0.9, "end_seconds": 1.1, "confidence": 0.98},
        {"text": "real", "start_seconds": 1.1, "end_seconds": 1.5, "confidence": 0.98},
        {"text": "project.", "start_seconds": 3.5, "end_seconds": 4.0, "confidence": 0.9},
    ],
    "silences": [{"start_seconds": 1.5, "end_seconds": 3.5}],
}


@pytest.fixture
def analysis(tmp_path: Path) -> Path:
    path = tmp_path / "sequence.analysis.json"
    path.write_text(json.dumps(ANALYSIS), encoding="utf-8")
    return path


@pytest.fixture
def paused(tmp_path: Path) -> Path:
    path = tmp_path / "paused.analysis.json"
    path.write_text(json.dumps(PAUSED), encoding="utf-8")
    return path


@pytest.fixture
def one_line(tmp_path: Path) -> Path:
    path = tmp_path / "one-line.txt"
    path.write_text("Building a real project.\n", encoding="utf-8")
    return path


@pytest.fixture
def script(tmp_path: Path) -> Path:
    path = tmp_path / "script.txt"
    path.write_text("Building a real project.\r\n\r\nThe end.\r\n", encoding="utf-8")
    return path


def test_rendering_an_analysis_writes_a_sequence_and_a_report(
    analysis: Path, script: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out"

    code = main(["render", str(analysis), str(script), "-o", str(out)])

    assert code == 0
    assert (out / "sequence.report.txt").read_text(encoding="utf-8").startswith("Rough cut")
    sequence = ET.parse(out / "sequence.xml").getroot().find("sequence")
    assert sequence is not None
    assert sequence.findtext("name") == "RoughCut"
    # Two lines, 1.5s and 0.6s of speech, spliced: 2.1s is 126 frames at 60fps.
    assert sequence.findtext("duration") == "126"
    assert [marker.findtext("name") for marker in sequence.findall("marker")] == [
        "Line 1",
        "Line 2",
    ]


def test_rendering_needs_no_media_present(analysis: Path, script: Path, tmp_path: Path) -> None:
    # The analysis names sequence.mp4, which exists nowhere near this test.
    assert main(["render", str(analysis), str(script), "-o", str(tmp_path / "out")]) == 0


def test_a_missing_script_is_reported_without_writing_anything(
    analysis: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "out"

    code = main(["render", str(analysis), str(tmp_path / "nope.txt"), "-o", str(out)])

    assert code == 2
    assert "Script not found" in capsys.readouterr().err
    assert not out.exists()


def test_a_missing_analysis_is_reported(
    script: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["render", str(tmp_path / "nope.json"), str(script), "-o", str(tmp_path / "out")])

    assert code == 2
    assert "Analysis not found" in capsys.readouterr().err


def test_a_malformed_analysis_is_reported_by_field(
    script: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "broken.analysis.json"
    document = dict(ANALYSIS)
    del document["source"]
    path.write_text(json.dumps(document), encoding="utf-8")

    code = main(["render", str(path), str(script), "-o", str(tmp_path / "out")])

    assert code == 2
    assert "'source'" in capsys.readouterr().err


def test_cutting_a_recording_that_is_not_there_is_reported(
    script: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        ["cut", str(tmp_path / "nope.mp4"), str(script), "-o", str(tmp_path / "out")]
    )

    assert code == 2
    assert "Recording not found" in capsys.readouterr().err


def test_cutting_reads_the_script_before_touching_the_recording(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Both inputs are wrong; the script is the one worth complaining about first,
    # because the alternative is discovering it after a transcription.
    code = main(
        [
            "cut",
            str(tmp_path / "nope.mp4"),
            str(tmp_path / "nope.txt"),
            "-o",
            str(tmp_path / "out"),
        ]
    )

    assert code == 2
    assert "Script not found" in capsys.readouterr().err


def rendered_frames(analysis: Path, script: Path, out: Path, *flags: str) -> str | None:
    """How long the rough cut runs, in frames, for one run of `render`."""
    assert main(["render", str(analysis), str(script), "-o", str(out), *flags]) == 0
    sequence = ET.parse(out / "sequence.xml").getroot().find("sequence")
    assert sequence is not None
    return sequence.findtext("duration")


def test_the_pause_floor_and_threshold_are_command_line_options(
    paused: Path, one_line: Path, tmp_path: Path
) -> None:
    # 3.5s of line with a 2s pause in it, at 60fps: 1.8s by default as the pause
    # collapses to the 0.3s floor, 2.5s with the floor raised to a second, and the
    # whole 3.5s once the threshold is lifted past the gap.
    default = rendered_frames(paused, one_line, tmp_path / "a")
    floored = rendered_frames(paused, one_line, tmp_path / "b", "--pause-floor-seconds", "1.0")
    kept = rendered_frames(paused, one_line, tmp_path / "c", "--pause-threshold-seconds", "3")

    assert (default, floored, kept) == ("108", "150", "210")


def test_the_pause_padding_is_a_command_line_option(
    paused: Path, one_line: Path, tmp_path: Path
) -> None:
    # A pad wider than half the silence leaves nothing of it safe to cut.
    padded = rendered_frames(paused, one_line, tmp_path / "a", "--pause-padding-seconds", "1.5")

    assert padded == "210"


def test_how_long_an_off_script_region_must_run_to_survive_is_an_option(
    analysis: Path, one_line: Path, tmp_path: Path
) -> None:
    # "The end." is in the recording but not in a one-line script: 0.6s of speech,
    # dropped as a fragment by default and kept in place once the bar is under it.
    dropped = rendered_frames(analysis, one_line, tmp_path / "a")
    kept = rendered_frames(
        analysis, one_line, tmp_path / "b", "--off-script-keep-seconds", "0.5"
    )

    assert (dropped, kept) == ("90", "126")


def test_the_stop_phrase_list_is_a_command_line_option(
    analysis: Path, one_line: Path, tmp_path: Path
) -> None:
    # Given phrases replace the built-in list rather than adding to it, so what the
    # run drops is exactly what was asked for.
    silenced = rendered_frames(
        analysis,
        one_line,
        tmp_path / "a",
        "--off-script-keep-seconds",
        "0.5",
        "--stop-phrases",
        "the end",
    )

    assert silenced == "90"


def test_the_report_is_printed_as_well_as_written(
    analysis: Path, script: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["render", str(analysis), str(script), "-o", str(tmp_path / "out")])

    assert "Source duration    00:01:26.250" in capsys.readouterr().out
