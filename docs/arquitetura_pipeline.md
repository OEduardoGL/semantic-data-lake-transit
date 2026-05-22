# Arquitetura e Pipeline de Dados

## Objetivo do documento
Consolidar a arquitetura tecnica do projeto e a funcao de cada componente do pipeline.

## Visao geral
A arquitetura foi desenhada para separar claramente:
- armazenamento bruto e processado;
- processamento em lote;
- camada semantica;
- geracao automatizada de codigo por LLM;
- avaliacao de ML;
- publicacao final de agregados gerenciais em grafo.

## Componentes principais
### MinIO
Usado como object storage local do projeto, com as camadas:
- `bronze`;
- `silver`;
- `gold`;
- `mart`.

O MinIO recebeu tanto o bruto oficial quanto as saidas Parquet intermediarias e finais.

### Spark / PySpark
Usado para:
- leitura do bruto `JSON Lines`;
- normalizacao e particionamento da Silver;
- sanity checks de wrangling;
- materializacao e enriquecimento da Gold;
- execucao dos pipelines de ML em escala local.

### Neo4j
Usado em duas funcoes distintas:
- publicacao inicial de ontologia, mapeamentos e relacoes semanticas;
- publicacao final de agregados gerenciais para exploracao relacional e visualizacao em grafo.

### LLMs externas
Foram usadas duas LLMs hospedadas:
- OpenAI `gpt-4o`;
- `Llama 3.3 70B Instruct` via OpenRouter.

As LLMs nao processaram diretamente o bruto de aproximadamente 37 GB. Elas receberam contexto textual estruturado e geraram codigo Python, depois executado e validado localmente no Spark.

## Camadas de dados
### Bronze
Conteudo:
- bruto original `messages_fortaleza.json` em object storage.

Papel:
- preservar o dado fonte em formato bruto;
- servir como entrada unica da etapa de engenharia de dados;
- manter auditabilidade da origem.

### Silver
Conteudo:
- tabelas Parquet separadas por tipo funcional de evento:
  - `gps_events`
  - `stop_events`
  - `fare_events`
  - `operational_events`

Papel:
- reduzir heterogeneidade estrutural do bruto;
- criar schemas mais estaveis para joins, checks e prompts;
- preservar chaves operacionais e colunas de rastreabilidade.

### Gold
Conteudo:
- `final_table` enriquecida.

Papel:
- concentrar features e target em granularidade de `janela_5min` por `cod_linha + cod_veiculo`;
- servir como base unica para baseline, ML e agregados gerenciais.

### Mart
Conteudo:
- reservado em configuracao, mas nao foi usado como camada central do experimento final.

Papel:
- permanecer como extensao possivel para consumos derivados fora do escopo principal do projeto.

## Fluxo tecnico do pipeline
### 1. Perfilamento e decisoes de schema
Base de apoio:
- `artifacts/dq_profile_raw40gb_2026-02-14.md`
- `docs/schema_decisions.md`

Decisoes principais:
- separar a Silver em quatro tabelas funcionais;
- preservar `id_empresa`, `cod_linha`, `cod_veiculo` e `event_ts` como eixos operacionais;
- manter GPS invalido como informacao analitica, e nao como descarte automatico.

### 2. Bronze -> Silver
Script principal:
- `code/01_bronze_to_silver.py`

Saidas:
- particoes Parquet em `s3a://transport/silver`

Transformacoes centrais:
- flatten de `avlHeader`;
- explode de `gps[]` quando aplicavel;
- separacao por tipo funcional de evento;
- normalizacao temporal e de coordenadas;
- particionamento para consumo posterior.

### 3. Qualidade da Silver
Script principal:
- `code/dq_silver_checks.py`

Saidas:
- relatorios CSV em `artifacts/dq_silver_report_*.csv`

Objetivo:
- validar se a Silver estava apta a sustentar a camada semantica, os prompts de wrangling e a Gold.

### 4. Camada semantica
Script principal:
- `code/02_build_semantic_model.py`

Recursos de apoio:
- `code/semantic_mapping.yaml`
- `docs/ontologia_transporte.ttl`
- `docs/regras_semanticas.md`
- `docs/mapeamento_silver_ontologia.md`

Papel arquitetural:
- explicitar o modelo conceitual do dominio;
- alinhar tabelas Silver a classes e relacoes semanticamente nomeadas;
- oferecer contexto estruturado para o Prompt 1 de wrangling;
- sustentar parte da exploracao em grafo no Neo4j.

