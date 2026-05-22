from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, when, expr, window, lit
from pyspark.sql.types import DoubleType, StringType, DateType

def build_final_table(df_dict: dict[str, DataFrame]) -> DataFrame:
    # Validate input DataFrames
    required_columns = {
        "gps_events": ["event_id", "gps_idx", "event_ts", "event_dt", "id_empresa", "cod_linha", "cod_veiculo", "gps_sinal", "latitude", "longitude"],
        "stop_events": ["event_id", "gps_idx", "event_ts", "event_dt", "id_empresa", "cod_linha", "cod_veiculo"],
        "fare_events": ["event_id", "gps_idx", "event_ts", "event_dt", "id_empresa", "cod_linha", "cod_veiculo"],
        "operational_events": ["event_id", "gps_idx", "event_ts", "event_dt", "id_empresa", "cod_linha", "cod_veiculo"]
    }
    
    for key, columns in required_columns.items():
        if key not in df_dict:
            raise ValueError(f"Missing DataFrame for key: {key}")
        for column in columns:
            if column not in df_dict[key].columns:
                raise ValueError(f"Missing column '{column}' in DataFrame '{key}'")

    # Apply semantic rules
    def apply_semantic_rules(df: DataFrame) -> DataFrame:
        return df.withColumn("id_empresa", when(col("id_empresa").isNull(), lit(-1)).otherwise(col("id_empresa"))) \
                 .withColumn("cod_linha", when(col("cod_linha").isNull(), lit(-1)).otherwise(col("cod_linha"))) \
                 .withColumn("cod_veiculo", when(col("cod_veiculo").isNull(), lit(-1)).otherwise(col("cod_veiculo"))) \
                 .withColumn("gps_is_invalid", when((col("gps_sinal") == 0) | col("latitude").isNull() | col("longitude").isNull(), lit(True)).otherwise(lit(False)))

    gps_events = apply_semantic_rules(df_dict["gps_events"])
    stop_events = apply_semantic_rules(df_dict["stop_events"])
    fare_events = apply_semantic_rules(df_dict["fare_events"])
    operational_events = apply_semantic_rules(df_dict["operational_events"])

    # Combine DataFrames
    combined_df = gps_events.unionByName(stop_events).unionByName(fare_events).unionByName(operational_events)

    # Create final table
    final_table = combined_df.withColumn("janela_5min", expr("window(event_ts, '5 minutes').start")) \
                             .withColumn("headway_observado_min", lit(None).cast(DoubleType())) \
                             .withColumn("headway_referencia_min", lit(None).cast(DoubleType())) \
                             .withColumn("atraso_aproximado_min", lit(None).cast(DoubleType())) \
                             .select("event_dt", "cod_linha", "cod_veiculo", "janela_5min", "headway_observado_min", "headway_referencia_min", "atraso_aproximado_min")

    validate_final_table(final_table)
    return final_table

def validate_final_table(df_final: DataFrame) -> None:
    # Check for required columns
    required_columns = ["event_dt", "cod_linha", "cod_veiculo", "janela_5min", "headway_observado_min", "headway_referencia_min", "atraso_aproximado_min"]
    for column in required_columns:
        if column not in df_final.columns:
            raise ValueError(f"Missing required column: {column}")

    # Check for numeric types
    numeric_columns = ["headway_observado_min", "headway_referencia_min", "atraso_aproximado_min"]
    for column in numeric_columns:
        if not isinstance(df_final.schema[column].dataType, DoubleType):
            raise TypeError(f"Column {column} must be of type DoubleType")

    # Check for nulls in key columns
    key_columns = ["event_dt", "cod_linha", "cod_veiculo"]
    for column in key_columns:
        if df_final.filter(col(column).isNull()).count() > 0:
            raise ValueError(f"Null values found in key column: {column}")

    # Check coordinate ranges if used
    if "latitude" in df_final.columns and "longitude" in df_final.columns:
        if df_final.filter((col("latitude") < -90) | (col("latitude") > 90) | (col("longitude") < -180) | (col("longitude") > 180)).count() > 0:
            raise ValueError("Latitude or longitude values out of range")
