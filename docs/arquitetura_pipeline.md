# Arquitetura e Pipeline de Dados

## Objetivo do documento
Consolidar a arquitetura técnica do projeto e a função de cada componente do pipeline.

## Visão geral
A arquitetura foi desenhada para separar claramente:
- armazenamento bruto e processado;
- processamento em lote;
- camada semântica;
- geração automatizada de código por LLM;
- avaliação de ML;
- publicação final de agregados gerenciais em grafo.

## Componentes principais
### MinIO
Usado como object storage local do projeto, com as camadas:
- `bronze`;
- `silver`;
- `gold`;
- `mart`.

O MinIO recebeu tanto o bruto oficial quanto as saídas Parquet intermediárias e finais.

### Spark / PySpark
Usado para:
- leitura do bruto `JSON Lines`;
- normalização e particionamento da Silver;
- sanity checks de wrangling;
- materialização e enriquecimento da Gold;
- execução dos pipelines de ML em escala local.

### Neo4j
Usado em duas funções distintas:
- publicação inicial de ontologia, mapeamentos e relações semânticas;
- publicação final de agregados gerenciais para exploração relacional e visualização em grafo.

### LLMs externas
Foram usadas duas LLMs hospedadas:
- OpenAI `gpt-4o`;
- `Llama 3.3 70B Instruct` via OpenRouter.

As LLMs não processaram diretamente o bruto de aproximadamente 37 GB. Elas receberam contexto textual estruturado e geraram código Python, depois executado e validado localmente no Spark.

## Camadas de dados
### Bronze
Conteúdo:
- bruto original `messages_fortaleza.json` em object storage.

Papel:
- preservar o dado fonte em formato bruto;
- servir como entrada única da etapa de engenharia de dados;
- manter auditabilidade da origem.

### Silver
Conteúdo:
- tabelas Parquet separadas por tipo funcional de evento:
  - `gps_events`
  - `stop_events`
  - `fare_events`
  - `operational_events`

Papel:
- reduzir heterogeneidade estrutural do bruto;
- criar schemas mais estáveis para joins, checks e prompts;
- preservar chaves operacionais e colunas de rastreabilidade.

### Gold
Conteúdo:
- `final_table` enriquecida.

Papel:
- concentrar features e target em granularidade de `janela_5min` por `cod_linha + cod_veiculo`;
- servir como base única para baseline, ML e agregados gerenciais.

### Mart
Conteúdo:
- reservado em configuração, mas não foi usado como camada central do experimento final.

Papel:
- permanecer como extensão possível para consumos derivados fora do escopo principal do projeto.

## Fluxo técnico do pipeline
### 1. Perfilamento e decisões de schema
Base de apoio:
- `artifacts/dq_profile_raw40gb_2026-02-14.md`
- `docs/schema_decisions.md`

Decisões principais:
- separar a Silver em quatro tabelas funcionais;
- preservar `id_empresa`, `cod_linha`, `cod_veiculo` e `event_ts` como eixos operacionais;
- manter GPS inválido como informação analítica, e não como descarte automático.

### 2. Bronze -> Silver
Script principal:
- `code/01_bronze_to_silver.py`

Saídas:
- partições Parquet em `s3a://transport/silver`

Transformações centrais:
- flatten de `avlHeader`;
- explode de `gps[]` quando aplicável;
- separação por tipo funcional de evento;
- normalização temporal e de coordenadas;
- particionamento para consumo posterior.

### 3. Qualidade da Silver
Script principal:
- `code/dq_silver_checks.py`

Saídas:
- relatórios CSV em `artifacts/dq_silver_report_*.csv`

Objetivo:
- validar se a Silver estava apta a sustentar a camada semântica, os prompts de wrangling e a Gold.

### 4. Camada semântica
Script principal:
- `code/02_build_semantic_model.py`

Recursos de apoio:
- `code/semantic_mapping.yaml`
- `docs/ontologia_transporte.ttl`
- `docs/regras_semanticas.md`
- `docs/mapeamento_silver_ontologia.md`

