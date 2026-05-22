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

## Modelo atual
meta-llama/llama-3.3-70b-instruct

## Resumo do erro observado
Llama v2 retry1 ainda falhou no agregado por linha/faixa horaria porque reset_index tentou reinserir cod_linha ja existente apos contar a propria coluna do groupby

## Traceback real
```text
# ML Run Error - Llama v2 Retry 1

- timestamp: `2026-04-18T19:21`
- model_label: `llama_3_3_70b_v2_retry1`
- source_file: `tcc/code/generated/ml_retry_openrouter_meta_llama_llama_3_3_70b_instruct_attempt1_2026-04-18_1913.py`
- stage: `11.2 / Bloco E`
- summary: `O agregado por linha/faixa horaria contou cod_linha dentro do proprio groupby e depois o reset_index tentou reinserir uma coluna com nome duplicado.`

## Traceback real
```text
Traceback (most recent call last):
  File "/home/eduardo/code/reproducao-artigo/tcc/code/10_run_ml_pipeline.py", line 262, in <module>
    main()
  File "/home/eduardo/code/reproducao-artigo/tcc/code/10_run_ml_pipeline.py", line 182, in main
    result = generated_module.run_ml_pipeline(pdf.copy())
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/eduardo/code/reproducao-artigo/tcc/code/generated/ml_retry_openrouter_meta_llama_llama_3_3_70b_instruct_attempt1_2026-04-18_1913.py", line 92, in run_ml_pipeline
    }).reset_index()
       ^^^^^^^^^^^^^
  File "/home/eduardo/code/reproducao-artigo/tcc/code/.venv/lib/python3.12/site-packages/pandas/core/frame.py", line 6472, in reset_index
    new_obj.insert(
  File "/home/eduardo/code/reproducao-artigo/tcc/code/.venv/lib/python3.12/site-packages/pandas/core/frame.py", line 5158, in insert
    raise ValueError(f"cannot insert {column}, already exists")
ValueError: cannot insert cod_linha, already exists
```
```

## Codigo anterior que falhou
```python
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, median_absolute_error
from sklearn.preprocessing import StandardScaler

def run_ml_pipeline(df_final):
    # Verificar se as colunas obrigatorias estao presentes
    required_columns = [
        "cod_linha", "cod_veiculo", "id_empresa", "viagem_sentido",
        "janela_5min", "latitude_media", "longitude_media", "velocidade_media",
        "gps_invalid_pct", "qtd_eventos_gps", "qtd_eventos_stop", "max_satelites",
        "headway_observado_min", "headway_referencia_min", "atraso_aproximado_min", "event_dt"
    ]
    if not all(column in df_final.columns for column in required_columns):
        raise ValueError("Colunas obrigatorias ausentes")

    # Ordenar por tempo e criar target deslocado para frente
    df_final = df_final.sort_values(by="janela_5min")
    df_final["y_true"] = df_final.groupby(["cod_linha", "cod_veiculo"])["atraso_aproximado_min"].shift(-1)

    # Descartar linhas sem proxima observacao disponivel
    df_final = df_final.dropna(subset=["y_true"])

    # Criar features temporais e historicas simples
    df_final["hour"] = df_final["janela_5min"].dt.hour
    df_final["day_of_week"] = df_final["event_dt"].dt.dayofweek
    df_final["is_weekend"] = df_final["day_of_week"].isin([5, 6])

    # Split temporal explicito
    train_df, val_test_df = train_test_split(df_final, test_size=0.3, shuffle=False, random_state=42)
    val_df, test_df = train_test_split(val_test_df, test_size=0.5, shuffle=False, random_state=42)

    # Preprocessamento
    scaler = StandardScaler()
    X_train = train_df[[
        "velocidade_media", "gps_invalid_pct", "qtd_eventos_gps", "qtd_eventos_stop", "max_satelites",
        "hour", "day_of_week"
    ]]
    y_train = train_df["y_true"]
    X_val = val_df[[
        "velocidade_media", "gps_invalid_pct", "qtd_eventos_gps", "qtd_eventos_stop", "max_satelites",
        "hour", "day_of_week"
    ]]
    y_val = val_df["y_true"]
    X_test = test_df[[
        "velocidade_media", "gps_invalid_pct", "qtd_eventos_gps", "qtd_eventos_stop", "max_satelites",
        "hour", "day_of_week"
    ]]
    y_test = test_df["y_true"]

    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    # Treinar baseline e modelo principal
    baseline_model = np.median(y_train)
    baseline_pred = np.full_like(y_test, baseline_model)

    model = HistGradientBoostingRegressor(random_state=42)
    model.fit(X_train_scaled, y_train)
    y_pred = model.predict(X_test_scaled)

    # Calcular metricas
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    wape = np.sum(np.abs(y_test - y_pred)) / np.sum(y_test)
    medae = median_absolute_error(y_test, y_pred)

    baseline_mae = mean_absolute_error(y_test, baseline_pred)
    baseline_rmse = np.sqrt(mean_squared_error(y_test, baseline_pred))
    baseline_wape = np.sum(np.abs(y_test - baseline_pred)) / np.sum(y_test)

    # Gerar saidas gerenciais
    predictions_df = pd.DataFrame({
        "event_dt": test_df["event_dt"],
        "janela_5min": test_df["janela_5min"],
        "cod_linha": test_df["cod_linha"],
        "cod_veiculo": test_df["cod_veiculo"],
        "y_true": y_test,
        "y_pred": y_pred
    })

    # Corrigir a coluna 'hour' para 'janela_5min'
    predictions_df['hour'] = predictions_df['janela_5min'].dt.hour

    line_hour_metrics_df = predictions_df.groupby(["cod_linha", "hour"]).agg({
        "y_pred": "mean",
        "y_true": "mean",
        "cod_linha": "count"
    }).reset_index()
    line_hour_metrics_df = line_hour_metrics_df.rename(columns={
        "y_pred": "avg_pred_atraso_aproximado_min",
        "y_true": "avg_real_atraso_aproximado_min",
        "cod_linha": "n_registros"
    })

    vehicle_day_metrics_df = predictions_df.groupby(["event_dt", "cod_veiculo"]).agg({
        "y_pred": "mean",
        "y_true": "mean",
        "cod_veiculo": "count"
    }).reset_index()
    vehicle_day_metrics_df = vehicle_day_metrics_df.rename(columns={
        "y_pred": "avg_pred_atraso_aproximado_min",
        "y_true": "avg_real_atraso_aproximado_min",
        "cod_veiculo": "n_registros"
    })

    return {
        "metrics": {
            "mae": mae,
            "rmse": rmse,
            "wape": wape,
            "medae": medae
        },
        "baseline_metrics": {
            "mae": baseline_mae,
            "rmse": baseline_rmse,
            "wape": baseline_wape
        },
        "predictions_df": predictions_df,
        "line_hour_metrics_df": line_hour_metrics_df,
        "vehicle_day_metrics_df": vehicle_day_metrics_df
    }
```

## Tarefa
Reescreva o codigo completo corrigindo o erro acima, preservando o split temporal, o baseline obrigatorio e o contrato de saida do pipeline de ML.
