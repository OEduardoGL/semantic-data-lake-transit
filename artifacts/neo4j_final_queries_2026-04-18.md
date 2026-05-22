# Neo4j Final Queries

## Query 1 - Top linhas por atraso previsto
```cypher
MATCH (run:DecisionAggregateRun {id: 'agg_final_2026_04_18_2044'})-[r:RANKS_LINE]->(l:Linha)
RETURN l.code AS cod_linha,
       r.rank AS rank,
       r.pred_atraso_aproximado_min AS pred_atraso_aproximado_min,
       r.real_atraso_aproximado_min AS real_atraso_aproximado_min,
       r.n_registros AS n_registros
ORDER BY r.rank ASC
LIMIT 10;
```

## Query 2 - Faixas horarias criticas
```cypher
MATCH (run:DecisionAggregateRun {id: 'agg_final_2026_04_18_2044'})-[r:RANKS_HOUR]->(h:FaixaHoraria)
RETURN h.hour AS hour,
       r.rank AS rank,
       r.pred_atraso_aproximado_min AS pred_atraso_aproximado_min,
       r.real_atraso_aproximado_min AS real_atraso_aproximado_min,
       r.n_registros AS n_registros
ORDER BY r.rank ASC
LIMIT 10;
```

## Query 3 - Veiculos mais instaveis
```cypher
MATCH (run:DecisionAggregateRun {id: 'agg_final_2026_04_18_2044'})-[r:RANKS_VEHICLE]->(v:Veiculo)
RETURN v.code AS cod_veiculo,
       r.rank AS rank,
       r.mean_abs_gap_pred_real AS mean_abs_gap_pred_real,
       r.pred_atraso_aproximado_min AS pred_atraso_aproximado_min,
       r.real_atraso_aproximado_min AS real_atraso_aproximado_min,
       r.n_registros AS n_registros
ORDER BY r.rank ASC
LIMIT 10;
```

## Query 4 - Linha/hora com maior gap versus baseline
```cypher
MATCH (:DecisionAggregateRun {id: 'agg_final_2026_04_18_2044'})-[:INCLUDES_LINE_HOUR]->(m:LineHourMetric)-[:AT_HOUR]->(h:FaixaHoraria)
MATCH (l:Linha)-[:HAS_LINE_HOUR_METRIC]->(m)
RETURN l.code AS cod_linha,
       h.hour AS hour,
       m.pred_atraso_aproximado_min AS pred_atraso_aproximado_min,
       m.baseline_pred_atraso_aproximado_min AS baseline_pred_atraso_aproximado_min,
       m.pred_minus_baseline AS pred_minus_baseline,
       m.n_registros AS n_registros
ORDER BY m.pred_minus_baseline DESC
LIMIT 10;
```

## Queries para screenshots em grafo

### Query 5 - Grafo geral da execucao final
Use esta query para um print de visao geral, mostrando o `DecisionAggregateRun` conectado ao top 5 de linhas, horarios e veiculos.
```cypher
MATCH p=(run:DecisionAggregateRun {id: 'agg_final_2026_04_18_2044'})-[r]->(n)
WHERE (type(r) = 'RANKS_LINE' AND r.rank <= 5)
   OR (type(r) = 'RANKS_HOUR' AND r.rank <= 5)
   OR (type(r) = 'RANKS_VEHICLE' AND r.rank <= 5)
RETURN p;
```

### Query 6 - Grafo focado em uma linha critica e seus veiculos
Use esta query para mostrar a linha mais critica expandida para os veiculos associados aos segmentos mais criticos dessa linha.
```cypher
MATCH p1=(run:DecisionAggregateRun {id: 'agg_final_2026_04_18_2044'})-[r:RANKS_LINE]->(l:Linha)
WITH run, p1, r, l
ORDER BY r.rank ASC
LIMIT 1
MATCH (run)-[:INCLUDES_SEGMENT]->(s:CriticalSegment)-[:OF_LINE]->(l)
MATCH (s)-[:OF_VEHICLE]->(v:Veiculo)
WITH run, p1, l, s, v
ORDER BY s.mean_abs_error DESC
LIMIT 6
MATCH p2=(s)-[:OF_LINE]->(l)
MATCH p3=(s)-[:OF_VEHICLE]->(v)
RETURN p1, p2, p3;
```

### Query 7 - Grafo do segmento mais critico
Use esta query para um print mostrando um `CriticalSegment` ligado a `Linha`, `Veiculo` e `FaixaHoraria`.
```cypher
MATCH (run:DecisionAggregateRun {id: 'agg_final_2026_04_18_2044'})-[:INCLUDES_SEGMENT]->(s:CriticalSegment)
WITH run, s
ORDER BY s.mean_abs_error DESC
LIMIT 1
MATCH p1=(run)-[:INCLUDES_SEGMENT]->(s)
MATCH p2=(s)-[:OF_LINE]->(l:Linha)
MATCH p3=(s)-[:OF_VEHICLE]->(v:Veiculo)
MATCH p4=(s)-[:AT_HOUR]->(h:FaixaHoraria)
RETURN p1, p2, p3, p4;
```

## Nomes recomendados para os screenshots
Salvar em `tcc/figures/` com estes nomes:

- `neo4j_graph_overview_2026-04-19.png`
- `neo4j_graph_line_hour_focus_2026-04-19.png`
- `neo4j_graph_critical_segment_2026-04-19.png`

Opcional, se quiser um quarto print tabular para reforco quantitativo:
- `neo4j_table_top_lines_2026-04-19.png`