Papel arquitetural:
- explicitar o modelo conceitual do domínio;
- alinhar tabelas Silver a classes e relações semanticamente nomeadas;
- oferecer contexto estruturado para o Prompt 1 de wrangling;
- sustentar parte da exploração em grafo no Neo4j.

### 5. Wrangling com LLM
Scripts:
- `code/03_prompt_wrangling.py`
- `code/04_run_wrangling.py`
- `code/05_retry_wrangling.py`

Fluxo:
- renderizar prompt com schema, regras e contrato da `final_table`;
- gerar código via OpenAI e Llama;
- executar sanity check no Spark;
- em caso de erro, abrir retry com traceback real;
- selecionar e versionar a saída válida adotada.

Resultado arquitetural:
- o wrangling com LLM não grava diretamente a Gold final; ele gera o módulo de transformação que depois é validado, escolhido e incorporado à materialização final.

### 6. Materialização da Gold
Script:
- `code/06_materialize_final_table.py`

Fluxo:
- importar o wrangling aprovado da OpenAI;
- validar o contrato mínimo da `final_table`;
- recalcular métricas centrais de forma determinística;
- enriquecer a tabela com contexto operacional e espacial;
- escrever a Gold final em `s3a://transport/gold/final_table`.

Papel arquitetural:
- separar a comparação entre LLMs da construção efetiva da camada Gold final;
- garantir que a tabela de ML e decisão tenha qualidade e rastreabilidade suficientes.

### 7. ML e baseline
Scripts:
- `code/07_prompt_ml.py`
- `code/08_run_ml_codegen.py`
- `code/09_run_baseline.py`
- `code/10_run_ml_pipeline.py`
- `code/11_retry_ml.py`

Fluxo:
- renderizar prompt de ML a partir da Gold enriquecida;
- gerar código via LLM;
- validar importação e execução;
- rodar o baseline definido para comparação;
- rodar retries quando necessário;
- comparar rodadas e fixar a referência metodológica principal.

Papel arquitetural:
- manter baseline e pipelines LLM lado a lado sob o mesmo contrato de dados e split temporal.

### 8. Agregados para decisão
Script:
- `code/12_generate_decision_aggregates.py`

Fontes adotadas após refinamento metodológico:
- baseline v2;
- pipeline Llama v2 válido.

Saídas principais:
- ranking de linhas críticas;
- ranking de faixas horárias críticas;
- erro por segmento;
- instabilidade por veículo;
- manifestos para carga final no Neo4j.

### 9. Publicação final no Neo4j
Script:
- `code/13_publish_neo4j.py`

Papel:
- transformar agregados tabulares finais em uma camada relacional explorável em grafo;
- permitir consultas gerenciais e evidência visual no projeto.

## Ordem de execução dos scripts
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

## Princípios de desenho adotados
### Separação entre comparação e produção
A comparação entre LLMs foi mantida nas etapas de geração, sanity check e retry. A Gold final foi enriquecida depois, de forma determinística, para não contaminar a comparação experimental.

### Rastreabilidade obrigatória
Cada etapa relevante precisou manter o vínculo entre:
- script;
- configuração;
- evidência;
- registro no diário técnico privado do projeto original.

### Preferência por contratos explícitos
A arquitetura privilegiou:
- schemas nomeados na Silver;
- colunas obrigatórias na Gold;
- prompts versionados;
- regras formais de retry;
- métricas adotadas e política anti-vazamento na rodada 2 de ML.

### Uso seletivo do Neo4j
O Neo4j não foi usado para armazenar o bruto ou a Silver completa. Ele foi reservado para os pontos em que o grafo agrega valor real:
- estrutura conceitual do domínio;
- navegação final sobre agregados gerenciais.

## Evidências-chave desta arquitetura
- `README.md`
- `docs/reproducibility_matrix.md`
- `docs/schema_decisions.md`
- `docs/final_table_enrichment.md`
- `docs/ml_v2_methodological_rules.md`
- `artifacts/aggregate_source_contract_2026-04-18.md`
- `artifacts/neo4j_final_validation_2026-04-18.md`
