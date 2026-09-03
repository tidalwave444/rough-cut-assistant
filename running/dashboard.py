#!/usr/bin/env python3
"""Builds out/dashboard.html: one page showing what this repo is doing.

Nothing here is imported by the tool, and nothing here decides anything. It reads what
is already written down — the git history, `out/`, `work/`, `settled/` — and lays it out
so the three cycles this project runs on can be seen at once:

  the pipeline    a recording and a script in, an XML and a report out
  the fix loop    running/xml-fix-loop/loop.sh, iteration by iteration, red count falling
  the work loop   a listen, a ticket, a decision, a golden

The cut is described from its clips, never from its report — decision 0011. The report can
say a line was found at full coverage while the clips beneath it play an abandoned attempt,
so both are shown side by side and neither is scored. No health number is computed here on
purpose: a proxy is the thing this repo has been burned by.

    uv run python running/dashboard.py            # newest run in out/
    uv run python running/dashboard.py out/seq07-final
"""

from __future__ import annotations

import html
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
DASHBOARD = OUT / "dashboard.html"

esc = html.escape


# ---------------------------------------------------------------- reading the repo


@dataclass
class Iteration:
    sha: str
    when: datetime
    number: int
    red: int
    subject: str


@dataclass
class LoopRun:
    iterations: list[Iteration] = field(default_factory=list)
    after: list[tuple[str, datetime, str]] = field(default_factory=list)

    @property
    def started(self) -> datetime:
        return self.iterations[0].when

    @property
    def opening_red(self) -> int:
        return self.iterations[0].red

    @property
    def closing_red(self) -> int:
        return self.iterations[-1].red

    @property
    def outcome(self) -> tuple[str, str]:
        """How the run went, read off the counts alone.

        A commit records the count at the moment its iteration *began*, so the state the loop
        finally exited on is not in this history at all. What is here is whether the count was
        falling while it ran, which is the only thing the loop itself steers on.
        """
        reds = [it.red for it in self.iterations]
        if any(r == 999 for r in reds):
            return ("critical", "999 — a crash, not a count")
        if len(reds) == 1:
            return ("idle", "one iteration only")
        if reds[-1] > reds[-2]:
            return ("critical", f"the count rose, {reds[-2]} → {reds[-1]}")
        if reds[-1] == reds[-2]:
            return ("warning", "a flat iteration — no fall")
        return ("good", f"falling, {reds[0]} → {reds[-1]}")


ITERATION = re.compile(r"^xml fix loop, iteration (\d+) \(was (\d+) red\)$")


