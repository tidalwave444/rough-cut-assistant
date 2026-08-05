"""The report: what the tool did, in the order a person would ask about it.

A pure function over the same plan the XML is rendered from, so the report can never
describe a cut other than the one that was emitted. It grows an entry per decision as
the decisions arrive — pauses, takes, off-script material — but the top of it always
answers the first question: how long was the recording, and how long is the cut.

Below that it answers the second: where did each line of my script end up, and what
did I say that the cut is not using.
"""

from roughcut.align import Leftover
from roughcut.analysis import Analysis
from roughcut.plan import Plan, rough_cut, timeline_duration_seconds
from roughcut.script import ScriptLine

LABEL_WIDTH = 19
TIME_WIDTH = 15
REASON_WIDTH = 20
EXCERPT_LENGTH = 60

NOT_FOUND = "not found"
NOWHERE = "—"

HOW_THE_CUT_WAS_MADE = (
    "One clip per script line, spliced in the order the script writes them — so the\n"
    "dead air between lines is gone, while a pause inside a line is still as it was\n"
    "spoken. Where a line was read more than once the first reading plays, and every\n"
    "reading the cut passed over is listed below."
)


def render_report(analysis: Analysis, script: list[ScriptLine], plan: Plan) -> str:
    """Describe a plan in plain text, for reading next to the imported sequence."""
    source_seconds = analysis.source.duration_seconds
    # The rough cut alone: the alternates sequence holds the takes that lost, and
    # counting those as output would say a cut ran longer than the recording.
    output_seconds = timeline_duration_seconds(rough_cut(plan))
    return "\n".join(
        [
            f"Rough cut — {analysis.source.filename}",
            "",
            _label("Source duration", _duration(source_seconds)),
            _label("Output duration", _duration(output_seconds)),
            _label("Removed", _duration(source_seconds - output_seconds)),
            _label("Words transcribed", len(analysis.words)),
            _label("Script lines", len(script)),
            _label("Lines found", len(plan.lines)),
            _label("Lines not found", len(plan.missing)),
            "",
            HOW_THE_CUT_WAS_MADE,
            "",
            *_where_each_line_went(script, plan),
            *_what_is_not_used(plan.leftovers),
            "",
        ]
    )


def _where_each_line_went(script: list[ScriptLine], plan: Plan) -> list[str]:
    """Every line of the script, with the time in the recording it was found at."""
    placed = {line.line.number: line for line in plan.lines}
    rows = [
        "Where each line was found",
        "",
        f"Line  {'Source'.ljust(TIME_WIDTH)}{'Timeline'.ljust(TIME_WIDTH)}Script",
    ]
    for line in script:
        found = placed.get(line.number)
        source = _duration(found.source_in_seconds) if found else NOT_FOUND
        timeline = _duration(found.timeline_start_seconds) if found else NOWHERE
        rows.append(
            f"{line.number:>4}  {source.ljust(TIME_WIDTH)}"
            f"{timeline.ljust(TIME_WIDTH)}{line.text}"
        )
    return rows


def _what_is_not_used(leftovers: list[Leftover]) -> list[str]:
    """The speech the cut leaves behind, so that nothing disappears unannounced."""
    if not leftovers:
        return []
    rows = ["", "Not used", ""]
    for leftover in leftovers:
        when = f"{_duration(leftover.start_seconds)}–{_duration(leftover.end_seconds)}"
        rows.append(f"  {when}  {_why(leftover).ljust(REASON_WIDTH)}{_excerpt(leftover.text)}")
    return rows


def _why(leftover: Leftover) -> str:
    if leftover.retake_of is None:
        return "off-script"
    return f"retake of line {leftover.retake_of.number}"


def _excerpt(text: str) -> str:
    if len(text) <= EXCERPT_LENGTH:
        return text
    return text[:EXCERPT_LENGTH].rstrip() + "…"


def _label(label: str, value: object) -> str:
    return f"{label.ljust(LABEL_WIDTH)}{value}"


def _duration(seconds: float) -> str:
    """`hh:mm:ss.mmm` — milliseconds, because a cut's worth of time is fractions.

    Signed, so a cut that somehow ran longer than its source reads as `-00:00:01.500`
    rather than as an hour and change of nonsense.
    """
    sign = "-" if seconds < 0 else ""
    whole, milliseconds = divmod(round(abs(seconds) * 1000), 1000)
    minutes, remaining = divmod(whole, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{sign}{hours:02d}:{minutes:02d}:{remaining:02d}.{milliseconds:03d}"
