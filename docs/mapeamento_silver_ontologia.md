# Mapeamento Silver -> Ontologia

Versao: 2026-02-16
Arquivo de referencia tecnica: `code/semantic_mapping.yaml`

## Objetivo

Documentar como colunas da camada Silver alimentam classes e propriedades do modelo semantico.

## Estrategia de chave tecnica

- `gps_events`: `event_id + gps_idx`
- `stop_events`: `event_id + gps_idx`
- `fare_events`: `event_id + gps_idx`
- `operational_events`: `event_id + gps_idx`

## Mapeamento essencial (comum as tabelas)

- `event_id` -> `tcc:eventId`
- `event_ts` -> `tcc:eventTs`
- `event_dt` -> `tcc:eventDate`
- `gps_idx` -> `tcc:gpsIndex`
- `gps_sinal` -> `tcc:gpsSinal`
- `latitude` -> `tcc:latitude`
- `longitude` -> `tcc:longitude`
- `velocidade` -> `tcc:velocidade`
- `viagem_sentido` -> `tcc:sentidoViagem`

## Ligacoes semanticas principais

- `cod_linha` -> `Evento* tcc:temLinha Linha`
- `cod_veiculo` -> `Evento* tcc:temVeiculo Veiculo`
- `id_empresa` -> `Evento* tcc:temEmpresa Empresa`
- `cod_garagem` -> `Evento* tcc:temGaragem Garagem` (quando disponivel)
- `cod_tabela_programacao` -> `Evento* tcc:temJornadaProgramacao JornadaProgramacao`
- `tipo_mensagem` -> `Evento* tcc:temTipoMensagem TipoMensagemAVL`
- `id_ponto` (somente `stop_events`) -> `EventoParada tcc:ocorreNoPonto PontoParada`

## Correspondencia por tabela Silver

- `gps_events` -> classe `tcc:EventoGPS`
- `stop_events` -> classe `tcc:EventoParada`
- `fare_events` -> classe `tcc:EventoTarifa`
- `operational_events` -> classe `tcc:EventoOperacional`

## Regras semanticas vinculadas ao mapeamento

- fallback de chaves: `tcc:RegraFallbackChaves`
- timestamp canonico: `tcc:RegraTimestampCanonico`
- GPS invalido: `tcc:RegraGPSInvalido`

## Observacoes

- `cod_tabela_programacao` e `viagem_sentido` podem ser nulos; nao usar como chave obrigatoria.
- O mapeamento foi versionado em `YAML` para alimentar carga no Neo4j na etapa 6.
