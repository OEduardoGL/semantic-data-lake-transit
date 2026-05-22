# Confirmacao de formato e particionamento da camada Silver

Data: 2026-02-14

## Configuracao adotada
- `silver_format`: `parquet` (arquivo `tcc/code/config.yaml`)
- Particionamento de escrita: `event_dt`, `tipo_mensagem`, `id_empresa` (funcao `write_partitioned` em `tcc/code/01_bronze_to_silver.py`)

## Evidencias de diretorio (amostras)
- `gps_events`: `event_dt=.../tipo_mensagem=.../id_empresa=...`
- `stop_events`: `event_dt=.../tipo_mensagem=.../id_empresa=...`
- `fare_events`: `event_dt=.../tipo_mensagem=.../id_empresa=...`
- `operational_events`: `event_dt=.../tipo_mensagem=.../id_empresa=...`

## Decisao
- Para este TCC, a Silver fica em **Parquet particionado**.
- O item do checklist "Parquet/Delta com particionamento definido" foi atendido via Parquet.

## Observacao operacional
- Validacoes de leitura devem usar caminho logico S3A (`s3a://transport/...`).
- Evitar leitura direta da pasta interna do MinIO (`tcc/infra/minio-data/...`), pois ela contem metadados internos do backend.
