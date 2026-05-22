# Decisoes de Schema e de Desenho do Pipeline

Data-base inicial: 2026-02-14
Base de decisao inicial: `artifacts/dq_profile_raw40gb_2026-02-14.md`

## Objetivo do documento
Consolidar as decisoes de desenho que tiveram impacto estrutural no pipeline.

Este documento comeca nas decisoes de schema do bruto e da Silver, mas foi ampliado para registrar tambem decisoes posteriores que afetam:
- a forma da Gold;
- o desenho de ML;
- o uso seletivo do Neo4j;
- a leitura metodologica final do experimento.

## Nota rapida: o que e `payload`
No contexto deste dataset AVL, `payload` e o bloco especifico do tipo de evento (campos `avlEvento...`), enquanto `avlHeader` representa o cabecalho comum.

Exemplos:
- `AVL_EVT_ENTRADA_SAIDA_PONTO` -> payload `avlEventoEntradaSaidaPonto`
- `AVL_EVT_PASSAGEM_CARTAO` -> payload `avlEventoPassagemCartao`
- `AVL_EVT_RECEBIMENTO_TABELA_PARCIAL` -> payload `avlEventoTabelaParcial`

## 1. Estrategia de separacao Silver
Decisao:
- separar por tipo funcional de evento em 4 tabelas:
  - `gps_events`
  - `stop_events`
  - `fare_events`
  - `operational_events`

Justificativa:
- alta heterogeneidade de payloads;
- quatro tipos concentram quase todo volume e demandam tratamentos diferentes;
- essa separacao reduz complexidade de wrangling, checks e joins posteriores.

## 2. Chaves tecnicas e de negocio
Decisao:
- chave tecnica por registro: `event_id` (origem `_id`) + `gps_idx` quando houver `explode` de `gps[]`;
- chaves de negocio prioritarias: `id_empresa`, `cod_linha`, `cod_veiculo`, `event_ts`.

Justificativa:
- `codVeiculo` praticamente completo no bruto;
- `codLinha` quase completo no bruto;
- o conjunto escolhido permite rastreabilidade operacional sem depender de campos auxiliares mais incompletos.

## 3. Campos nao obrigatorios para join
Decisao:
- `jornada.codOperador` e `viagem.sentido` sao tratados como auxiliares, e nao como chaves obrigatorias.

Justificativa:
- nulos relevantes no bruto:
  - `jornada.codOperador`: `17,54%`
  - `viagem.sentido`: `20,55%`
- forcar esses campos como chave degradaria cobertura e estabilidade dos joins.

## 4. Tratamento de GPS invalido
Decisao:
- nao descartar automaticamente registros com `sinalGps=AVL_QUALIDADE_SINAL_INVALIDO`;
- criar flag `gps_is_invalid` para uso analitico posterior.

Justificativa:
- cerca de `21,79%` dos registros possuem pelo menos um ponto GPS invalido;
- exclusao direta geraria vies e perda de contexto operacional.

## 5. Coordenadas e tempo
Decisao:
- preservar valores brutos (`latitude_raw`, `longitude_raw`) e criar normalizados (`latitude`, `longitude`);
- usar `timestamp` como tempo canonico (`event_ts`) e manter `createdAtOrigem` para auditoria.

Justificativa:
- necessidade de rastreabilidade e auditoria fim a fim.

## 6. Particionamento Silver
Decisao:
- particionar por `event_dt`, `tipo_mensagem`, `id_empresa`;
- subparticao opcional por `cod_linha` para consultas operacionais.

Justificativa:
- cardinalidade equilibrada e alinhada ao padrao de consulta por data/empresa/tipo.

## 7. Prioridade de carga (MVP)
Decisao:
- ordem inicial de implementacao Silver:
  1. `AVL_EVT_POSICIONAMENTO` -> `gps_events`
  2. `AVL_EVT_ENTRADA_SAIDA_PONTO` -> `stop_events`
  3. `AVL_EVT_PASSAGEM_CARTAO` -> `fare_events`
  4. demais tipos -> `operational_events`

Justificativa:
- maximo impacto com risco controlado no inicio do pipeline.

## 8. Contrato minimo da Gold
Decisao:
- o wrangling gerado por LLM foi avaliado contra um contrato minimo da `final_table` com:
  - `event_dt`
  - `cod_linha`
  - `cod_veiculo`
  - `janela_5min`
  - `headway_observado_min`
  - `headway_referencia_min`
  - `atraso_aproximado_min`

Justificativa:
- esse contrato permitiu comparar LLMs sob criterio objetivo antes de enriquecer a Gold.

## 9. Gold enriquecida como refinamento deterministico
Decisao:
- a Gold final do projeto nao e a Gold minima contratual;
- ela foi enriquecida de forma deterministica na etapa 9, ainda em `code/06_materialize_final_table.py`.

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
- a Gold minima inicial era estruturalmente valida, mas insuficiente para ML e decisao gerencial;
- o enriquecimento nao reabre a comparacao entre LLMs, apenas transforma a saida vencedora em tabela util.

## 10. Target como proxy operacional
Decisao:
- definir o target final como:
  - `atraso_aproximado_min = max(0, headway_observado_min - headway_referencia_min)`

Justificativa:
- havia necessidade de um target numerico derivado de comportamento operacional observavel;
- a literatura de dominio sustenta o papel de `headway` e `bunching` como eixos centrais de confiabilidade.

## 11. Rodada 2 de ML como referencia metodologica principal
Decisao:
- manter a rodada 1 como diagnostico historico;
- usar a rodada 2 como referencia principal de avaliacao.

Justificativa:
- a rodada 1 mostrou `MAPE` inadequado, ambiguidade da tarefa e risco de vazamento;
- a rodada 2 introduziu horizonte `t+1`, split temporal, seed congelada e politica anti-vazamento explicita.

## 12. Metricas centrais de ML
Decisao:
- manter `MAE`, `RMSE`, `WAPE` e `MedAE` como metricas centrais da rodada 2;
- rebaixar `MAPE` a papel secundario/diagnostico.

Justificativa:
- alta massa do target em zero ou muito proximo de zero tornava o `MAPE` instavel e pouco informativo.

## 13. Preservacao de IDs operacionais
Decisao:
- `cod_linha` e `cod_veiculo` originais devem ser preservados nos artefatos finais usados em agregados e Neo4j.

Justificativa:
- IDs recodificados ou sobrescritos comprometem interpretabilidade gerencial;
- essa decisao foi particularmente importante para excluir a Llama da camada final de agregados da rodada anterior quando ela havia recodificado identificadores.

## 14. Uso seletivo do Neo4j
Decisao:
- nao usar Neo4j para armazenar o bruto ou a Silver completa;
- usar Neo4j em dois pontos de alto valor:
  - camada semantica inicial;
  - publicacao final dos agregados gerenciais.

Justificativa:
- o grafo agrega valor para semantica e exploracao relacional, mas nao era a tecnologia certa para o armazenamento massivo de toda a base operacional.

## 15. Decisoes oficiais de interpretacao
Para interpretar os artefatos publicados, devem ser mantidas as seguintes decisoes:
- a comparacao de wrangling termina com a convergencia da OpenAI no `attempt 2`;
- a Gold final do trabalho e a Gold enriquecida, nao a Gold minima inicial;
- a rodada 2 de ML e a referencia metodologica principal;
- o baseline v2 e a ancora quantitativa principal;
- a Llama v2 e o melhor pipeline LLM valido da rodada 2, sem superioridade sobre o baseline;
- a OpenAI v2 permanece como evidencia experimental, nao como artefato final valido.
