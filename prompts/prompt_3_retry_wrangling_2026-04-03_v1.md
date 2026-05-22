# Prompt 3 - Retry de Wrangling Semantico (v1)

## Objetivo
Corrigir codigo PySpark de wrangling previamente gerado por uma LLM que falhou em importacao ou execucao.

Este prompt deve ser usado no fluxo:
`codigo anterior -> erro real/traceback -> correcao pela LLM -> novo sanity check`.

Escopo desta versao:
- suportar retry controlado para:
  - OpenAI `gpt-4o`;
  - `Llama 3.3 70B Instruct`;
- usar como entrada o codigo anterior e o erro real observado;
- produzir uma nova versao executavel do wrangling, sem explicacoes fora do codigo.

## Contexto obrigatorio a ser fornecido ao modelo
Ao montar este prompt para execucao real, incluir sempre:

1. O codigo anterior completo que falhou.
2. O traceback real completo, sem resumir.
3. O resumo objetivo do erro.
4. As regras semanticas obrigatorias.
5. O contrato de saida obrigatorio.

## Resumo dos erros reais ja observados
### Caso OpenAI
- erro principal: `AnalysisException` em `unionByName`
- causa objetiva: tentativa de unir `gps_events`, `stop_events`, `fare_events` e `operational_events` como se tivessem schemas identicos
- restricao implicita para a correcao:
  - nao usar `unionByName` entre tabelas de schemas diferentes sem padronizacao explicita de colunas

### Caso Llama
- erro principal: `NameError: name 'DataFrame' is not defined`
- causa objetiva: uso de anotacao `DataFrame` sem importar o simbolo
- problema adicional:
  - o codigo incluiu um bloco de exemplo executavel fora de `if __name__ == "__main__":`
- restricao implicita para a correcao:
  - o arquivo gerado precisa ser importavel como modulo, sem executar exemplos no import

## Regras semanticas obrigatorias
Aplicar obrigatoriamente estas regras:

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
A saida deve conter, no minimo:
- `event_dt`
- `cod_linha`
- `cod_veiculo`
- `janela_5min`
- `headway_observado_min`
- `headway_referencia_min`
- `atraso_aproximado_min`

## Contrato de saida obrigatorio
Responda com **apenas codigo Python** contendo:

1. Imports completos e corretos no topo.
2. Funcao principal com assinatura exata:
```python
def build_final_table(df_dict: dict[str, DataFrame]) -> DataFrame:
    ...
```
3. Funcao de validacao:
```python
def validate_final_table(df_final: DataFrame) -> None:
    ...
```

## Restricoes tecnicas obrigatorias
- usar apenas API PySpark DataFrame;
- nao usar Pandas;
- nao incluir texto explicativo fora do codigo;
- nao incluir exemplo executavel fora de `if __name__ == "__main__":`;
- o arquivo precisa ser importavel como modulo sem side effects;
- validar presenca de colunas minimas antes das transformacoes;
- falhar com erro explicito quando faltar coluna critica;
- evitar `unionByName` entre tabelas com schemas diferentes, salvo se houver alinhamento explicito de schema;
- preferir joins, agregacoes e selecoes semanticamente consistentes com as 4 tabelas Silver;
- manter transformacoes deterministicas.

## Instrucoes de correcao
Corrija o codigo anterior levando em conta o erro observado.

Regras para a resposta:
- preserve o maximo possivel do que estiver correto;
- altere apenas o necessario para tornar o modulo importavel e a logica executavel;
- se o erro vier de schema, corrija a estrategia de combinacao das tabelas;
- se o erro vier de importacao, corrija imports, anotacoes e side effects;
- retorne uma nova versao completa do codigo, nao apenas diff.

## Variaveis de entrada esperadas na montagem do prompt renderizado
Na execucao real, o runner deve preencher algo como:

```text
{{MODEL_NAME}}
{{FAILED_CODE}}
{{ERROR_SUMMARY}}
{{TRACEBACK}}
```

## Formato final da resposta da LLM
- um unico bloco de codigo Python executavel;
- sem markdown adicional fora do bloco;
- com imports necessarios no topo;
- pronto para salvar como nova versao do wrangling.
