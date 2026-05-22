# ML Retry Compare

## Baseline Oficial
- `MAE = 0.578168`
- `RMSE = 3.665268`
- `MAPE = 80.337892`
- evidencia: `tcc/artifacts/metrics_ml_baseline_2026-04-04_1141.csv`

## OpenAI
- `attempt 1`: erro por desalinhamento entre `y_test/y_pred_test` e `predictions_df`
- `attempt 2`: sucesso
- `MAE = 0.910709`
- `RMSE = 3.556105`
- `MAPE = inf`
- leitura: pior que o baseline em `MAE`, ligeiramente melhor em `RMSE`, e com `MAPE` inutilizavel por divisao sobre zeros.
- evidencias: `tcc/artifacts/metrics_ml_openai_gpt_4o_retry2_2026-04-04_1247.csv`, `tcc/artifacts/ml_run_report_openai_gpt_4o_retry2_2026-04-04_1247.md`

## Llama 3.3 70B Instruct
- `attempt 1`: sucesso apos corrigir imputacao em dataframe misto
- `MAE = 0.010248`
- `RMSE = 0.246974`
- `MAPE = 10562382324701.594`
- leitura: `MAE/RMSE` ficaram dramaticamente melhores que o baseline, mas o `MAPE` explodiu e o desenho do pipeline continua suspeito de vazamento/metodologia fraca (baseline e agregados montados no dataframe inteiro, sem isolamento forte do conjunto de teste).
- evidencias: `tcc/artifacts/metrics_ml_llama_3_3_70b_retry1_2026-04-04_1248.csv`, `tcc/artifacts/ml_run_report_llama_3_3_70b_retry1_2026-04-04_1248.md`

## Conclusao Critica
- agora os dois modelos executam fim a fim apos retry.
- a OpenAI converge com pipeline mais simples e rastreavel, mas nao supera o baseline em `MAE`.
- a Llama apresenta metricas numericas muito fortes em `MAE/RMSE`, porem o resultado e metodologicamente suspeito e nao deve ser aceito sem discussao explicita de possivel vazamento/fragilidade do pipeline.
- para o TCC, a comparacao quantitativa pode ser apresentada, mas com ressalva metodologica forte na Llama e com destaque para o baseline como referencia robusta.

## Evidencia Consolidada
- `tcc/artifacts/ml_retry_log_2026-04-04.csv`
- `tcc/artifacts/ml_retry_compare_2026-04-04.md`
