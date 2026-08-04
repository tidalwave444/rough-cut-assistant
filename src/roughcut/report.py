"""The report: what the tool did, in the order a person would ask about it.

A pure function over the same plan the XML is rendered from, so the report can never
describe a cut other than the one that was emitted. It grows an entry per decision as
the decisions arrive — pauses, takes, off-script material — but the top of it always
answers the first question: how long was the recording, and how long is the cut.
"""

from roughcut.analysis import Analysis
from roughcut.plan import Plan, rough_cut, timeline_duration_seconds
from roughcut.script import ScriptLine

LABEL_WIDTH = 19


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
            _line("Source duration", _duration(source_seconds)),
            _line("Output duration", _duration(output_seconds)),
            _line("Removed", _duration(source_seconds - output_seconds)),
            _line("Words transcribed", len(analysis.words)),
            _line("Script lines", len(script)),
            "",
            "The whole recording plays as one clip: no pauses removed, no takes chosen.",
            "",
        ]
    )


def _line(label: str, value: object) -> str:
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
