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
from roughcut.pauses import Pause
from roughcut.plan import PlacedLine, Plan, rough_cut, timeline_duration_seconds
from roughcut.script import ScriptLine

LABEL_WIDTH = 19
TIME_WIDTH = 15
REASON_WIDTH = 20
COVERAGE_WIDTH = 10
DISFLUENCY_WIDTH = 14
EXCERPT_LENGTH = 60

NOT_FOUND = "not found"
NOWHERE = "—"
OFF_SCRIPT = "off-script"

HOW_THE_CUT_WAS_MADE = (
    "One clip per script line, spliced in the order the script writes them — so the\n"
    "dead air between lines is gone, while a long pause inside a line is shortened to\n"
    "a beat rather than closed. Where a line was read more than once the last complete\n"
    "reading plays, and every reading passed over is laid end to end in the alternates\n"
    "sequence beside the cut."
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
            _label("Takes considered", sum(len(line.chosen.decisions) for line in plan.lines)),
            _label("Lines flagged", len(plan.flagged)),
            _label("Pauses shortened", len(plan.shortened)),
            "",
            HOW_THE_CUT_WAS_MADE,
            "",
            *_where_each_line_went(script, plan),
            *_every_take_considered(plan.lines),
            *_which_take_was_used(plan.lines),
            *_which_lines_are_poor(plan.flagged),
            *_what_each_pause_gave_up(plan.shortened),
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


def _every_take_considered(lines: list[PlacedLine]) -> list[str]:
    """Every reading of every line, and why each one won or lost.

    One row per take, with the line number written once and its takes hanging below
    it, so a line read four times reads as one block rather than as four rows that
    have to be matched up by eye.
    """
    if not lines:
        return []
    rows = [
        "",
        "Every take considered",
        "",
        f"Line  Take  {'Source'.ljust(TIME_WIDTH)}"
        f"{'Coverage'.ljust(COVERAGE_WIDTH)}{'Disfluencies'.ljust(DISFLUENCY_WIDTH)}Outcome",
    ]
    for line in lines:
        for index, decision in enumerate(line.chosen.decisions):
            take = decision.take
            number = f"{line.line.number:>4}" if index == 0 else " " * 4
            rows.append(
                f"{number}  {take.number:>4}  "
                f"{_duration(take.start_seconds).ljust(TIME_WIDTH)}"
                f"{_percentage(take.coverage).ljust(COVERAGE_WIDTH)}"
                f"{str(take.disfluencies).ljust(DISFLUENCY_WIDTH)}{decision.reason}"
            )
    return rows


def _which_take_was_used(lines: list[PlacedLine]) -> list[str]:
    """Each line that was read more than once, and why its cut is what it is.

    One sentence per line, because "take 3 of 3; take 1 incomplete — 4 of 9 words" is
    the answer to the only question a table of takes leaves open: not what each take
    was, but why this one. Lines read once say nothing here — take 1 of 1 explains
    itself, and eight rows saying so would bury the lines that need reading.
    """
    retaken = [line for line in lines if len(line.chosen.decisions) > 1]
    if not retaken:
        return []
    return [
        "",
        "Which take was used",
        "",
        *(f"  Line {line.line.number}  {line.chosen.summary}" for line in retaken),
    ]


def _which_lines_are_poor(flagged: list[PlacedLine]) -> list[str]:
    """The lines no take of which stood up — the ones worth recording again.

    Listed on their own rather than left to be spotted in the table above, because
    this is the one thing in the report that asks the reader to do something.
    """
    if not flagged:
        return []
    return [
        "",
        "Lines whose best take was poor",
        "",
        *(f"  Line {line.line.number}  {line.chosen.summary}" for line in flagged),
    ]


def _what_each_pause_gave_up(pauses: list[Pause]) -> list[str]:
    """Every pause the cut took time out of — where it was, and how much came out.

    Both the old length and the new one, because the question this answers is whether
    the cut is too tight, and "1.7 s removed" does not say what is left.
    """
    if not pauses:
        return []
    rows = [
        "",
        "What each pause gave up",
        "",
        f"  {'At'.ljust(TIME_WIDTH)}{'Was'.ljust(TIME_WIDTH)}{'Now'.ljust(TIME_WIDTH)}Removed",
    ]
    for pause in pauses:
        rows.append(
            f"  {_duration(pause.gap_start_seconds).ljust(TIME_WIDTH)}"
            f"{_duration(pause.gap_seconds).ljust(TIME_WIDTH)}"
            f"{_duration(pause.remaining_seconds).ljust(TIME_WIDTH)}"
            f"{_duration(pause.removed_seconds)}"
        )
    return rows


def _what_is_not_used(leftovers: list[Leftover]) -> list[str]:
    """The speech no line accounts for, so that nothing disappears unannounced."""
    if not leftovers:
        return []
    rows = ["", "Not used", ""]
    for leftover in leftovers:
        when = f"{_duration(leftover.start_seconds)}–{_duration(leftover.end_seconds)}"
        rows.append(f"  {when}  {OFF_SCRIPT.ljust(REASON_WIDTH)}{_excerpt(leftover.text)}")
    return rows


def _excerpt(text: str) -> str:
    if len(text) <= EXCERPT_LENGTH:
        return text
    return text[:EXCERPT_LENGTH].rstrip() + "…"


def _label(label: str, value: object) -> str:
    return f"{label.ljust(LABEL_WIDTH)}{value}"


def _percentage(fraction: float) -> str:
    return f"{round(fraction * 100)}%"


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
