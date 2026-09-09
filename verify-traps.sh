#!/bin/bash
# Adversarial verification.
#
# A task is only as good as its verifier. Passing the oracle proves the task is
# solvable; failing the null agent proves it isn't free. Neither proves the
# grader rejects a solution that is wrong in a way a competent agent would
# actually be wrong.
#
# Each variant in adversarial/ is a complete working implementation applied
# inside the agent container. The declared artifacts are then copied out and
# graded by the real verifier image, exactly as in run-local.sh. Each must
# score 0.
#
# usage: ./verify-traps.sh <task-name>
set -uo pipefail

TASK=${1:?usage: verify-traps.sh <task-name>}
ROOT=$(cd "$(dirname "$0")" && pwd)
DIR="$ROOT/tasks/$TASK"
ENV_IMAGE="tb3-local/$TASK-env"
VERIFIER_IMAGE="tb3-local/$TASK-verifier"

docker build -q -t "$ENV_IMAGE" "$DIR/environment" >/dev/null
docker build -q -t "$VERIFIER_IMAGE" "$DIR/tests" >/dev/null

fails=0
for variant in "$DIR"/adversarial/*/; do
    name=$(basename "$variant")
    work=$(mktemp -d); logs=$(mktemp -d); mkdir -p "$logs/verifier"

    cid=$(docker run -d --rm \
        -v "$DIR/solution:/solution:ro" \
        -v "$DIR/adversarial:/adversarial:ro" \
        "$ENV_IMAGE" sleep infinity)
    docker exec "$cid" bash "/adversarial/$name/apply.sh" >/dev/null
    docker cp "$cid:/app/curriculum" "$work/curriculum" >/dev/null
    docker kill "$cid" >/dev/null

    out=$(docker run --rm \
        -v "$work/curriculum:/app/curriculum" \
        -v "$logs:/logs" \
        "$VERIFIER_IMAGE" bash /tests/test.sh 2>&1)

    reward=$(cat "$logs/verifier/reward.txt" 2>/dev/null || echo "-")
    caught=$(echo "$out" | grep -E '^FAILED' | sed 's#.*test_state.py::#    caught by: #' | sed 's/ -.*//')
    rm -rf "$work" "$logs"

    if [ "$reward" = "0" ]; then
        echo "REJECTED  $name  (reward 0)"
        echo "$caught"
    else
        echo "ESCAPED   $name  (reward $reward)  <-- the verifier let a wrong fix through"
        fails=$((fails + 1))
    fi
    echo
done

if [ "$fails" -ne 0 ]; then echo "$fails variant(s) escaped the verifier"; exit 1; fi
echo "all adversarial variants rejected"
