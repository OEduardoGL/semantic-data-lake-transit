#!/usr/bin/env python3
"""Etapa 6 (Bloco A): setup do modelo semantico no Neo4j.

Este script valida:
1) conexao com Neo4j
2) leitura dos artefatos semanticos (TTL, mapping YAML, regras MD)
3) resumo estrutural da ontologia para preparar a carga (Bloco B)
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any
from datetime import datetime

import yaml
from neo4j import GraphDatabase


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"YAML invalido em {path}")
    return data


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8") as f:
        return f.read()


def parse_ttl_summary(ttl_text: str) -> dict[str, int]:
    class_count = len(re.findall(r"^\s*tcc:[A-Za-z0-9_]+\s+a\s+owl:Class\s*;", ttl_text, flags=re.M))
    obj_prop_count = len(
        re.findall(r"^\s*tcc:[A-Za-z0-9_]+\s+a\s+owl:ObjectProperty\s*;", ttl_text, flags=re.M)
    )
    data_prop_count = len(
        re.findall(r"^\s*tcc:[A-Za-z0-9_]+\s+a\s+owl:DatatypeProperty\s*;", ttl_text, flags=re.M)
    )
    semantic_rules = len(
        re.findall(r"^\s*tcc:Regra[A-Za-z0-9_]+\s+a\s+tcc:RegraSemantica\s*;", ttl_text, flags=re.M)
    )
    return {
        "classes": class_count,
        "object_properties": obj_prop_count,
        "datatype_properties": data_prop_count,
        "semantic_rules": semantic_rules,
    }


def extract_ttl_entities(ttl_text: str) -> dict[str, list[dict[str, Any]]]:
    classes: list[dict[str, Any]] = []
    object_properties: list[dict[str, Any]] = []
    datatype_properties: list[dict[str, Any]] = []
    rules: list[dict[str, Any]] = []

    class_pattern = re.compile(
        r"^\s*(tcc:[A-Za-z0-9_]+)\s+a\s+owl:Class\s*;\s*(.*?)\s*\.\s*$",
        flags=re.M | re.S,
    )
    obj_pattern = re.compile(
        r"^\s*(tcc:[A-Za-z0-9_]+)\s+a\s+owl:ObjectProperty\s*;\s*(.*?)\s*\.\s*$",
        flags=re.M | re.S,
    )
    data_pattern = re.compile(
        r"^\s*(tcc:[A-Za-z0-9_]+)\s+a\s+owl:DatatypeProperty\s*;\s*(.*?)\s*\.\s*$",
        flags=re.M | re.S,
    )
    rule_pattern = re.compile(
        r"^\s*(tcc:Regra[A-Za-z0-9_]+)\s+a\s+tcc:RegraSemantica\s*;\s*(.*?)\s*\.\s*$",
        flags=re.M | re.S,
    )

    def extract_label_pt(body: str) -> str | None:
        m = re.search(r'rdfs:label\s+"([^"]+)"@pt', body)
        return m.group(1) if m else None

    def extract_literal(body: str, field: str) -> str | None:
        m = re.search(rf'{re.escape(field)}\s+"([^"]+)"', body)
        return m.group(1) if m else None

    def extract_int(body: str, field: str) -> int | None:
        m = re.search(rf"{re.escape(field)}\s+([0-9]+)", body)
        return int(m.group(1)) if m else None

    for sid, body in class_pattern.findall(ttl_text):
        classes.append({"id": sid, "label_pt": extract_label_pt(body)})
    for sid, body in obj_pattern.findall(ttl_text):
        object_properties.append({"id": sid, "label_pt": extract_label_pt(body), "property_type": "object"})
    for sid, body in data_pattern.findall(ttl_text):
        datatype_properties.append({"id": sid, "label_pt": extract_label_pt(body), "property_type": "datatype"})
    for sid, body in rule_pattern.findall(ttl_text):
        rules.append(
            {
                "id": sid,
                "code": extract_literal(body, "tcc:ruleCode"),
                "priority": extract_int(body, "tcc:rulePriority"),
                "description": extract_literal(body, "tcc:ruleDescription"),
                "fallback_sequence": extract_literal(body, "tcc:ruleFallbackSequence"),
            }
        )

    return {
        "classes": classes,
        "object_properties": object_properties,
        "datatype_properties": datatype_properties,
        "rules": rules,
    }


def parse_args() -> argparse.Namespace:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Build semantic model - Bloco A")
    parser.add_argument("--config", default=str(base / "config.yaml"))
    parser.add_argument("--ttl", default=str(base.parent / "docs" / "ontologia_transporte.ttl"))
    parser.add_argument("--mapping", default=str(base / "semantic_mapping.yaml"))
    parser.add_argument("--rules-md", default=str(base.parent / "docs" / "regras_semanticas.md"))
    parser.add_argument("--preview", action="store_true", help="Mostra resumo sem conectar no Neo4j")
    parser.add_argument(
        "--load-metadata",
        action="store_true",
        help="Carrega ontologia/mapping/regras como metadados no Neo4j",
    )
    parser.add_argument(
        "--ensure-constraints",
        action="store_true",
        help="Cria constraints/indexes minimos no Neo4j",
    )
    parser.add_argument(
        "--validate-graph",
        action="store_true",
        help="Executa consultas basicas de validacao do grafo semantico",
    )
    return parser.parse_args()


def validate_files(ttl_path: Path, mapping_path: Path, rules_path: Path) -> None:
    for p in (ttl_path, mapping_path, rules_path):
        if not p.exists():
            raise FileNotFoundError(f"Arquivo nao encontrado: {p}")


def check_neo4j_connection(cfg: dict[str, Any]) -> tuple[str, str]:
    neo4j_cfg = cfg["neo4j"]
    uri = neo4j_cfg["uri"]
    auth = (neo4j_cfg["user"], neo4j_cfg["password"])
    database = neo4j_cfg.get("database", "neo4j")

    driver = GraphDatabase.driver(uri, auth=auth)
    try:
        with driver.session(database=database) as session:
            rec = session.run("RETURN 1 AS ok").single()
            if rec is None or rec["ok"] != 1:
                raise RuntimeError("Falha na validacao de conexao com Neo4j")
            user = str(neo4j_cfg["user"])
            try:
                user_rec = session.run("SHOW CURRENT USER YIELD user RETURN user").single()
                if user_rec is not None and user_rec.get("user"):
                    user = str(user_rec["user"])
            except Exception:
                pass
            return user, database
    finally:
        driver.close()


def load_metadata_to_neo4j(
    cfg: dict[str, Any],
    ttl_text: str,
    mapping: dict[str, Any],
    rules_md: str,
    ttl_path: Path,
    mapping_path: Path,
    rules_path: Path,
) -> dict[str, int]:
    neo4j_cfg = cfg["neo4j"]
    uri = neo4j_cfg["uri"]
    auth = (neo4j_cfg["user"], neo4j_cfg["password"])
    database = neo4j_cfg.get("database", "neo4j")
    entities = extract_ttl_entities(ttl_text)

    driver = GraphDatabase.driver(uri, auth=auth)
    try:
        with driver.session(database=database) as session:
            session.run(
                """
                MERGE (o:Ontology {id: $id})
                SET o.label = $label,
                    o.namespace = $namespace,
                    o.source_ttl = $source_ttl,
                    o.ttl_text = $ttl_text
                """,
                {
                    "id": "tcc:OntologiaTransporte",
                    "label": "OntologiaTransporte",
                    "namespace": mapping.get("namespace", ""),
                    "source_ttl": str(ttl_path),
                    "ttl_text": ttl_text,
                },
            ).consume()

            session.run(
                """
                UNWIND $rows AS row
                MERGE (c:SemanticClass {id: row.id})
                SET c.label_pt = row.label_pt
                WITH c
                MATCH (o:Ontology {id: 'tcc:OntologiaTransporte'})
                MERGE (o)-[:HAS_CLASS]->(c)
                """,
                {"rows": entities["classes"]},
            ).consume()

            properties = entities["object_properties"] + entities["datatype_properties"]
            session.run(
                """
                UNWIND $rows AS row
                MERGE (p:SemanticProperty {id: row.id})
                SET p.label_pt = row.label_pt,
                    p.property_type = row.property_type
                WITH p
                MATCH (o:Ontology {id: 'tcc:OntologiaTransporte'})
                MERGE (o)-[:HAS_PROPERTY]->(p)
                """,
                {"rows": properties},
            ).consume()

            session.run(
                """
                UNWIND $rows AS row
                MERGE (r:SemanticRule {id: row.id})
                SET r.code = row.code,
                    r.priority = row.priority,
                    r.description = row.description,
                    r.fallback_sequence = row.fallback_sequence
                WITH r
                MATCH (o:Ontology {id: 'tcc:OntologiaTransporte'})
                MERGE (o)-[:HAS_RULE]->(r)
                """,
                {"rows": entities["rules"]},
            ).consume()

            tables = mapping.get("silver_tables", {})
            table_rows: list[dict[str, Any]] = []
            link_rows: list[dict[str, Any]] = []
            for table_name, table_cfg_any in tables.items():
                if not isinstance(table_cfg_any, dict):
                    continue
                semantic_class = str(table_cfg_any.get("semantic_class", ""))
                natural_key = table_cfg_any.get("natural_key", {})
                strategy = None
                columns: list[str] = []
                if isinstance(natural_key, dict):
                    strategy = natural_key.get("strategy")
                    nk_cols = natural_key.get("columns", [])
                    if isinstance(nk_cols, list):
                        columns = [str(x) for x in nk_cols]
                table_rows.append(
                    {
                        "name": table_name,
                        "semantic_class": semantic_class,
                        "natural_key_strategy": strategy,
                        "natural_key_columns": columns,
                    }
                )
                link_rows.append({"table": table_name, "semantic_class": semantic_class})

            session.run(
                """
                MERGE (m:SemanticMapping {id: 'semantic_mapping'})
                SET m.version = $version,
                    m.namespace = $namespace,
                    m.source_yaml = $source_yaml,
                    m.raw_yaml = $raw_yaml
                """,
                {
                    "version": str(mapping.get("version", "")),
                    "namespace": str(mapping.get("namespace", "")),
                    "source_yaml": str(mapping_path),
                    "raw_yaml": yaml.safe_dump(mapping, sort_keys=False),
                },
            ).consume()

            session.run(
                """
                UNWIND $rows AS row
                MERGE (t:SilverTable {name: row.name})
                SET t.semantic_class = row.semantic_class,
                    t.natural_key_strategy = row.natural_key_strategy,
                    t.natural_key_columns = row.natural_key_columns
                WITH t
                MATCH (m:SemanticMapping {id: 'semantic_mapping'})
                MERGE (m)-[:MAPS_TABLE]->(t)
                """,
                {"rows": table_rows},
            ).consume()

            session.run(
                """
                UNWIND $rows AS row
                MATCH (t:SilverTable {name: row.table})
                MATCH (c:SemanticClass {id: row.semantic_class})
                MERGE (t)-[:MAPS_TO_CLASS]->(c)
                """,
                {"rows": link_rows},
            ).consume()

            session.run(
                """
                MERGE (d:SemanticRulesDoc {id: 'regras_semanticas_md'})
                SET d.source_md = $source_md,
                    d.raw_md = $raw_md,
                    d.line_count = $line_count
                """,
                {
                    "source_md": str(rules_path),
                    "raw_md": rules_md,
                    "line_count": len(rules_md.splitlines()),
                },
            ).consume()

        return {
            "classes_loaded": len(entities["classes"]),
            "properties_loaded": len(entities["object_properties"]) + len(entities["datatype_properties"]),
            "rules_loaded": len(entities["rules"]),
            "tables_loaded": len(mapping.get("silver_tables", {})),
        }
    finally:
        driver.close()


def ensure_constraints(cfg: dict[str, Any]) -> list[str]:
    neo4j_cfg = cfg["neo4j"]
    uri = neo4j_cfg["uri"]
    auth = (neo4j_cfg["user"], neo4j_cfg["password"])
    database = neo4j_cfg.get("database", "neo4j")

    statements = [
        "CREATE CONSTRAINT linha_code_unique IF NOT EXISTS FOR (n:Linha) REQUIRE n.code IS UNIQUE",
        "CREATE CONSTRAINT veiculo_code_unique IF NOT EXISTS FOR (n:Veiculo) REQUIRE n.code IS UNIQUE",
        "CREATE CONSTRAINT empresa_code_unique IF NOT EXISTS FOR (n:Empresa) REQUIRE n.code IS UNIQUE",
        "CREATE CONSTRAINT tipo_mensagem_code_unique IF NOT EXISTS FOR (n:TipoMensagem) REQUIRE n.code IS UNIQUE",
    ]

    driver = GraphDatabase.driver(uri, auth=auth)
    try:
        with driver.session(database=database) as session:
            for stmt in statements:
                session.run(stmt).consume()

            rows = session.run(
                """
                SHOW CONSTRAINTS YIELD name
                WHERE name IN [
                  'linha_code_unique',
                  'veiculo_code_unique',
                  'empresa_code_unique',
                  'tipo_mensagem_code_unique'
                ]
                RETURN name
                ORDER BY name
                """
            ).data()
            return [str(r["name"]) for r in rows]
    finally:
        driver.close()


def validate_graph_queries(cfg: dict[str, Any], artifact_path: Path) -> dict[str, Any]:
    neo4j_cfg = cfg["neo4j"]
    uri = neo4j_cfg["uri"]
    auth = (neo4j_cfg["user"], neo4j_cfg["password"])
    database = neo4j_cfg.get("database", "neo4j")

    q1 = """
    MATCH (o:Ontology {id:'tcc:OntologiaTransporte'})
    OPTIONAL MATCH (o)-[:HAS_CLASS]->(c:SemanticClass)
    OPTIONAL MATCH (o)-[:HAS_PROPERTY]->(p:SemanticProperty)
    OPTIONAL MATCH (o)-[:HAS_RULE]->(r:SemanticRule)
    OPTIONAL MATCH (m:SemanticMapping {id:'semantic_mapping'})-[:MAPS_TABLE]->(t:SilverTable)
    RETURN o.id AS ontology,
           count(DISTINCT c) AS classes,
           count(DISTINCT p) AS properties,
           count(DISTINCT r) AS rules,
           count(DISTINCT t) AS silver_tables
    """
    q2 = """
    MATCH (m:SemanticMapping {id:'semantic_mapping'})-[:MAPS_TABLE]->(t:SilverTable)
    OPTIONAL MATCH (t)-[:MAPS_TO_CLASS]->(c:SemanticClass)
    RETURN t.name AS silver_table, c.id AS semantic_class
    ORDER BY silver_table
    """
    q3 = """
    MATCH (r:SemanticRule)
    RETURN r.id AS id, r.code AS code, r.priority AS priority
    ORDER BY priority ASC
    """

    driver = GraphDatabase.driver(uri, auth=auth)
    try:
        with driver.session(database=database) as session:
            r1 = session.run(q1).data()
            r2 = session.run(q2).data()
            r3 = session.run(q3).data()

        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        with artifact_path.open("w", encoding="utf-8") as f:
            f.write(f"# Neo4j Graph Validation - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write("## Q1 - Resumo semantico\n")
            f.write(q1.strip() + "\n\n")
            f.write(str(r1) + "\n\n")
            f.write("## Q2 - Tabela Silver -> Classe semantica\n")
            f.write(q2.strip() + "\n\n")
            f.write(str(r2) + "\n\n")
            f.write("## Q3 - Regras semanticas por prioridade\n")
            f.write(q3.strip() + "\n\n")
            f.write(str(r3) + "\n")

        return {
            "q1_rows": len(r1),
            "q2_rows": len(r2),
            "q3_rows": len(r3),
            "artifact": str(artifact_path),
        }
    finally:
        driver.close()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    ttl_path = Path(args.ttl).resolve()
    mapping_path = Path(args.mapping).resolve()
    rules_path = Path(args.rules_md).resolve()

    cfg = load_yaml(config_path)
    validate_files(ttl_path, mapping_path, rules_path)

    ttl_text = read_text(ttl_path)
    mapping = load_yaml(mapping_path)
    rules_md = read_text(rules_path)
    ttl_summary = parse_ttl_summary(ttl_text)

    print("=== Arquivos semanticos ===")
    print(f"config:  {config_path}")
    print(f"ttl:     {ttl_path}")
    print(f"mapping: {mapping_path}")
    print(f"rules:   {rules_path}")

    print("\n=== Resumo ontologia ===")
    for k, v in ttl_summary.items():
        print(f"{k}: {v}")

    silver_tables = mapping.get("silver_tables", {})
    print("\n=== Resumo mapping ===")
    print(f"tabelas mapeadas: {len(silver_tables)}")
    print("nomes:", ", ".join(sorted(silver_tables.keys())))
    print(f"rules_md_linhas: {len(rules_md.splitlines())}")

    if args.preview:
        print("\n[OK] Preview concluido (sem conexao Neo4j).")
        return

    user, db = check_neo4j_connection(cfg)
    print("\n=== Neo4j ===")
    print(f"conexao: ok")
    print(f"user: {user}")
    print(f"database: {db}")

    if not args.load_metadata and not args.ensure_constraints and not args.validate_graph:
        print("\n[OK] Bloco A concluido: conexao e artefatos semanticos validados.")
        return

    if args.load_metadata:
        stats = load_metadata_to_neo4j(cfg, ttl_text, mapping, rules_md, ttl_path, mapping_path, rules_path)
        print("\n=== Carga semantica (Bloco B) ===")
        for key, value in stats.items():
            print(f"{key}: {value}")
        print("\n[OK] Bloco B concluido: ontologia, mapping e regras carregados no Neo4j.")

    if args.ensure_constraints:
        created = ensure_constraints(cfg)
        print("\n=== Constraints (Bloco C) ===")
        print("constraints_encontrados:", ", ".join(created))

    if args.validate_graph:
        ts = datetime.now().strftime("%Y-%m-%d")
        artifact = Path(__file__).resolve().parent.parent / "artifacts" / f"neo4j_graph_validation_{ts}.txt"
        result = validate_graph_queries(cfg, artifact)
        print("\n=== Validacao de consultas (Bloco C) ===")
        for key, value in result.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
