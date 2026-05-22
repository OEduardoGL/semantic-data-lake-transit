# Enriquecimento da FinalTable

## Motivo
A `final_table` gerada pelo wrangling aprovado da OpenAI preservou o contrato minimo da etapa de comparacao entre LLMs, mas permaneceu pobre para ML e visualizacao gerencial:
- continha apenas as colunas obrigatorias minimas;
- as metricas `headway_observado_min`, `headway_referencia_min` e `atraso_aproximado_min` vinham como `null`.

Por isso, o enriquecimento foi realizado como refinamento deterministico na etapa 9 (`Gold`), sem reabrir a comparacao entre OpenAI e Llama.

## Principio metodologico
A comparacao entre LLMs ficou encerrada nas etapas 7 e 8:
- mesmo contexto semantico;
- mesmo fluxo de retry;
- mesmo limite de tentativas.

O enriquecimento da `final_table` nao altera esse experimento. Ele apenas transforma a saida vencedora do wrangling em uma tabela Gold util para as etapas seguintes.

## Como foi feito
O enriquecimento foi implementado em `code/06_materialize_final_table.py`.

### 1. Base contratual da LLM
Primeiro, o script executa o modulo aprovado do wrangling OpenAI e valida o contrato minimo:
- `event_dt`
- `cod_linha`
- `cod_veiculo`
- `janela_5min`
- `headway_observado_min`
- `headway_referencia_min`
- `atraso_aproximado_min`

### 2. Regras semanticas reaplicadas
Antes do enriquecimento, o script reaplica regras semanticas deterministicas sobre Silver:
- `id_empresa`, `cod_linha`, `cod_veiculo` com fallback para `-1`;
- `viagem_sentido` com fallback para `ND`;
- `event_ts` convertido para timestamp canonico;
- criacao da `janela_5min`;
- criacao da flag `gps_is_invalid`.

### 3. Contexto por janela de veiculo
A partir de `gps_events`, o script agrega por:
- `event_dt`
- `cod_linha`
- `cod_veiculo`
- `janela_5min`

Gerando:
- `id_empresa`
- `viagem_sentido`
- `latitude_media`
- `longitude_media`
- `velocidade_media`
- `gps_invalid_pct`
- `qtd_eventos_gps`
- `max_satelites`

### 4. Calculo de headway observado
A partir de `stop_events`, o script:
- ordena eventos por `event_ts_ts` dentro de `event_dt`, `cod_linha`, `viagem_sentido`;
- calcula a diferenca para o evento anterior com `lag`;
- converte a diferenca para minutos (`headway_diff_min`);
- descarta diferencas nulas, negativas ou acima de 180 minutos;
- agrega por janela de 5 minutos para formar `headway_observado_min`.

### 5. Calculo de headway de referencia
Ainda a partir da serie observada, o script calcula:
- `faixa_horaria = hour(janela_5min)`
- `headway_referencia_min = percentile_approx(headway_observado_min, 0.5)`

A referencia e calculada por:
- `cod_linha`
- `viagem_sentido`
- `faixa_horaria`

### 6. Calculo do target final
O target final segue a definicao fechada do plano:
- `atraso_aproximado_min = max(0, headway_observado_min - headway_referencia_min)`

## Colunas finais produzidas
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

## Limites observados
- `viagem_sentido` ainda aparece muitas vezes como `ND`;
- varias janelas possuem `gps_invalid_pct` alto;
- a Gold enriquecida exigiu ajuste de memoria no Spark local para concluir a gravacao full.

## Evidencias
- `code/06_materialize_final_table.py`
- `artifacts/final_table_materialization_2026-04-03_2237.md`
- `artifacts/final_table_validation_2026-04-03_2243.md`
