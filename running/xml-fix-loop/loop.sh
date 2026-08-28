#!/usr/bin/env bash
#
# Runs `claude -p` over src/ until the checks go green, or until it stops making progress.
#
# The point of this script is that nothing here asks the model whether it is finished. The
# loop ends on `pytest` and `mypy` exiting zero, on running out of iterations, or on two
# rounds without the red count going down. See running/xml-fix-loop/prompt.md for what the model
# is told; the two files are meant to be read together.
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

run_checks() {
    : > "$CHECK_LOG"
    uv run pytest -q >>"$CHECK_LOG" 2>&1
    local pytest_status=$?
    uv run mypy >>"$CHECK_LOG" 2>&1
    local mypy_status=$?
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
