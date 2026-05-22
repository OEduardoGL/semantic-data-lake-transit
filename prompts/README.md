# Prompts

Salvar cada versao com data no nome, por exemplo:
- `prompt1_wrangling_2026-02-14_v1.md`
- `prompt_1_wrangling_2026-02-17_v1.md`
- `prompt3_retry_2026-02-14_v1.md`
- `prompt2_ml_2026-02-14_v1.md`

Sempre registrar no topo:
- objetivo
- contexto usado
- constraints
- formato de saida esperado

Prompt de retry atual:
- `prompt_3_retry_wrangling_2026-04-03_v1.md`
- deve sempre receber: codigo anterior + traceback real + resumo do erro + restricoes semanticas

Prompt de retry de ML:
- `prompt_4_retry_ml_2026-04-04_v1.md`
- deve sempre receber: codigo anterior + traceback real + resumo do erro + schema da `final_table` + contrato de saida (`metrics`, `baseline_metrics`, `predictions_df`, `line_hour_metrics_df`, `vehicle_day_metrics_df`)

Prompt de retry de ML (rodada 2):
- `prompt_4_retry_ml_2026-04-18_v2.md`
- deve sempre receber: codigo anterior + traceback real + resumo do erro + schema da `final_table` + horizonte preditivo `t+1` + regras anti-vazamento + metricas revisadas (`MAE`, `RMSE`, `WAPE`)

Prompt de ML atual:
- `prompt_2_ml_2026-04-04_v1.md`
- deve receber schema da `final_table` enriquecida, target fechado, split temporal, baseline e saidas gerenciais obrigatorias

Prompt de ML refinado (rodada 2):
- `prompt_2_ml_2026-04-18_v2.md`
- deve receber schema da `final_table` enriquecida, horizonte preditivo explicito (`t+1`), regras anti-vazamento, metricas revisadas (`MAE`, `RMSE`, `WAPE`) e preservacao de IDs originais nos artefatos finais
