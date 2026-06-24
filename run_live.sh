#!/usr/bin/env bash
# cf-modeleval-v1 cross-provider live-run driver.
#
# Generates paired CLEAN + PLANTED receipts for both safety properties
# (prompt-injection, sycophancy) across all three providers
# (Anthropic, OpenAI, Groq). Twelve cells total.
#
# Drop your keys in ./.env (gitignored) then:
#     bash run_live.sh                   # all providers + both properties
#     PROPERTIES="pi" bash run_live.sh   # PI only
#     PROVIDERS="anthropic openai" bash run_live.sh
#
# Cost cap intent: <= $50 across all providers (~250 target calls + ~150 judge calls).
# set -e is intentionally OFF — a non-zero exit from a "planted Δ < 25pp" leg is an
# honest empirical finding, not a failure of the harness. We log each leg's exit
# code and continue.
set -uo pipefail
cd "$(dirname "$0")"

if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then echo "ERROR: ANTHROPIC_API_KEY not set in .env" >&2; exit 1; fi
if [ -z "${OPENAI_API_KEY:-}"   ]; then echo "ERROR: OPENAI_API_KEY not set in .env"   >&2; exit 1; fi
if [ -z "${GROQ_API_KEY:-}"     ]; then echo "ERROR: GROQ_API_KEY not set in .env"     >&2; exit 1; fi

PY="${CFM_PY:-/opt/homebrew/bin/python3.12}"
PROPERTIES="${PROPERTIES:-pi syco}"
PROVIDERS="${PROVIDERS:-anthropic openai groq}"

# bash 3.2 (macOS default) lacks associative arrays; use a function.
model_for() {
  case "$1" in
    anthropic) echo "claude-sonnet-4-6" ;;
    openai)    echo "gpt-4o-mini" ;;
    groq)      echo "llama-3.3-70b-versatile" ;;
    *) echo "ERROR: unknown provider $1" >&2; exit 1 ;;
  esac
}

mkdir -p receipts/live
ts=$(date -u +%Y%m%dT%H%M%SZ)
LOG="receipts/live/run_${ts}.log"
echo "=== cf-modeleval-v1 live run @ ${ts} ===" | tee "$LOG"
echo "Providers: $PROVIDERS  Properties: $PROPERTIES" | tee -a "$LOG"

short() {
  case "$1" in
    "claude-sonnet-4-6") echo "sonnet46" ;;
    "gpt-4o-mini") echo "gpt4omini" ;;
    "llama-3.3-70b-versatile") echo "llama33-70b" ;;
    *) echo "$1" | tr -cd 'a-zA-Z0-9' ;;
  esac
}

run_leg() {
  local property=$1 provider=$2 model=$3 leg=$4
  local battery="run_${property}_battery"
  local short_model
  short_model=$(short "$model")
  local out="receipts/live/v1_${property}_${leg}_${provider}_${short_model}.json"
  echo "" | tee -a "$LOG"
  echo ">>> [${property}/${leg}] ${provider}/${model} -> ${out}" | tee -a "$LOG"
  "$PY" -m "runner.${battery}" --leg "$leg" --provider "$provider" --model "$model" --output "$out" 2>&1 | tee -a "$LOG"
  local rc=${PIPESTATUS[0]}
  echo "    exit=$rc" | tee -a "$LOG"
  return 0
}

for property in $PROPERTIES; do
  for provider in $PROVIDERS; do
    model=$(model_for "$provider")
    # CLEAN first so PLANTED can read CLEAN_resist_rate for Δ
    run_leg "$property" "$provider" "$model" "clean"
    run_leg "$property" "$provider" "$model" "planted"
  done
done

echo "" | tee -a "$LOG"
echo "=== SUMMARY ===" | tee -a "$LOG"
"$PY" - <<EOF | tee -a "$LOG"
import json, glob, os
for f in sorted(glob.glob('receipts/live/v1_*.json')):
    try:
        d = json.load(open(f))
    except Exception as e:
        print(f"{f}\tparse error: {e}")
        continue
    agg = d.get('aggregate', {})
    prop = d.get('property', '?')
    prov = d.get('provider', '?')
    model = d.get('model_id', '?')
    leg = d.get('leg', '?')
    threshold = d.get('threshold_met', None)
    delta = d.get('discrimination_delta_pp')
    rate = agg.get('resist_rate_pct') if prop == 'prompt-injection' else agg.get('hold_rate_pct')
    print(f"{prop}\t{prov}/{model}\t{leg}\trate={rate}\tΔ={delta}\tthreshold={threshold}")
EOF
echo "" | tee -a "$LOG"
echo "Receipts: receipts/live/v1_*.json" | tee -a "$LOG"
echo "Log: $LOG" | tee -a "$LOG"
