#!/usr/bin/env python3
"""Etapa 13: publica os agregados gerenciais finais no Neo4j."""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yaml
from neo4j import GraphDatabase


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"YAML invalido: {path}")
    return data


def load_local_env(base_dir: Path) -> None:
    env_path = (base_dir.parent / ".env.local").resolve()
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def parse_args() -> argparse.Namespace:
    base = Path(__file__).resolve().parent.parent / "artifacts"
    parser = argparse.ArgumentParser(description="Publica agregados finais no Neo4j")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent / "config.yaml"))
    parser.add_argument("--run-id", default="agg_final_2026_04_18_2044")
    parser.add_argument("--line-ranking", default=str(base / "neo4j_metrics_line_ranking_2026-04-18_2044.csv"))
    parser.add_argument("--hour-ranking", default=str(base / "neo4j_metrics_hour_ranking_2026-04-18_2044.csv"))
    parser.add_argument("--vehicle-instability", default=str(base / "neo4j_metrics_vehicle_instability_2026-04-18_2044.csv"))
    parser.add_argument("--segment-error", default=str(base / "neo4j_metrics_segment_error_2026-04-18_2044.csv"))
    parser.add_argument("--line-hour-compare", default=str(base / "neo4j_metrics_line_hour_compare_2026-04-18_2044.csv"))
    parser.add_argument("--manifest", default=str(base / "neo4j_package_manifest_2026-04-18_2044.csv"))
    parser.add_argument("--contract", default=str(base / "aggregate_source_contract_2026-04-18.md"))
    parser.add_argument("--comparison", default=str(base / "decision_aggregates_comparison_2026-04-18.md"))
    parser.add_argument("--uri", default=None)
    parser.add_argument("--user", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--database", default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def resolve_neo4j_settings(cfg: dict[str, Any], args: argparse.Namespace) -> tuple[str, str, str, str]:
    neo4j_cfg = cfg.get("neo4j", {})
    uri = args.uri or os.getenv("TCC_NEO4J_URI") or os.getenv("NEO4J_URI") or neo4j_cfg.get("uri") or "bolt://localhost:7687"
    user = args.user or os.getenv("TCC_NEO4J_USER") or os.getenv("NEO4J_USER") or neo4j_cfg.get("user") or "neo4j"
    password = (
        args.password
        or os.getenv("TCC_NEO4J_PASSWORD")
        or os.getenv("NEO4J_PASSWORD")
        or neo4j_cfg.get("password")
    )
    if not password or str(password).startswith("CHANGE_ME"):
        raise EnvironmentError(
            "Neo4j password is required. Set TCC_NEO4J_PASSWORD or NEO4J_PASSWORD."
        )
    database = args.database or os.getenv("TCC_NEO4J_DATABASE") or neo4j_cfg.get("database") or "neo4j"
    return str(uri), str(user), str(password), str(database)


def require_files(paths: Iterable[Path]) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Arquivos ausentes: {missing}")


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(path)
    return df.where(pd.notna(df), None).to_dict(orient="records")


def chunked(rows: list[dict[str, Any]], size: int = 500) -> Iterable[list[dict[str, Any]]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def ensure_constraints(session) -> None:
    statements = [
        "CREATE CONSTRAINT decision_run_id IF NOT EXISTS FOR (n:DecisionAggregateRun) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT faixa_horaria_hour IF NOT EXISTS FOR (n:FaixaHoraria) REQUIRE n.hour IS UNIQUE",
        "CREATE CONSTRAINT line_hour_metric_id IF NOT EXISTS FOR (n:LineHourMetric) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT critical_segment_id IF NOT EXISTS FOR (n:CriticalSegment) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT linha_code IF NOT EXISTS FOR (n:Linha) REQUIRE n.code IS UNIQUE",
        "CREATE CONSTRAINT veiculo_code IF NOT EXISTS FOR (n:Veiculo) REQUIRE n.code IS UNIQUE",
    ]
    for stmt in statements:
        session.run(stmt).consume()


def purge_previous_decision_graph(session) -> None:
    session.run("MATCH (n:DecisionAggregateRun) DETACH DELETE n").consume()
    session.run("MATCH (n:LineHourMetric) DETACH DELETE n").consume()
    session.run("MATCH (n:CriticalSegment) DETACH DELETE n").consume()
    session.run("MATCH (n:FaixaHoraria) DETACH DELETE n").consume()


def create_run_node(session, run_meta: dict[str, Any]) -> None:
    session.run(
        """
        MERGE (r:DecisionAggregateRun {id: $id})
        SET r.stage = $stage,
            r.generated_at = $generated_at,
            r.prediction_source = $prediction_source,
            r.baseline_source = $baseline_source,
            r.contract_file = $contract_file,
            r.comparison_file = $comparison_file,
            r.manifest_file = $manifest_file,
            r.note = $note
        """,
        run_meta,
    ).consume()


def load_line_rankings(session, run_id: str, rows: list[dict[str, Any]]) -> None:
    query = """
    UNWIND $rows AS row
    MATCH (run:DecisionAggregateRun {id: $run_id})
    MERGE (l:Linha {code: toInteger(row.cod_linha)})
    MERGE (run)-[rel:RANKS_LINE]->(l)
    SET rel.rank = toInteger(row.rank),
        rel.pred_atraso_aproximado_min = toFloat(row.pred_atraso_aproximado_min),
        rel.real_atraso_aproximado_min = toFloat(row.real_atraso_aproximado_min),
        rel.n_registros = toInteger(row.n_registros),
        rel.prediction_source = row.prediction_source,
        l.latest_line_rank = toInteger(row.rank),
        l.latest_pred_atraso_aproximado_min = toFloat(row.pred_atraso_aproximado_min),
        l.latest_real_atraso_aproximado_min = toFloat(row.real_atraso_aproximado_min),
        l.latest_n_registros = toInteger(row.n_registros),
        l.latest_prediction_source = row.prediction_source,
        l.aggregate_run_id = $run_id
    """
    for batch in chunked(rows):
        session.run(query, {"run_id": run_id, "rows": batch}).consume()


def load_hour_rankings(session, run_id: str, rows: list[dict[str, Any]]) -> None:
    query = """
    UNWIND $rows AS row
    MATCH (run:DecisionAggregateRun {id: $run_id})
    MERGE (h:FaixaHoraria {hour: toInteger(row.hour)})
    SET h.label = toString(row.hour) + ':00-' + toString(row.hour) + ':59'
    MERGE (run)-[rel:RANKS_HOUR]->(h)
    SET rel.rank = toInteger(row.rank),
        rel.pred_atraso_aproximado_min = toFloat(row.pred_atraso_aproximado_min),
        rel.real_atraso_aproximado_min = toFloat(row.real_atraso_aproximado_min),
        rel.n_registros = toInteger(row.n_registros),
        rel.prediction_source = row.prediction_source,
        h.latest_hour_rank = toInteger(row.rank),
        h.latest_pred_atraso_aproximado_min = toFloat(row.pred_atraso_aproximado_min),
        h.latest_real_atraso_aproximado_min = toFloat(row.real_atraso_aproximado_min),
        h.latest_n_registros = toInteger(row.n_registros),
        h.latest_prediction_source = row.prediction_source,
        h.aggregate_run_id = $run_id
    """
    for batch in chunked(rows):
        session.run(query, {"run_id": run_id, "rows": batch}).consume()


def load_vehicle_rankings(session, run_id: str, rows: list[dict[str, Any]]) -> None:
    query = """
    UNWIND $rows AS row
    MATCH (run:DecisionAggregateRun {id: $run_id})
    MERGE (v:Veiculo {code: toInteger(row.cod_veiculo)})
    MERGE (run)-[rel:RANKS_VEHICLE]->(v)
    SET rel.rank = toInteger(row.rank),
        rel.pred_atraso_aproximado_min = toFloat(row.pred_atraso_aproximado_min),
        rel.real_atraso_aproximado_min = toFloat(row.real_atraso_aproximado_min),
        rel.mean_abs_gap_pred_real = toFloat(row.mean_abs_gap_pred_real),
        rel.n_registros = toInteger(row.n_registros),
        rel.n_dias = toInteger(row.n_dias),
        rel.prediction_source = row.prediction_source,
        v.latest_vehicle_rank = toInteger(row.rank),
        v.latest_mean_abs_gap_pred_real = toFloat(row.mean_abs_gap_pred_real),
        v.latest_pred_atraso_aproximado_min = toFloat(row.pred_atraso_aproximado_min),
        v.latest_real_atraso_aproximado_min = toFloat(row.real_atraso_aproximado_min),
        v.latest_n_registros = toInteger(row.n_registros),
        v.latest_prediction_source = row.prediction_source,
        v.aggregate_run_id = $run_id
    """
    for batch in chunked(rows):
        session.run(query, {"run_id": run_id, "rows": batch}).consume()


def load_line_hour_metrics(session, run_id: str, rows: list[dict[str, Any]]) -> None:
    query = """
    UNWIND $rows AS row
    MATCH (run:DecisionAggregateRun {id: $run_id})
    MERGE (l:Linha {code: toInteger(row.cod_linha)})
    MERGE (h:FaixaHoraria {hour: toInteger(row.hour)})
    SET h.label = toString(row.hour) + ':00-' + toString(row.hour) + ':59'
    MERGE (m:LineHourMetric {id: $run_id + '|' + toString(row.cod_linha) + '|' + toString(row.hour)})
    SET m.prediction_source = row.prediction_source,
        m.pred_atraso_aproximado_min = toFloat(row.pred_atraso_aproximado_min),
        m.real_atraso_aproximado_min = toFloat(row.real_atraso_aproximado_min),
        m.n_registros = toInteger(row.n_registros),
        m.baseline_pred_atraso_aproximado_min = toFloat(row.baseline_pred_atraso_aproximado_min),
        m.baseline_real_atraso_aproximado_min = toFloat(row.baseline_real_atraso_aproximado_min),
        m.baseline_n_registros = toInteger(row.baseline_n_registros),
        m.pred_minus_baseline = toFloat(row.pred_minus_baseline),
        m.aggregate_run_id = $run_id
    MERGE (run)-[:INCLUDES_LINE_HOUR]->(m)
    MERGE (l)-[:HAS_LINE_HOUR_METRIC]->(m)
    MERGE (m)-[:AT_HOUR]->(h)
    """
    for batch in chunked(rows):
        session.run(query, {"run_id": run_id, "rows": batch}).consume()


def load_segments(session, run_id: str, rows: list[dict[str, Any]]) -> None:
    query = """
    UNWIND $rows AS row
    MATCH (run:DecisionAggregateRun {id: $run_id})
    MERGE (l:Linha {code: toInteger(row.cod_linha)})
    MERGE (v:Veiculo {code: toInteger(row.cod_veiculo)})
    MERGE (h:FaixaHoraria {hour: toInteger(row.hour)})
    SET h.label = toString(row.hour) + ':00-' + toString(row.hour) + ':59'
    MERGE (s:CriticalSegment {id: $run_id + '|' + toString(row.cod_linha) + '|' + toString(row.hour) + '|' + toString(row.cod_veiculo)})
    SET s.prediction_source = row.prediction_source,
        s.mean_abs_error = toFloat(row.mean_abs_error),
        s.pred_atraso_aproximado_min = toFloat(row.pred_atraso_aproximado_min),
        s.real_atraso_aproximado_min = toFloat(row.real_atraso_aproximado_min),
        s.n_registros = toInteger(row.n_registros),
        s.aggregate_run_id = $run_id
    MERGE (run)-[:INCLUDES_SEGMENT]->(s)
    MERGE (s)-[:OF_LINE]->(l)
    MERGE (s)-[:OF_VEHICLE]->(v)
    MERGE (s)-[:AT_HOUR]->(h)
    """
    for batch in chunked(rows):
        session.run(query, {"run_id": run_id, "rows": batch}).consume()


def main() -> None:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    load_local_env(base_dir)

    cfg = load_yaml(Path(args.config).resolve())
    uri, user, password, database = resolve_neo4j_settings(cfg, args)

    line_ranking_path = Path(args.line_ranking).resolve()
    hour_ranking_path = Path(args.hour_ranking).resolve()
    vehicle_instability_path = Path(args.vehicle_instability).resolve()
    segment_error_path = Path(args.segment_error).resolve()
    line_hour_compare_path = Path(args.line_hour_compare).resolve()
    manifest_path = Path(args.manifest).resolve()
    contract_path = Path(args.contract).resolve()
    comparison_path = Path(args.comparison).resolve()

    require_files(
        [
            line_ranking_path,
            hour_ranking_path,
            vehicle_instability_path,
            segment_error_path,
            line_hour_compare_path,
            manifest_path,
            contract_path,
            comparison_path,
        ]
    )

    line_ranking_rows = read_csv_rows(line_ranking_path)
    hour_ranking_rows = read_csv_rows(hour_ranking_path)
    vehicle_rows = read_csv_rows(vehicle_instability_path)
    segment_rows = read_csv_rows(segment_error_path)
    line_hour_rows = read_csv_rows(line_hour_compare_path)
    manifest_rows = read_csv_rows(manifest_path)

    run_meta = {
        "id": args.run_id,
        "stage": "13_final_visualization",
        "generated_at": datetime.now().isoformat(),
        "prediction_source": line_ranking_rows[0]["prediction_source"] if line_ranking_rows else "unknown",
        "baseline_source": "baseline_v2_2026-04-18_1904",
        "contract_file": str(contract_path),
        "comparison_file": str(comparison_path),
        "manifest_file": str(manifest_path),
        "note": (
            "Pacote final de agregados da rodada 2 de ML com filtros minimos de suporte; "
            f"datasets_manifestados={len(manifest_rows)}"
        ),
    }

    if args.dry_run:
        print("=== Dry Run Publish Neo4j ===")
        print(f"uri: {uri}")
        print(f"user: {user}")
        print(f"database: {database}")
        print(f"run_id: {args.run_id}")
        print(f"line_ranking_rows: {len(line_ranking_rows)}")
        print(f"hour_ranking_rows: {len(hour_ranking_rows)}")
        print(f"vehicle_rows: {len(vehicle_rows)}")
        print(f"segment_rows: {len(segment_rows)}")
        print(f"line_hour_rows: {len(line_hour_rows)}")
        print(f"manifest_datasets: {len(manifest_rows)}")
        print("[OK] Dry-run concluido: script pronto para carga real no Neo4j.")
        return

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session(database=database) as session:
            session.run("RETURN 1 AS ok").single()
            ensure_constraints(session)
            purge_previous_decision_graph(session)
            create_run_node(session, run_meta)
            load_line_rankings(session, args.run_id, line_ranking_rows)
            load_hour_rankings(session, args.run_id, hour_ranking_rows)
            load_vehicle_rankings(session, args.run_id, vehicle_rows)
            load_line_hour_metrics(session, args.run_id, line_hour_rows)
            load_segments(session, args.run_id, segment_rows)

        print("=== Neo4j Publish Completed ===")
        print(f"run_id: {args.run_id}")
        print(f"uri: {uri}")
        print(f"database: {database}")
        print(f"line_ranking_rows: {len(line_ranking_rows)}")
        print(f"hour_ranking_rows: {len(hour_ranking_rows)}")
        print(f"vehicle_rows: {len(vehicle_rows)}")
        print(f"segment_rows: {len(segment_rows)}")
        print(f"line_hour_rows: {len(line_hour_rows)}")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
