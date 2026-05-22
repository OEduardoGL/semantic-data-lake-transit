#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="$(cd "${ROOT_DIR}/.." && pwd)"
PY="${PROJECT_DIR}/tcc/code/.venv/bin/python"
ARTIFACTS_DIR="${PROJECT_DIR}/tcc/artifacts"
REPRO_DIR="${ARTIFACTS_DIR}/repro_sample_1gb"
RUN_TS="$(date +%Y-%m-%d_%H%M%S)"
RUN_DIR="${REPRO_DIR}/${RUN_TS}"
CONFIG_PATH="${RUN_DIR}/config_sample_1gb.yaml"
LOG_PATH="${RUN_DIR}/run.log"
SUMMARY_PATH="${RUN_DIR}/summary.md"
SILVER_BASE="${RUN_DIR}/silver"
GOLD_BASE="${RUN_DIR}/gold"
MART_BASE="${RUN_DIR}/mart"
INPUT_PATH="${PROJECT_DIR}/messages_fortaleza_1gb.json"
MODEL_FILE="${PROJECT_DIR}/tcc/code/generated/ml_retry_openrouter_meta_llama_llama_3_3_70b_instruct_attempt2_2026-04-18_1922.py"
MODEL_LABEL="llama_3_3_70b_v2_retry2_sample1gb"

mkdir -p "${RUN_DIR}"

cat <<HDR | tee "${SUMMARY_PATH}" > /dev/null
# Reproducibility Run - Sample 1GB
- run_ts: ${RUN_TS}
- input_path: ${INPUT_PATH}
- model_file: ${MODEL_FILE}
- model_label: ${MODEL_LABEL}
HDR

"${PY}" - <<PYCFG
from pathlib import Path
import yaml
base_cfg = yaml.safe_load(Path('${PROJECT_DIR}/tcc/code/config.yaml').read_text(encoding='utf-8'))
base_cfg['paths']['bronze_input'] = '${INPUT_PATH}'
base_cfg['paths']['silver_base'] = '${SILVER_BASE}'
base_cfg['paths']['gold_base'] = '${GOLD_BASE}'
base_cfg['paths']['mart_base'] = '${MART_BASE}'
Path('${CONFIG_PATH}').write_text(yaml.safe_dump(base_cfg, sort_keys=False, allow_unicode=False), encoding='utf-8')
print('${CONFIG_PATH}')
PYCFG

run_step() {
  local name="$1"
  shift
  echo -e "\n## ${name}" | tee -a "${SUMMARY_PATH}" >> "${LOG_PATH}"
  echo "[INFO] ${name}" | tee -a "${LOG_PATH}"
  "$@" 2>&1 | tee -a "${LOG_PATH}"
}

run_step "Bronze to Silver (sample 1GB)" \
  "${PY}" "${PROJECT_DIR}/tcc/code/01_bronze_to_silver.py" \
  --config "${CONFIG_PATH}" \
  --preview-n 2 \
  --write-gps-events \
  --write-stop-events \
  --write-fare-events \
  --write-operational-events

run_step "Materialize FinalTable" \
  "${PY}" "${PROJECT_DIR}/tcc/code/06_materialize_final_table.py" \
  --config "${CONFIG_PATH}" \
  --output-path "${GOLD_BASE}/final_table"

run_step "Baseline ML" \
  "${PY}" "${PROJECT_DIR}/tcc/code/09_run_baseline.py" \
  --config "${CONFIG_PATH}" \
  --input-path "${GOLD_BASE}/final_table"

run_step "LLM ML Pipeline" \
  "${PY}" "${PROJECT_DIR}/tcc/code/10_run_ml_pipeline.py" \
  --config "${CONFIG_PATH}" \
  --model-file "${MODEL_FILE}" \
  --model-label "${MODEL_LABEL}" \
  --input-path "${GOLD_BASE}/final_table"

BASELINE_PRED="$(ls -t "${ARTIFACTS_DIR}"/predictions_baseline_*.csv | head -n1)"
MODEL_PRED="$(ls -t "${ARTIFACTS_DIR}"/predictions_${MODEL_LABEL}_*.csv | head -n1)"
MODEL_LINE="$(ls -t "${ARTIFACTS_DIR}"/neo4j_metrics_line_hour_${MODEL_LABEL}_*.csv | head -n1)"
MODEL_VEHICLE="$(ls -t "${ARTIFACTS_DIR}"/neo4j_metrics_vehicle_day_${MODEL_LABEL}_*.csv | head -n1)"

run_step "Decision Aggregates" \
  "${PY}" "${PROJECT_DIR}/tcc/code/12_generate_decision_aggregates.py" \
  --baseline-predictions "${BASELINE_PRED}" \
  --model-name "${MODEL_LABEL}" \
  --model-predictions "${MODEL_PRED}" \
  --model-line-hour "${MODEL_LINE}" \
  --model-vehicle-day "${MODEL_VEHICLE}" \
  --min-line-records 3 \
  --min-line-hour-records 2 \
  --min-segment-records 1 \
  --min-vehicle-records 3

cat <<EOF2 >> "${SUMMARY_PATH}"

## Output references
- config: ${CONFIG_PATH}
- silver_base: ${SILVER_BASE}
- gold_base: ${GOLD_BASE}
- mart_base: ${MART_BASE}
- baseline_predictions: ${BASELINE_PRED}
- model_predictions: ${MODEL_PRED}
- model_line_hour: ${MODEL_LINE}
- model_vehicle_day: ${MODEL_VEHICLE}
- log: ${LOG_PATH}
EOF2

echo "[OK] Sample 1GB reproducibility run finished."
echo "summary=${SUMMARY_PATH}"
