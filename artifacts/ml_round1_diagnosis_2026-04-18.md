# Diagnostico da Rodada 1 de ML

## Escopo
- objetivo: documentar as principais fragilidades metodologicas observadas na primeira rodada de ML antes de iniciar a `11.2) REFINAMENTO METODOLOGICO (ML V2)`.
- artefatos analisados:
  - `tcc/artifacts/metrics_ml_baseline_2026-04-04_1141.csv`
  - `tcc/artifacts/metrics_ml_openai_gpt_4o_retry2_2026-04-04_1247.csv`
  - `tcc/artifacts/metrics_ml_llama_3_3_70b_retry1_2026-04-04_1248.csv`
  - `tcc/artifacts/predictions_baseline_2026-04-04_1141.csv`
  - `tcc/artifacts/predictions_openai_gpt_4o_retry2_2026-04-04_1247.csv`
  - `tcc/artifacts/predictions_llama_3_3_70b_retry1_2026-04-04_1248.csv`
  - `tcc/code/generated/ml_retry_openai_gpt_4o_attempt2_2026-04-04_1246.py`
  - `tcc/code/generated/ml_retry_openrouter_meta_llama_llama_3_3_70b_instruct_attempt1_2026-04-04_1248.py`
  - `tcc/code/09_run_baseline.py`

## Perfil do target no teste
- a distribuicao do target nos arquivos de previsao da rodada 1 e fortemente concentrada perto de zero:
  - baseline oficial: `32375 / 56195` linhas com `y_true = 0` (`57.6119%`)
  - OpenAI: `32372 / 56196` linhas com `y_true = 0` (`57.6055%`)
  - Llama: `32395 / 56265` linhas com `y_true = 0` (`57.5758%`)
- alem dos zeros exatos, entre `79.2%` e `79.4%` das linhas de teste possuem `|y_true| <= 0.1` minuto.
- implicacao direta:
  - metricas percentuais baseadas em divisao por `y_true` ficam instaveis ou deixam de ser interpretaveis neste problema.

## Por que o `MAPE` nao funcionou
- o baseline oficial em `tcc/code/09_run_baseline.py` ja usa uma variante protegida (`safe_mape`) para evitar divisao por zero. Mesmo assim, o baseline oficial ainda produziu `MAPE = 80.337892`, valor de interpretacao limitada diante da massa concentrada em zero.
- os pipelines gerados pelas LLMs usaram formas diretas de erro percentual:
  - OpenAI: `np.mean(np.abs((y_test - y_pred_test) / y_test)) * 100`
  - Llama: `mean_absolute_percentage_error(y_test, y_pred)`
- consequencia observada:
  - OpenAI: `MAPE = inf`
  - Llama: `MAPE = 10562382324701.594`
- diagnostico:
  - `MAPE` nao deve ser metrica principal neste target, porque o target tem muitos zeros e muitos valores muito pequenos.
  - a rodada 2 deve substituir `MAPE` por uma metrica mais estavel, como `WAPE`, mantendo `MAE` e `RMSE`.

## Diagnostico da OpenAI
- arquivo analisado:
  - `tcc/code/generated/ml_retry_openai_gpt_4o_attempt2_2026-04-04_1246.py`
- metricas finais:
  - `MAE = 0.910709`
  - `RMSE = 3.556105`
  - `MAPE = inf`
- modelo escolhido:
  - `LinearRegression`
- features utilizadas:
  - `cod_linha`
  - `cod_veiculo`
  - `hour`
  - `minute`
  - `day_of_week`
- fragilidades principais:
  - o modelo e simples demais para o problema.
  - `cod_linha` e `cod_veiculo` foram tratados como variaveis numericas comuns, o que e uma representacao fraca para identificadores.
  - o pipeline ignorou quase todo o contexto operacional disponivel na `final_table` enriquecida, como `id_empresa`, `viagem_sentido`, `velocidade_media`, `gps_invalid_pct`, `qtd_eventos_gps`, `qtd_eventos_stop`, `max_satelites` e `headway_referencia_min`.
  - o baseline interno desse codigo foi calculado sobre o dataframe completo antes do split temporal, o que enfraquece a comparacao interna.
- interpretacao:
  - caso tipico de underfitting.
  - a OpenAI gerou um pipeline mais rastreavel do que a Llama, mas com modelo e conjunto de features fracos demais para capturar o comportamento do atraso.

## Diagnostico da Llama
- arquivo analisado:
  - `tcc/code/generated/ml_retry_openrouter_meta_llama_llama_3_3_70b_instruct_attempt1_2026-04-04_1248.py`
- metricas finais:
  - `MAE = 0.010248`
  - `RMSE = 0.246974`
  - `MAPE = 10562382324701.594`
- modelo escolhido:
  - `RandomForestRegressor`
- estrategia de features:
  - `X = df_final.drop(['atraso_aproximado_min', 'event_dt', 'janela_5min'], axis=1)`
- fragilidades principais:
  - o modelo usou praticamente todas as colunas remanescentes como entrada.
  - isso inclui colunas muito proximas da propria definicao do target.
  - na `final_table` enriquecida, o target e definido como `max(0, headway_observado_min - headway_referencia_min)`.
  - como `headway_observado_min` e `headway_referencia_min` permaneceram em `X`, o modelo recebeu informacao que praticamente reconstrui o target.
  - `cod_linha`, `cod_veiculo` e `viagem_sentido` foram recodificados com `LabelEncoder` no dataframe completo, o que reduz interpretabilidade e depois atrapalhou a publicacao gerencial.
  - o baseline interno tambem foi calculado sobre o dataframe completo antes do split.
  - os agregados gerenciais `line_hour_metrics_df` e `vehicle_day_metrics_df` foram produzidos sobre o dataframe inteiro, e nao estritamente sobre o conjunto de teste previsto.
- interpretacao:
  - o resultado numerico e forte demais para ser aceito sem ressalva.
  - a explicacao mais provavel e vazamento ou trivializacao da tarefa, nao superioridade confiavel do modelo.

## Por que o baseline oficial continua sendo a referencia principal
- arquivo analisado:
  - `tcc/code/09_run_baseline.py`
- pontos metodologicos positivos:
  - split temporal explicito `70/15/15`
  - agregacoes do baseline calculadas somente no treino
  - fallback de `linha + hora` para `linha` e depois para baseline global
- interpretacao:
  - mesmo com os modelos gerados por LLM executando ponta a ponta apos retry, o baseline oficial continua sendo a referencia quantitativa mais defensavel da rodada 1.

## Implicacoes para a rodada 2
- retirar `MAPE` do centro da avaliacao.
- adotar conjunto de metricas revisado, com foco em `MAE`, `RMSE` e uma metrica percentual robusta a zeros (`WAPE`).
- definir politica explicita de features permitidas e proibidas para evitar vazamento.
- definir horizonte preditivo de forma explicita, em vez de deixar a tarefa ambigua entre estimacao contemporanea e previsao.
- pedir modelos e features mais fortes do que a regressao linear, mas sem permitir colunas que praticamente definem o target.
