#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RESUME_FILE="data/resume_d3.txt"
OUT_DIR="data/skill_gap_runs"
MODEL_ARG=""

if [[ ${1:-} == "--model" && -n ${2:-} ]]; then
  MODEL_ARG="$2"
elif [[ -n ${1:-} ]]; then
  MODEL_ARG="$1"
fi

mkdir -p "$OUT_DIR"

if [[ ! -f "$RESUME_FILE" ]]; then
  echo "[Error] Resume not found: $RESUME_FILE"
  exit 1
fi

backup_path="$RESUME_FILE.bak"
cp "$RESUME_FILE" "$backup_path"

non_tech_words=("Experienced" "professional" "leadership" "summary" "education" "champion")
replacements=("Seasoned" "skilled" "mentor" "overview" "training" "winner")

cleanup() {
  if [[ -f "$backup_path" ]]; then
    mv "$backup_path" "$RESUME_FILE"
  fi
}
trap cleanup EXIT

for i in 1 2 3 4 5; do
  idx=$((RANDOM % ${#non_tech_words[@]}))
  from_word="${non_tech_words[$idx]}"
  to_word="${replacements[$idx]}"

  # Replace a single non-technical word occurrence to keep skills intact.
  sed -i "0,/${from_word}/s/${from_word}/${to_word}/" "$RESUME_FILE"

  output_file="$OUT_DIR/run_${i}.txt"
  if [[ -n "$MODEL_ARG" ]]; then
    uv run find_skil_gaps.py "$MODEL_ARG" > "$output_file"
  else
    uv run find_skil_gaps.py > "$output_file"
  fi

  # Trim trailing time/tokens from the output line.
  sed -i -E "s/ time=[0-9.]+ tokens=[0-9]+$//" "$output_file"
  # Remove transient retry/progress lines to keep diffs stable.
  sed -i -E "/^Attempt [0-9]+ failed:/d" "$output_file"
  sed -i -E "/^Retrying in [0-9]+s\.\.\.$/d" "$output_file"

done

echo "Wrote 5 outputs to $OUT_DIR"

baseline="$OUT_DIR/run_1.txt"
if [[ -f "$baseline" ]]; then
  for i in 2 3 4 5; do
    current="$OUT_DIR/run_${i}.txt"
    if [[ ! -f "$current" ]]; then
      echo "[Diff] run_${i}.txt missing"
      continue
    fi
    if diff -q "$baseline" "$current" >/dev/null; then
      echo "[Diff] run_1.txt vs run_${i}.txt: SAME"
    else
      echo "[Diff] run_1.txt vs run_${i}.txt: DIFFERENT"
    fi
  done
else
  echo "[Diff] Baseline run_1.txt missing"
fi
