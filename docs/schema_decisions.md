# Decisões de Schema e de Desenho do Pipeline

Data-base inicial: 2026-02-14
Base de decisão inicial: `artifacts/dq_profile_raw40gb_2026-02-14.md`

## Objetivo do documento
Consolidar as decisões de desenho que tiveram impacto estrutural no pipeline.

Este documento começa nas decisões de schema do bruto e da Silver, mas foi ampliado para registrar também decisões posteriores que afetam:
- a forma da Gold;
- o desenho de ML;
- o uso seletivo do Neo4j;
- a leitura metodológica final do experimento.

## 1. Estratégia de separação Silver
Decisão:
- separar por tipo funcional de evento em 4 tabelas:
  - `gps_events`
  - `stop_events`
  - `fare_events`
  - `operational_events`

Justificativa:
- alta heterogeneidade estrutural dos eventos;
- quatro tipos concentram quase todo volume e demandam tratamentos diferentes;
- essa separação reduz complexidade de wrangling, checks e joins posteriores.

## 2. Chaves técnicas e de negócio
Decisão:
- chave técnica por registro: `event_id` (origem `_id`) + `gps_idx` quando houver `explode` de `gps[]`;
- chaves de negócio prioritárias: `id_empresa`, `cod_linha`, `cod_veiculo`, `event_ts`.

Justificativa:
- `codVeiculo` praticamente completo no bruto;
- `codLinha` quase completo no bruto;
- o conjunto escolhido permite rastreabilidade operacional sem depender de campos auxiliares mais incompletos.

## 3. Campos não obrigatórios para join
Decisão:
- `jornada.codOperador` e `viagem.sentido` são tratados como auxiliares, e não como chaves obrigatórias.

Justificativa:
- nulos relevantes no bruto:
  - `jornada.codOperador`: `17,54%`
  - `viagem.sentido`: `20,55%`
- forçar esses campos como chave degradaria cobertura e estabilidade dos joins.

## 4. Tratamento de GPS inválido
Decisão:
- não descartar automaticamente registros com `sinalGps=AVL_QUALIDADE_SINAL_INVALIDO`;
- criar flag `gps_is_invalid` para uso analítico posterior.

Justificativa:
- cerca de `21,79%` dos registros possuem pelo menos um ponto GPS inválido;
- exclusão direta geraria viés e perda de contexto operacional.

## 5. Coordenadas e tempo
Decisão:
- preservar valores brutos (`latitude_raw`, `longitude_raw`) e criar normalizados (`latitude`, `longitude`);
- usar `timestamp` como tempo canônico (`event_ts`) e manter `createdAtOrigem` para auditoria.

Justificativa:
- necessidade de rastreabilidade e auditoria fim a fim.

## 6. Particionamento Silver
Decisão:
- particionar por `event_dt`, `tipo_mensagem`, `id_empresa`;
- subpartição opcional por `cod_linha` para consultas operacionais.

Justificativa:
- cardinalidade equilibrada e alinhada ao padrão de consulta por data/empresa/tipo.

## 7. Prioridade de carga (MVP)
Decisão:
- ordem inicial de implementação Silver:
  1. `AVL_EVT_POSICIONAMENTO` -> `gps_events`
  2. `AVL_EVT_ENTRADA_SAIDA_PONTO` -> `stop_events`
  3. `AVL_EVT_PASSAGEM_CARTAO` -> `fare_events`
  4. demais tipos -> `operational_events`

Justificativa:
- máximo impacto com risco controlado no início do pipeline.

## 8. Contrato mínimo da Gold
Decisão:
- o wrangling gerado por LLM foi avaliado contra um contrato mínimo da `final_table` com:
  - `event_dt`
  - `cod_linha`
  - `cod_veiculo`
  - `janela_5min`
  - `headway_observado_min`
  - `headway_referencia_min`
  - `atraso_aproximado_min`

Justificativa:
- esse contrato permitiu comparar LLMs sob critério objetivo antes de enriquecer a Gold.

## 9. Gold enriquecida como refinamento determinístico
Decisão:
- a Gold final do projeto não é a Gold mínima contratual;
- ela foi enriquecida de forma determinística na etapa 9, ainda em `code/06_materialize_final_table.py`.

Colunas finais consolidadas:
- `cod_linha`
- `cod_veiculo`
- `id_empresa`
- `viagem_sentido`
- `janela_5min`
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
- `event_dt`

Justificativa:
- a Gold mínima inicial era estruturalmente válida, mas insuficiente para ML e decisão gerencial;
- o enriquecimento não reabre a comparação entre LLMs, apenas transforma a saída selecionada em tabela adequada para análise.

## 10. Target como proxy operacional
Decisão:
- definir o target final como:
  - `atraso_aproximado_min = max(0, headway_observado_min - headway_referencia_min)`

Justificativa:
- havia necessidade de um target numérico derivado de comportamento operacional observável;
- a literatura de domínio sustenta o papel de `headway` e `bunching` como eixos centrais de confiabilidade.

## 11. Rodada 2 de ML como referência metodológica principal
Decisão:
- manter a rodada 1 como diagnóstico histórico;
- usar a rodada 2 como referência principal de avaliação.

Justificativa:
- a rodada 1 mostrou `MAPE` inadequado, ambiguidade da tarefa e risco de vazamento;
- a rodada 2 introduziu horizonte `t+1`, split temporal, seed fixa e política anti-vazamento explícita.

## 12. Métricas centrais de ML
Decisão:
- manter `MAE`, `RMSE`, `WAPE` e `MedAE` como métricas centrais da rodada 2;
- rebaixar `MAPE` a papel secundário/diagnóstico.

Justificativa:
- alta massa do target em zero ou muito próximo de zero tornava o `MAPE` instável e pouco informativo.

## 13. Preservação de IDs operacionais
Decisão:
- `cod_linha` e `cod_veiculo` originais devem ser preservados nos artefatos finais usados em agregados e Neo4j.

Justificativa:
- IDs recodificados ou sobrescritos comprometem interpretabilidade gerencial;
- essa decisão foi particularmente importante para excluir o pipeline Llama da camada final de agregados da rodada anterior quando ele havia recodificado identificadores.

## 14. Uso seletivo do Neo4j
Decisão:
- não usar Neo4j para armazenar o bruto ou a Silver completa;
- usar Neo4j em dois pontos de alto valor:
  - camada semântica inicial;
  - publicação final dos agregados gerenciais.

Justificativa:
- o grafo agrega valor para semântica e exploração relacional, mas não era a tecnologia certa para o armazenamento massivo de toda a base operacional.

## 15. Decisões de interpretação adotadas
Para interpretar os artefatos publicados, devem ser mantidas as seguintes decisões:
- a comparação de wrangling termina com a convergência da OpenAI no `attempt 2`;
- a Gold final do trabalho é a Gold enriquecida, não a Gold mínima inicial;
- a rodada 2 de ML é a referência metodológica principal;
- o baseline v2 é a âncora quantitativa principal;
- o pipeline Llama v2 é o melhor pipeline LLM válido da rodada 2, sem superioridade sobre o baseline;
- a OpenAI v2 permanece como evidência experimental, não como artefato final válido.
