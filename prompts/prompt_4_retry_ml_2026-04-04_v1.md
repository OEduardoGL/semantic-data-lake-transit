# Prompt 4 - Retry de ML Orientado por Erro Real

## Objetivo
Corrigir codigo Python de pipeline de ML previamente gerado por LLM, usando erro real de execucao sobre a `final_table` enriquecida.

## Contexto
O pipeline deve receber um `pandas.DataFrame` chamado `df_final` contendo a `final_table` materializada em `s3a://transport/gold/final_table`.

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

Target fechado:
- `atraso_aproximado_min`

## Contrato de Saida Obrigatorio
Retorne apenas codigo Python executavel.

O modulo corrigido deve expor exatamente:
- `run_ml_pipeline(df_final)`

A funcao deve retornar um `dict` com:
- `metrics`
- `baseline_metrics`
- `predictions_df`
- `line_hour_metrics_df`
- `vehicle_day_metrics_df`

Requisitos:
- usar split temporal coerente;
- nao usar o conjunto inteiro para construir artefatos de teste;
- evitar desalinhamento entre vetores e colunas auxiliares;
- tratar colunas numericas e categoricas separadamente;
- nao aplicar `mean()` em dataframe misto;
- garantir que `predictions_df` tenha colunas:
  - `event_dt`
  - `janela_5min`
  - `cod_linha`
  - `cod_veiculo`
  - `y_true`
  - `y_pred`
- garantir que `line_hour_metrics_df` e `vehicle_day_metrics_df` sejam coerentes com as previsoes realmente produzidas;
- usar baseline simples e auditavel;
- evitar dependencias fora de `pandas`, `numpy` e `scikit-learn`.

## Erro Real Observado
O codigo anterior falhou em execucao real. O erro e o traceback completos serao fornecidos abaixo.

## Entrada Esperada Neste Prompt
1. Resumo do erro
2. Traceback real
3. Codigo anterior completo

## Tarefa
Reescreva o codigo completo corrigindo especificamente o erro informado, mas preservando:
- target fechado;
- split temporal;
- baseline obrigatorio;
- saidas gerenciais obrigatorias.

## Formato de Resposta
Responda apenas com um unico bloco de codigo Python.
