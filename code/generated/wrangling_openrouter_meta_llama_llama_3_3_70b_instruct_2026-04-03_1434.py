from pyspark.sql import functions as F
from pyspark.sql import types as T

def build_final_table(df_dict: dict[str, DataFrame]) -> DataFrame:
    # Validate input DataFrames
    required_dfs = ["gps_events", "stop_events", "fare_events", "operational_events"]
    if not all(df in df_dict for df in required_dfs):
        raise ValueError("All required DataFrames must be present in the input dictionary")

    # Apply semantic rules
    gps_events = df_dict["gps_events"]
    stop_events = df_dict["stop_events"]
    fare_events = df_dict["fare_events"]
    operational_events = df_dict["operational_events"]

    # Fallback for missing keys
    gps_events = gps_events.withColumn("id_empresa", F.coalesce(gps_events["id_empresa"], F.lit(-1))) \
                         .withColumn("cod_linha", F.coalesce(gps_events["cod_linha"], F.lit(-1))) \
                         .withColumn("cod_veiculo", F.coalesce(gps_events["cod_veiculo"], F.lit(-1)))

    stop_events = stop_events.withColumn("id_empresa", F.coalesce(stop_events["id_empresa"], F.lit(-1))) \
                            .withColumn("cod_linha", F.coalesce(stop_events["cod_linha"], F.lit(-1))) \
                            .withColumn("cod_veiculo", F.coalesce(stop_events["cod_veiculo"], F.lit(-1)))

    fare_events = fare_events.withColumn("id_empresa", F.coalesce(fare_events["id_empresa"], F.lit(-1))) \
                           .withColumn("cod_linha", F.coalesce(fare_events["cod_linha"], F.lit(-1))) \
                           .withColumn("cod_veiculo", F.coalesce(fare_events["cod_veiculo"], F.lit(-1)))

    operational_events = operational_events.withColumn("id_empresa", F.coalesce(operational_events["id_empresa"], F.lit(-1))) \
                                    .withColumn("cod_linha", F.coalesce(operational_events["cod_linha"], F.lit(-1))) \
                                    .withColumn("cod_veiculo", F.coalesce(operational_events["cod_veiculo"], F.lit(-1)))

    # Create a flag for invalid GPS
    gps_events = gps_events.withColumn("gps_is_invalid", F.when((gps_events["gps_sinal"] == "invalid") | 
                                                                (gps_events["latitude"].isNull()) | 
                                                                (gps_events["longitude"].isNull()) | 
                                                                (gps_events["latitude"] < -90) | 
                                                                (gps_events["latitude"] > 90) | 
                                                                (gps_events["longitude"] < -180) | 
                                                                (gps_events["longitude"] > 180), F.lit(True)).otherwise(F.lit(False)))

    stop_events = stop_events.withColumn("gps_is_invalid", F.when((stop_events["gps_sinal"] == "invalid") | 
                                                                (stop_events["latitude"].isNull()) | 
                                                                (stop_events["longitude"].isNull()) | 
                                                                (stop_events["latitude"] < -90) | 
                                                                (stop_events["latitude"] > 90) | 
                                                                (stop_events["longitude"] < -180) | 
                                                                (stop_events["longitude"] > 180), F.lit(True)).otherwise(F.lit(False)))

    fare_events = fare_events.withColumn("gps_is_invalid", F.when((fare_events["gps_sinal"] == "invalid") | 
                                                                (fare_events["latitude"].isNull()) | 
                                                                (fare_events["longitude"].isNull()) | 
                                                                (fare_events["latitude"] < -90) | 
                                                                (fare_events["latitude"] > 90) | 
                                                                (fare_events["longitude"] < -180) | 
                                                                (fare_events["longitude"] > 180), F.lit(True)).otherwise(F.lit(False)))

    operational_events = operational_events.withColumn("gps_is_invalid", F.when((operational_events["gps_sinal"] == "invalid") | 
                                                                            (operational_events["latitude"].isNull()) | 
                                                                            (operational_events["longitude"].isNull()) | 
                                                                            (operational_events["latitude"] < -90) | 
                                                                            (operational_events["latitude"] > 90) | 
                                                                            (operational_events["longitude"] < -180) | 
                                                                            (operational_events["longitude"] > 180), F.lit(True)).otherwise(F.lit(False)))

    # Create a canonical timestamp
    gps_events = gps_events.withColumn("event_ts", F.col("event_ts")) \
                         .withColumn("created_at_origem", F.col("created_at_origem")) \
                         .withColumn("created_at_ingestao", F.col("created_at_ingestao"))

    stop_events = stop_events.withColumn("event_ts", F.col("event_ts")) \
                           .withColumn("created_at_origem", F.col("created_at_origem")) \
                           .withColumn("created_at_ingestao", F.col("created_at_ingestao"))

    fare_events = fare_events.withColumn("event_ts", F.col("event_ts")) \
                           .withColumn("created_at_origem", F.col("created_at_origem")) \
                           .withColumn("created_at_ingestao", F.col("created_at_ingestao"))

    operational_events = operational_events.withColumn("event_ts", F.col("event_ts")) \
                                    .withColumn("created_at_origem", F.col("created_at_origem")) \
                                    .withColumn("created_at_ingestao", F.col("created_at_ingestao"))

    # Generate the final table
    final_table = gps_events.join(stop_events, on=["event_id", "gps_idx"], how="outer") \
                          .join(fare_events, on=["event_id", "gps_idx"], how="outer") \
                          .join(operational_events, on=["event_id", "gps_idx"], how="outer")

    final_table = final_table.select("event_dt", "cod_linha", "cod_veiculo", 
                                    F.window(F.col("event_ts"), "5 minutes").alias("janela_5min"), 
                                    F.lag("event_ts", 1).over(F.window(F.col("event_ts"))).alias("headway_observado_min"), 
                                    F.lit(8).alias("headway_referencia_min"), 
                                    (F.col("event_ts") - F.lag("event_ts", 1).over(F.window(F.col("event_ts")))).alias("atraso_aproximado_min"))

    return final_table

