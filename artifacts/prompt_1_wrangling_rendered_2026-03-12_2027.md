# Prompt 1 - Wrangling Semantico para FinalTable (v1)

## Objetivo
Gerar codigo PySpark para transformar tabelas Silver de transporte em uma `final_table` analitica, seguindo o fluxo:
`modelo semantico -> prompt LLM -> wrangling -> FinalTable`.

Escopo desta versao:
- suportar comparacao entre 2 LLMs:
  - OpenAI `gpt-4o`;
  - `Llama 3.3 70B Instruct`;
- focar em gerar codigo executavel e rastreavel;
- priorizar robustez de schema e qualidade de dados.

## Contexto dos dados (Silver)
As tabelas Silver estao em Parquet e foram geradas pela etapa Bronze -> Silver:
- `gps_events`
- `stop_events`
- `fare_events`
- `operational_events`

### Colunas-base relevantes
Chaves e tempo:
- `event_id`, `gps_idx`
- `event_ts`, `event_dt`
- `tipo_mensagem`
- `id_empresa`, `cod_linha`, `cod_veiculo`
- `cod_tabela_programacao`, `viagem_sentido`

Posicionamento:
- `latitude_raw`, `longitude_raw`
- `latitude`, `longitude`
- `velocidade`, `direcao`
- `gps_sinal`, `numero_satelites`, `odometro_calculado`

Parada (quando aplicavel):
- `id_ponto`, `evento_ponto`

## Regras semanticas obrigatorias
Aplicar obrigatoriamente estas regras (fonte: ontologia/mapeamento/regras):

1. Fallback de chaves:
- `id_empresa`, `cod_linha`, `cod_veiculo`: usar fallback para `-1` quando ausente.
- `cod_tabela_programacao` e `viagem_sentido`: podem permanecer `null`.

2. Timestamp canonico:
- usar `event_ts` como tempo canonico de analise;
- preservar `created_at_origem` e `created_at_ingestao` para auditoria.

3. GPS invalido:
- nao descartar automaticamente registros com GPS invalido;
- criar/propagar flag `gps_is_invalid` quando `gps_sinal` invalido, coordenadas nulas ou fora de faixa.

## Requisitos da FinalTable
A saida deve conter, no minimo, as colunas:
- `event_dt`
- `cod_linha`
- `cod_veiculo`
- `janela_5min`
- `headway_observado_min`
- `headway_referencia_min`
- `atraso_aproximado_min`

Pode incluir colunas auxiliares adicionais, desde que as obrigatorias existam.

## Contrato de saida obrigatorio do LLM
Responda com **apenas codigo Python** (sem texto fora de bloco) contendo:

1. Funcao principal com assinatura exata:
```python
def build_final_table(df_dict: dict[str, DataFrame]) -> DataFrame:
    ...
```

2. `df_dict` deve esperar chaves:
- `"gps_events"`, `"stop_events"`, `"fare_events"`, `"operational_events"`.

3. O codigo deve:
- usar apenas API PySpark DataFrame (sem Pandas);
- validar presenca de colunas minimas antes das transformacoes;
- falhar com erro explicito quando faltar coluna critica;
- garantir unicidade tecnica no nivel de evento (`event_id` + `gps_idx` quando aplicavel);
- evitar UDF quando funcao nativa Spark resolver.

4. Incluir uma funcao de validacao:
```python
def validate_final_table(df_final: DataFrame) -> None:
    ...
```
que verifique:
- colunas obrigatorias;
- tipos numericos de metricas;
- nulos em colunas-chave;
- ranges basicos de coordenadas, se usados na saida.

## Exemplo minimo de input/output esperado
### Exemplo de input (estrutura)
```python
df_dict = {
    "gps_events": df_gps,              # DataFrame Spark
    "stop_events": df_stop,            # DataFrame Spark
    "fare_events": df_fare,            # DataFrame Spark
    "operational_events": df_oper,     # DataFrame Spark
}
```

### Exemplo de output (schema minimo da final_table)
```text
event_dt (date)
cod_linha (string/int normalizado)
cod_veiculo (string/int normalizado)
janela_5min (string ou timestamp truncado em 5 min)
headway_observado_min (double)
headway_referencia_min (double)
atraso_aproximado_min (double)
```

### Exemplo de linhas (didatico)
```text
2023-03-01 | 120 | 4587 | 2023-03-01 07:35 | 9.5  | 8.0 | 1.5
2023-03-01 | 120 | 4587 | 2023-03-01 07:40 | 12.0 | 8.0 | 4.0
```

## Checklist de validacao que o codigo deve cumprir
- [ ] Le as 4 tabelas Silver via `df_dict`.
- [ ] Aplica regras semanticas obrigatorias.
- [ ] Gera `final_table` com colunas obrigatorias.
- [ ] Mantem transformacoes reproduziveis (sem fonte aleatoria).
- [ ] Executa `validate_final_table` antes de retornar.

