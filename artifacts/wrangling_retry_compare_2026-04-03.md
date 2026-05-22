# Comparacao de Retry de Wrangling - 2026-04-03

## Escopo
Comparacao completa das tentativas reais de retry de wrangling para:
- OpenAI `gpt-4o`
- OpenRouter `Llama 3.3 70B Instruct`

Historico consolidado em:
- `tcc/artifacts/wrangling_retry_log_2026-04-03.csv`

## OpenAI - gpt-4o
### attempt 1
- tempo: ver `elapsed_sec` no CSV consolidado
- resultado: `erro`
- erro: `AnalysisException`
- causa objetiva: `event_ts` estava como `BIGINT` na chamada de `window(..., '5 minutes')`
- evidencia: `tcc/artifacts/wrangling_sanity_openai_retry_attempt1_2026-04-03.txt`

### attempt 2
- tempo: ver `elapsed_sec` no CSV consolidado
- resultado: `ok`
- import do modulo: `ok`
- `build_final_table_status`: `ok`
- linhas geradas: `9512`
- schema final minimo presente: `sim`
- evidencia: `tcc/artifacts/wrangling_sanity_openai_retry_attempt2_2026-04-03.txt`

## OpenRouter - Llama 3.3 70B Instruct
### attempt 1
- tempo: ver `elapsed_sec` no CSV consolidado
- resultado: `erro`
- erro: `TypeError`
- causa objetiva: uso incorreto de `window()` em contexto de `over(...)`
- evidencia: `tcc/artifacts/wrangling_sanity_openrouter_retry_attempt1_2026-04-03.txt`

### attempt 2
- tempo: ver `elapsed_sec` no CSV consolidado
- resultado: `erro`
- erro: `AnalysisException`
- causa objetiva: referencia ambigua a `event_dt` apos joins entre tabelas com colunas homonimas
- evidencia: `tcc/artifacts/wrangling_sanity_openrouter_retry_attempt2_2026-04-03.txt`

### attempt 3
- tempo: ver `elapsed_sec` no CSV consolidado
- resultado: `erro`
- erro: `AnalysisException`
- causa objetiva: uso invalido de `lag()` com frame explicito (`Cannot specify window frame for lag function`)
- evidencia: `tcc/artifacts/wrangling_sanity_openrouter_retry_attempt3_2026-04-03.txt`

## Comparacao objetiva final do wrangling
- OpenAI convergiu no `attempt 2`
- Llama nao convergiu ate o limite de `attempt 3`
- ambos os modelos melhoraram entre tentativas, mas a OpenAI convergiu com menos retries e menor ambiguidade tecnica
- melhor resultado final do wrangling: `OpenAI gpt-4o`

## Decisao metodologica
- a comparacao de wrangling pode ser considerada completa:
  - mesmo prompt base semantico
  - mesmos criterios de sucesso
  - mesmo fluxo de retry guiado por erro real
  - limite maximo de 3 tentativas aplicado
- a versao OpenAI do `attempt 2` deve seguir para a etapa 9 (`final_table`)
- a Llama permanece como baseline comparativo que nao convergiu no limite definido