def git_log() -> list[tuple[str, datetime, str]]:
    out = subprocess.run(
        ["git", "log", "--format=%h%x09%aI%x09%s"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    rows = []
    for line in out.splitlines():
        sha, when, subject = line.split("\t", 2)
        rows.append((sha, datetime.fromisoformat(when), subject))
    return rows


def loop_runs(log: list[tuple[str, datetime, str]]) -> list[LoopRun]:
    """Group the loop's own commits into runs, oldest first.

    The loop commits one per iteration and numbers them from 1, so a number that does not
    climb starts a new run. What a person committed after a run is kept beside it: that is
    the golden they accepted, or the check they wrote next.
    """
    runs: list[LoopRun] = []
    current: LoopRun | None = None
    for sha, when, subject in reversed(log):
        match = ITERATION.match(subject)
        if match is None:
            if current is not None:
                current.after.append((sha, when, subject))
            continue
        number, red = int(match.group(1)), int(match.group(2))
        if current is None or number <= current.iterations[-1].number:
            current = LoopRun()
            runs.append(current)
        current.iterations.append(Iteration(sha, when, number, red, subject))
    return runs


@dataclass
class Checks:
    exists: bool
    when: datetime | None
    failed: list[str]
    type_errors: list[str]
    summary: str

    @property
    def red(self) -> int:
        total = len(self.failed) + len(self.type_errors)
        return 999 if total == 0 and not self.green else total

    @property
    def green(self) -> bool:
        return bool(re.search(r"Success: no issues found", self.summary)) and not self.failed


def read_checks() -> Checks:
    log = OUT / "check.txt"
    if not log.exists():
        return Checks(False, None, [], [], "")
    text = log.read_text(errors="replace")
    failed = [line[len("FAILED "):] for line in text.splitlines() if line.startswith("FAILED")]
    errors = [
        line for line in text.splitlines()
        if re.match(r"^[^ ]+\.py:[0-9]+: error:", line)
    ]
    tail = [
        line for line in text.splitlines()
        if re.search(r"(passed|failed|error)", line) and ("=" in line or "Found" in line)
        or line.startswith("Success: no issues found")
    ]
    when = datetime.fromtimestamp(log.stat().st_mtime, tz=timezone.utc).astimezone()
    return Checks(True, when, failed, errors, "\n".join(tail[-4:]))


@dataclass
class Ticket:
    number: str
    title: str
    status: str
    blocked_by: str
    listen_for: int
    path: Path


STATUS_ORDER = ["ready-for-agent", "awaiting-listen", "done"]


def tickets(feature: Path) -> list[Ticket]:
    found: list[Ticket] = []
    for path in sorted((feature / "open").glob("*.md")):
        text = path.read_text()
        heading = re.search(r"^# *(\S+) *[—-] *(.+)$", text, re.M)
        status = re.search(r"^\*\*Status:\*\* *(\S+)", text, re.M)
        blocked = re.search(r"^\*\*Blocked by:\*\* *(.+)$", text, re.M)
        section = text.split("## Listen for", 1)[-1].split("- [", 1)[0]
        listen = re.findall(r"^\d+\. ", section, re.M)
        found.append(Ticket(
            number=heading.group(1) if heading else path.stem[:2],
            title=heading.group(2).strip() if heading else path.stem,
            status=status.group(1) if status else "unknown",
            blocked_by=blocked.group(1).strip() if blocked else "None",
            listen_for=len(listen),
            path=path.relative_to(ROOT),
        ))
    return found


def closed_tickets(feature: Path) -> list[tuple[str, str]]:
    closed = feature / "closed.md"
    if not closed.exists():
        return []
    return re.findall(r"^## *(\S+) *[—-] *(.+)$", closed.read_text(), re.M)


def decisions() -> list[tuple[str, str]]:
    found = []
    for path in sorted((ROOT / "settled" / "decisions").glob("*.md")):
        number, _, slug = path.stem.partition("-")
        claim = slug.replace("-", " ")
        found.append((number, claim[:1].upper() + claim[1:]))
    return found


# ---------------------------------------------------------------- reading a run


@dataclass
class Line:
    number: str
    start_seconds: float
    seconds: float
    clips: int


@dataclass
class Cut:
    name: str
    timebase: int
    duration_seconds: float
    lines: list[Line]
    alternate_clips: int
    alternate_seconds: float


def parse_cut(path: Path) -> Cut:
    """The clip list, which is the only description of a cut this project trusts."""
    root = ET.parse(path).getroot()
    sequences = list(root.iter("sequence"))
    main = sequences[0]
    timebase = int(main.findtext("rate/timebase") or "60")

    clips: list[tuple[int, int]] = []
    for track in main.iter("track"):
        for item in track.findall("clipitem"):
            clips.append((int(item.findtext("start") or 0), int(item.findtext("end") or 0)))
    clips.sort()
    duration = int(main.findtext("duration") or 0)

    markers = [
        (m.findtext("name") or "", int(m.findtext("in") or 0)) for m in main.findall("marker")
    ]
    # A line enumerating its items carries a marker per item — "Line 5.1", "Line 5.2". The
    # line is the whole span, so the sub-markers fold into their parent.
    # A marker is placed on the word, which is not always where the clip carrying it begins —
    # line 6 of Sequence 07 is marked nine frames into its clip. A line starts where its clip
    # starts, so the marker is snapped back to the clip it falls inside.
    starts = sorted(start for start, _ in clips)
    heads: list[tuple[str, int]] = []
    for name, frame in markers:
        number = re.sub(r"^Line +", "", name).split(".")[0]
        if not heads or heads[-1][0] != number:
            snapped = max((s for s in starts if s <= frame), default=frame)
            heads.append((number, snapped))

    lines: list[Line] = []
    for index, (number, frame) in enumerate(heads):
        end = heads[index + 1][1] if index + 1 < len(heads) else duration
        inside = [c for c in clips if frame <= c[0] < end]
        lines.append(Line(
            number=number,
            start_seconds=frame / timebase,
            seconds=(end - frame) / timebase,
            clips=len(inside),
        ))

    alt_clips, alt_frames = 0, 0
    if len(sequences) > 1:
        for track in sequences[1].iter("track"):
            for item in track.findall("clipitem"):
                alt_clips += 1
                alt_frames += int(item.findtext("end") or 0) - int(item.findtext("start") or 0)

    return Cut(
        name=main.findtext("name") or path.stem,
        timebase=timebase,
        duration_seconds=duration / timebase,
        lines=lines,
        alternate_clips=alt_clips,
        alternate_seconds=alt_frames / timebase,
    )


@dataclass
class Report:
    stats: list[tuple[str, str]]
    lines: dict[str, tuple[str, str, str]]
    poor: dict[str, str]
    used: dict[str, str]


def parse_report(path: Path) -> Report:
    text = path.read_text(errors="replace")
    body = text.splitlines()

    stats: list[tuple[str, str]] = []
    for line in body[2:]:
        if not line.strip():
            if stats:
                break
            continue
        parts = re.split(r"\s{2,}", line.strip(), maxsplit=1)
        if len(parts) == 2:
            stats.append((parts[0], parts[1]))
        elif stats:
            break

    lines: dict[str, tuple[str, str, str]] = {}
    row = re.compile(
        r"^\s*(\d+)\s{2,}(not found|[\d:.]+)\s{2,}(\S+)\s{2,}(.*)$"
    )
    section = text.split("Where each line was found", 1)[-1].split("Every take", 1)[0]
    for line in section.splitlines():
        match = row.match(line)
        if match:
            lines[match.group(1)] = (match.group(2), match.group(3), match.group(4).strip())

    poor = dict(re.findall(r"^ +Line (\d+) +(.+)$",
                           text.split("Lines whose best take was poor", 1)[-1]
                               .split("What each pause", 1)[0], re.M))
    used = dict(re.findall(r"^ +Line (\d+) +(.+)$",
                           text.split("Which take was used", 1)[-1]
                               .split("Lines whose", 1)[0], re.M))
    return Report(stats, lines, poor, used)


@dataclass
class Run:
    directory: Path
    xml: Path | None
    report: Path | None
    analysis: Path | None

    @property
    def when(self) -> datetime:
        newest = max(
            p.stat().st_mtime for p in (self.xml, self.report, self.analysis) if p is not None
        )
        return datetime.fromtimestamp(newest, tz=timezone.utc).astimezone()

    @property
    def label(self) -> str:
        return str(self.directory.relative_to(ROOT))


def runs() -> list[Run]:
    found: list[Run] = []
    for directory in [OUT, *sorted(p for p in OUT.iterdir() if p.is_dir())]:
        xmls = sorted(directory.glob("*.xml"))
        if not xmls:
            continue
        reports = sorted(directory.glob("*.report.txt"))
        analyses = sorted(directory.glob("*.analysis.json"))
        found.append(Run(
            directory=directory,
            xml=xmls[0],
            report=reports[0] if reports else None,
            analysis=analyses[0] if analyses else None,
        ))
    return sorted(found, key=lambda r: r.when, reverse=True)


def counts() -> dict[str, int]:
    return {
        "modules": len(list((ROOT / "src" / "roughcut").glob("*.py"))),
        "tests": len(list((ROOT / "tests").glob("test_*.py"))),
        "committed": len(list((ROOT / "tests" / "committed").iterdir())),
        "recordings": len(list((ROOT / "recordings").iterdir())),
        "decisions": len(list((ROOT / "settled" / "decisions").glob("*.md"))),
    }


# ---------------------------------------------------------------- the page

CSS = """
:root {
  color-scheme: light;
  --surface-0: #f6f5f2;
  --surface-1: #fcfcfb;
  --surface-2: #efeeea;
  --line:      #ddddd6;
  --ink:       #0b0b0b;
  --ink-2:     #52514e;
  --ink-3:     #86857e;
  --series-1:  #2a78d6;
  --series-2:  #eb6834;
  --seq-200:   #9ec5f4;
  --seq-450:   #2a78d6;
  --good:      #0ca30c;
  --warning:   #fab219;
  --critical:  #d03b3b;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --surface-0: #121211;
    --surface-1: #1a1a19;
    --surface-2: #232322;
    --line:      #383835;
    --ink:       #ffffff;
    --ink-2:     #c3c2b7;
    --ink-3:     #8d8c84;
    --series-1:  #3987e5;
    --series-2:  #d95926;
    --seq-200:   #184f95;
    --seq-450:   #3987e5;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --surface-0: #121211;
  --surface-1: #1a1a19;
  --surface-2: #232322;
  --line:      #383835;
  --ink:       #ffffff;
  --ink-2:     #c3c2b7;
  --ink-3:     #8d8c84;
  --series-1:  #3987e5;
  --series-2:  #d95926;
  --seq-200:   #184f95;
  --seq-450:   #3987e5;
}

* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--surface-0);
  color: var(--ink);
  font: 14px/1.5 ui-sans-serif, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
main { max-width: 1120px; margin: 0 auto; padding: 0 24px 72px; }
header {
  max-width: 1120px; margin: 0 auto; padding: 32px 24px 20px;
  display: flex; align-items: baseline; gap: 16px; flex-wrap: wrap;
}
h1 { font-size: 20px; margin: 0; letter-spacing: -0.01em; }
h2 {
  font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--ink-3); margin: 40px 0 12px; font-weight: 600;
}
h3 { font-size: 14px; margin: 0 0 8px; font-weight: 600; }
p { margin: 0 0 12px; color: var(--ink-2); max-width: 76ch; }
a { color: var(--series-1); }
code, .mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
}
.sub { color: var(--ink-3); font-size: 12px; }
.card {
  background: var(--surface-1); border: 1px solid var(--line);
  border-radius: 10px; padding: 16px;
}
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; }
.tile { background: var(--surface-1); border: 1px solid var(--line);
        border-radius: 10px; padding: 12px 14px; }
.tile .n { font-size: 26px; font-weight: 600; letter-spacing: -0.02em; display: block; }
.tile .k { font-size: 12px; color: var(--ink-3); }
.chip {
  display: inline-flex; align-items: center; gap: 6px; border-radius: 999px;
  padding: 2px 10px; font-size: 12px; font-weight: 600;
  border: 1px solid var(--line); background: var(--surface-2); color: var(--ink-2);
}
.chip .dot { width: 8px; height: 8px; border-radius: 50%; }
.dot.good { background: var(--good); } .dot.warning { background: var(--warning); }
.dot.critical { background: var(--critical); } .dot.idle { background: var(--ink-3); }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th {
  text-align: left; font-weight: 600; color: var(--ink-3); font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.06em;
  border-bottom: 1px solid var(--line); padding: 6px 10px 6px 0;
}
td { padding: 7px 10px 7px 0; border-bottom: 1px solid var(--line);
     vertical-align: top; color: var(--ink-2); }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums;
                 font-family: ui-monospace, Menlo, Consolas, monospace; }
td strong { color: var(--ink); font-weight: 600; }
.scroll { overflow-x: auto; }
.bar { height: 10px; border-radius: 0 4px 4px 0; background: var(--seq-450); display: block; }
.bartrack { background: var(--surface-2); border-radius: 0 4px 4px 0; min-width: 120px; }
.runs { display: flex; gap: 18px; align-items: flex-end; overflow-x: auto; padding: 8px 0 0; }
.run { flex: 0 0 auto; }
.run .cols { display: flex; align-items: flex-end; gap: 2px; height: 132px; }
.col {
  width: 20px; background: var(--seq-450); border-radius: 4px 4px 0 0; position: relative;
}
.col.crash {
  background: repeating-linear-gradient(45deg, var(--seq-200) 0 4px, var(--surface-2) 4px 8px);
  border: 1px solid var(--seq-450);
}
.run .foot { border-top: 1px solid var(--line); margin-top: 6px; padding-top: 6px; }
.cols-legend { display: flex; gap: 14px; align-items: center; margin: 6px 0 0; }
.swatch { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
.board { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
.board ul { list-style: none; margin: 8px 0 0; padding: 0; }
.board li { padding: 8px 0; border-top: 1px solid var(--line); }
.warn {
  border-left: 3px solid var(--warning); background: var(--surface-1);
  padding: 12px 14px; border-radius: 0 8px 8px 0; margin: 0 0 14px;
}
.warn strong { color: var(--ink); }
svg { width: 100%; height: auto; display: block; }
.node { fill: var(--surface-1); stroke: var(--line); }
.node.pure { fill: var(--surface-2); }
.node-t { fill: var(--ink); font-size: 12px; font-weight: 600; }
.node-s { fill: var(--ink-3); font-size: 10.5px; }
.edge { stroke: var(--ink-3); stroke-width: 1.5; fill: none; }
.edge.soft { stroke-dasharray: 4 4; }
.seam { stroke: var(--series-2); stroke-width: 1.5; stroke-dasharray: 6 5; }
.seam-t { fill: var(--series-2); font-size: 11px; font-weight: 600; }
.band { fill: var(--surface-2); }
.band-t { fill: var(--ink-3); font-size: 10.5px; letter-spacing: 0.08em; font-weight: 600; }
#tip {
  position: fixed; pointer-events: none; opacity: 0; transition: opacity .1s;
  background: var(--surface-1); border: 1px solid var(--line); border-radius: 8px;
  padding: 6px 9px; font-size: 12px; color: var(--ink); box-shadow: 0 4px 14px #0003;
  max-width: 280px; z-index: 9;
}
button.theme {
  margin-left: auto; background: var(--surface-1); color: var(--ink-2);
  border: 1px solid var(--line); border-radius: 999px; padding: 4px 12px;
  font: inherit; font-size: 12px; cursor: pointer;
}
"""

JS = """
const tip = document.getElementById('tip');
document.querySelectorAll('[data-tip]').forEach(el => {
  el.addEventListener('mouseenter', () => {
    tip.textContent = el.dataset.tip; tip.style.opacity = 1;
  });
  el.addEventListener('mousemove', e => {
    tip.style.left = Math.min(e.clientX + 14, innerWidth - 300) + 'px';
    tip.style.top = (e.clientY + 18) + 'px';
  });
  el.addEventListener('mouseleave', () => { tip.style.opacity = 0; });
});
const root = document.documentElement;
document.querySelector('button.theme').addEventListener('click', () => {
  const dark = getComputedStyle(root).getPropertyValue('--ink').trim() === '#ffffff';
  root.dataset.theme = dark ? 'light' : 'dark';
});
"""


def tick(path: Path | None) -> str:
    return "✓" if path is not None else "—"


def stat_chip(status: str, text: str) -> str:
    return f'<span class="chip"><span class="dot {status}"></span>{esc(text)}</span>'


def timecode(seconds: float) -> str:
    minutes, rest = divmod(seconds, 60)
    return f"{int(minutes):02d}:{rest:06.3f}"


def diagram(open_tickets: int, decision_count: int, module_count: int) -> str:
    """The pipeline, the bridge out, and the loop that comes back to the code.

    Hand-placed, orthogonal, and deliberately crossing-free: the only two edges that cross
    the seam are the artifact and the script, which is exactly what does cross it.
    """
    nodes = [
        # x, y, w, h, title, subtitle, class
        (16, 44, 176, 46, "recordings/*.mp4", "the recording", ""),
        (16, 102, 176, 46, "recordings/*.txt", "the script", ""),
        (232, 73, 128, 46, "analyze", "ffmpeg · Whisper · GPU", ""),
        (400, 73, 190, 46, "out/*.analysis.json", "the artifact · cached", ""),
        (400, 139, 190, 42, "tests/committed/*.json", "committed · costs a GPU", ""),
        (660, 44, 116, 46, "plan", "pure", "pure"),
        (660, 102, 116, 46, "render", "pure", "pure"),
        (816, 30, 200, 44, "out/*.xml", "RoughCut + Alternates", ""),
        (816, 82, 200, 44, "out/*.report.txt", "what it claims", ""),
        (816, 134, 200, 44, "tests/committed goldens", "test_golden.py", ""),
        (16, 268, 176, 46, "/mnt/win-xml", "write-only bridge", ""),
        (232, 268, 150, 46, "Premiere", "import · relink once", ""),
        (424, 268, 166, 46, "the listen", "a person, with ears", ""),
        (660, 268, 150, 46, "work/open/NN", f"{open_tickets} open", ""),
        (852, 268, 164, 46, "settled/decisions", f"{decision_count} settled", ""),
        (424, 350, 166, 46, "pytest + mypy", "the contract", ""),
        (660, 350, 150, 46, "xml-fix-loop", "claude -p, boxed", ""),
        (852, 350, 164, 46, "src/roughcut", f"{module_count} modules", ""),
    ]
    edges = [
        ("M192,67 H212 V96 H232", ""),            # the recording is the only thing analyze opens
        ("M192,125 H212 V196 H646 V67 H660", ""),  # the script goes to plan, not to the model
        ("M360,96 H400", ""),
        ("M590,96 H636 V67 H660", ""),             # the artifact crosses the seam
        ("M590,160 H636 V125 H660", "soft"),       # and so does what the tests read instead
        ("M718,90 V102", ""),
        ("M776,118 H796 V52 H816", ""),
        ("M776,132 H796 V104 H816", ""),
        ("M916,126 V134", "soft"),
        ("M1016,52 H1024 V208 H104 V268", ""),     # out of the repo and onto Windows
        ("M192,291 H232", ""),
        ("M382,291 H424", ""),
        ("M590,291 H660", ""),
        ("M810,291 H852", "soft"),
        ("M734,314 V350", ""),
        ("M590,373 H660", ""),
        ("M810,373 H852", ""),
        ("M934,396 V416 H507 V396", ""),           # and round again
    ]
    parts = [
        '<svg viewBox="0 0 1032 432" role="img" aria-label="A recording and a script become an '
        'XML; the XML goes to Premiere, the listen becomes a ticket, and the loop edits the '
        'code the checks measure">',
        '<defs><marker id="a" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" '
        'markerHeight="7" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="currentColor" '
        'opacity=".55"/></marker></defs>',
        '<rect class="band" x="8" y="248" width="1016" height="176" rx="10" opacity=".55"/>',
        '<text class="band-t" x="20" y="18">THE PIPELINE</text>',
        '<text class="band-t" x="20" y="262">AND BACK AROUND</text>',
    ]
    for path, kind in edges:
        parts.append(f'<path class="edge {kind}" d="{path}" marker-end="url(#a)"/>')
    parts.append('<line class="seam" x1="624" y1="24" x2="624" y2="200"/>')
    parts.append('<text class="seam-t" x="632" y="20">the seam — nothing right of here opens '
                 "media</text>")
    for x, y, w, h, title, subtitle, cls in nodes:
        parts.append(
            f'<rect class="node {cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/>'
            f'<text class="node-t" x="{x + 12}" y="{y + 20}">{esc(title)}</text>'
            f'<text class="node-s" x="{x + 12}" y="{y + 36}">{esc(subtitle)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def render(chosen: Run | None) -> str:
    log = git_log()
    all_runs = runs()
    run_list = loop_runs(log)
    checks = read_checks()
    feature = ROOT / "work" / "rough-cut-assistant"
    open_tickets = tickets(feature)
    closed = closed_tickets(feature)
    settled = decisions()
    n = counts()
    now = datetime.now().astimezone()

    cut = parse_cut(chosen.xml) if chosen and chosen.xml else None
    report = parse_report(chosen.report) if chosen and chosen.report else None

    h: list[str] = []
    add = h.append

    add("<!doctype html>")
    add('<html lang="en"><head><meta charset="utf-8">')
    add('<meta name="viewport" content="width=device-width, initial-scale=1">')
    add("<title>Rough Cut Assistant — dashboard</title>")
    add(f"<style>{CSS}</style></head><body><div id='tip'></div>")

    # --- header ------------------------------------------------------------
    # out/check.txt is written by loop.sh and by nothing else, so it can easily be older than
    # the code it describes. A green chip over a stale log is the one lie this page could tell.
    head_sha, head_when, _ = log[0]
    stale = checks.when is not None and checks.when < head_when
    if not checks.exists:
        state = stat_chip("idle", "checks never run here")
    elif stale:
        state = stat_chip("warning", f"stale — written before {head_sha}")
    elif checks.green:
        state = stat_chip("good", "green")
    elif checks.red == 999:
        state = stat_chip("critical", "red, and it does not name a failure — 999")
    else:
        state = stat_chip("critical", f"{checks.red} red")
    add("<header><h1>Rough Cut Assistant</h1>")
    add(f'<span class="sub">a recording plus its script in, an FCP7 XML for Premiere out · '
        f'built {now:%d %b %Y %H:%M}</span>')
    add('<button class="theme" type="button">theme</button></header><main>')

    # --- where it stands ---------------------------------------------------
    add("<h2>Where it stands</h2>")
    add('<div class="tiles">')
    checked = f"{checks.when:%d %b %H:%M}" if checks.when else "never"
    tiles = [
        (state, "checks · out/check.txt",
         f"{checks.red} red when written, {checked}" if checks.exists and not checks.green
         else f"last written {checked}"),
        (f"{len(open_tickets)}", "tickets open", f"{len(closed)} closed"),
        (f"{sum(1 for t in open_tickets if t.status == 'awaiting-listen')}", "awaiting a listen",
         "only a person closes these"),
        (f"{len(settled)}", "decisions settled", "settled/decisions/"),
        (f"{len(run_list)}", "loop runs",
         f"{sum(len(r.iterations) for r in run_list)} iterations"),
        (f"{len(all_runs)}", "cuts kept in out/", "disposable, git-ignored"),
    ]
    for value, key, sub in tiles:
        big = value if value.startswith("<") else f'<span class="n">{esc(value)}</span>'
        add(f'<div class="tile">{big}<span class="k">{esc(key)}<br>{esc(sub)}</span></div>')
    add("</div>")

    if checks.failed or checks.type_errors:
        add('<div class="card" style="margin-top:12px">')
        add("<h3>What was red when the log was written</h3>")
        if stale:
            add('<p class="sub">HEAD has moved since — <code>uv run pytest -q; uv run mypy</code>'
                " or another turn of the loop rewrites this.</p>")
        add("<ul class='mono' style='margin:0;padding-left:18px'>")
        for name in checks.failed[:12]:
            add(f"<li>{esc(name)}</li>")
        for name in checks.type_errors[:8]:
            add(f"<li>{esc(name)}</li>")
        add("</ul></div>")

    # --- the pipeline ------------------------------------------------------
    add("<h2>How it fits together</h2>")
    add('<div class="card">')
    add(diagram(len(open_tickets), len(settled), n["modules"]))
    add('<p class="sub" style="margin-top:12px">'
        "<code>analyze</code> is the only stage that opens the recording. "
        "<code>plan</code> and <code>render</code> are pure functions over its artifact — that "
        "is the seam, and it is why the suite runs in half a second with no GPU. Dashed edges "
        "are what is read rather than produced. The loop edits <code>src/roughcut</code>, "
        "which is the code every box in the top half runs on — nothing else on this page "
        "closes that circle for you.</p>")
    add("</div>")

    # --- the cut, from its clips ------------------------------------------
    add("<h2>The cut, read from its clips</h2>")
    add('<div class="warn">Decision 0011 — <strong>a cut is described from its clips, not from '
        "its report.</strong> The report has called a line 100% covered and selected while the "
        "clips beneath it played the whole abandoned attempt. Both columns are here; neither is "
        "scored, and nothing on this page decides which one is right. Play it.</div>")
    if cut is None:
        add('<div class="card"><p>No XML in <code>out/</code> yet. '
            "<code>uv run roughcut cut recordings/&lt;name&gt;.mp4 "
            "recordings/&lt;script&gt;.txt -o out</code></p></div>")
    else:
        assert chosen is not None
        add('<div class="card">')
        add(f'<h3>{esc(cut.name)} · <span class="mono">{esc(chosen.label)}</span></h3>')
        add(f'<p class="sub">{timecode(cut.duration_seconds)} across '
            f"{sum(l.clips for l in cut.lines)} clipitems at {cut.timebase} fps · "
            f"{cut.alternate_clips} rejected readings laid out in RoughCut_Alternates "
            f"({timecode(cut.alternate_seconds)}) · rendered {chosen.when:%d %b %H:%M}</p>")
        widest = max((l.seconds for l in cut.lines), default=1.0)
        add('<div class="scroll"><table><thead><tr>')
        add('<th class="num">Line</th><th class="num">Starts</th><th>Plays for</th>'
            '<th class="num">s</th><th class="num">clips</th>'
            '<th>What the report says</th><th>Script</th>')
        add("</tr></thead><tbody>")
        for line in cut.lines:
            found, timeline, script = ("—", "—", "")
            if report and line.number in report.lines:
                found, timeline, script = report.lines[line.number]
            claim = "found" if found != "not found" else "not found"
            if report and line.number in report.poor:
                claim = "least bad take — " + report.poor[line.number].split("—", 1)[-1].strip()
            elif report and line.number in report.used:
                claim = report.used[line.number]
            width = max(2.0, 100 * line.seconds / widest)
            tip = (f"line {line.number} · starts {timecode(line.start_seconds)} · "
                   f"{line.seconds:.2f} s · {line.clips} clipitems")
            add(f'<tr><td class="num"><strong>{esc(line.number)}</strong></td>')
            add(f'<td class="num mono">{timecode(line.start_seconds)}</td>')
            add(f'<td class="bartrack" data-tip="{esc(tip)}">'
                f'<span class="bar" style="width:{width:.1f}%"></span></td>')
            add(f'<td class="num">{line.seconds:.2f}</td>')
            add(f'<td class="num">{line.clips}</td>')
            add(f"<td>{esc(claim)}</td>")
            add(f'<td><span class="sub">{esc(script[:74])}</span></td></tr>')
        if report:
            for number, (found, _, script) in report.lines.items():
                if found == "not found":
                    add(f'<tr><td class="num">{esc(number)}</td><td class="num">—</td>'
                        f'<td class="sub">no clip</td>'
                        f'<td class="num">—</td><td class="num">0</td>'
                        f"<td>not found in the recording</td>"
                        f'<td><span class="sub">{esc(script[:74])}</span></td></tr>')
        add("</tbody></table></div>")
        if report:
            add('<div class="tiles" style="margin-top:14px">')
            for key, value in report.stats:
                add(f'<div class="tile"><span class="n">{esc(value)}</span>'
                    f'<span class="k">{esc(key)}</span></div>')
            add("</div>")
            add('<p class="sub" style="margin-top:10px">These are the report\'s own numbers. '
                "They describe what the planner decided, which is not the same claim as what "
                "plays.</p>")
        add("</div>")

    # --- the fix loop ------------------------------------------------------
    add("<h2>The fix loop, run by run</h2>")
    add('<p>Each bar is one iteration of <code>running/xml-fix-loop/loop.sh</code>, as tall as '
        "the tree was red when it started. Nothing in that script asks the model whether it is "
        "finished: it ends on pytest and mypy exiting zero, on the count refusing to fall twice "
        "over, or on the goldens being the only thing red — which is a diff for a person.</p>")
    add('<div class="card">')
    real = [it.red for run in run_list for it in run.iterations if it.red != 999]
    ceiling = max(real) if real else 1
    add('<div class="runs">')
    for run in run_list:
        status, sentence = run.outcome
        add('<div class="run">')
        add('<div class="cols">')
        for it in run.iterations:
            crash = it.red == 999
            height = 132 if crash else max(6, round(132 * it.red / ceiling))
            tip = (f"iteration {it.number} · {it.red} red · {it.when:%d %b %H:%M} · {it.sha}"
                   if not crash else
                   f"iteration {it.number} · 999 — a crash or collection error, not a count · "
                   f"{it.when:%d %b %H:%M}")
            add(f'<div class="col{" crash" if crash else ""}" style="height:{height}px" '
                f'data-tip="{esc(tip)}"></div>')
        add("</div>")
        add(f'<div class="foot"><div class="sub mono">{run.started:%d %b}</div>')
        add(f'<div style="margin:4px 0">{stat_chip(status, sentence)}</div>')
        add(f'<div class="sub">{run.opening_red if run.opening_red != 999 else "999"} → '
            f'{run.closing_red if run.closing_red != 999 else "999"} red, '
            f"{len(run.iterations)} iteration(s)</div></div></div>")
    add("</div>")
    add('<div class="cols-legend sub">'
        f'<span><span class="swatch" style="background:var(--seq-450)"></span> red count '
        f"(scale to {ceiling})</span>"
        '<span><span class="swatch" style="background:repeating-linear-gradient(45deg,'
        'var(--seq-200) 0 3px,var(--surface-2) 3px 6px);'
        'border:1px solid var(--seq-450)"></span> 999 — no failure named</span></div>')
    add('<p class="sub" style="margin:14px 0 0">A commit records the count at the moment '
        "its iteration began, so the state the loop exited on is not in this history — what a "
        "person committed next is.</p>")
    add('<div class="scroll" style="margin-top:10px"><table><thead><tr>'
        '<th>Started</th><th class="num">Iterations</th><th class="num">Red at each start</th>'
        "<th>How it ended</th><th>What a person committed next</th>"
        "</tr></thead><tbody>")
    for run in reversed(run_list):
        status, sentence = run.outcome
        after = "; ".join(subject for _, _, subject in run.after[:2]) or "—"
        add(f'<tr><td class="mono">{run.started:%d %b %H:%M}</td>'
            f'<td class="num">{len(run.iterations)}</td>'
            f'<td class="num">{" · ".join(str(i.red) for i in run.iterations)}</td>'
            f"<td>{stat_chip(status, sentence)}</td>"
            f'<td><span class="sub">{esc(after)}</span></td></tr>')
    add("</tbody></table></div></div>")

    # --- tickets -----------------------------------------------------------
    add("<h2>The work loop</h2>")
    add("<p><code>Status: done</code> means a person confirmed the behaviour with their own "
        "senses. An agent's last act on a ticket is <code>awaiting-listen</code> — it never "
        "writes the verdict, and <code>loop.sh</code> reverts the iteration if it tries.</p>")
    add('<div class="board">')
    for status in STATUS_ORDER[:2]:
        group = [t for t in open_tickets if t.status == status]
        dot = "warning" if status == "awaiting-listen" else "idle"
        add(f'<div class="card"><h3>{stat_chip(dot, f"{status} · {len(group)}")}</h3><ul>')
        for ticket in group:
            blocked = "" if ticket.blocked_by.lower().startswith("none") else \
                f' · blocked by {esc(ticket.blocked_by)}'
            add(f"<li><strong>{esc(ticket.number)}</strong> {esc(ticket.title)}<br>"
                f'<span class="sub mono">{esc(str(ticket.path))}</span>'
                f'<span class="sub"> · {ticket.listen_for} listen-for{blocked}</span></li>')
        add("</ul></div>")
    add(f'<div class="card"><h3>{stat_chip("good", f"closed · {len(closed)}")}</h3><ul>')
    for number, title in closed:
        add(f"<li><strong>{esc(number)}</strong> {esc(title)}</li>")
    add("</ul></div></div>")

    # --- decisions ---------------------------------------------------------
    add("<h2>What the project has decided</h2>")
    add('<div class="card"><div class="scroll"><table><tbody>')
    for number, claim in settled:
        add(f'<tr><td class="num mono" style="width:56px">{esc(number)}</td>'
            f"<td><strong>{esc(claim)}</strong></td></tr>")
    add("</tbody></table></div></div>")

    # --- where things live -------------------------------------------------
    add("<h2>Where things live</h2>")
    add('<div class="card"><div class="scroll"><table><thead><tr><th>Path</th>'
        '<th class="num">Holds</th><th>What it is</th></tr></thead><tbody>')
    where = [
        ("recordings/", n["recordings"], "the recordings and the scripts read from them — input"),
        ("src/roughcut/", n["modules"], "the tool itself"),
        ("tests/", n["tests"], "everything below the seam, driven by hand-written analysis JSON"),
        ("tests/committed/", n["committed"],
         "committed by hand: the import contract, the real analyses, the goldens"),
        ("out/", len(all_runs), "what a run writes — disposable, git-ignored"),
        ("work/rough-cut-assistant/", len(open_tickets), "the live tickets"),
        ("settled/decisions/", len(settled), "what outlives a ticket"),
        ("running/", 4, "for the operator: the Windows bridge, the fix loop, this page"),
    ]
    for path, count, what in where:
        add(f'<tr><td class="mono"><strong>{esc(path)}</strong></td>'
            f'<td class="num">{count}</td><td>{esc(what)}</td></tr>')
    add("</tbody></table></div></div>")

    # --- runs in out/ ------------------------------------------------------
    add("<h2>Cuts kept in out/</h2>")
    add('<div class="card"><div class="scroll"><table><thead><tr><th>Directory</th>'
        "<th>Rendered</th><th>XML</th><th>Report</th><th>Analysis</th>"
        "</tr></thead><tbody>")
    for kept in all_runs:
        here = " ← shown above" if chosen and kept.directory == chosen.directory else ""
        add(f'<tr><td class="mono"><strong>{esc(kept.label)}</strong>'
            f'<span class="sub">{esc(here)}</span></td>'
            f'<td class="mono">{kept.when:%d %b %H:%M}</td>'
            f"<td>{tick(kept.xml)}</td><td>{tick(kept.report)}</td>"
            f"<td>{tick(kept.analysis)}</td></tr>")
    add("</tbody></table></div></div>")

    add("</main>")
    add(f"<script>{JS}</script></body></html>")
    return "\n".join(h)


def main(argv: list[str]) -> int:
    available = runs()
    chosen: Run | None = available[0] if available else None
    if len(argv) > 1:
        wanted = (ROOT / argv[1]).resolve()
        chosen = next((r for r in available if r.directory == wanted), None)
        if chosen is None:
            print(f"no rendered XML under {argv[1]}", file=sys.stderr)
            return 1
    OUT.mkdir(exist_ok=True)
    DASHBOARD.write_text(render(chosen), encoding="utf-8")
    print(f"wrote {DASHBOARD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
