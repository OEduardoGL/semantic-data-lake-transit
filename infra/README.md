# Infraestrutura local

Este diretório contém uma composição mínima para MinIO e Neo4j. Volumes locais e credenciais reais não são versionados.

Uso:

```bash
cp ../.env.example ../.env
docker compose -f docker-compose.yml --env-file ../.env up -d
```

Serviços:

- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`
- Neo4j Browser: `http://localhost:7474`
- Neo4j Bolt: `bolt://localhost:7687`
