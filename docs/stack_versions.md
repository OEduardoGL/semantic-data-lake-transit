# Versoes das Ferramentas (Base do projeto)

## 1) Versoes detectadas no ambiente atual
- Python: 3.12.3
- pip: 24.0
- Java: OpenJDK 21.0.10
- Docker: 28.5.1
- Docker Compose: 2.40.0
- PySpark (venv `code/.venv`): 3.5.3 (validado com sessao local)
- Spark CLI (`spark-submit`): nao instalado
- Neo4j CLI (`neo4j`): nao instalado
- Neo4j Desktop: 2.0.3 (instalado localmente)

## 2) Versoes-alvo do projeto

### Runtime
- Python: 3.12.x
- Java: 21

### Processamento de dados
- Apache Spark: 3.5.3
- Delta Lake (`delta-spark`): 3.2.0

### Banco de grafo
- Neo4j: 5.26.x (LTS da serie 5)
- Neo4j Python Driver: 5.28.x

### LLM/API
- OpenAI Python SDK: 1.x (fixar no `requirements.txt`)
- Modelo fechado principal: `gpt-4o`
- Modelo open source de comparacao: `Llama 3.3 70B Instruct`
- Recomendacao pratica: consumir a LLM open source via provedor compativel com API (ex.: OpenRouter/Together), evitando execucao local.

### Bibliotecas auxiliares
- pandas: 2.2.x
- pyarrow: 17.x
- pyyaml: 6.0.x

## 3) Observacao de padronizacao
Para evitar drift de ambiente, manter as versoes pinadas em:
- `code/requirements.txt`
- imagem Docker (quando usada) para Spark/Neo4j.