## Restricoes
- Nao usar dados externos.
- Nao expandir o benchmark para muitas LLMs; manter apenas 2 modelos.
- Nao alterar escopo para deep learning complexo.
- Nao remover eventos apenas por GPS invalido.

## Formato final da resposta da LLM
- Um unico bloco de codigo Python executavel.
- Sem markdown adicional fora do bloco.
- Com imports necessarios no topo.

---

## Contexto adicional (gerado automaticamente): schema Silver e mapeamento semantico

### Tabela `fare_events`
- Classe semantica: `tcc:EventoTarifa`
- Chave natural: `event_id+gps_idx` (event_id, gps_idx)
- Links semanticos: `cod_linha` -> `tcc:temLinha` -> `tcc:Linha`; `cod_veiculo` -> `tcc:temVeiculo` -> `tcc:Veiculo`; `id_empresa` -> `tcc:temEmpresa` -> `tcc:Empresa`; `cod_tabela_programacao` -> `tcc:temJornadaProgramacao` -> `tcc:JornadaProgramacao`; `tipo_mensagem` -> `tcc:temTipoMensagem` -> `tcc:TipoMensagemAVL`
- Colunas mapeadas (data properties): `event_dt`, `event_id`, `event_ts`, `gps_idx`, `gps_sinal`, `latitude`, `longitude`, `velocidade`, `viagem_sentido`

### Tabela `gps_events`
- Classe semantica: `tcc:EventoGPS`
- Chave natural: `event_id+gps_idx` (event_id, gps_idx)
- Links semanticos: `cod_linha` -> `tcc:temLinha` -> `tcc:Linha`; `cod_veiculo` -> `tcc:temVeiculo` -> `tcc:Veiculo`; `id_empresa` -> `tcc:temEmpresa` -> `tcc:Empresa`; `cod_garagem` -> `tcc:temGaragem` -> `tcc:Garagem`; `cod_tabela_programacao` -> `tcc:temJornadaProgramacao` -> `tcc:JornadaProgramacao`; `tipo_mensagem` -> `tcc:temTipoMensagem` -> `tcc:TipoMensagemAVL`
- Colunas mapeadas (data properties): `event_dt`, `event_id`, `event_ts`, `gps_idx`, `gps_sinal`, `latitude`, `longitude`, `velocidade`, `viagem_sentido`

### Tabela `operational_events`
- Classe semantica: `tcc:EventoOperacional`
- Chave natural: `event_id+gps_idx` (event_id, gps_idx)
- Links semanticos: `cod_linha` -> `tcc:temLinha` -> `tcc:Linha`; `cod_veiculo` -> `tcc:temVeiculo` -> `tcc:Veiculo`; `id_empresa` -> `tcc:temEmpresa` -> `tcc:Empresa`; `cod_tabela_programacao` -> `tcc:temJornadaProgramacao` -> `tcc:JornadaProgramacao`; `tipo_mensagem` -> `tcc:temTipoMensagem` -> `tcc:TipoMensagemAVL`
- Colunas mapeadas (data properties): `event_dt`, `event_id`, `event_ts`, `gps_idx`, `gps_sinal`, `latitude`, `longitude`, `velocidade`, `viagem_sentido`

### Tabela `stop_events`
- Classe semantica: `tcc:EventoParada`
- Chave natural: `event_id+gps_idx` (event_id, gps_idx)
- Links semanticos: `cod_linha` -> `tcc:temLinha` -> `tcc:Linha`; `cod_veiculo` -> `tcc:temVeiculo` -> `tcc:Veiculo`; `id_empresa` -> `tcc:temEmpresa` -> `tcc:Empresa`; `cod_tabela_programacao` -> `tcc:temJornadaProgramacao` -> `tcc:JornadaProgramacao`; `tipo_mensagem` -> `tcc:temTipoMensagem` -> `tcc:TipoMensagemAVL`; `id_ponto` -> `tcc:ocorreNoPonto` -> `tcc:PontoParada`
- Colunas mapeadas (data properties): `event_dt`, `event_id`, `event_ts`, `gps_idx`, `gps_sinal`, `latitude`, `longitude`, `velocidade`, `viagem_sentido`


---

## Colunas obrigatorias da FinalTable (config.yaml)
- `event_dt`
- `cod_linha`
- `cod_veiculo`
- `janela_5min`
- `headway_observado_min`
- `headway_referencia_min`
- `atraso_aproximado_min`


---

## Regras semanticas (texto de referencia)
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

- Ontologia TTL: `tcc/docs/ontologia_transporte.ttl`
- Indicadores de qualidade Silver: `tcc/artifacts/dq_silver_report_2026-02-16.csv`
