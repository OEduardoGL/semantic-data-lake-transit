# DQ Silver - Bloco A (execucao segura)

Data: 2026-02-16

## Escopo

- Teste de contagem de registros por tabela
- Teste de duplicidade de chave tecnica (`event_id + gps_idx` quando aplicavel)

## Estrategia anti-crash

- Execucao por subconjunto de tabelas (nao tudo de uma vez)
- `gps_events` processado com `--gps-by-day` (por `event_dt`, depois consolidado)
- Spark com perfil mais estavel: `master=local[4]`, `shuffle_partitions=64`
- Memoria controlada por execucao (`4g` em non-gps, `6g` em gps)

## Comandos usados

```bash
cd tcc/code
.venv/bin/python dq_silver_checks.py \
  --tables stop_events,fare_events,operational_events \
  --driver-memory 4g --master 'local[4]' --shuffle-partitions 64 \
  --output-csv ../artifacts/dq_silver_report_blockA_nongps_2026-02-15.csv

.venv/bin/python dq_silver_checks.py \
  --tables gps_events --gps-by-day \
  --driver-memory 6g --master 'local[4]' --shuffle-partitions 64 \
  --output-csv ../artifacts/dq_silver_report_blockA_gps_2026-02-15.csv
```

## Resultado consolidado

Arquivo final:
- `tcc/artifacts/dq_silver_report_blockA_2026-02-16.csv`

Resumo:
- `gps_events`: 38.678.181 linhas, duplicidade=0
- `stop_events`: 11.484.461 linhas, duplicidade=0
- `fare_events`: 2.434.106 linhas, duplicidade=0
- `operational_events`: 5.261.765 linhas, duplicidade=0
