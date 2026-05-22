# Comparacao da Rodada 1 vs Rodada 2 de ML

## Observacao metodologica inicial
A comparacao numerica entre rodada 1 e rodada 2 **nao e diretamente apples-to-apples**, porque a rodada 2 mudou o problema de forma deliberada:
- rodada 1: tarefa mais proxima de uma estimacao contemporanea, com risco de vazamento e `MAPE` inadequado;
- rodada 2: previsao do target da proxima `janela_5min` (`t+1`), com regras anti-vazamento e metricas revisadas.

Mesmo assim, a comparacao e util para mostrar:
- o efeito da remocao do vazamento;
- o efeito de tornar a tarefa mais honesta e operacionalmente plausivel;
- a robustez relativa do baseline.

## Base consolidada
Arquivo principal:
- `tcc/artifacts/ml_round_comparison_2026-04-18.csv`

## Metricas padronizadas a partir dos CSVs de previsao

### Rodada 1
- baseline:
  - `MAE = 0.578168`
  - `RMSE = 3.665268`
  - `MedAE = 0.003249`
  - `WAPE = 1.034837`
- OpenAI:
  - `MAE = 0.910709`
  - `RMSE = 3.556105`
  - `MedAE = 0.464324`
  - `WAPE = 1.641316`
- Llama:
  - `MAE = 0.010248`
  - `RMSE = 0.246974`
  - `MedAE = 0.000015`
  - `WAPE = 0.018348`

### Rodada 2
- baseline:
  - `MAE = 0.568983`
  - `RMSE = 3.712559`
  - `MedAE = 0.003309`
  - `WAPE = 1.067038`
- OpenAI:
  - `status = invalid_predictions`
  - `rows_total = 54981`
  - `rows_valid = 7196`
  - `nan_y_true = 47785`
  - leitura:
    - o pipeline executou sem excecao final, mas o `predictions_df` saiu com grande volume de `NaN` em `y_true`;
    - portanto, a OpenAI **nao deve ser aceita como artefato final valido** da rodada 2.
- Llama:
  - `MAE = 0.866448`
  - `RMSE = 3.381694`
  - `MedAE = 0.315441`
  - `WAPE = 1.632771`

## Leitura critica

### 1. O baseline continua forte
- mesmo na rodada 2, com tarefa mais dificil e mais honesta, o baseline continuou competitivo.
- na comparacao valida da rodada 2:
  - baseline teve melhor `MAE` e melhor `WAPE` do que a Llama;
  - a Llama teve `RMSE` melhor do que o baseline, mas pior `MAE` e pior `WAPE`.

### 2. A Llama perdeu a aparente superioridade da rodada 1
- rodada 1:
  - `MAE = 0.010248`
  - `WAPE = 0.018348`
- rodada 2:
  - `MAE = 0.866448`
  - `WAPE = 1.632771`
- interpretacao:
  - essa queda brusca e coerente com a hipotese de que a rodada 1 estava inflada por vazamento ou trivializacao do target.
  - a rodada 2 produz um resultado muito mais plausivel e metodologicamente defensavel.

### 3. A OpenAI continuou fraca e instavel
- na rodada 1, a OpenAI ja era pior que o baseline em `MAE`.
- na rodada 2, mesmo apos 3 tentativas, o pipeline ainda nao entregou um `predictions_df` valido.
- interpretacao:
  - a OpenAI melhorou o enquadramento metodologico do codigo, mas nao conseguiu estabilizar a implementacao do pipeline no limite de retries definido.

## Conclusoes praticas para o TCC
- o refinamento metodologico da rodada 2 foi necessario e produziu um resultado mais confiavel do que a rodada 1.
- `MAPE` deve sair do centro da analise e ser substituido por `WAPE`, mantendo `MAE` e `RMSE`.
- a principal evidencia tecnica da rodada 2 e:
  - baseline forte e robusto;
  - Llama convergindo com metricas plausiveis, porem sem superar o baseline em `MAE`/`WAPE`;
  - OpenAI sem artefato final valido na rodada 2.

## Decisao recomendada
- usar a rodada 2 como referencia metodologica principal para a discussao de ML.
- manter a rodada 1 como evidencia historica do problema original:
  - `MAPE` inadequado;
  - risco de vazamento;
  - necessidade de refino metodologico.
