#!/bin/bash
# Run a task the way Harbor runs it in separate-verifier mode, without Harbor.
#
#   1. build the agent environment image and the verifier image
#   2. start an agent container, apply a candidate fix inside it
#   3. copy the declared artifacts out of the agent container
#   4. start the verifier container, mount the artifacts at /app, run test.sh
#
# The verifier never sees the agent's container, only the files task.toml
# declares — the same isolation Harbor enforces.
#
#   oracle  — apply solution/solve.sh. Must score 1.
#   null    — change nothing. Must score 0.
#
# usage: ./run-local.sh <task-name> [oracle|null|both]
set -euo pipefail

TASK=${1:?usage: run-local.sh <task-name> [oracle|null|both]}
MODE=${2:-both}
ROOT=$(cd "$(dirname "$0")" && pwd)
DIR="$ROOT/tasks/$TASK"
ENV_IMAGE="tb3-local/$TASK-env"
VERIFIER_IMAGE="tb3-local/$TASK-verifier"

[ -d "$DIR" ] || { echo "no task at $DIR"; exit 1; }

echo "── build ─────────────────────────────────────────────"
docker build -q -t "$ENV_IMAGE" "$DIR/environment" >/dev/null
docker build -q -t "$VERIFIER_IMAGE" "$DIR/tests" >/dev/null
echo "built $ENV_IMAGE and $VERIFIER_IMAGE"

# Apply a candidate fix inside a fresh agent container and print the host path
# the declared artifacts were copied to.
stage() {
    local apply=$1 work
    work=$(mktemp -d)
    local cid
    cid=$(docker run -d --rm \
        -v "$DIR/solution:/solution:ro" \
        -v "$DIR/adversarial:/adversarial:ro" \
        "$ENV_IMAGE" sleep infinity)
    if [ -n "$apply" ]; then
        docker exec "$cid" bash -c "$apply" >/dev/null
    fi
    docker cp "$cid:/app/curriculum" "$work/curriculum" >/dev/null
    docker kill "$cid" >/dev/null
    echo "$work"
}

verify() {
    local work=$1 logs
    logs=$(mktemp -d); mkdir -p "$logs/verifier"
    docker run --rm \
        -v "$work/curriculum:/app/curriculum" \
        -v "$logs:/logs" \
        "$VERIFIER_IMAGE" bash /tests/test.sh 2>&1 | tail -40 || true
    cat "$logs/verifier/reward.txt" 2>/dev/null || echo "-"
    rm -rf "$logs"
}

run() {
    local mode=$1 apply="" work reward out
    [ "$mode" = oracle ] && apply="/solution/solve.sh"

    echo
    echo "── $mode ────────────────────────────────────────────"
    work=$(stage "$apply")
    out=$(verify "$work")
    reward=$(echo "$out" | tail -1)
    echo "$out" | sed '$d'
    rm -rf "$work"

    echo "reward($mode) = $reward"
    if [ "$mode" = oracle ] && [ "$reward" != "1" ]; then echo "FAIL: oracle did not solve the task"; return 1; fi
    if [ "$mode" = null ]   && [ "$reward" = "1" ]; then echo "FAIL: the task passes with no agent"; return 1; fi
    return 0
}

case "$MODE" in
    oracle) run oracle ;;
    null)   run null ;;
    both)   run null && run oracle ;;
esac
echo
echo "OK"
