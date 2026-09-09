#!/bin/bash
# Adversarial verification.
#
# A task is only as good as its verifier. Passing the oracle proves the task is
# solvable; failing the null agent proves it isn't free. Neither proves the
# grader rejects a solution that is wrong in a way a competent agent would
# actually be wrong.
#
# This runs each variant in adversarial/ through the real verifier and requires
# a reward of 0, then prints the assertions that caught it.
#
# usage: ./verify-traps.sh <task-name>
set -uo pipefail

TASK=${1:?usage: verify-traps.sh <task-name>}
ROOT=$(cd "$(dirname "$0")" && pwd)
DIR="$ROOT/tasks/$TASK"
IMAGE="tb3-local/$TASK"

docker build -q -t "$IMAGE" "$DIR/environment" >/dev/null

fails=0
for variant in "$DIR"/adversarial/*/; do
    name=$(basename "$variant")
    logs=$(mktemp -d); mkdir -p "$logs/verifier"

    out=$(docker run --rm \
        -v "$DIR/tests:/tests:ro" \
        -v "$DIR/solution:/solution:ro" \
        -v "$DIR/adversarial:/adversarial:ro" \
        -v "$logs:/logs" \
        "$IMAGE" bash -c "/adversarial/$name/apply.sh >/dev/null && /tests/test.sh" 2>&1)

    reward=$(cat "$logs/verifier/reward.txt" 2>/dev/null || echo "-")
    caught=$(echo "$out" | grep -E '^FAILED' | sed 's#.*test_state.py::#    caught by: #' | sed 's/ -.*//')
    rm -rf "$logs"

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
