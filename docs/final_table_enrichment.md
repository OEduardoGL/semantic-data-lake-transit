# Enriquecimento da FinalTable

## Motivo
A `final_table` gerada pelo wrangling aprovado da OpenAI preservou o contrato mínimo da etapa de comparação entre LLMs, mas permaneceu insuficiente para ML e visualização gerencial:
- continha apenas as colunas obrigatórias mínimas;
- as métricas `headway_observado_min`, `headway_referencia_min` e `atraso_aproximado_min` vinham como `null`.

Por isso, o enriquecimento foi realizado como refinamento determinístico na etapa 9 (`Gold`), sem reabrir a comparação entre OpenAI e Llama.

## Princípio metodológico
A comparação entre LLMs ficou encerrada nas etapas 7 e 8:
- mesmo contexto semântico;
- mesmo fluxo de retry;
- mesmo limite de tentativas.

O enriquecimento da `final_table` não altera esse experimento. Sua função é transformar a saída selecionada do wrangling em uma tabela Gold adequada às etapas seguintes.

## Como foi feito
O enriquecimento foi implementado em `code/06_materialize_final_table.py`.

### 1. Base contratual da LLM
Primeiro, o script executa o módulo aprovado do wrangling OpenAI e valida o contrato mínimo:
- `event_dt`
- `cod_linha`
- `cod_veiculo`
- `janela_5min`
- `headway_observado_min`
- `headway_referencia_min`
- `atraso_aproximado_min`

### 2. Regras semânticas reaplicadas
Antes do enriquecimento, o script reaplica regras semânticas determinísticas sobre Silver:
- `id_empresa`, `cod_linha`, `cod_veiculo` com fallback para `-1`;
- `viagem_sentido` com fallback para `ND`;
- `event_ts` convertido para timestamp canônico;
- criação da `janela_5min`;
- criação da flag `gps_is_invalid`.

### 3. Contexto por janela de veículo
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

### 4. Cálculo de headway observado
A partir de `stop_events`, o script:
- ordena eventos por `event_ts_ts` dentro de `event_dt`, `cod_linha`, `viagem_sentido`;
- calcula a diferença para o evento anterior com `lag`;
- converte a diferença para minutos (`headway_diff_min`);
- descarta diferenças nulas, negativas ou acima de 180 minutos;
- agrega por janela de 5 minutos para formar `headway_observado_min`.

### 5. Cálculo de headway de referência
Ainda a partir da série observada, o script calcula:
- `faixa_horaria = hour(janela_5min)`
- `headway_referencia_min = percentile_approx(headway_observado_min, 0.5)`

A referência é calculada por:
- `cod_linha`
- `viagem_sentido`
- `faixa_horaria`

### 6. Cálculo do target final
O target final segue a definição fechada do plano:
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
- várias janelas possuem `gps_invalid_pct` alto;
- a Gold enriquecida exigiu ajuste de memória no Spark local para concluir a gravação completa.

## Evidências
- `code/06_materialize_final_table.py`
- `artifacts/final_table_materialization_2026-04-03_2237.md`
- `artifacts/final_table_validation_2026-04-03_2243.md`
