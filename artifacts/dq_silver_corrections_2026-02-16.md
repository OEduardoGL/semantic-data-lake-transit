# DQ Silver - Correcoes Aplicadas (Etapa 4)

Data: 2026-02-16

## Escopo

Este documento registra as correcoes aplicadas durante os testes de qualidade da Silver.

## Correcoes de processo (aplicadas)

1. Execucao segura anti-crash para Spark local
- Problema: tentativa inicial de duplicidade em volume completo causou `OutOfMemoryError`.
- Correcao: execucao por tabela e `gps_events` por `event_dt` (`--gps-by-day`), com `master=local[4]`, `shuffle_partitions=64`, memoria controlada por execucao.

2. Regra de chave tecnica corrigida para duplicidade
- Problema: usar apenas `event_id` em tabelas com multiplos pontos GPS no mesmo evento gera falso duplicado.
- Correcao: regra final adotada `event_id + gps_idx` quando aplicavel (incluindo `stop_events`, `fare_events`, `operational_events` no schema atual).

3. Escrita de CSV robusta com colunas dinamicas
- Problema: falha ao salvar CSV quando tabelas tinham conjuntos de colunas diferentes.
- Correcao: rotina de escrita atualizada para usar uniao de colunas entre linhas.

4. Consolidacao final dos relatórios com tratamento de fim de linha
- Problema: parse incorreto por `CRLF` em alguns arquivos CSV.
- Correcao: consolidacao refeita com limpeza de `\r` antes do join.

## Correcoes de dados (Silver)

- Nao foi aplicada correcao destrutiva/reescrita de dados nesta etapa.
- A etapa 4 foi diagnostica (medicao e validacao).

## Pendencias recomendadas para etapas seguintes

- Definir tratamento de negocio para nulos de `cod_tabela_programacao` e `viagem_sentido` (sobretudo em `operational_events`).
- Decidir politica de imputacao/fallback semantico antes da `final_table`.
