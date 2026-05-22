#!/usr/bin/env python3
"""Etapa 9 (Bloco A): materializa a final_table na camada Gold."""

from __future__ import annotations

import argparse
import importlib.util
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def load_config(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"YAML invalido: {config_path}")
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


def resolve_s3_credentials(cfg: dict[str, Any]) -> None:
    s3_cfg = cfg["s3"]
    access_key = s3_cfg.get("access_key")
    secret_key = s3_cfg.get("secret_key")

    if isinstance(access_key, str) and access_key.startswith("CHANGE_ME"):
        access_key = os.getenv("TCC_S3_ACCESS_KEY") or os.getenv("MINIO_ROOT_USER") or os.getenv("MINIO_ACCESS_KEY")
    if isinstance(secret_key, str) and secret_key.startswith("CHANGE_ME"):
        secret_key = os.getenv("TCC_S3_SECRET_KEY") or os.getenv("MINIO_ROOT_PASSWORD") or os.getenv("MINIO_SECRET_KEY")

    if not access_key or not secret_key:
        raise EnvironmentError("Credenciais S3/MinIO ausentes. Defina em config.yaml ou tcc/.env.local.")

    s3_cfg["access_key"] = access_key
    s3_cfg["secret_key"] = secret_key


def build_spark(cfg: dict[str, Any], app_suffix: str = "final-table") -> SparkSession:
    spark_cfg = cfg["spark"]
    s3_cfg = cfg["s3"]
    driver_memory = spark_cfg.get("driver_memory", "4g")
    executor_memory = spark_cfg.get("executor_memory", "4g")
    io_codec = spark_cfg.get("io_compression_codec", "snappy")
    default_parallelism = spark_cfg.get("default_parallelism", 96)

    builder = (
        SparkSession.builder.master(spark_cfg["master"])
        .appName(f"{spark_cfg['app_name']}-{app_suffix}")
        .config("spark.sql.shuffle.partitions", str(spark_cfg["shuffle_partitions"]))
        .config("spark.default.parallelism", str(default_parallelism))
        .config("spark.sql.adaptive.enabled", str(spark_cfg["adaptive_enabled"]).lower())
        .config("spark.sql.session.timeZone", spark_cfg["session_timezone"])
        .config("spark.driver.memory", driver_memory)
        .config("spark.executor.memory", executor_memory)
        .config("spark.io.compression.codec", io_codec)
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

    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel(spark_cfg.get("log_level", "WARN"))
    return spark


def parse_args() -> argparse.Namespace:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Materializa final_table na Gold")
    parser.add_argument("--config", default=str(base / "config.yaml"))
    parser.add_argument(
        "--wrangling-module",
        default=str(base / "generated" / "wrangling_retry_openai_gpt_4o_attempt2_2026-04-03_1943.py"),
    )
    parser.add_argument("--output-path", default=None, help="Sobrescreve o destino Gold/final_table")
    parser.add_argument("--date-from", default=None, help="Filtro opcional em event_dt (YYYY-MM-DD)")
    parser.add_argument("--date-to", default=None, help="Filtro opcional em event_dt (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Valida leitura/import sem escrever")
    return parser.parse_args()


def load_wrangling_module(module_path: Path):
    spec = importlib.util.spec_from_file_location("approved_wrangling", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Nao foi possivel carregar modulo: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "build_final_table"):
        raise AttributeError(f"Modulo sem build_final_table: {module_path}")
    if not hasattr(module, "validate_final_table"):
        raise AttributeError(f"Modulo sem validate_final_table: {module_path}")
    return module


def apply_optional_date_filter(df: DataFrame, date_from: str | None, date_to: str | None) -> DataFrame:
    out = df
    if date_from:
        out = out.filter(F.col("event_dt") >= F.lit(date_from))
    if date_to:
        out = out.filter(F.col("event_dt") <= F.lit(date_to))
    return out


def load_silver_tables(spark: SparkSession, cfg: dict[str, Any], date_from: str | None, date_to: str | None) -> dict[str, DataFrame]:
    silver_base = cfg["paths"]["silver_base"].rstrip("/")
    tables = {}
    for table_name in ("gps_events", "stop_events", "fare_events", "operational_events"):
        path = f"{silver_base}/{table_name}"
        df = spark.read.parquet(path)
        df = apply_optional_date_filter(df, date_from, date_to)
        tables[table_name] = df
    return tables


def apply_semantic_fallbacks(df: DataFrame) -> DataFrame:
    gps_invalid_expr = (
        (F.col("gps_sinal") == 0)
        | F.col("latitude").isNull()
        | F.col("longitude").isNull()
        | (F.col("latitude") < F.lit(-90.0))
        | (F.col("latitude") > F.lit(90.0))
        | (F.col("longitude") < F.lit(-180.0))
        | (F.col("longitude") > F.lit(180.0))
    )

    return (
        df.withColumn("id_empresa", F.coalesce(F.col("id_empresa"), F.lit(-1)))
        .withColumn("cod_linha", F.coalesce(F.col("cod_linha"), F.lit(-1)))
        .withColumn("cod_veiculo", F.coalesce(F.col("cod_veiculo"), F.lit(-1)))
        .withColumn("viagem_sentido", F.coalesce(F.col("viagem_sentido"), F.lit("ND")))
        .withColumn("event_ts_ts", F.to_timestamp(F.from_unixtime(F.col("event_ts"))))
        .withColumn("janela_5min", F.window(F.col("event_ts_ts"), "5 minutes").start)
        .withColumn("gps_is_invalid", gps_invalid_expr.cast("int"))
    )


def build_vehicle_window_context(gps_events: DataFrame) -> DataFrame:
    gps_norm = apply_semantic_fallbacks(gps_events)

    return (
        gps_norm.groupBy("event_dt", "cod_linha", "cod_veiculo", "janela_5min")
        .agg(
            F.first("id_empresa", ignorenulls=True).alias("id_empresa"),
            F.first("viagem_sentido", ignorenulls=True).alias("viagem_sentido"),
            F.avg("latitude").alias("latitude_media"),
            F.avg("longitude").alias("longitude_media"),
            F.avg("velocidade").alias("velocidade_media"),
            F.avg(F.col("gps_is_invalid").cast("double")).alias("gps_invalid_pct"),
            F.count(F.lit(1)).alias("qtd_eventos_gps"),
            F.max("numero_satelites").alias("max_satelites"),
        )
    )


def build_stop_headway_metrics(stop_events: DataFrame) -> DataFrame:
    stop_norm = apply_semantic_fallbacks(stop_events)

    event_order_window = (
        Window.partitionBy("event_dt", "cod_linha", "viagem_sentido")
        .orderBy("event_ts_ts", "event_id", "gps_idx")
    )

    stop_with_lag = (
        stop_norm.withColumn("prev_event_ts_ts", F.lag("event_ts_ts").over(event_order_window))
        .withColumn(
            "headway_diff_min",
            (
                F.col("event_ts_ts").cast("long") - F.col("prev_event_ts_ts").cast("long")
            )
            / F.lit(60.0),
        )
    )

    stop_valid = stop_with_lag.filter(
        F.col("headway_diff_min").isNotNull()
        & (F.col("headway_diff_min") > F.lit(0.0))
        & (F.col("headway_diff_min") <= F.lit(180.0))
    )

    observed = (
        stop_valid.groupBy("event_dt", "cod_linha", "viagem_sentido", "janela_5min")
        .agg(
            F.avg("headway_diff_min").alias("headway_observado_min"),
            F.count(F.lit(1)).alias("n_eventos_ponto"),
        )
        .withColumn("faixa_horaria", F.hour("janela_5min"))
    )

    reference = (
        observed.groupBy("cod_linha", "viagem_sentido", "faixa_horaria")
        .agg(F.expr("percentile_approx(headway_observado_min, 0.5)").alias("headway_referencia_min"))
    )

    return (
        observed.join(reference, on=["cod_linha", "viagem_sentido", "faixa_horaria"], how="left")
        .withColumn(
            "atraso_aproximado_min",
            F.greatest(F.lit(0.0), F.col("headway_observado_min") - F.col("headway_referencia_min")),
        )
        .drop("faixa_horaria")
    )


def build_final_table_enriched(df_llm: DataFrame, df_dict: dict[str, DataFrame]) -> DataFrame:
    vehicle_context = build_vehicle_window_context(df_dict["gps_events"]).select(
        "event_dt",
        "cod_linha",
        "cod_veiculo",
        "janela_5min",
        F.col("id_empresa").alias("ctx_id_empresa"),
        F.col("viagem_sentido").alias("ctx_viagem_sentido"),
        "latitude_media",
        "longitude_media",
        "velocidade_media",
        "gps_invalid_pct",
        "qtd_eventos_gps",
        "max_satelites",
    )
    headway_metrics = build_stop_headway_metrics(df_dict["stop_events"])

    llm_keys = (
        df_llm.select("event_dt", "cod_linha", "cod_veiculo", "janela_5min")
        .dropDuplicates()
    )

    stop_vehicle_windows = (
        apply_semantic_fallbacks(df_dict["stop_events"])
        .groupBy("event_dt", "cod_linha", "cod_veiculo", "janela_5min")
        .agg(
            F.first("viagem_sentido", ignorenulls=True).alias("viagem_sentido"),
            F.count(F.lit(1)).alias("qtd_eventos_stop"),
        )
    )

    base = (
        llm_keys.join(stop_vehicle_windows, on=["event_dt", "cod_linha", "cod_veiculo", "janela_5min"], how="inner")
        .join(vehicle_context, on=["event_dt", "cod_linha", "cod_veiculo", "janela_5min"], how="left")
        .withColumn(
            "viagem_sentido",
            F.coalesce(F.col("viagem_sentido"), F.col("ctx_viagem_sentido"), F.lit("ND")),
        )
        .withColumn("id_empresa", F.coalesce(F.col("ctx_id_empresa"), F.lit(-1)))
        .drop("ctx_id_empresa", "ctx_viagem_sentido")
    )

    final_table = (
        base.join(
            headway_metrics,
            on=["event_dt", "cod_linha", "viagem_sentido", "janela_5min"],
            how="left",
        )
        .withColumn("id_empresa", F.coalesce(F.col("id_empresa"), F.lit(-1)))
        .withColumn("gps_invalid_pct", F.coalesce(F.col("gps_invalid_pct"), F.lit(0.0)))
        .withColumn("qtd_eventos_gps", F.coalesce(F.col("qtd_eventos_gps"), F.lit(0)))
        .withColumn("qtd_eventos_stop", F.coalesce(F.col("qtd_eventos_stop"), F.lit(0)))
        .withColumn(
            "headway_observado_min",
            F.col("headway_observado_min").cast("double"),
        )
        .withColumn(
            "headway_referencia_min",
            F.col("headway_referencia_min").cast("double"),
        )
        .withColumn(
            "atraso_aproximado_min",
            F.col("atraso_aproximado_min").cast("double"),
        )
        .select(
            "event_dt",
            "cod_linha",
            "cod_veiculo",
            "id_empresa",
            "viagem_sentido",
            "janela_5min",
            "latitude_media",
            "longitude_media",
            "velocidade_media",
            "gps_invalid_pct",
            "qtd_eventos_gps",
            "qtd_eventos_stop",
            "max_satelites",
            "headway_observado_min",
            "headway_referencia_min",
            "atraso_aproximado_min",
        )
    )
    return final_table.repartition(256, "event_dt", "cod_linha")


def write_artifact(base_dir: Path, lines: list[str]) -> Path:
    artifacts_dir = (base_dir.parent / "artifacts").resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    path = artifacts_dir / f"final_table_materialization_{ts}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    load_local_env(base_dir)
    config_path = Path(args.config).resolve()
    wrangling_module_path = Path(args.wrangling_module).resolve()

    cfg = load_config(config_path)
    resolve_s3_credentials(cfg)
    output_path = args.output_path or f"{cfg['paths']['gold_base'].rstrip('/')}/final_table"
    write_mode = cfg["spark"].get("write_mode", "overwrite")
    gold_format = cfg["spark"].get("gold_format", "parquet")

    module = load_wrangling_module(wrangling_module_path)
    spark = build_spark(cfg)

    artifact_lines = [
        "# FinalTable Materialization",
        f"- timestamp: {datetime.now().isoformat()}",
        f"- wrangling_module: `{wrangling_module_path}`",
        f"- output_path: `{output_path}`",
        f"- write_mode: `{write_mode}`",
        f"- gold_format: `{gold_format}`",
        f"- date_from: `{args.date_from}`",
        f"- date_to: `{args.date_to}`",
        f"- dry_run: `{args.dry_run}`",
    ]

    try:
        df_dict = load_silver_tables(spark, cfg, args.date_from, args.date_to)
        artifact_lines.append("- silver_tables_loaded: `ok`")

        df_llm = module.build_final_table(df_dict)
        module.validate_final_table(df_llm)
        artifact_lines.append("- wrangling_execution: `ok`")
        artifact_lines.append(f"- llm_contract_columns: `{df_llm.columns}`")

        df_final = build_final_table_enriched(df_llm, df_dict)
        artifact_lines.append("- gold_refinement: `deterministic_enrichment`")
        artifact_lines.append(f"- final_columns: `{df_final.columns}`")

        if not args.dry_run:
            writer = df_final.write.mode(write_mode)
            if gold_format == "parquet":
                writer = writer.partitionBy("event_dt")
            writer.format(gold_format).save(output_path)
            artifact_lines.append("- write_status: `ok`")
        else:
            artifact_lines.append("- write_status: `skipped (dry-run)`")
    finally:
        spark.stop()

    artifact_path = write_artifact(base_dir, artifact_lines)
    print("=== FinalTable Materialization ===")
    print(f"wrangling_module: {wrangling_module_path}")
    print(f"output_path: {output_path}")
    print(f"artifact: {artifact_path}")
    print("\n[OK] Etapa de materializacao concluida.")


if __name__ == "__main__":
    main()
