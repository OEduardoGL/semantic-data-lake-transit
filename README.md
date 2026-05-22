# Semantic Data Lake Transit

Repositório curado com scripts, prompts, documentação técnica e evidências de um pipeline experimental para dados AVL de transporte público urbano. O fluxo combina engenharia de dados em camadas, gestão semântica, geração de código com LLMs, avaliação de Machine Learning, baseline histórico, agregados gerenciais e publicação final em Neo4j.

## Objetivo

O projeto avalia se um pipeline end-to-end pode transformar dados operacionais brutos de transporte público em uma base analítica enriquecida e em resultados gerenciais rastreáveis. O foco não é demonstrar superioridade preditiva de modelos gerados por LLM, mas documentar um processo executável, auditável e criticamente avaliado.

## Estrutura

- `code/`: scripts numerados do pipeline e códigos gerados por LLM preservados como artefatos técnicos.
- `prompts/`: prompts versionados usados para wrangling, ML e retries.
- `docs/`: documentação técnica mínima para arquitetura, schema, semântica, ML e reprodutibilidade.
- `artifacts/`: evidências pequenas e selecionadas dos experimentos, incluindo métricas, validações e relatórios.
- `figures/`: imagens usadas para documentação e interpretação dos resultados.
- `infra/`: composição local mínima para MinIO e Neo4j, sem volumes ou credenciais reais.
- `data/`: amostras pequenas da tabela final; a base bruta completa não é distribuída.

## Fluxo resumido

1. Ingestão e normalização dos eventos AVL em camadas Bronze e Silver.
2. Construção de uma camada semântica com entidades e relações do domínio.
3. Geração de código de wrangling por LLM a partir de prompts estruturados.
4. Materialização e enriquecimento determinístico da camada Gold (`final_table`).
5. Geração de pipeline de ML, baseline histórico e métricas revisadas.
6. Produção de agregados gerenciais por linha, horário, veículo e segmento.
7. Publicação dos agregados no Neo4j para exploração em grafo.

## Execução local

Crie um arquivo de ambiente a partir do exemplo:

```bash
cp .env.example .env
```

Suba os serviços locais:

```bash
docker compose -f infra/docker-compose.yml --env-file .env up -d
```

Crie a configuração efetiva do pipeline:

```bash
cp code/config.example.yaml code/config.yaml
```

Instale as dependências Python:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r code/requirements.txt
```

A ordem lógica dos scripts está documentada em `code/README.md`. Para reprodução completa, é necessário disponibilizar localmente a base AVL bruta no caminho configurado em `code/config.yaml`.

## Resultados principais preservados

- Validação da camada Gold: `artifacts/final_table_validation_2026-04-03_2243.md`.
- Diagnóstico da primeira rodada de ML: `artifacts/ml_round1_diagnosis_2026-04-18.md`.
- Comparação final de ML: `artifacts/ml_round_comparison_2026-04-18.md`.
- Métricas do baseline: `artifacts/metrics_ml_baseline_2026-04-18_1904.csv`.
- Métricas do pipeline Llama v2: `artifacts/metrics_ml_llama_3_3_70b_v2_retry2_2026-04-18_1924.csv`.
- Validação final do Neo4j: `artifacts/neo4j_final_validation_2026-04-18.md`.
- Queries Cypher finais: `artifacts/neo4j_final_queries_2026-04-18.md`.

## Limitação de dados

A base bruta não é publicada por volume e por restrições práticas de distribuição. As amostras em `data/` servem apenas para inspeção de formato e não substituem a execução completa do pipeline.

## Reprodutibilidade

A matriz de reprodutibilidade está em `docs/reproducibility_matrix.md`. O registro técnico completo do projeto original não é publicado neste repositório; as evidências selecionadas foram preservadas em `artifacts/`, `docs/` e `figures/`.