### 5. Wrangling com LLM
Scripts:
- `code/03_prompt_wrangling.py`
- `code/04_run_wrangling.py`
- `code/05_retry_wrangling.py`

Fluxo:
- renderizar prompt com schema, regras e contrato da `final_table`;
- gerar codigo via OpenAI e Llama;
- executar sanity check no Spark;
- em caso de erro, abrir retry com traceback real;
- congelar a melhor saida valida.

Resultado arquitetural:
- o wrangling LLM nao grava diretamente a Gold final; ele gera o modulo de transformacao que depois e validado, escolhido e incorporado na materializacao oficial.

### 6. Materializacao da Gold
Script:
- `code/06_materialize_final_table.py`

Fluxo:
- importar o wrangling aprovado da OpenAI;
- validar o contrato minimo da `final_table`;
- recalcular metricas centrais de forma deterministica;
- enriquecer a tabela com contexto operacional e espacial;
- escrever a Gold final em `s3a://transport/gold/final_table`.

Papel arquitetural:
- separar a comparacao entre LLMs da construcao efetiva da camada Gold final;
- garantir que a tabela de ML e decisao tenha qualidade e rastreabilidade suficientes.

### 7. ML e baseline
Scripts:
- `code/07_prompt_ml.py`
- `code/08_run_ml_codegen.py`
- `code/09_run_baseline.py`
- `code/10_run_ml_pipeline.py`
- `code/11_retry_ml.py`

Fluxo:
- renderizar prompt de ML a partir da Gold enriquecida;
- gerar codigo via LLM;
- validar importacao e execucao;
- rodar baseline oficial;
- rodar retries quando necessario;
- comparar rodadas e congelar a referencia metodologica principal.

Papel arquitetural:
- manter baseline e pipelines LLM lado a lado sob o mesmo contrato de dados e split temporal.

### 8. Agregados para decisao
Script:
- `code/12_generate_decision_aggregates.py`

Fontes oficiais apos refinamento metodologico:
- baseline v2;
- Llama v2 valida.

Saidas principais:
- ranking de linhas criticas;
- ranking de faixas horarias criticas;
- erro por segmento;
- instabilidade por veiculo;
- manifestos para carga final no Neo4j.

### 9. Publicacao final no Neo4j
Script:
- `code/13_publish_neo4j.py`

Papel:
- transformar agregados tabulares finais em uma camada relacional exploravel em grafo;
- permitir consultas gerenciais e evidencia visual no projeto.

## Ordem oficial dos scripts
1. `code/01_bronze_to_silver.py`
2. `code/dq_silver_checks.py`
3. `code/02_build_semantic_model.py`
4. `code/03_prompt_wrangling.py`
5. `code/04_run_wrangling.py`
6. `code/05_retry_wrangling.py`
7. `code/06_materialize_final_table.py`
8. `code/07_prompt_ml.py`
9. `code/08_run_ml_codegen.py`
10. `code/09_run_baseline.py`
11. `code/10_run_ml_pipeline.py`
12. `code/11_retry_ml.py`
13. `code/12_generate_decision_aggregates.py`
14. `code/13_publish_neo4j.py`

## Principios de desenho adotados
### Separacao entre comparacao e producao
A comparacao entre LLMs foi mantida nas etapas de geracao, sanity check e retry. A Gold final foi enriquecida depois, de forma deterministica, para nao contaminar a comparacao experimental.

### Rastreabilidade obrigatoria
Cada etapa relevante precisou manter o vinculo entre:
- script;
- configuracao;
- evidencia;
- registro no registro tecnico privado do projeto original.

### Preferencia por contratos explicitos
A arquitetura privilegiou:
- schemas nomeados na Silver;
- colunas obrigatorias na Gold;
- prompts versionados;
- regras formais de retry;
- metricas oficiais e politica anti-vazamento na rodada 2 de ML.

### Uso seletivo do Neo4j
O Neo4j nao foi usado para armazenar o bruto ou a Silver completa. Ele foi reservado para os pontos em que o grafo agrega valor real:
- estrutura conceitual do dominio;
- navegacao final sobre agregados gerenciais.

## Evidencias-chave desta arquitetura
- `README.md`
- `docs/reproducibility_matrix.md`
- `docs/schema_decisions.md`
- `docs/final_table_enrichment.md`
- `docs/ml_v2_methodological_rules.md`
- `artifacts/aggregate_source_contract_2026-04-18.md`
- `artifacts/neo4j_final_validation_2026-04-18.md`
