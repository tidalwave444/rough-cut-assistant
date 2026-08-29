#!/usr/bin/env bash
#
# Runs `claude -p` over src/ until the checks go green, or until it stops making progress.
#
# The point of this script is that nothing here asks the model whether it is finished. The
# loop ends on `pytest` and `mypy` exiting zero, on running out of iterations, on two rounds
# without the red count going down, or on the goldens being the only thing red — which is a
# diff for a human and exits 2. See running/xml-fix-loop/prompt.md for what the model is
# told; the two files are meant to be read together.
#
#   running/xml-fix-loop/loop.sh              # up to 8 iterations
#   MAX_ITERATIONS=3 running/xml-fix-loop/loop.sh
#
set -uo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1

MAX_ITERATIONS=${MAX_ITERATIONS:-8}
STALL_LIMIT=${STALL_LIMIT:-2}
PROMPT=running/xml-fix-loop/prompt.md
CHECK_LOG=out/check.txt

# Everything the model may not touch. src/ is what is left, and that is deliberate: the
# checks are the contract, and a contract the other party can edit is not one.
PROTECTED=(tests settled recordings running work)

# Narrow this if you want a tighter cage, e.g. --allowed-tools Read Edit Bash Grep Glob.
CLAUDE_FLAGS=(--permission-mode acceptEdits)

say() { printf '\n== %s\n' "$*"; }

# Both checks colour their output when the environment tells them to, and they do it
# writing to a file as readily as to a terminal — FORCE_COLOR is set inside a Claude Code
# shell, which is where this loop is usually started from. Every grep below is anchored to
# the start of a line, so one escape sequence in front of FAILED scores a red run as no
# failures at all, which red_count then reads as 999. A finished run stalls on its own
# success. Asked not to colour, and stripped anyway, because the asking is per-tool and
# the stripping is not.
UNCOLOURED=(env -u FORCE_COLOR -u MYPY_FORCE_COLOR NO_COLOR=1 PY_COLORS=0)

strip_colour() {
    sed -i 's/\x1b\[[0-9;]*[a-zA-Z]//g; s/\x1b[()][A-Za-z]//g' "$CHECK_LOG"
}

run_checks() {
    : > "$CHECK_LOG"
    "${UNCOLOURED[@]}" uv run pytest -q >>"$CHECK_LOG" 2>&1
    local pytest_status=$?
    "${UNCOLOURED[@]}" uv run mypy >>"$CHECK_LOG" 2>&1
    local mypy_status=$?
    strip_colour
    [ $pytest_status -eq 0 ] && [ $mypy_status -eq 0 ]
}

# How red the tree is: failing tests plus type errors. Only ever compared with itself, so
# the mix of the two units does not matter — what matters is that it falls.
red_count() {
    local failed errors total
    failed=$(grep -c '^FAILED' "$CHECK_LOG")
    errors=$(grep -cE '^[^ ]+\.py:[0-9]+: error:' "$CHECK_LOG")
    total=$((failed + errors))
    # A crash or a collection error is red without naming a single failure. Scoring that as
    # zero would read as a clean sweep and stop the loop on the worst state it can reach.
    [ "$total" -eq 0 ] && total=999
    echo "$total"
}

# The goldens are the rendered cut, and they are locked like the rest of tests/. A change
# that is genuinely meant to move them therefore cannot go green here, and left alone the
# loop would spend its whole stall budget discovering that. Stop on the spot instead: a
# golden diff is meant to be read, and reading it is the one thing a loop cannot do.
only_the_goldens_are_red() {
    grep -qE '^[^ ]+\.py:[0-9]+: error:' "$CHECK_LOG" && return 1
    local failed
    failed=$(grep '^FAILED' "$CHECK_LOG")
    [ -n "$failed" ] || return 1
    [ -z "$(grep -v '^FAILED tests/test_golden\.py::' <<<"$failed")" ]
}

protected_edits() { git diff --name-only -- "${PROTECTED[@]}"; }
protected_additions() { git ls-files --others --exclude-standard -- "${PROTECTED[@]}"; }

require_clean_tree() {
    [ -z "$(git status --porcelain)" ] && return 0
    say "the tree is dirty — commit or stash first, the loop commits after every iteration"
    git status --short
    exit 1
}

mkdir -p out
require_clean_tree

previous=999999
stall=0
iteration=0

for ((iteration = 1; iteration <= MAX_ITERATIONS; iteration++)); do
    if run_checks; then
        say "green after $((iteration - 1)) iteration(s)"
        exit 0
    fi

    current=$(red_count)
    say "iteration $iteration/$MAX_ITERATIONS — $current red"
    tail -n 20 "$CHECK_LOG"

    if only_the_goldens_are_red; then
        say "the cut's output moved and nothing else is red — that is a diff, not a defect"
        echo "Read what moved, and accept it yourself if it is what you meant:"
        echo "    uv run pytest tests/test_golden.py   # the failure names the lines"
        echo "    uv run pytest --update-golden        # then read git diff, and commit it"
        echo "Re-run this loop afterwards to confirm the rest is still green."
        exit 2
    fi

    if [ "$current" -ge "$previous" ]; then
        stall=$((stall + 1))
    else
        stall=0
    fi
    if [ "$stall" -ge "$STALL_LIMIT" ]; then
        say "no progress in $STALL_LIMIT iterations, still $current red — stopping"
        echo "Hand it to a second implementer rather than spending more turns here:"
        echo "open a session and give the same prompt to the codex:codex-rescue agent."
        exit 1
    fi
    previous=$current

    claude -p "$(cat "$PROMPT")

## The checks that are red right now

\`\`\`
$(tail -n 60 "$CHECK_LOG")
\`\`\`
" "${CLAUDE_FLAGS[@]}"

    if [ -n "$(protected_additions)" ]; then
        say "new files under a locked path — stopping rather than deleting them"
        protected_additions
        exit 1
    fi
    if [ -n "$(protected_edits)" ]; then
        say "locked paths were edited — reverting them, the iteration is spent"
        protected_edits
        git checkout -- "${PROTECTED[@]}"
    fi

    git add -A
    git commit -qm "xml fix loop, iteration $iteration (was $current red)" --allow-empty
done

if run_checks; then
    say "green after $MAX_ITERATIONS iteration(s)"
    exit 0
fi
say "out of iterations, still $(red_count) red"
tail -n 20 "$CHECK_LOG"
exit 1
