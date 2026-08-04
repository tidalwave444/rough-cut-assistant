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
from roughcut.plan import build_plan
from roughcut.render import render_fcp7
from roughcut.report import render_report
from roughcut.script import ScriptLine, read_script

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
    _write_cut(run.analysis, script, Path(args.out_dir))
    return 0


def _render(args: argparse.Namespace) -> int:
    """Plan and render from an existing artifact, without opening the recording."""
    script = read_script(Path(args.script))
    _write_cut(load_analysis(Path(args.analysis)), script, Path(args.out_dir))
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


def _report_analysis(run: AnalysisRun, artifact: Path) -> None:
    what = "Reused analysis" if run.reused else "Analyzed"
    print(f"{what}: {artifact} ({len(run.analysis.words)} words)")


def _write_cut(analysis: Analysis, script: list[ScriptLine], out_dir: Path) -> None:
    plan = build_plan(analysis, script)
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
        parents=[_output_options(), _media_options()],
        help="Analyze, plan and render: the whole tool.",
    )
    cut.add_argument("recording", help="The MP4 to cut.")
    cut.add_argument("script", help="The script, one sentence per line.")
    cut.set_defaults(handler=_cut)

    render = commands.add_parser(
        "render",
        parents=[_output_options()],
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
