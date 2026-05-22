#!/usr/bin/env python3
"""Checks de Qualidade de Dados da camada Silver.

Bloco A:
- contagem de registros por tabela
- duplicidade de chave tecnica (event_id + gps_idx quando aplicavel)

Modo seguro:
- execucao por tabela
- opcao de calcular gps_events por event_dt (particao) e consolidar
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


def load_config(config_path: str) -> dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_spark(
    cfg: dict[str, Any],
    driver_memory: str | None = None,
    master: str | None = None,
    shuffle_partitions: int | None = None,
) -> SparkSession:
    spark_cfg = cfg["spark"]
    s3_cfg = cfg["s3"]

    builder = (
        SparkSession.builder.master(master or spark_cfg["master"])
        .appName("tcc-dq-silver")
        .config(
            "spark.sql.shuffle.partitions",
            str(shuffle_partitions if shuffle_partitions is not None else spark_cfg["shuffle_partitions"]),
        )
        .config("spark.sql.adaptive.enabled", str(spark_cfg["adaptive_enabled"]).lower())
        .config("spark.sql.session.timeZone", spark_cfg["session_timezone"])
        .config("spark.hadoop.fs.s3a.endpoint", s3_cfg["endpoint"])
        .config("spark.hadoop.fs.s3a.access.key", s3_cfg["access_key"])
        .config("spark.hadoop.fs.s3a.secret.key", s3_cfg["secret_key"])
        .config("spark.hadoop.fs.s3a.path.style.access", str(s3_cfg["path_style_access"]).lower())
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", str(s3_cfg["ssl_enabled"]).lower())
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    )

    packages = s3_cfg.get("extra_packages", [])
    if packages:
        builder = builder.config("spark.jars.packages", ",".join(packages))
    if driver_memory:
        builder = (
            builder.config("spark.driver.memory", driver_memory)
            .config("spark.executor.memory", driver_memory)
        )

    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel(spark_cfg.get("log_level", "WARN"))
    return spark


def resolve_artifacts_dir(cfg: dict[str, Any], config_path: str) -> Path:
    cfg_path = Path(config_path).resolve()
    artifacts_rel = cfg["paths"]["artifacts_local"]
    return (cfg_path.parent / artifacts_rel).resolve()


def duplicate_rows_from_distinct(total_rows: int, distinct_keys: int) -> int:
    return max(total_rows - distinct_keys, 0)


def _agg_non_gps_table(df: DataFrame) -> tuple[int, Any, Any, int, str]:
    has_gps_idx = "gps_idx" in df.columns
    if has_gps_idx:
        row = df.select("event_id", "event_dt", "gps_idx").agg(
            F.count(F.lit(1)).alias("rows_total"),
            F.min("event_dt").alias("min_dt"),
            F.max("event_dt").alias("max_dt"),
            F.sum(F.when(F.col("gps_idx").isNotNull(), F.lit(1)).otherwise(F.lit(0))).alias(
                "gps_idx_non_null_rows"
            ),
            F.countDistinct(F.struct(F.col("event_id"), F.col("gps_idx"))).alias("distinct_event_gps"),
            F.countDistinct("event_id").alias("distinct_event"),
        ).collect()[0]
        key_rule = "event_id+gps_idx" if int(row["gps_idx_non_null_rows"] or 0) > 0 else "event_id"
        distinct_keys = int(
            row["distinct_event_gps"] if key_rule == "event_id+gps_idx" else row["distinct_event"]
        )
    else:
        row = df.select("event_id", "event_dt").agg(
            F.count(F.lit(1)).alias("rows_total"),
            F.min("event_dt").alias("min_dt"),
            F.max("event_dt").alias("max_dt"),
            F.countDistinct("event_id").alias("distinct_event"),
        ).collect()[0]
        key_rule = "event_id"
        distinct_keys = int(row["distinct_event"] or 0)

    return (
        int(row["rows_total"] or 0),
        row["min_dt"],
        row["max_dt"],
        distinct_keys,
        key_rule,
    )


def _agg_gps_table(df: DataFrame) -> tuple[int, Any, Any, int]:
    row = df.select("event_id", "gps_idx", "event_dt").agg(
        F.count(F.lit(1)).alias("rows_total"),
        F.min("event_dt").alias("min_dt"),
        F.max("event_dt").alias("max_dt"),
        F.countDistinct(F.struct(F.col("event_id"), F.col("gps_idx"))).alias("distinct_keys"),
    ).collect()[0]
    return (
        int(row["rows_total"] or 0),
        row["min_dt"],
        row["max_dt"],
        int(row["distinct_keys"] or 0),
    )


def _date_list(df: DataFrame) -> list[str]:
    rows = (
        df.select("event_dt")
        .where(F.col("event_dt").isNotNull())
        .distinct()
        .orderBy("event_dt")
        .collect()
    )
    return [str(r["event_dt"]) for r in rows]


def run_block_a(
    cfg: dict[str, Any],
    run_ts: str,
    tables: list[str],
    driver_memory: str | None = None,
    master: str | None = None,
    shuffle_partitions: int | None = None,
    gps_by_day: bool = False,
) -> list[dict[str, Any]]:
    silver_base = cfg["paths"]["silver_base"].rstrip("/")
    results: list[dict[str, Any]] = []

    spark = build_spark(
        cfg,
        driver_memory=driver_memory,
        master=master,
        shuffle_partitions=shuffle_partitions,
    )
    try:
        for table in tables:
            path = f"{silver_base}/{table}"
            df = spark.read.parquet(path)

            if table == "gps_events" and gps_by_day:
                per_day = _date_list(df)
                total_rows = 0
                total_distinct = 0
                min_dt = None
                max_dt = None
                for dt in per_day:
                    dfd = df.where(F.col("event_dt") == F.lit(dt))
                    rows_d, min_d, max_d, distinct_d = _agg_gps_table(dfd)
                    total_rows += rows_d
                    total_distinct += distinct_d
                    min_dt = min(min_dt, min_d) if min_dt is not None else min_d
                    max_dt = max(max_dt, max_d) if max_dt is not None else max_d
                    print(
                        f"[DQ-A][gps/day] dt={dt}: rows={rows_d}, distinct_keys={distinct_d}, "
                        f"dup_rows={duplicate_rows_from_distinct(rows_d, distinct_d)}"
                    )
                key_rule = "event_id+gps_idx"
                total_rows, min_dt, max_dt, distinct_keys = total_rows, min_dt, max_dt, total_distinct
            elif table == "gps_events":
                key_rule = "event_id+gps_idx"
                total_rows, min_dt, max_dt, distinct_keys = _agg_gps_table(df)
            else:
                total_rows, min_dt, max_dt, distinct_keys, key_rule = _agg_non_gps_table(df)
            dup_rows = duplicate_rows_from_distinct(total_rows, distinct_keys)

            result = {
                "run_ts_utc": run_ts,
                "table_name": table,
                "path": path,
                "rows_total": total_rows,
                "event_dt_min": str(min_dt) if min_dt is not None else "",
                "event_dt_max": str(max_dt) if max_dt is not None else "",
                "key_rule": key_rule,
                "duplicate_rows": dup_rows,
                "status": "ok" if total_rows > 0 else "empty",
            }
            results.append(result)

            print(
                f"[DQ-A] {table}: rows={total_rows}, key={key_rule}, "
                f"dup_rows={dup_rows}, dt=({min_dt}..{max_dt})"
            )
    finally:
        spark.stop()

    return results


def run_block_b(
    cfg: dict[str, Any],
    run_ts: str,
    tables: list[str],
    driver_memory: str | None = None,
    master: str | None = None,
    shuffle_partitions: int | None = None,
) -> list[dict[str, Any]]:
    silver_base = cfg["paths"]["silver_base"].rstrip("/")
    results: list[dict[str, Any]] = []

    spark = build_spark(
        cfg,
        driver_memory=driver_memory,
        master=master,
        shuffle_partitions=shuffle_partitions,
    )
    try:
        for table in tables:
            path = f"{silver_base}/{table}"
            df = spark.read.parquet(path)

            row = df.select("latitude", "longitude", "event_dt").agg(
                F.count(F.lit(1)).alias("rows_total"),
                F.min("event_dt").alias("event_dt_min"),
                F.max("event_dt").alias("event_dt_max"),
                F.sum(
                    F.when(F.col("latitude").isNotNull() & F.col("longitude").isNotNull(), F.lit(1)).otherwise(
                        F.lit(0)
                    )
                ).alias("coords_non_null_rows"),
                F.sum(F.when(F.col("latitude").isNull() | F.col("longitude").isNull(), F.lit(1)).otherwise(F.lit(0))).alias(
                    "coords_null_rows"
                ),
                F.sum(
                    F.when(
                        F.col("latitude").isNotNull()
                        & ((F.col("latitude") < F.lit(-90.0)) | (F.col("latitude") > F.lit(90.0))),
                        F.lit(1),
                    ).otherwise(F.lit(0))
                ).alias("invalid_lat_rows"),
                F.sum(
                    F.when(
                        F.col("longitude").isNotNull()
                        & ((F.col("longitude") < F.lit(-180.0)) | (F.col("longitude") > F.lit(180.0))),
                        F.lit(1),
                    ).otherwise(F.lit(0))
                ).alias("invalid_lon_rows"),
                F.sum(
                    F.when(
                        F.col("latitude").isNotNull()
                        & F.col("longitude").isNotNull()
                        & (
                            (F.col("latitude") < F.lit(-90.0))
                            | (F.col("latitude") > F.lit(90.0))
                            | (F.col("longitude") < F.lit(-180.0))
                            | (F.col("longitude") > F.lit(180.0))
                        ),
                        F.lit(1),
                    ).otherwise(F.lit(0))
                ).alias("invalid_coord_pair_rows"),
            ).collect()[0]

            rows_total = int(row["rows_total"] or 0)
            coords_non_null = int(row["coords_non_null_rows"] or 0)
            coords_null = int(row["coords_null_rows"] or 0)
            invalid_lat = int(row["invalid_lat_rows"] or 0)
            invalid_lon = int(row["invalid_lon_rows"] or 0)
            invalid_pair = int(row["invalid_coord_pair_rows"] or 0)
            pct_invalid_pair = (invalid_pair / coords_non_null * 100.0) if coords_non_null > 0 else 0.0

            result = {
                "run_ts_utc": run_ts,
                "table_name": table,
                "path": path,
                "rows_total": rows_total,
                "event_dt_min": str(row["event_dt_min"]) if row["event_dt_min"] is not None else "",
                "event_dt_max": str(row["event_dt_max"]) if row["event_dt_max"] is not None else "",
                "coords_non_null_rows": coords_non_null,
                "coords_null_rows": coords_null,
                "invalid_lat_rows": invalid_lat,
                "invalid_lon_rows": invalid_lon,
                "invalid_coord_pair_rows": invalid_pair,
                "pct_invalid_coord_pair": f"{pct_invalid_pair:.6f}",
                "status": "ok" if invalid_pair == 0 else "warning",
            }
            results.append(result)

            print(
                f"[DQ-B] {table}: rows={rows_total}, non_null={coords_non_null}, "
                f"invalid_pair={invalid_pair}, pct_invalid_pair={pct_invalid_pair:.6f}%"
            )
    finally:
        spark.stop()

    return results


def _sum_invalid_int(df: DataFrame, col_name: str) -> Any:
    return F.sum(
        F.when(F.col(col_name).isNotNull() & (F.col(col_name) < F.lit(0)), F.lit(1)).otherwise(F.lit(0))
    ).alias(f"invalid_{col_name}_rows")


def _sum_invalid_double_nan(df: DataFrame, col_name: str) -> Any:
    return F.sum(
        F.when(F.col(col_name).isNotNull() & F.isnan(F.col(col_name)), F.lit(1)).otherwise(F.lit(0))
    ).alias(f"invalid_{col_name}_nan_rows")


def run_block_c(
    cfg: dict[str, Any],
    run_ts: str,
    tables: list[str],
    driver_memory: str | None = None,
    master: str | None = None,
    shuffle_partitions: int | None = None,
) -> list[dict[str, Any]]:
    silver_base = cfg["paths"]["silver_base"].rstrip("/")
    results: list[dict[str, Any]] = []

    spark = build_spark(
        cfg,
        driver_memory=driver_memory,
        master=master,
        shuffle_partitions=shuffle_partitions,
    )
    try:
        for table in tables:
            path = f"{silver_base}/{table}"
            df = spark.read.parquet(path)
            cols = set(df.columns)

            key_map = {
                "cod_linha": "linha",
                "cod_veiculo": "veiculo",
                "cod_tabela_programacao": "jornada_proxy",
                "viagem_sentido": "sentido",
            }
            existing_keys = [c for c in key_map.keys() if c in cols]

            agg_exprs = [
                F.count(F.lit(1)).alias("rows_total"),
                F.min("event_dt").alias("event_dt_min"),
                F.max("event_dt").alias("event_dt_max"),
            ]
            for c in existing_keys:
                agg_exprs.append(
                    F.sum(F.when(F.col(c).isNull(), F.lit(1)).otherwise(F.lit(0))).alias(f"null_{c}_rows")
                )

            # Regras de consistencia numerica (faixas/minimos e NaN)
            int_non_negative = [
                "id_empresa",
                "cod_linha",
                "cod_veiculo",
                "cod_garagem",
                "cod_operador",
                "gps_idx",
                "id_ponto",
                "numero_satelites",
            ]
            for c in int_non_negative:
                if c in cols:
                    agg_exprs.append(_sum_invalid_int(df, c))

            # direcao esperada no intervalo [0, 360]
            if "direcao" in cols:
                agg_exprs.append(
                    F.sum(
                        F.when(
                            F.col("direcao").isNotNull()
                            & ((F.col("direcao") < F.lit(0.0)) | (F.col("direcao") > F.lit(360.0))),
                            F.lit(1),
                        ).otherwise(F.lit(0))
                    ).alias("invalid_direcao_range_rows")
                )

            # velocidade e odometro nao-negativos
            for c in ["velocidade", "odometro_calculado"]:
                if c in cols:
                    agg_exprs.append(
                        F.sum(
                            F.when(F.col(c).isNotNull() & (F.col(c) < F.lit(0.0)), F.lit(1)).otherwise(F.lit(0))
                        ).alias(f"invalid_{c}_negative_rows")
                    )

            # NaN em doubles relevantes
            for c in ["latitude", "longitude", "velocidade", "direcao", "hdop", "pdop"]:
                if c in cols:
                    agg_exprs.append(_sum_invalid_double_nan(df, c))

            row = df.agg(*agg_exprs).collect()[0].asDict()
            rows_total = int(row["rows_total"] or 0)

            result: dict[str, Any] = {
                "run_ts_utc": run_ts,
                "table_name": table,
                "path": path,
                "rows_total": rows_total,
                "event_dt_min": str(row["event_dt_min"]) if row["event_dt_min"] is not None else "",
                "event_dt_max": str(row["event_dt_max"]) if row["event_dt_max"] is not None else "",
            }

            # Nulos de chaves + percentuais
            for c in existing_keys:
                null_rows = int(row.get(f"null_{c}_rows") or 0)
                null_pct = (null_rows / rows_total * 100.0) if rows_total > 0 else 0.0
                result[f"null_{c}_rows"] = null_rows
                result[f"null_{c}_pct"] = f"{null_pct:.6f}"

            invalid_total = 0
            for k, v in row.items():
                if k.startswith("invalid_"):
                    iv = int(v or 0)
                    result[k] = iv
                    invalid_total += iv
            result["invalid_numeric_total_rows"] = invalid_total
            result["status"] = "ok" if invalid_total == 0 else "warning"

            results.append(result)
            print(
                f"[DQ-C] {table}: rows={rows_total}, invalid_numeric_total={invalid_total}, "
                f"null_cod_linha={result.get('null_cod_linha_rows', 0)}, "
                f"null_cod_veiculo={result.get('null_cod_veiculo_rows', 0)}"
            )
    finally:
        spark.stop()

    return results


def write_csv(output_csv: Path, rows: list[dict[str, Any]]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        fieldnames: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for k in row.keys():
                if k not in seen:
                    seen.add(k)
                    fieldnames.append(k)
    else:
        fieldnames = ["run_ts_utc"]
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    default_cfg = str(Path(__file__).with_name("config.yaml"))
    parser = argparse.ArgumentParser(description="DQ Silver - Bloco A")
    parser.add_argument(
        "--block",
        choices=["a", "b", "c"],
        default="a",
        help="Bloco de qualidade a executar: a=contagem+duplicidade, b=range de coordenadas, c=nulos+tipos.",
    )
    parser.add_argument("--config", default=default_cfg, help="Caminho do config.yaml")
    parser.add_argument(
        "--output-csv",
        default=None,
        help="Caminho do CSV de saida. Se omitido, grava em tcc/artifacts.",
    )
    parser.add_argument(
        "--driver-memory",
        default="6g",
        help="Memoria do driver/executor local do Spark (ex.: 4g, 6g, 8g).",
    )
    parser.add_argument(
        "--tables",
        default="gps_events,stop_events,fare_events,operational_events",
        help="Lista de tabelas separadas por virgula.",
    )
    parser.add_argument(
        "--gps-by-day",
        action="store_true",
        help="No gps_events, calcula por event_dt e consolida (modo mais estavel).",
    )
    parser.add_argument(
        "--master",
        default="local[4]",
        help="Spark master para checks (padrao seguro: local[4]).",
    )
    parser.add_argument(
        "--shuffle-partitions",
        type=int,
        default=64,
        help="spark.sql.shuffle.partitions para checks (padrao seguro: 64).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    artifacts_dir = resolve_artifacts_dir(cfg, args.config)
    if args.output_csv:
        output_csv = Path(args.output_csv).resolve()
    else:
        output_csv = artifacts_dir / f"dq_silver_report_blockA_{run_ts}.csv"

    tables = [t.strip() for t in args.tables.split(",") if t.strip()]
    if args.block == "a":
        rows = run_block_a(
            cfg,
            run_ts,
            tables=tables,
            driver_memory=args.driver_memory,
            master=args.master,
            shuffle_partitions=args.shuffle_partitions,
            gps_by_day=args.gps_by_day,
        )
    else:
        if args.block == "b":
            rows = run_block_b(
                cfg,
                run_ts,
                tables=tables,
                driver_memory=args.driver_memory,
                master=args.master,
                shuffle_partitions=args.shuffle_partitions,
            )
        else:
            rows = run_block_c(
                cfg,
                run_ts,
                tables=tables,
                driver_memory=args.driver_memory,
                master=args.master,
                shuffle_partitions=args.shuffle_partitions,
            )
    write_csv(output_csv, rows)
    print(f"[OK] Relatorio Bloco {args.block.upper()} salvo em: {output_csv}")


if __name__ == "__main__":
    main()
