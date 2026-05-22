# Regras Semanticas - Ontologia de Transporte (Etapa 5 / Bloco B)

Data: 2026-02-16

Este documento detalha as regras semanticas operacionalizadas no modelo `TTL`.

## 1) Regra de fallback de chaves

Objetivo: reduzir perda de eventos por chave ausente e manter consistencia de join.

Prioridade:
- `id_empresa`: usar `id_empresa`; se ausente, preencher com `-1`.
- `cod_linha`: usar `cod_linha`; se ausente, preencher com `-1`.
- `cod_veiculo`: usar `cod_veiculo`; se ausente, preencher com `-1`.
- `cod_tabela_programacao` (jornada): manter `null` quando ausente (nao forcar chave falsa).
- `viagem_sentido`: manter `null` quando ausente.

Racional:
- `id_empresa/cod_linha/cod_veiculo` sao chaves operacionais fortes para agregacao e ML.
- Jornada/sentido podem vir nulos em parte relevante dos eventos (sobretudo operacionais), portanto devem ser opcionais no join semantico.

## 2) Regra de timestamp canonico

Objetivo: padronizar o tempo usado em particoes, janelas e features.

Ordem canonica:
1. `event_ts` (derivado de `timestamp`) -> tempo principal de analise.
2. `created_at_origem` -> fallback para auditoria.
3. `created_at_ingestao` -> fallback final de rastreabilidade.

Racional:
- `event_ts` representa melhor o instante operacional do evento.
- Campos `created_at_*` ficam preservados para lineage e investigacao de atrasos de ingestao.

## 3) Regra de tratamento de GPS invalido

Objetivo: preservar informacao e evitar vies por descarte agressivo.

Regra:
- Nao descartar automaticamente pontos com GPS invalido.
- Marcar `gpsIsInvalid=true` quando:
  - `gps_sinal` indicar invalidez, ou
  - `latitude/longitude` forem nulas, ou
  - coordenadas estiverem fora de faixa valida.

Racional:
- Eventos com GPS invalido podem ser relevantes para diagnostico operacional.
- A decisao de filtrar deve ocorrer na camada analitica (consulta/feature), nao na ingestao semantica.

## Referencias de implementacao

- Ontologia TTL: `docs/ontologia_transporte.ttl`
- Indicadores de qualidade Silver: `artifacts/dq_silver_report_2026-02-16.csv`
