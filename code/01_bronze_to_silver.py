#!/usr/bin/env python3
"""Bronze -> Silver (Blocos A-E)

Implementa o nucleo inicial do pipeline:
1) leitura JSON Lines do Bronze
2) flatten de campos do avlHeader
3) explode do array gps[] com indice
4) normalizacao de timestamps (event_ts, event_dt)
5) normalizacao de coordenadas (raw + convertido)

Atualmente cobre:
- `gps_events` (Bloco B)
- `stop_events` (Bloco C)
- `fare_events` (Bloco D)
- `operational_events` (Bloco E)
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

# Conversao observada no dataset AVL de Fortaleza.
COORD_SCALE = 360000.0


def load_config(config_path: str) -> dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_spark(cfg: dict[str, Any]) -> SparkSession:
    spark_cfg = cfg["spark"]
    s3_cfg = cfg["s3"]

    builder = (
        SparkSession.builder.master(spark_cfg["master"])
        .appName(spark_cfg["app_name"] + "-block-a")
        .config("spark.sql.shuffle.partitions", str(spark_cfg["shuffle_partitions"]))
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

    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel(spark_cfg.get("log_level", "WARN"))
    return spark


def flatten_avl_header(df_raw: DataFrame) -> DataFrame:
    return df_raw.select(
        F.col("_id").getField("$oid").alias("event_id"),
        F.col("timestamp").cast("long").alias("event_ts_raw"),
        F.col("createdAtOrigem").getField("$date").alias("created_at_origem_raw"),
        F.col("createdAt").getField("$date").alias("created_at_ingestao_raw"),
        F.col("avlHeader.tipoMensagem").alias("tipo_mensagem"),
        F.col("avlHeader.sequencial").cast("long").alias("sequencial"),
        F.col("avlHeader.dataHora").alias("data_hora_header"),
        F.col("avlHeader.validador.idEmpresa").cast("int").alias("id_empresa"),
        F.col("avlHeader.validador.codLinha").cast("int").alias("cod_linha"),
        F.col("avlHeader.validador.prefixoLinha").alias("prefixo_linha"),
        F.col("avlHeader.validador.codVeiculo").cast("int").alias("cod_veiculo"),
        F.col("avlHeader.validador.prefixoVeiculo").alias("prefixo_veiculo"),
        F.col("avlHeader.validador.codGaragem").cast("int").alias("cod_garagem"),
        F.col("avlHeader.jornada.codOperador").cast("long").alias("cod_operador"),
        F.col("avlHeader.jornada.codTabelaProgramacao").alias("cod_tabela_programacao"),
        F.col("avlHeader.viagem.sentido").alias("viagem_sentido"),
        F.col("avlHeader.sensores.statusIgnicao").alias("status_ignicao"),
        F.col("avlHeader.sensores.statusPanico").alias("status_panico"),
        F.col("avlHeader.gps").alias("gps_array"),
        F.col("avlEventoEntradaSaidaPonto.idPonto").cast("int").alias("id_ponto"),
        F.col("avlEventoEntradaSaidaPonto.eventoPonto").alias("evento_ponto"),
    )


def explode_gps(df_flat: DataFrame) -> DataFrame:
    return df_flat.select(
        "*",
        F.posexplode_outer("gps_array").alias("gps_idx", "gps_point"),
    )


def normalize_time_and_coords(df_gps: DataFrame) -> DataFrame:
    lat_raw = F.col("gps_point.latitude").cast("double")
    lon_raw = F.col("gps_point.longitude").cast("double")

    return (
        df_gps.withColumn("event_ts", F.col("event_ts_raw").cast("long"))
        .withColumn("event_dt", F.to_date(F.from_unixtime(F.col("event_ts"))))
        .withColumn("created_at_origem", F.to_timestamp(F.col("created_at_origem_raw")))
        .withColumn("created_at_ingestao", F.to_timestamp(F.col("created_at_ingestao_raw")))
        .withColumn("gps_timestamp_utc_geracao", F.col("gps_point.timestampUtcGeracao").cast("long"))
        .withColumn("gps_sinal", F.col("gps_point.sinalGps"))
        .withColumn("latitude_raw", lat_raw)
        .withColumn("longitude_raw", lon_raw)
        .withColumn("latitude", F.when(lat_raw.isNotNull(), lat_raw / F.lit(COORD_SCALE)))
        .withColumn("longitude", F.when(lon_raw.isNotNull(), lon_raw / F.lit(COORD_SCALE)))
        .withColumn("velocidade", F.col("gps_point.velocidade").cast("double"))
        .withColumn("direcao", F.col("gps_point.direcao").cast("double"))
        .withColumn("numero_satelites", F.col("gps_point.numeroSatelites").cast("int"))
        .withColumn("hdop", F.col("gps_point.hdop").cast("double"))
        .withColumn("pdop", F.col("gps_point.pdop").cast("double"))
        .withColumn("odometro_calculado", F.col("gps_point.odometroCalculado").cast("double"))
        .withColumn("lat_erro", F.col("gps_point.latErro").cast("double"))
        .withColumn("lon_erro", F.col("gps_point.lonErro").cast("double"))
    )


def build_gps_events(df_norm: DataFrame) -> DataFrame:
    """Seleciona colunas finais da gps_events.

    Regra:
    - mantem somente linhas originadas de pontos gps (gps_idx nao nulo)
    """
    gps_cols = [
        "event_id",
        "event_ts",
        "event_dt",
        "created_at_origem",
        "created_at_ingestao",
        "tipo_mensagem",
        "sequencial",
        "id_empresa",
        "cod_linha",
        "prefixo_linha",
        "cod_veiculo",
        "prefixo_veiculo",
        "cod_garagem",
        "cod_operador",
        "cod_tabela_programacao",
        "viagem_sentido",
        "status_ignicao",
        "status_panico",
        "gps_idx",
        "gps_timestamp_utc_geracao",
        "gps_sinal",
        "latitude_raw",
        "longitude_raw",
        "latitude",
        "longitude",
        "velocidade",
        "direcao",
        "numero_satelites",
        "hdop",
        "pdop",
        "odometro_calculado",
        "lat_erro",
        "lon_erro",
    ]
    return df_norm.filter(F.col("gps_idx").isNotNull()).select(*gps_cols)


def apply_optional_date_filter(
    df: DataFrame, date_from: str | None, date_to: str | None
) -> DataFrame:
    """Aplica filtro opcional por data em `event_dt` (YYYY-MM-DD)."""
    out = df
    if date_from:
        out = out.filter(F.col("event_dt") >= F.lit(date_from))
    if date_to:
        out = out.filter(F.col("event_dt") <= F.lit(date_to))
    return out


def write_partitioned(df_out: DataFrame, cfg: dict[str, Any], table_name: str) -> str:
    silver_base = cfg["paths"]["silver_base"].rstrip("/")
    output_path = f"{silver_base}/{table_name}"
    spark_cfg = cfg["spark"]
    (
        df_out.write.mode(spark_cfg["write_mode"])
        .partitionBy("event_dt", "tipo_mensagem", "id_empresa")
        .format(spark_cfg["silver_format"])
        .save(output_path)
    )
    return output_path


def _to_utc(ts: int | None) -> str:
    if ts is None:
        return "null"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def validate_gps_events(df_gps_events: DataFrame, output_path: str) -> dict[str, Any]:
    """Validacao minima para checklist do Bloco B."""
    total = df_gps_events.count()
    mm = df_gps_events.agg(
        F.min("event_ts").alias("min_ts"),
        F.max("event_ts").alias("max_ts"),
        F.countDistinct("event_id").alias("distinct_events"),
    ).collect()[0]
    min_ts = int(mm["min_ts"]) if mm["min_ts"] is not None else None
    max_ts = int(mm["max_ts"]) if mm["max_ts"] is not None else None
    distinct_events = int(mm["distinct_events"]) if mm["distinct_events"] is not None else 0

    print("\n=== Validacao minima: gps_events ===")
    print("output_path=", output_path)
    print("rows=", total)
    print("distinct_event_id=", distinct_events)
    print(f"event_ts_range={min_ts} ({_to_utc(min_ts)}) -> {max_ts} ({_to_utc(max_ts)})")
    print("schema:")
    df_gps_events.printSchema()

    if total <= 0:
        raise RuntimeError("Validacao falhou: gps_events sem registros.")

    return {
        "rows": total,
        "distinct_event_id": distinct_events,
        "min_ts": min_ts,
        "max_ts": max_ts,
        "output_path": output_path,
    }


def build_stop_events(df_norm: DataFrame) -> DataFrame:
    """Seleciona colunas finais da stop_events."""
    stop_cols = [
        "event_id",
        "event_ts",
        "event_dt",
        "created_at_origem",
        "created_at_ingestao",
        "tipo_mensagem",
        "sequencial",
        "id_empresa",
        "cod_linha",
        "prefixo_linha",
        "cod_veiculo",
        "prefixo_veiculo",
        "cod_garagem",
        "cod_operador",
        "cod_tabela_programacao",
        "viagem_sentido",
        "status_ignicao",
        "status_panico",
        "id_ponto",
        "evento_ponto",
        "gps_idx",
        "gps_sinal",
        "latitude_raw",
        "longitude_raw",
        "latitude",
        "longitude",
        "velocidade",
        "direcao",
        "numero_satelites",
        "odometro_calculado",
    ]
    return df_norm.filter(F.col("tipo_mensagem") == F.lit("AVL_EVT_ENTRADA_SAIDA_PONTO")).select(*stop_cols)


def validate_stop_events(df_stop_events: DataFrame, output_path: str) -> dict[str, Any]:
    """Validacao minima para checklist do Bloco C."""
    total = df_stop_events.count()
    mm = df_stop_events.agg(
        F.min("event_ts").alias("min_ts"),
        F.max("event_ts").alias("max_ts"),
        F.countDistinct("event_id").alias("distinct_events"),
        F.countDistinct("id_ponto").alias("distinct_stops"),
    ).collect()[0]
    min_ts = int(mm["min_ts"]) if mm["min_ts"] is not None else None
    max_ts = int(mm["max_ts"]) if mm["max_ts"] is not None else None
    distinct_events = int(mm["distinct_events"]) if mm["distinct_events"] is not None else 0
    distinct_stops = int(mm["distinct_stops"]) if mm["distinct_stops"] is not None else 0

    print("\n=== Validacao minima: stop_events ===")
    print("output_path=", output_path)
    print("rows=", total)
    print("distinct_event_id=", distinct_events)
    print("distinct_id_ponto=", distinct_stops)
    print(f"event_ts_range={min_ts} ({_to_utc(min_ts)}) -> {max_ts} ({_to_utc(max_ts)})")
    print("schema:")
    df_stop_events.printSchema()

    if total <= 0:
        raise RuntimeError("Validacao falhou: stop_events sem registros.")

    return {
        "rows": total,
        "distinct_event_id": distinct_events,
        "distinct_id_ponto": distinct_stops,
        "min_ts": min_ts,
        "max_ts": max_ts,
        "output_path": output_path,
    }


def build_fare_events(df_norm: DataFrame) -> DataFrame:
    """Seleciona colunas finais da fare_events."""
    fare_cols = [
        "event_id",
        "event_ts",
        "event_dt",
        "created_at_origem",
        "created_at_ingestao",
        "tipo_mensagem",
        "sequencial",
        "id_empresa",
        "cod_linha",
        "prefixo_linha",
        "cod_veiculo",
        "prefixo_veiculo",
        "cod_garagem",
        "cod_operador",
        "cod_tabela_programacao",
        "viagem_sentido",
        "status_ignicao",
        "status_panico",
        "gps_idx",
        "gps_sinal",
        "latitude_raw",
        "longitude_raw",
        "latitude",
        "longitude",
        "velocidade",
        "direcao",
        "numero_satelites",
        "odometro_calculado",
    ]
    # Escopo atual: passagem por cartao. Outros eventos tarifarios entram no bloco operacional.
    return df_norm.filter(F.col("tipo_mensagem") == F.lit("AVL_EVT_PASSAGEM_CARTAO")).select(*fare_cols)


def validate_fare_events(df_fare_events: DataFrame, output_path: str) -> dict[str, Any]:
    """Validacao minima para checklist do Bloco D."""
    total = df_fare_events.count()
    mm = df_fare_events.agg(
        F.min("event_ts").alias("min_ts"),
        F.max("event_ts").alias("max_ts"),
        F.countDistinct("event_id").alias("distinct_events"),
        F.countDistinct("cod_linha").alias("distinct_lines"),
        F.countDistinct("cod_veiculo").alias("distinct_vehicles"),
    ).collect()[0]
    min_ts = int(mm["min_ts"]) if mm["min_ts"] is not None else None
    max_ts = int(mm["max_ts"]) if mm["max_ts"] is not None else None
    distinct_events = int(mm["distinct_events"]) if mm["distinct_events"] is not None else 0
    distinct_lines = int(mm["distinct_lines"]) if mm["distinct_lines"] is not None else 0
    distinct_vehicles = int(mm["distinct_vehicles"]) if mm["distinct_vehicles"] is not None else 0

    print("\n=== Validacao minima: fare_events ===")
    print("output_path=", output_path)
    print("rows=", total)
    print("distinct_event_id=", distinct_events)
    print("distinct_cod_linha=", distinct_lines)
    print("distinct_cod_veiculo=", distinct_vehicles)
    print(f"event_ts_range={min_ts} ({_to_utc(min_ts)}) -> {max_ts} ({_to_utc(max_ts)})")
    print("schema:")
    df_fare_events.printSchema()

    if total <= 0:
        raise RuntimeError("Validacao falhou: fare_events sem registros.")

    return {
        "rows": total,
        "distinct_event_id": distinct_events,
        "distinct_cod_linha": distinct_lines,
        "distinct_cod_veiculo": distinct_vehicles,
        "min_ts": min_ts,
        "max_ts": max_ts,
        "output_path": output_path,
    }


def build_operational_events(df_norm: DataFrame) -> DataFrame:
    """Seleciona colunas finais da operational_events."""
    operational_cols = [
        "event_id",
        "event_ts",
        "event_dt",
        "created_at_origem",
        "created_at_ingestao",
        "tipo_mensagem",
        "sequencial",
        "id_empresa",
        "cod_linha",
        "prefixo_linha",
        "cod_veiculo",
        "prefixo_veiculo",
        "cod_garagem",
        "cod_operador",
        "cod_tabela_programacao",
        "viagem_sentido",
        "status_ignicao",
        "status_panico",
        "gps_idx",
        "gps_sinal",
        "latitude_raw",
        "longitude_raw",
        "latitude",
        "longitude",
        "velocidade",
        "direcao",
        "numero_satelites",
        "odometro_calculado",
    ]
    excluded_types = [
        "AVL_EVT_POSICIONAMENTO",
        "AVL_EVT_ENTRADA_SAIDA_PONTO",
        "AVL_EVT_PASSAGEM_CARTAO",
    ]
    return df_norm.filter(~F.col("tipo_mensagem").isin(excluded_types)).select(*operational_cols)


def validate_operational_events(df_operational_events: DataFrame, output_path: str) -> dict[str, Any]:
    """Validacao minima para checklist do Bloco E."""
    total = df_operational_events.count()
    mm = df_operational_events.agg(
        F.min("event_ts").alias("min_ts"),
        F.max("event_ts").alias("max_ts"),
    ).collect()[0]
    min_ts = int(mm["min_ts"]) if mm["min_ts"] is not None else None
    max_ts = int(mm["max_ts"]) if mm["max_ts"] is not None else None

    print("\n=== Validacao minima: operational_events ===")
    print("output_path=", output_path)
    print("rows=", total)
    print(f"event_ts_range={min_ts} ({_to_utc(min_ts)}) -> {max_ts} ({_to_utc(max_ts)})")
    print("schema:")
    df_operational_events.printSchema()

    if total <= 0:
        raise RuntimeError("Validacao falhou: operational_events sem registros.")

    return {
        "rows": total,
        "min_ts": min_ts,
        "max_ts": max_ts,
        "output_path": output_path,
    }


def run_preview(df_norm: DataFrame, preview_n: int) -> None:
    cols = [
        "event_id",
        "tipo_mensagem",
        "event_ts",
        "event_dt",
        "id_empresa",
        "cod_linha",
        "cod_veiculo",
        "gps_idx",
        "gps_sinal",
        "latitude_raw",
        "longitude_raw",
        "latitude",
        "longitude",
        "velocidade",
        "id_ponto",
        "evento_ponto",
    ]

    print("\n=== Schema (transformado - bloco A) ===")
    df_norm.select(*cols).printSchema()

    print(f"\n=== Preview ({preview_n} linhas) ===")
    df_norm.select(*cols).show(preview_n, truncate=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bronze -> Silver (Blocos A e B)")
    default_cfg = str(Path(__file__).with_name("config.yaml"))
    parser.add_argument("--config", default=default_cfg, help="Caminho do config.yaml")
    parser.add_argument("--preview-n", type=int, default=10, help="Numero de linhas no preview")
    parser.add_argument(
        "--date-from",
        default=None,
        help="Filtro opcional (inclusive) de event_dt, formato YYYY-MM-DD",
    )
    parser.add_argument(
        "--date-to",
        default=None,
        help="Filtro opcional (inclusive) de event_dt, formato YYYY-MM-DD",
    )
    parser.add_argument(
        "--sample-fraction",
        type=float,
        default=None,
        help="Amostragem opcional uniforme (0 < f <= 1) aplicada apos filtro de data.",
    )
    parser.add_argument(
        "--sample-seed",
        type=int,
        default=42,
        help="Seed da amostragem opcional.",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Limite opcional de registros apos filtros/amostragem (janela curta de desenvolvimento).",
    )
    parser.add_argument(
        "--write-gps-events",
        action="store_true",
        help="Escreve tabela gps_events na camada Silver e executa validacao minima.",
    )
    parser.add_argument(
        "--write-stop-events",
        action="store_true",
        help="Escreve tabela stop_events na camada Silver e executa validacao minima.",
    )
    parser.add_argument(
        "--write-fare-events",
        action="store_true",
        help="Escreve tabela fare_events na camada Silver e executa validacao minima.",
    )
    parser.add_argument(
        "--write-operational-events",
        action="store_true",
        help="Escreve tabela operational_events na camada Silver e executa validacao minima.",
    )
    parser.add_argument(
        "--skip-validations",
        action="store_true",
        help="Pula validacoes minimas apos escrita (util para rodada end-to-end de carga).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    input_path = cfg["paths"]["bronze_input"]

    spark = build_spark(cfg)
    try:
        print(f"[INFO] Lendo Bronze JSONL: {input_path}")
        df_raw = spark.read.option("multiLine", "false").json(input_path)

        print("[INFO] Flatten avlHeader")
        df_flat = flatten_avl_header(df_raw)

        print("[INFO] Explode gps[] com indice")
        df_gps = explode_gps(df_flat)

        print("[INFO] Normalizando timestamps e coordenadas")
        df_norm = normalize_time_and_coords(df_gps)

        run_preview(df_norm, args.preview_n)

        print("[INFO] Aplicando filtro opcional por data (se informado)")
        df_filtered = apply_optional_date_filter(df_norm, args.date_from, args.date_to)
        if args.sample_fraction is not None:
            if not (0 < args.sample_fraction <= 1):
                raise ValueError("--sample-fraction deve estar no intervalo (0, 1].")
            print(f"[INFO] Aplicando amostragem opcional: fraction={args.sample_fraction}, seed={args.sample_seed}")
            df_filtered = df_filtered.sample(withReplacement=False, fraction=args.sample_fraction, seed=args.sample_seed)
        if args.max_records is not None:
            if args.max_records <= 0:
                raise ValueError("--max-records deve ser > 0.")
            print(f"[INFO] Aplicando limite opcional de registros: max_records={args.max_records}")
            df_filtered = df_filtered.limit(args.max_records)

        if args.write_gps_events:
            print("[INFO] Construindo tabela gps_events")
            gps_events = build_gps_events(df_filtered)

            print("[INFO] Escrevendo gps_events no Silver particionado")
            output_path = write_partitioned(gps_events, cfg, "gps_events")

            if not args.skip_validations:
                validate_gps_events(gps_events, output_path)
            print("\n[OK] Bloco B concluido: gps_events criado e validado.")
        if args.write_stop_events:
            print("[INFO] Construindo tabela stop_events")
            stop_events = build_stop_events(df_filtered)

            print("[INFO] Escrevendo stop_events no Silver particionado")
            output_path = write_partitioned(stop_events, cfg, "stop_events")

            if not args.skip_validations:
                validate_stop_events(stop_events, output_path)
            print("\n[OK] Bloco C concluido: stop_events criado e validado.")

        if args.write_fare_events:
            print("[INFO] Construindo tabela fare_events")
            fare_events = build_fare_events(df_filtered)

            print("[INFO] Escrevendo fare_events no Silver particionado")
            output_path = write_partitioned(fare_events, cfg, "fare_events")

            if not args.skip_validations:
                validate_fare_events(fare_events, output_path)
            print("\n[OK] Bloco D concluido: fare_events criado e validado.")

        if args.write_operational_events:
            print("[INFO] Construindo tabela operational_events")
            operational_events = build_operational_events(df_filtered)

            print("[INFO] Escrevendo operational_events no Silver particionado")
            output_path = write_partitioned(operational_events, cfg, "operational_events")

            if not args.skip_validations:
                validate_operational_events(operational_events, output_path)
            print("\n[OK] Bloco E concluido: operational_events criado e validado.")

        if (
            not args.write_gps_events
            and not args.write_stop_events
            and not args.write_fare_events
            and not args.write_operational_events
        ):
            print("\n[OK] Bloco A concluido no script.")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
