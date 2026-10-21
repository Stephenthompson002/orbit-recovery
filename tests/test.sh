#!/usr/bin/env bash
set -u

mkdir -p /logs/verifier
printf '0' > /logs/verifier/reward.txt

python -m unittest discover -s /tests -p 'test_*.py' -v
status=$?

if [ "$status" -eq 0 ]; then
    printf '1' > /logs/verifier/reward.txt
fi

exit 0
