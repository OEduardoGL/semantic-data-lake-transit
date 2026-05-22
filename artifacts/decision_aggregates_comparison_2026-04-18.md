# Comparacao dos Agregados Antigos vs Atualizados

## Contexto
A etapa 12 original usou `baseline + OpenAI retry 2` da rodada 1.
A etapa 12.1 atualizada usa `baseline v2 + Llama v2 (retry 2)` da rodada 2, com:
- horizonte preditivo `t+1`
- controle anti-vazamento
- exclusao da OpenAI v2 do pacote final
- filtros minimos de suporte para uso gerencial

## Observacao metodologica
Os dois conjuntos de agregados nao sao estritamente equivalentes, porque a rodada 2 mudou deliberadamente o problema de ML.
Ainda assim, a comparacao e util para mostrar como o refinamento metodologico alterou a leitura gerencial.

## Linha critica principal
### Etapa 12 antiga
- `cod_linha = 958`
- `pred_atraso_aproximado_min = 1.017714`
- `n_registros = 180`
- fonte: `OpenAI retry 2`

### Etapa 12.1 atualizada
- `cod_linha = 150`
- `pred_atraso_aproximado_min = 2.143987`
- `n_registros = 15`
- fonte: `Llama v2 retry 2`

## Faixa horaria critica principal
### Etapa 12 antiga
- `hour = 23`
- `pred_atraso_aproximado_min = 0.588284`
- `n_registros = 3241`

### Etapa 12.1 atualizada
- `hour = 23`
- `pred_atraso_aproximado_min = 1.029320`
- `n_registros = 2816`

## Veiculo mais instavel
### Etapa 12 antiga
- `cod_veiculo = 10411`
- `mean_abs_gap_pred_real = 67.646642`
- `n_registros = 1`
- leitura: ranking muito fragil por suporte minimo insuficiente

### Etapa 12.1 atualizada
- `cod_veiculo = 9974`
- `mean_abs_gap_pred_real = 10.682689`
- `n_registros = 10`
- leitura: ranking mais robusto para visualizacao final

## Segmento com maior erro medio absoluto
### Etapa 12 antiga
- `cod_linha = 70`
- `cod_veiculo = 4292`
- `hour = 23`
- `mean_abs_error = 163.514150`
- `n_registros = 1`

### Etapa 12.1 atualizada
- `cod_linha = 625`
- `cod_veiculo = 3333`
- `hour = 20`
- `mean_abs_error = 31.524338`
- `n_registros = 5`

## Conclusoes
- os agregados atualizados sao mais coerentes com a rodada 2 de ML, que e a referencia metodologica principal do TCC;
- o uso de suporte minimo eliminou rankings artificiais baseados em observacao unica;
- a etapa 12 antiga deve permanecer no TCC como historico da rodada 1;
- o pacote final para Neo4j deve usar os agregados gerados em `2026-04-18_2044`.
