"""The report: what the tool did, in the order a person would ask about it.

A pure function over the same plan the XML is rendered from, so the report can never
describe a cut other than the one that was emitted. It grows an entry per decision as
the decisions arrive — pauses, takes, off-script material — but the top of it always
answers the first question: how long was the recording, and how long is the cut.

Below that it answers the second: where did each line of my script end up, and what
did I say that the cut is not using.
"""

from roughcut.analysis import Analysis
from roughcut.falsestarts import FalseStart
from roughcut.offscript import OffScript
from roughcut.pauses import Pause
from roughcut.plan import PlacedLine, Plan, rough_cut, timeline_duration_seconds
from roughcut.script import ScriptLine

LABEL_WIDTH = 19
TIME_WIDTH = 15
COVERAGE_WIDTH = 10
DISFLUENCY_WIDTH = 14

# Wide enough for the longest outcome an off-script region can carry, which is a stop
# phrase quoted back: `cut — a stop phrase, "let me try that again"`.
OUTCOME_WIDTH = 46

# Wide enough for either reason a stretch comes out of the middle of a take, the longer
# of them being `nothing of the line opposite it`.
FAULT_WIDTH = 34

NOT_FOUND = "not found"
NOWHERE = "—"

HOW_THE_CUT_WAS_MADE = (
    "One clip per script line, spliced in the order the script writes them — so the\n"
    "dead air between lines is gone, and so is the quiet at either end of what plays,\n"
    "while a long silence inside a line is shortened to a beat rather than closed. The\n"
    "quiet is heard rather than read: it is where the room went silent, which is not\n"
    "where the transcript ran out of words. Where a line was read more than once the\n"
    "last complete reading plays, and every reading passed over is laid end to end in\n"
    "the alternates sequence beside the cut. An attempt abandoned in the middle of a\n"
    "line comes out of it, on the evidence of a word said twice and never at the cost\n"
    "of one of the line's own words — a word the transcriber misheard was spoken and\n"
    "stays. Anything said that the script does not account for goes only if it is\n"
    "short, an abandoned attempt at the line beside it, or on the stop-phrase list;\n"
    "anything else stays where it was said, marked as off-script."
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
            _label("False starts cut", len(plan.removed)),
            _label("Off-script kept", len(plan.kept)),
            _label("Off-script cut", len(plan.cut)),
            "",
            HOW_THE_CUT_WAS_MADE,
            "",
            *_where_each_line_went(script, plan),
            *_every_take_considered(plan.lines),
            *_which_take_was_used(plan.lines),
            *_which_lines_are_poor(plan.flagged),
            *_what_each_pause_gave_up(plan.shortened),
            *_what_came_out_of_a_take(plan.removed),
            *_what_was_said_off_script(plan.off_script),
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

    A pause is a stretch of detected quiet, so that is what the row describes: where
    the room went quiet, how long it stayed quiet, and how long it stays quiet now.
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
            f"  {_duration(pause.quiet_start_seconds).ljust(TIME_WIDTH)}"
            f"{_duration(pause.quiet_seconds).ljust(TIME_WIDTH)}"
            f"{_duration(pause.remaining_seconds).ljust(TIME_WIDTH)}"
            f"{_duration(pause.removed_seconds)}"
        )
    return rows


def _what_came_out_of_a_take(removals: list[FalseStart]) -> list[str]:
    """Every abandoned attempt taken out from inside a line that plays.

    Quoted in full, for the reason the off-script section quotes what it removed: this
    is the only record that the stretch was ever spoken. It matters more here, if
    anything — a removed off-script region is at least a silence between two lines,
    whereas this vanishes into the middle of a line that otherwise sounds untouched.
    """
    if not removals:
        return []
    rows = [
        "",
        "What came out from inside a take",
        "",
        f"Line  {'At'.ljust(TIME_WIDTH)}{'Duration'.ljust(TIME_WIDTH)}"
        f"{'Why'.ljust(FAULT_WIDTH)}What was said",
    ]
    for removal in removals:
        rows.append(
            f"{removal.line.number:>4}  {_duration(removal.start_seconds).ljust(TIME_WIDTH)}"
            f"{_duration(removal.duration_seconds).ljust(TIME_WIDTH)}"
            f"{removal.fault.ljust(FAULT_WIDTH)}{removal.text}"
        )
    return rows


def _what_was_said_off_script(regions: list[OffScript]) -> list[str]:
    """Every region the script does not account for, and what became of it.

    The ones that were cut are listed beside the ones that were kept, and both quote
    what was said — in full, however long, because this section is the only record a
    removed region ever existed, and a person who does not know it existed cannot go
    looking for it. An excerpt would be the one place in the report where reading it
    is not enough.
    """
    if not regions:
        return []
    rows = [
        "",
        "Off-script material",
        "",
        f"  {'At'.ljust(TIME_WIDTH)}{'Duration'.ljust(TIME_WIDTH)}"
        f"{'Outcome'.ljust(OUTCOME_WIDTH)}What was said",
    ]
    for region in regions:
        rows.append(
            f"  {_duration(region.start_seconds).ljust(TIME_WIDTH)}"
            f"{_duration(region.duration_seconds).ljust(TIME_WIDTH)}"
            f"{region.reason.ljust(OUTCOME_WIDTH)}{region.text}"
        )
    return rows


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
