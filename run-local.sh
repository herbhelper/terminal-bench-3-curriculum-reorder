#!/bin/bash
# Run a task the way Harbor does, without Harbor: build the environment image,
# then run it twice.
#
#   oracle  — mount solution/ and tests/, run solve.sh, then test.sh. Must pass.
#   null    — mount tests/ only, run test.sh against the untouched repo. Must fail.
#
# A task that does not pass as oracle is not solvable. A task that passes as
# null is not a task.
#
# usage: ./run-local.sh <task-name> [oracle|null|both]
set -euo pipefail

TASK=${1:?usage: run-local.sh <task-name> [oracle|null|both]}
MODE=${2:-both}
ROOT=$(cd "$(dirname "$0")" && pwd)
DIR="$ROOT/tasks/$TASK"
IMAGE="tb3-local/$TASK"

[ -d "$DIR" ] || { echo "no task at $DIR"; exit 1; }

echo "── build ─────────────────────────────────────────────"
docker build -q -t "$IMAGE" "$DIR/environment" >/dev/null
echo "built $IMAGE"

run() {
    local mode=$1 logs
    logs=$(mktemp -d)
    mkdir -p "$logs/verifier"
    local script="/tests/test.sh"
    [ "$mode" = oracle ] && script="/solution/solve.sh && /tests/test.sh"

    echo
    echo "── $mode ────────────────────────────────────────────"
    docker run --rm \
        -v "$DIR/tests:/tests:ro" \
        -v "$DIR/solution:/solution:ro" \
        -v "$logs:/logs" \
        "$IMAGE" bash -c "$script" 2>&1 | tail -40

    local reward
    reward=$(cat "$logs/verifier/reward.txt" 2>/dev/null || echo "-")
    echo "reward($mode) = $reward"
    rm -rf "$logs"

    if [ "$mode" = oracle ] && [ "$reward" != "1" ]; then echo "FAIL: oracle did not solve the task"; return 1; fi
    if [ "$mode" = null ]   && [ "$reward" = "1" ]; then echo "FAIL: the task passes with no agent"; return 1; fi
    return 0
}

case "$MODE" in
    oracle) run oracle ;;
    null)   run null ;;
    both)   run null; run oracle ;;
esac
echo
echo "OK"
