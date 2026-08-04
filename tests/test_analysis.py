import json
from pathlib import Path

import pytest

from conftest import FIXTURE_SOURCE

from roughcut.analysis import Analysis, Silence, SourceMedia, Word, load_analysis, save_analysis
from roughcut.errors import RoughCutError

ANALYSIS = Analysis(
    source=FIXTURE_SOURCE,
    words=[
        Word("Building", 0.5, 0.9, 0.98),
        Word("it.", 0.9, 1.4, 0.71),
    ],
    silences=[Silence(1.4, 3.0)],
    fingerprint="abc123",
)


def written(analysis: Analysis, tmp_path: Path) -> Path:
    path = tmp_path / "analysis.json"
    save_analysis(analysis, path)
    return path


def test_an_artifact_survives_a_round_trip(tmp_path: Path) -> None:
    assert load_analysis(written(ANALYSIS, tmp_path)) == ANALYSIS


def test_the_artifact_holds_source_properties_words_and_silences(tmp_path: Path) -> None:
    # This shape is the contract every later stage is tested against, so it is
    # asserted on directly rather than only through a round trip.
    document = json.loads(written(ANALYSIS, tmp_path).read_text(encoding="utf-8"))

    assert document["source"] == {
        "filename": "sequence.mp4",
        "duration_seconds": 86.25,
        "fps": 60.0,
        "ntsc": False,
        "width": 1920,
        "height": 1080,
        "audio_sample_rate": 48000,
        "audio_channels": 2,
        "audio_bit_depth": 16,
    }
    assert document["words"][0] == {
        "text": "Building",
        "start_seconds": 0.5,
        "end_seconds": 0.9,
        "confidence": 0.98,
    }
    assert document["silences"] == [{"start_seconds": 1.4, "end_seconds": 3.0}]


def test_an_artifact_is_written_as_readable_json(tmp_path: Path) -> None:
    text = written(ANALYSIS, tmp_path).read_text(encoding="utf-8")

    assert text.startswith("{\n  ")
    assert text.endswith("\n")


HAND_WRITTEN = {
    "source": {
        "filename": "take.mp4",
        "duration_seconds": 4.0,
        "fps": 30,
        "ntsc": False,
        "audio_sample_rate": 48000,
    },
    "words": [{"text": "hello", "start_seconds": 0.0, "end_seconds": 0.5, "confidence": 1.0}],
    "silences": [],
}


def hand_written(tmp_path: Path) -> Path:
    path = tmp_path / "hand.json"
    path.write_text(json.dumps(HAND_WRITTEN), encoding="utf-8")
    return path


def test_a_hand_written_artifact_needs_only_the_documented_parts(tmp_path: Path) -> None:
    # Every later ticket is tested by hand-writing one of these, so nothing the tool
    # adds for its own bookkeeping may become mandatory.
    analysis = load_analysis(hand_written(tmp_path))

    assert analysis.source.fps == 30.0
    assert analysis.words == [Word("hello", 0.0, 0.5, 1.0)]
    assert analysis.fingerprint is None


def test_the_properties_a_fixture_leaves_out_describe_an_ordinary_recording(
    tmp_path: Path,
) -> None:
    # A fixture describes times, not a picture it never had.
    source = load_analysis(hand_written(tmp_path)).source

    assert (source.width, source.height) == (1920, 1080)
    assert (source.audio_channels, source.audio_bit_depth) == (2, 16)


def test_loading_a_missing_artifact_names_the_path(tmp_path: Path) -> None:
    missing = tmp_path / "nope.json"

    with pytest.raises(RoughCutError, match=f"Analysis not found: {missing}"):
        load_analysis(missing)


def test_loading_unparseable_json_says_which_file(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(RoughCutError, match="broken.json is not valid JSON"):
        load_analysis(path)


def test_a_missing_field_is_reported_by_name(tmp_path: Path) -> None:
    path = tmp_path / "partial.json"
    path.write_text(json.dumps({"words": [], "silences": []}), encoding="utf-8")

    with pytest.raises(RoughCutError, match="'source'"):
        load_analysis(path)


def test_a_field_of_the_wrong_type_is_reported_by_name(tmp_path: Path) -> None:
    path = tmp_path / "wrong.json"
    document = json.loads(written(ANALYSIS, tmp_path).read_text(encoding="utf-8"))
    document["words"][1]["start_seconds"] = "soon"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(RoughCutError, match="words\\[1\\].start_seconds"):
        load_analysis(path)
