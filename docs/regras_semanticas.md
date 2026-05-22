# Regras Semânticas - Ontologia de Transporte (Etapa 5 / Bloco B)

Data: 2026-02-16

Este documento detalha as regras semânticas operacionalizadas no modelo `TTL`.

## 1) Regra de fallback de chaves

Objetivo: reduzir perda de eventos por chave ausente e manter consistência de join.

Prioridade:
- `id_empresa`: usar `id_empresa`; se ausente, preencher com `-1`.
- `cod_linha`: usar `cod_linha`; se ausente, preencher com `-1`.
- `cod_veiculo`: usar `cod_veiculo`; se ausente, preencher com `-1`.
- `cod_tabela_programacao` (jornada): manter `null` quando ausente (não forçar chave falsa).
- `viagem_sentido`: manter `null` quando ausente.

Racional:
- `id_empresa/cod_linha/cod_veiculo` são chaves operacionais fortes para agregação e ML.
- Jornada/sentido podem vir nulos em parte relevante dos eventos (sobretudo operacionais), portanto devem ser opcionais no join semântico.

## 2) Regra de timestamp canônico

Objetivo: padronizar o tempo usado em partições, janelas e features.

Ordem canônica:
1. `event_ts` (derivado de `timestamp`) -> tempo principal de análise.
2. `created_at_origem` -> fallback para auditoria.
3. `created_at_ingestao` -> fallback final de rastreabilidade.

Racional:
- `event_ts` representa melhor o instante operacional do evento.
- Campos `created_at_*` ficam preservados para linhagem e investigação de atrasos de ingestão.

## 3) Regra de tratamento de GPS inválido

Objetivo: preservar informação e evitar viés por descarte agressivo.

Regra:
- Não descartar automaticamente pontos com GPS inválido.
- Marcar `gpsIsInvalid=true` quando:
  - `gps_sinal` indicar invalidez, ou
  - `latitude/longitude` forem nulas, ou
  - coordenadas estiverem fora de faixa válida.

Racional:
- Eventos com GPS inválido podem ser relevantes para diagnóstico operacional.
- A decisão de filtrar deve ocorrer na camada analítica (consulta/feature), não na ingestão semântica.

## Referências de implementação

- Ontologia TTL: `docs/ontologia_transporte.ttl`
- Indicadores de qualidade Silver: `artifacts/dq_silver_report_2026-02-16.csv`
