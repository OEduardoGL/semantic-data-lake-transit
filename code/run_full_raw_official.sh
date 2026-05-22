#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="$(cd "${ROOT_DIR}/.." && pwd)"
PY="${PROJECT_DIR}/tcc/code/.venv/bin/python"
SCRIPT="${PROJECT_DIR}/tcc/code/01_bronze_to_silver.py"
OUT_DIR="${PROJECT_DIR}/tcc/artifacts/full_raw_official"
RUN_TS="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "${OUT_DIR}"

SUMMARY="${OUT_DIR}/summary_${RUN_TS}.txt"
echo "run_ts=${RUN_TS}" > "${SUMMARY}"
echo "start_utc=$(date -u +%FT%TZ)" >> "${SUMMARY}"

run_step() {
  local name="$1"
  local flag="$2"
  local log="${OUT_DIR}/${name}_${RUN_TS}.log"
  echo "step=${name} status=started utc=$(date -u +%FT%TZ)" | tee -a "${SUMMARY}"
  /usr/bin/time -p "${PY}" "${SCRIPT}" --preview-n 3 "${flag}" --skip-validations 2>&1 | tee "${log}"
  echo "step=${name} status=finished utc=$(date -u +%FT%TZ) log=${log}" | tee -a "${SUMMARY}"
}

run_step "gps_events" "--write-gps-events"
run_step "stop_events" "--write-stop-events"
run_step "fare_events" "--write-fare-events"
run_step "operational_events" "--write-operational-events"

echo "end_utc=$(date -u +%FT%TZ)" >> "${SUMMARY}"
echo "status=success" >> "${SUMMARY}"
echo "summary=${SUMMARY}"
