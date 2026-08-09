"""The command line: three ways in, one path through.

`cut` is the whole tool — a recording and a script go in, a sequence Premiere can
import comes out. The other two exist because the analysis artifact sits between the
media stage and everything else: `analyze` produces one, and `render` works from one
that already exists, so iterating on the cut costs no transcription.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from roughcut.analysis import Analysis, load_analysis
from roughcut.analyze import AnalysisRun, AnalysisSettings, analysis_for
from roughcut.errors import RoughCutError
from roughcut.offscript import OffScriptSettings
from roughcut.pauses import PauseSettings
from roughcut.plan import build_plan
from roughcut.render import render_fcp7
from roughcut.report import render_report
from roughcut.script import ScriptLine, read_script
from roughcut.splice import SpliceSettings

DEFAULT_OUT_DIR = Path("out")
ANALYSIS_SUFFIX = ".analysis.json"
REPORT_SUFFIX = ".report.txt"


def main(argv: Sequence[str] | None = None) -> int:
    """Run one command, reporting anything the user can fix as a plain message."""
    args = _parser().parse_args(argv)
    try:
        run: int = args.handler(args)
        return run
    except RoughCutError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


def _analyze(args: argparse.Namespace) -> int:
    recording = Path(args.recording)
    _report_analysis(_analysis_run(args, recording), _analysis_path(args, recording))
    return 0


def _cut(args: argparse.Namespace) -> int:
    recording = Path(args.recording)
    # The script is read first: a typo in its path should not cost a transcription.
    script = read_script(Path(args.script))
    run = _analysis_run(args, recording)
    _report_analysis(run, _analysis_path(args, recording))
    _write_cut(
        run.analysis,
        script,
        Path(args.out_dir),
        _pauses(args),
        _off_script(args),
        _splice(args),
    )
    return 0


def _render(args: argparse.Namespace) -> int:
    """Plan and render from an existing artifact, without opening the recording."""
    script = read_script(Path(args.script))
    _write_cut(
        load_analysis(Path(args.analysis)),
        script,
        Path(args.out_dir),
        _pauses(args),
        _off_script(args),
        _splice(args),
    )
    return 0


def _analysis_run(args: argparse.Namespace, recording: Path) -> AnalysisRun:
    return analysis_for(recording, _analysis_path(args, recording), _settings(args))


def _analysis_path(args: argparse.Namespace, recording: Path) -> Path:
    if args.analysis_path is not None:
        return Path(args.analysis_path)
    return Path(args.out_dir) / f"{recording.stem}{ANALYSIS_SUFFIX}"


def _settings(args: argparse.Namespace) -> AnalysisSettings:
    """The media settings a run may vary.

    The model and its quantisation are fixed by the spec and the language is English,
    so none of the three is a flag: they are settings because they belong in the
    fingerprint, not because a run is meant to choose them.
    """
    return AnalysisSettings(
        device=args.device,
        silence_threshold_db=args.silence_threshold_db,
        silence_min_seconds=args.silence_min_seconds,
    )


def _pauses(args: argparse.Namespace) -> PauseSettings:
    """How tight this run's cut is, as asked for on the command line."""
    return PauseSettings(
        threshold_seconds=args.pause_threshold_seconds,
        floor_seconds=args.pause_floor_seconds,
        padding_seconds=args.pause_padding_seconds,
    )


def _splice(args: argparse.Namespace) -> SpliceSettings:
    """How much of the quiet either side of a splice this run keeps."""
    return SpliceSettings(padding_seconds=args.splice_padding_seconds)


def _off_script(args: argparse.Namespace) -> OffScriptSettings:
    """What this run removes without asking, as asked for on the command line.

    Phrases given on the command line replace the built-in list rather than adding to
    it, so what a run drops is exactly what was asked for — and `--stop-phrases` with
    nothing after it turns the rule off.
    """
    defaults = OffScriptSettings()
    return OffScriptSettings(
        keep_seconds=args.off_script_keep_seconds,
        restart_likeness=args.off_script_restart_likeness,
        stop_phrases=(
            defaults.stop_phrases if args.stop_phrases is None else tuple(args.stop_phrases)
        ),
    )


def _report_analysis(run: AnalysisRun, artifact: Path) -> None:
    what = "Reused analysis" if run.reused else "Analyzed"
    print(f"{what}: {artifact} ({len(run.analysis.words)} words)")


def _write_cut(
    analysis: Analysis,
    script: list[ScriptLine],
    out_dir: Path,
    pauses: PauseSettings,
    off_script: OffScriptSettings,
    splice: SpliceSettings,
) -> None:
    plan = build_plan(analysis, script, pauses, off_script, splice)
    stem = Path(analysis.source.filename).stem
    report = render_report(analysis, script, plan)
    _write(out_dir / f"{stem}.xml", render_fcp7(plan))
    _write(out_dir / f"{stem}{REPORT_SUFFIX}", report)
    print()
    print(report, end="")


