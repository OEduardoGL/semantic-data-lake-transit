# Prompt 4 - Retry de ML Orientado por Erro Real (v2)

## Objetivo
Corrigir codigo Python de pipeline de ML previamente gerado por LLM, usando erro real de execucao sobre a `final_table` enriquecida, agora no contexto metodologico da rodada 2.

## Contexto
O pipeline recebe um `pandas.DataFrame` chamado `df_final` contendo a `final_table` materializada em `s3a://transport/gold/final_table`.

Colunas relevantes da `final_table`:
- `event_dt`
- `janela_5min`
- `cod_linha`
- `cod_veiculo`
- `id_empresa`
- `viagem_sentido`
- `latitude_media`
- `longitude_media`
- `velocidade_media`
- `gps_invalid_pct`
- `qtd_eventos_gps`
- `qtd_eventos_stop`
- `max_satelites`
- `headway_observado_min`
- `headway_referencia_min`
- `atraso_aproximado_min`

## Regras metodologicas obrigatorias desta versao
- o target semantico continua sendo `atraso_aproximado_min`;
- o pipeline deve prever o target da **proxima `janela_5min` disponivel** para o mesmo `cod_linha + cod_veiculo`;
- o split deve ser temporal, sem `shuffle`;
- baseline, imputacao, codificacao e quaisquer agregados auxiliares devem ser ajustados somente no treino;
- nao usar como feature contemporanea da linha-alvo:
  - `atraso_aproximado_min`
  - `headway_observado_min`
  - qualquer derivacao direta dessas colunas na mesma linha do target;
- preservar `cod_linha` e `cod_veiculo` originais nos artefatos finais.

## Contrato de saida obrigatorio
Retorne apenas codigo Python executavel.

O modulo corrigido deve expor exatamente:
- `run_ml_pipeline(df_final)`

A funcao deve retornar um `dict` com:
- `metrics`
- `baseline_metrics`
- `predictions_df`
- `line_hour_metrics_df`
- `vehicle_day_metrics_df`

### Metricas obrigatorias
`metrics` e `baseline_metrics` devem conter obrigatoriamente:
- `mae`
- `rmse`
- `wape`

Opcionalmente podem conter:
- `medae`
- `mape_secondary`

### Estrutura dos DataFrames obrigatorios
- `predictions_df` deve conter pelo menos:
  - `event_dt`
  - `janela_5min`
  - `cod_linha`
  - `cod_veiculo`
  - `y_true`
  - `y_pred`
- `line_hour_metrics_df` deve conter pelo menos:
  - `cod_linha`
  - `faixa_horaria`
  - `avg_pred_atraso_aproximado_min`
  - `avg_real_atraso_aproximado_min`
  - `n_registros`
- `vehicle_day_metrics_df` deve conter pelo menos:
  - `event_dt`
  - `cod_veiculo`
  - `avg_pred_atraso_aproximado_min`
  - `avg_real_atraso_aproximado_min`
  - `n_registros`

## Requisitos adicionais
- nao usar o dataframe inteiro para construir artefatos de teste;
- evitar desalinhamento entre vetores de previsao e colunas auxiliares;
- garantir que os agregados finais sejam construidos a partir das previsoes realmente produzidas;
- evitar dependencias fora de `pandas`, `numpy` e `scikit-learn`;
- usar um modelo principal simples, reproduzivel e mais forte do que regressao linear simples.

## Erro real observado
O codigo anterior falhou em execucao real. O erro e o traceback completos serao fornecidos abaixo.

## Entrada esperada neste prompt
1. Resumo do erro
2. Traceback real
3. Codigo anterior completo

## Tarefa
Reescreva o codigo completo corrigindo especificamente o erro informado, mas preservando:
- o horizonte preditivo `t+1`;
- o split temporal;
- o baseline obrigatorio;
- as metricas principais `MAE`, `RMSE` e `WAPE`;
- as saidas gerenciais obrigatorias.

## Formato de resposta
Responda apenas com um unico bloco de codigo Python.
