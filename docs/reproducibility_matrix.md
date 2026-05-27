# Matriz de Reprodutibilidade

## Objetivo
Consolidar, por etapa, o vínculo entre:
- script executado;
- evidência gerada;
- evidência pública de rastreabilidade.

## Matriz principal

### Perfilamento bruto
- script / base:
  - análise exploratória documentada a partir do bruto oficial
- evidências:
  - `artifacts/dq_profile_raw40gb_2026-02-14.md`
- rastreabilidade:
  - evidências públicas listadas nesta seção

### Bronze -> Silver
- script:
  - `code/01_bronze_to_silver.py`
  - `code/run_full_raw_official.sh`
- evidências:
  - validações selecionadas em `artifacts/`
  - tabelas Silver em `s3a://transport/silver`
- rastreabilidade:
  - evidências públicas listadas nesta seção

### Qualidade Silver
- script:
  - `code/dq_silver_checks.py`
- evidências:
  - `artifacts/dq_silver_report_2026-02-16.csv`
  - relatórios complementares documentados em `docs/`
- rastreabilidade:
  - evidências públicas listadas nesta seção

### Modelo semântico e Neo4j semântico
- script:
  - `code/02_build_semantic_model.py`
- evidências:
  - `figures/neo4j_semantic_summary_2026-02-17.png`
  - `artifacts/neo4j_block_b_validation_2026-02-17.txt`
  - `artifacts/neo4j_graph_validation_2026-02-17.txt`
- rastreabilidade:
  - evidências públicas listadas nesta seção

### Wrangling com LLM
- scripts:
  - `code/03_prompt_wrangling.py`
  - `code/04_run_wrangling.py`
  - `code/05_retry_wrangling.py`
- evidências:
  - prompts renderizados em `artifacts/prompt_1_*`
  - código gerado em `code/generated/wrangling_*`
  - comparativos e retries em `artifacts/wrangling_*`
- rastreabilidade:
  - evidências públicas listadas nesta seção

### FinalTable / Gold
- script:
  - `code/06_materialize_final_table.py`
- evidências:
  - `artifacts/final_table_validation_2026-04-03_2243.md`
  - `data/final_table_sample.csv`
  - `docs/final_table_enrichment.md`
- rastreabilidade:
  - evidências públicas listadas nesta seção

### ML rodada 1
- scripts:
  - `code/07_prompt_ml.py`
  - `code/08_run_ml_codegen.py`
  - `code/09_run_baseline.py`
  - `code/10_run_ml_pipeline.py`
  - `code/11_retry_ml.py`
- evidências:
  - `artifacts/metrics_ml_baseline_2026-04-04_1141.csv`
  - `artifacts/ml_retry_compare_2026-04-04.md`
- rastreabilidade:
  - evidências públicas listadas nesta seção

### ML rodada 2 (referência principal)
- scripts:
  - `code/07_prompt_ml.py`
  - `code/08_run_ml_codegen.py`
  - `code/09_run_baseline.py`
  - `code/10_run_ml_pipeline.py`
  - `code/11_retry_ml.py`
- evidências:
  - `artifacts/metrics_ml_baseline_2026-04-18_1904.csv`
  - `artifacts/metrics_ml_llama_3_3_70b_v2_retry2_2026-04-18_1924.csv`
  - `artifacts/ml_round_comparison_2026-04-18.md`
  - `artifacts/ml_run_error_openai_gpt_4o_v2_2026-04-18_1905.md`
  - `artifacts/ml_run_error_openai_gpt_4o_v2_retry1_2026-04-18_1920.md`
  - `artifacts/ml_run_error_openai_gpt_4o_v2_retry2_2026-04-18_1935.md`
  - `artifacts/ml_run_error_llama_3_3_70b_v2_2026-04-18_1906.md`
  - `artifacts/ml_run_error_llama_3_3_70b_v2_retry1_2026-04-18_1921.md`
- rastreabilidade:
  - evidências públicas listadas nesta seção

### Agregados finais
- script:
  - `code/12_generate_decision_aggregates.py`
- evidências:
  - `artifacts/aggregate_source_contract_2026-04-18.md`
  - `artifacts/decision_aggregates_report_2026-04-18_2044.md`
  - `artifacts/decision_aggregates_comparison_2026-04-18.md`
  - `artifacts/neo4j_package_manifest_2026-04-18_2044.csv`
- rastreabilidade:
  - evidências públicas listadas nesta seção

### Neo4j final
- script:
  - `code/13_publish_neo4j.py`
- evidências:
  - `artifacts/neo4j_final_queries_2026-04-18.md`
  - `artifacts/neo4j_final_validation_2026-04-18.md`
  - `figures/neo4j_graph_overview_2026-04-19.png`
  - `figures/neo4j_graph_critical_segment_2026-04-19.png`
  - `figures/neo4j_graph_interactive_expansion_2026-04-20.png`
- rastreabilidade:
  - evidências públicas listadas nesta seção

## Prompts versionados
- wrangling:
  - `prompts/prompt_1_wrangling_2026-02-17_v1.md`
- ML:
  - `prompts/prompt_2_ml_2026-04-04_v1.md`
  - `prompts/prompt_2_ml_2026-04-18_v2.md`
- retry wrangling:
  - `prompts/prompt_3_retry_wrangling_2026-04-03_v1.md`
- retry ML:
  - `prompts/prompt_4_retry_ml_2026-04-04_v1.md`
  - `prompts/prompt_4_retry_ml_2026-04-18_v2.md`

## Decisão adotada
- usar a rodada 2 como referência metodológica principal;
- manter a rodada 1 como diagnóstico histórico do problema;
- usar sempre a matriz acima para localizar rapidamente script e evidências públicas de cada etapa.
