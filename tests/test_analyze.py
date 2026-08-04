"""Tests for the media stage's readable parts.

Everything here is pure: the probe document and the silence detector's output are
text, and the cache is a file. What actually opens the recording — the transcriber —
is exercised only by the slow smoke test.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from roughcut.analysis import Analysis, Silence, SourceMedia, Word, save_analysis
from roughcut.analyze import (
    AnalysisSettings,
    analysis_for,
    describe_model_failure,
    fingerprint,
    parse_probe,
    parse_silences,
)
from roughcut.errors import RoughCutError

AUDIO_STREAM = {
    "codec_type": "audio",
    "codec_name": "aac",
    "sample_rate": "48000",
    "channels": 2,
    "bits_per_sample": 0,
}

VIDEO_STREAM = {
    "codec_type": "video",
    "codec_name": "h264",
    "width": 1920,
    "height": 1080,
    "r_frame_rate": "60/1",
}


def probe_document(*streams: dict[str, Any], duration: str = "86.250000") -> dict[str, Any]:
    return {"streams": list(streams), "format": {"duration": duration}}


def test_the_source_is_read_from_the_container_not_assumed() -> None:
    source = parse_probe(probe_document(AUDIO_STREAM, VIDEO_STREAM), filename="sequence.mp4")

    assert source == SourceMedia(
        filename="sequence.mp4",
        duration_seconds=86.25,
        fps=60.0,
        ntsc=False,
        width=1920,
        height=1080,
        audio_sample_rate=48000,
        audio_channels=2,
        audio_bit_depth=16,
    )


def test_a_fractional_frame_rate_is_kept_exact_and_flagged_ntsc() -> None:
    source = parse_probe(
        probe_document(AUDIO_STREAM, {**VIDEO_STREAM, "r_frame_rate": "30000/1001"}),
        filename="ntsc.mp4",
    )

    assert source.fps == pytest.approx(29.97002997)
    assert source.ntsc is True


def test_a_recording_with_no_usable_frame_rate_falls_back_to_30fps() -> None:
    source = parse_probe(
        probe_document(AUDIO_STREAM, {**VIDEO_STREAM, "r_frame_rate": "0/0"}),
        filename="audio-only.mp4",
    )

    assert source.fps == 30.0
    assert source.ntsc is False


def test_a_rate_that_is_neither_whole_nor_broadcast_falls_back_rather_than_claiming_ntsc() -> None:
    # A variable-rate container averaging out at 30.303 is not 29.97, and authoring a
    # sequence as if it were would conform every clip in it.
    source = parse_probe(
        probe_document(AUDIO_STREAM, {**VIDEO_STREAM, "r_frame_rate": "1000/33"}),
        filename="variable.mp4",
    )

    assert source.fps == 30.0
    assert source.ntsc is False


def test_the_broadcast_rates_are_recognised() -> None:
    rates = {
        "24000/1001": 23.976023976,
        "30000/1001": 29.97002997,
        "60000/1001": 59.94005994,
    }

    for declared, expected in rates.items():
        source = parse_probe(
            probe_document(AUDIO_STREAM, {**VIDEO_STREAM, "r_frame_rate": declared}),
            filename="broadcast.mp4",
        )
        assert source.fps == pytest.approx(expected)
        assert source.ntsc is True


def test_a_recording_with_no_picture_still_yields_a_sequence_format() -> None:
    source = parse_probe(probe_document(AUDIO_STREAM), filename="voice.m4a")

    assert (source.fps, source.width, source.height) == (30.0, 1920, 1080)


def test_a_declared_audio_bit_depth_is_used_when_the_codec_has_one() -> None:
    source = parse_probe(
        probe_document({**AUDIO_STREAM, "bits_per_sample": 24}, VIDEO_STREAM),
        filename="take.mov",
    )

    assert source.audio_bit_depth == 24


def test_a_recording_without_audio_fails_by_name() -> None:
    with pytest.raises(RoughCutError, match="silent.mp4 has no audio stream"):
        parse_probe(probe_document(VIDEO_STREAM), filename="silent.mp4")


def test_a_container_that_declares_no_duration_fails_clearly() -> None:
    document = probe_document(AUDIO_STREAM, VIDEO_STREAM)
    del document["format"]["duration"]

    with pytest.raises(RoughCutError, match="duration"):
        parse_probe(document, filename="odd.mp4")


SILENCE_OUTPUT = """\
[silencedetect @ 0x72b0f8002e40] silence_start: 3.838312
[silencedetect @ 0x72b0f8002e40] silence_end: 4.628729 | silence_duration: 0.790417
[silencedetect @ 0x72b0f8002e40] silence_start: 5.448479
[silencedetect @ 0x72b0f8002e40] silence_end: 6.147958 | silence_duration: 0.699479
"""


def test_each_reported_region_becomes_a_silence() -> None:
    assert parse_silences(SILENCE_OUTPUT, duration_seconds=86.25) == [
        Silence(3.838312, 4.628729),
        Silence(5.448479, 6.147958),
    ]


def test_a_recording_that_ends_in_silence_is_closed_at_its_end() -> None:
    output = SILENCE_OUTPUT + "[silencedetect @ 0x0] silence_start: 84.5\n"

    assert parse_silences(output, duration_seconds=86.25)[-1] == Silence(84.5, 86.25)


def test_a_recording_with_no_silence_yields_none() -> None:
    assert parse_silences("frame= 5175 fps=0.0 q=-0.0 Lsize=N/A\n", duration_seconds=86.25) == []


ANALYSIS = Analysis(
    source=SourceMedia(
        filename="take.mp4",
        duration_seconds=4.0,
        fps=30.0,
        ntsc=False,
        width=1920,
        height=1080,
        audio_sample_rate=48000,
        audio_channels=2,
    ),
    words=[Word("hello", 0.0, 0.5, 0.9)],
    silences=[Silence(0.5, 2.0)],
)


class CountingAnalyzer:
    """Stands in for the transcriber, so the cache can be tested without a GPU."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, recording: Path, settings: AnalysisSettings) -> Analysis:
        self.calls += 1
        return ANALYSIS


