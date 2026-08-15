#!/usr/bin/env bash
# Writes a small themed banner to $GITHUB_STEP_SUMMARY after a CI job's tests
# pass. Purely cosmetic - never affects job success/failure.
set -euo pipefail

job_label="${1:?usage: forge-summary.sh <job-label>}"

quotes=(
  "The anvil doesn't complain."
  "Cold iron never built anything."
  "Strike while the template's hot."
  "No shortcuts, just good steel."
  "A well-forged project needs no polish."
  "Measure twice, generate once."
  "The hammer doesn't ask why, it just forges."
)

quote="${quotes[$RANDOM % ${#quotes[@]}]}"

{
  echo '```'
  echo '    ⚒️  FORGE'
  echo '   ╔═══════╗'
  echo '   ║ ▓▓▓▓▓ ║'
  echo '   ╚═══════╝'
  echo '```'
  echo ""
  echo "\"${quote}\" — ${job_label} forged clean."
} >> "$GITHUB_STEP_SUMMARY"