def validate_final_table(df_final: DataFrame) -> None:
    # Check for required columns
    required_columns = ["event_dt", "cod_linha", "cod_veiculo", "janela_5min", "headway_observado_min", "headway_referencia_min", "atraso_aproximado_min"]
    if not all(col in df_final.columns for col in required_columns):
        raise ValueError("Final table is missing required columns")

    # Check for numeric types
    numeric_columns = ["headway_observado_min", "headway_referencia_min", "atraso_aproximado_min"]
    for col in numeric_columns:
        if not df_final.schema[col].dataType.typeName() == "DoubleType":
            raise ValueError(f"Column {col} is not of type double")

    # Check for nulls in key columns
    key_columns = ["event_dt", "cod_linha", "cod_veiculo"]
    for col in key_columns:
        if df_final.filter(df_final[col].isNull()).count() > 0:
            raise ValueError(f"Column {col} contains null values")

    # Check for valid coordinate ranges
    if "latitude" in df_final.columns and "longitude" in df_final.columns:
        if df_final.filter((df_final["latitude"] < -90) | (df_final["latitude"] > 90) | (df_final["longitude"] < -180) | (df_final["longitude"] > 180)).count() > 0:
            raise ValueError("Invalid coordinate ranges found")

# Example usage
df_dict = {
    "gps_events": spark.createDataFrame([(1, 1, "2022-01-01", 10.0, 20.0), (2, 2, "2022-01-02", 30.0, 40.0)], ["event_id", "gps_idx", "event_dt", "latitude", "longitude"]),
    "stop_events": spark.createDataFrame([(1, 1, "2022-01-01", 10.0, 20.0), (2, 2, "2022-01-02", 30.0, 40.0)], ["event_id", "gps_idx", "event_dt", "latitude", "longitude"]),
    "fare_events": spark.createDataFrame([(1, 1, "2022-01-01", 10.0, 20.0), (2, 2, "2022-01-02", 30.0, 40.0)], ["event_id", "gps_idx", "event_dt", "latitude", "longitude"]),
    "operational_events": spark.createDataFrame([(1, 1, "2022-01-01", 10.0, 20.0), (2, 2, "2022-01-02", 30.0, 40.0)], ["event_id", "gps_idx", "event_dt", "latitude", "longitude"])
}

final_table = build_final_table(df_dict)
validate_final_table(final_table)
final_table.show()