def _write(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except OSError as error:
        raise RoughCutError(f"Could not write {path}: {error}") from None
    print(f"Wrote {path}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="roughcut",
        description="Turn a recording and its script into a Premiere-importable rough cut.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    analyze = commands.add_parser(
        "analyze", parents=[_output_options(), _media_options()], help="Transcribe and probe only."
    )
    analyze.add_argument("recording", help="The MP4 to analyze.")
    analyze.set_defaults(handler=_analyze)

    cut = commands.add_parser(
        "cut",
        parents=[
            _output_options(),
            _media_options(),
            _pause_options(),
            _splice_options(),
            _off_script_options(),
        ],
        help="Analyze, plan and render: the whole tool.",
    )
    cut.add_argument("recording", help="The MP4 to cut.")
    cut.add_argument("script", help="The script, one sentence per line.")
    cut.set_defaults(handler=_cut)

    render = commands.add_parser(
        "render",
        parents=[
            _output_options(),
            _pause_options(),
            _splice_options(),
            _off_script_options(),
        ],
        help="Plan and render from an existing analysis, touching no media.",
    )
    render.add_argument("analysis", help="An analysis artifact written by `analyze` or `cut`.")
    render.add_argument("script", help="The script, one sentence per line.")
    render.set_defaults(handler=_render)

    return parser


def _output_options() -> argparse.ArgumentParser:
    options = argparse.ArgumentParser(add_help=False)
    options.add_argument(
        "-o",
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help=f"Where the XML, the report and the analysis go (default: {DEFAULT_OUT_DIR}).",
    )
    return options


def _pause_options() -> argparse.ArgumentParser:
    """How tight the cut is.

    These decide the plan rather than the analysis, so they cost nothing to change:
    `render` takes them too, and re-running with a different floor never re-transcribes.
    """
    defaults = PauseSettings()
    options = argparse.ArgumentParser(add_help=False)
    options.add_argument(
        "--pause-threshold-seconds",
        type=float,
        default=defaults.threshold_seconds,
        help=(
            "A stretch of detected quiet longer than this is shortened. Shorter ones "
            "are kept as they were recorded."
        ),
    )
    options.add_argument(
        "--pause-floor-seconds",
        type=float,
        default=defaults.floor_seconds,
        help="How long a shortened pause still lasts. Pauses are collapsed, never closed.",
    )
    options.add_argument(
        "--pause-padding-seconds",
        type=float,
        default=defaults.padding_seconds,
        help=(
            "Quiet kept either side of a collapse, inside the region it takes time "
            "out of. What is left of a region is whichever is longer, the floor or "
            "twice this."
        ),
    )
    return options


def _splice_options() -> argparse.ArgumentParser:
    """How much of the quiet either side of every splice the cut keeps.

    Its own option rather than a second use of `--pause-padding-seconds`: that one
    holds a cut *inside* the quiet and this one extends a clip *into* it, so one number
    meaning both could be tuned for neither.
    """
    defaults = SpliceSettings()
    options = argparse.ArgumentParser(add_help=False)
    options.add_argument(
        "--splice-padding-seconds",
        type=float,
        default=defaults.padding_seconds,
        help=(
            "Quiet kept either side of every splice, so that a word's last consonant "
            "still plays. Only ever taken from quiet the detector heard."
        ),
    )
    return options


def _off_script_options() -> argparse.ArgumentParser:
    """What the cut removes without asking, out of what the script does not account for.

    Every one of them only ever removes more: leave them alone and anything that is not
    plainly a restart or a mutter survives into the cut with a marker on it.
    """
    defaults = OffScriptSettings()
    options = argparse.ArgumentParser(add_help=False)
    options.add_argument(
        "--off-script-keep-seconds",
        type=float,
        default=defaults.keep_seconds,
        help="Speech off the script shorter than this is dropped as a mutter.",
    )
    options.add_argument(
        "--off-script-restart-likeness",
        type=float,
        default=defaults.restart_likeness,
        help=(
            "How much of what was said has to be the words of the line beside it before "
            "it is dropped as an abandoned attempt at that line, from 0 to 1."
        ),
    )
    options.add_argument(
        "--stop-phrases",
        nargs="*",
        default=None,
        metavar="PHRASE",
        help=(
            "Phrases that mark a region as a restart. Replaces the built-in list; "
            "give none to keep everything the other rules leave alone."
        ),
    )
    return options


def _media_options() -> argparse.ArgumentParser:
    """The settings that change what the media stage produces — and so the cache key."""
    defaults = AnalysisSettings()
    options = argparse.ArgumentParser(add_help=False)
    options.add_argument(
        "--analysis",
        dest="analysis_path",
        default=None,
        help="Where to keep the analysis artifact (default: <out-dir>/<recording>.analysis.json).",
    )
    options.add_argument(
        "--device",
        default=defaults.device,
        choices=["cuda", "cpu", "auto"],
        help="Where to run the transcriber. cpu works everywhere and is slow.",
    )
    options.add_argument(
        "--silence-threshold-db",
        type=float,
        default=defaults.silence_threshold_db,
        help="Level below which the room counts as quiet.",
    )
    options.add_argument(
        "--silence-min-seconds",
        type=float,
        default=defaults.silence_min_seconds,
        help="Shortest region worth calling a silence.",
    )
    return options


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