@pytest.fixture
def recording(tmp_path: Path) -> Path:
    path = tmp_path / "take.mp4"
    path.write_bytes(b"pretend this is an mp4")
    return path


def test_a_recording_analyzed_twice_is_transcribed_once(recording: Path, tmp_path: Path) -> None:
    artifact = tmp_path / "take.analysis.json"
    analyzer = CountingAnalyzer()
    settings = AnalysisSettings()

    first = analysis_for(recording, artifact, settings, analyze=analyzer)
    second = analysis_for(recording, artifact, settings, analyze=analyzer)

    assert analyzer.calls == 1
    assert (first.reused, second.reused) == (False, True)
    assert second.analysis.words == first.analysis.words


def test_the_first_analysis_is_written_where_it_was_asked_for(
    recording: Path, tmp_path: Path
) -> None:
    artifact = tmp_path / "nested" / "take.analysis.json"

    analysis_for(recording, artifact, AnalysisSettings(), analyze=CountingAnalyzer())

    assert artifact.exists()


def test_changing_the_recording_re_analyzes(recording: Path, tmp_path: Path) -> None:
    artifact = tmp_path / "take.analysis.json"
    analyzer = CountingAnalyzer()
    analysis_for(recording, artifact, AnalysisSettings(), analyze=analyzer)

    recording.write_bytes(b"a different recording of the same length")
    run = analysis_for(recording, artifact, AnalysisSettings(), analyze=analyzer)

    assert analyzer.calls == 2
    assert run.reused is False


def test_changing_a_setting_that_moves_the_result_re_analyzes(
    recording: Path, tmp_path: Path
) -> None:
    artifact = tmp_path / "take.analysis.json"
    analyzer = CountingAnalyzer()
    analysis_for(recording, artifact, AnalysisSettings(), analyze=analyzer)

    analysis_for(
        recording,
        artifact,
        AnalysisSettings(silence_threshold_db=-40.0),
        analyze=analyzer,
    )

    assert analyzer.calls == 2


def test_running_on_the_same_machine_twice_over_produces_the_same_fingerprint(
    recording: Path,
) -> None:
    assert fingerprint(recording, AnalysisSettings()) == fingerprint(recording, AnalysisSettings())


def test_an_artifact_that_records_no_inputs_is_not_treated_as_a_cache(
    recording: Path, tmp_path: Path
) -> None:
    # A hand-written fixture describes a recording that never existed; reusing one
    # because it happens to sit at the cache path would be silently wrong.
    artifact = tmp_path / "take.analysis.json"
    save_analysis(ANALYSIS, artifact)
    analyzer = CountingAnalyzer()

    run = analysis_for(recording, artifact, AnalysisSettings(), analyze=analyzer)

    assert (analyzer.calls, run.reused) == (1, False)


def test_an_unreadable_cache_is_replaced_rather_than_fatal(
    recording: Path, tmp_path: Path
) -> None:
    artifact = tmp_path / "take.analysis.json"
    artifact.write_text("{ this was truncated", encoding="utf-8")
    analyzer = CountingAnalyzer()

    run = analysis_for(recording, artifact, AnalysisSettings(), analyze=analyzer)

    assert (analyzer.calls, run.reused) == (1, False)
    assert json.loads(artifact.read_text(encoding="utf-8"))["source"]["filename"] == "take.mp4"


def test_a_missing_gpu_is_reported_as_a_setup_problem_with_a_way_out() -> None:
    error = describe_model_failure(
        RuntimeError("no CUDA-capable device is detected"), AnalysisSettings()
    )

    assert "--device cpu" in str(error)
    assert "no CUDA-capable device is detected" in str(error)


def test_a_model_that_cannot_be_loaded_names_the_model() -> None:
    error = describe_model_failure(
        OSError("We couldn't connect to huggingface.co"), AnalysisSettings(device="cpu")
    )

    assert "large-v3" in str(error)
