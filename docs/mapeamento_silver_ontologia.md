# Mapeamento Silver -> Ontologia

Versão: 2026-02-16
Arquivo de referência técnica: `code/semantic_mapping.yaml`

## Objetivo

Documentar como colunas da camada Silver alimentam classes e propriedades do modelo semântico.

## Estratégia de chave técnica

- `gps_events`: `event_id + gps_idx`
- `stop_events`: `event_id + gps_idx`
- `fare_events`: `event_id + gps_idx`
- `operational_events`: `event_id + gps_idx`

## Mapeamento essencial (comum às tabelas)

- `event_id` -> `tcc:eventId`
- `event_ts` -> `tcc:eventTs`
- `event_dt` -> `tcc:eventDate`
- `gps_idx` -> `tcc:gpsIndex`
- `gps_sinal` -> `tcc:gpsSinal`
- `latitude` -> `tcc:latitude`
- `longitude` -> `tcc:longitude`
- `velocidade` -> `tcc:velocidade`
- `viagem_sentido` -> `tcc:sentidoViagem`

## Ligações semânticas principais

- `cod_linha` -> `Evento* tcc:temLinha Linha`
- `cod_veiculo` -> `Evento* tcc:temVeiculo Veiculo`
- `id_empresa` -> `Evento* tcc:temEmpresa Empresa`
- `cod_garagem` -> `Evento* tcc:temGaragem Garagem` (quando disponível)
- `cod_tabela_programacao` -> `Evento* tcc:temJornadaProgramacao JornadaProgramacao`
- `tipo_mensagem` -> `Evento* tcc:temTipoMensagem TipoMensagemAVL`
- `id_ponto` (somente `stop_events`) -> `EventoParada tcc:ocorreNoPonto PontoParada`

## Correspondência por tabela Silver

- `gps_events` -> classe `tcc:EventoGPS`
- `stop_events` -> classe `tcc:EventoParada`
- `fare_events` -> classe `tcc:EventoTarifa`
- `operational_events` -> classe `tcc:EventoOperacional`

## Regras semânticas vinculadas ao mapeamento

- fallback de chaves: `tcc:RegraFallbackChaves`
- timestamp canônico: `tcc:RegraTimestampCanonico`
- GPS inválido: `tcc:RegraGPSInvalido`

## Observações

- `cod_tabela_programacao` e `viagem_sentido` podem ser nulos; não usar como chave obrigatória.
- O mapeamento foi versionado em `YAML` para alimentar carga no Neo4j na etapa 6.
