# DQ Profile - Raw 40GB (messages_fortaleza.json)

Data: 2026-02-14
Fonte: `s3a://transport/bronze/messages_fortaleza.json`

## 1) Volume e janela temporal
- total_records: 21.513.073
- min_timestamp: 1677553201 (2023-02-28 03:00:01 UTC)
- max_timestamp: 1677726000 (2023-03-02 03:00:00 UTC)

## 2) Cardinalidades (aprox)
- codLinha: 461
- codVeiculo: 2075
- idEmpresa: 21

## 3) Qualidade de chaves e GPS
- null_codLinha: 749 (0,00%)
- null_codVeiculo: 0 (0,00%)
- null_jornada_codOperador: 3.773.742 (17,54%)
- null_viagem_sentido: 4.420.849 (20,55%)
- records_with_invalid_gps: 4.687.607 (21,79%)

## 4) Frequencia por tipo de evento
1. AVL_EVT_POSICIONAMENTO: 8.240.609
2. AVL_EVT_ENTRADA_SAIDA_PONTO: 5.576.593
3. AVL_EVT_RECEBIMENTO_TABELA_PARCIAL: 4.774.039
4. AVL_EVT_PASSAGEM_CARTAO: 2.434.106
5. AVL_EVT_ABERTURA_FECHAMENTO_VIAGEM: 225.167
6. AVL_EVT_RECARGA: 103.107
7. AVL_EVT_BLOQUEIO_CARTAO: 45.184
8. AVL_EVT_FECHAMENTO_JORNADA: 40.439
9. AVL_EVT_CATRACA_45_GRAUS: 24.701
10. AVL_EVT_ABERTURA_JORNADA: 23.421
11. AVL_EVT_LIGA_DESLIGA: 9.555
12. AVL_EVT_SELECAO_TABELA: 8.129
13. AVL_EVT_USU_ACAO_REALIZADA: 3.866
14. AVL_EVT_PASSAGEM_TICKET: 3.168
15. AVL_EVT_BOTAO_PANICO: 745
16. AVL_EVT_VEICULO_INICIALIZADO: 244

## 5) Arquivos complementares gerados
- `tcc/artifacts/profile_by_event_type_raw40gb_2026-02-14.csv`
- `tcc/artifacts/dq_keys_and_gps_raw40gb_2026-02-14.txt`
- `tcc/artifacts/fields_main_by_event_type_raw40gb_2026-02-14.md`
- `tcc/artifacts/raw40gb_tipoMensagem_counts_2026-02-14.txt`
