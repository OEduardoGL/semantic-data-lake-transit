# Aggregate Source Contract (Pos-ML V2)

- timestamp: `2026-04-18`
- etapa: `12.1) ATUALIZACAO DOS AGREGADOS (POS-ML V2)`

## Objetivo
Definir quais artefatos da rodada 2 sao validos como fonte principal dos agregados gerenciais e do pacote final para Neo4j.

## Fontes inspecionadas

### Baseline v2
- `tcc/artifacts/predictions_baseline_2026-04-18_1904.csv`
- `tcc/artifacts/metrics_ml_baseline_2026-04-18_1904.csv`
- status: `valido`
- papel:
  - ancora quantitativa principal
  - referencia robusta para comparacao linha/hora

### Llama 3.3 70B Instruct v2 (retry 2)
- `tcc/artifacts/predictions_llama_3_3_70b_v2_retry2_2026-04-18_1924.csv`
- `tcc/artifacts/metrics_ml_llama_3_3_70b_v2_retry2_2026-04-18_1924.csv`
- `tcc/artifacts/neo4j_metrics_line_hour_llama_3_3_70b_v2_retry2_2026-04-18_1924.csv`
- `tcc/artifacts/neo4j_metrics_vehicle_day_llama_3_3_70b_v2_retry2_2026-04-18_1924.csv`
- status: `valido`
- validacoes centrais:
  - IDs operacionais preservados: `sim`
  - `predictions_df` valido: `sim`
  - horizonte preditivo compatível com a rodada 2: `sim`
- papel:
  - fonte preditiva principal da visualizacao gerencial

### OpenAI v2 (retry 3)
- `tcc/artifacts/predictions_openai_gpt_4o_v2_retry3_2026-04-18_1946.csv`
- `tcc/artifacts/metrics_ml_openai_gpt_4o_v2_retry3_2026-04-18_1946.csv`
- status: `invalido_para_uso_final`
- problema:
  - `predictions_df` com `47785` linhas com `y_true = NaN`
- consequencia:
  - nao deve entrar no pacote final para Neo4j
  - permanece apenas como evidencia experimental da rodada 2

## Decisao oficial
- fonte principal dos agregados atualizados:
  - `baseline v2`
  - `Llama 3.3 70B Instruct v2 (retry 2)`
- fonte excluida do pacote final:
  - `OpenAI v2`

## Regra adicional de robustez gerencial
Para evitar rankings dominados por observacoes isoladas, os agregados finais da etapa 12.1 usam cortes minimos de suporte:
- `min_line_records = 10`
- `min_line_hour_records = 5`
- `min_segment_records = 5`
- `min_vehicle_records = 10`

## Contrato para a etapa 13
- o Neo4j final deve consumir os CSVs gerados em `2026-04-18_2044`
- os rankings finais devem usar a rodada 2 como referencia metodologica principal
- a comparacao com a etapa 12 antiga deve ser mantida apenas como contexto historico
