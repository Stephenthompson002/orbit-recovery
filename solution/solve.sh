#!/usr/bin/env bash
set -eu

solution_dir="$(cd "$(dirname "$0")" && pwd)"
cp "$solution_dir/checkpoint.py" /workspace/orbit_recovery/checkpoint.py
