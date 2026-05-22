# Comparacao de Wrangling LLMs - 2026-04-03

Prompt base utilizado:
- `tcc/artifacts/prompt_1_wrangling_rendered_2026-03-12_2027.md`

## OpenAI - gpt-4o
- chamada: `tcc/artifacts/wrangling_call_openai_gpt_4o_2026-03-12_2205.json`
- codigo: `tcc/code/generated/wrangling_openai_gpt_4o_2026-03-12_2205.py`
- compilacao Python: `ok`
- sanity check Spark: `falhou`
- ponto de falha: `unionByName` entre tabelas Silver com schemas diferentes
- evidencia: `tcc/artifacts/wrangling_sanity_openai_2026-04-03_v2.txt`
- observacao: gerou funcoes importaveis, mas a logica assumiu compatibilidade estrutural inexistente entre `gps_events`, `stop_events`, `fare_events` e `operational_events`

## OpenRouter - Llama 3.3 70B Instruct
- chamada: `tcc/artifacts/wrangling_call_openrouter_meta_llama_llama_3_3_70b_instruct_2026-04-03_1434.json`
- codigo: `tcc/code/generated/wrangling_openrouter_meta_llama_llama_3_3_70b_instruct_2026-04-03_1434.py`
- compilacao Python: `ok`
- sanity check Spark: `nao chegou a executar`
- ponto de falha: import do modulo
- evidencia: `tcc/artifacts/wrangling_sanity_openrouter_2026-04-03.txt`
- erro objetivo: `NameError: name 'DataFrame' is not defined`
- observacao: a saida incluiu anotacoes com `DataFrame` sem importar o simbolo e ainda trouxe um bloco de exemplo executavel fora de `if __name__ == "__main__":`, o que torna o arquivo inadequado para uso direto como modulo gerado

## Comparacao objetiva
- sucesso de geracao: ambos `sim`
- codigo salvo com versao/data: ambos `sim`
- compilacao Python: ambos `sim`
- importavel sem ajuste manual: OpenAI `sim`; Llama `nao`
- execucao funcional em Spark sem ajuste manual: OpenAI `nao`; Llama `nao`
- melhor resultado nesta etapa: `OpenAI`, porque ao menos chegou a executar ate o ponto de erro de logica de schema

## Decisao tecnica
- manter ambos como evidencias validas da etapa 7
- seguir com um fluxo de retry controlado na proxima iteracao, usando os erros reais capturados como entrada objetiva do novo prompt
