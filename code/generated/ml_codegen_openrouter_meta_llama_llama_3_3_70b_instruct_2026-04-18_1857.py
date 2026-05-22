import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, median_absolute_error
from sklearn.preprocessing import StandardScaler

def run_ml_pipeline(df_final):
    # Verificar se as colunas obrigatorias estao presentes
    required_columns = [
        "cod_linha", "cod_veiculo", "id_empresa", "viagem_sentido",
        "janela_5min", "latitude_media", "longitude_media", "velocidade_media",
        "gps_invalid_pct", "qtd_eventos_gps", "qtd_eventos_stop", "max_satelites",
        "headway_observado_min", "headway_referencia_min", "atraso_aproximado_min", "event_dt"
    ]
    if not all(column in df_final.columns for column in required_columns):
        raise ValueError("Colunas obrigatorias ausentes")

    # Ordenar por tempo e criar target deslocado para frente
    df_final = df_final.sort_values(by="janela_5min")
    df_final["y_true"] = df_final.groupby(["cod_linha", "cod_veiculo"])["atraso_aproximado_min"].shift(-1)

    # Descartar linhas sem proxima observacao disponivel
    df_final = df_final.dropna(subset=["y_true"])

    # Criar features temporais e historicas simples
    df_final["hour"] = df_final["janela_5min"].dt.hour
    df_final["day_of_week"] = df_final["event_dt"].dt.dayofweek
    df_final["is_weekend"] = df_final["day_of_week"].isin([5, 6])

    # Split temporal explicito
    train_df, val_test_df = train_test_split(df_final, test_size=0.3, shuffle=False, random_state=42)
    val_df, test_df = train_test_split(val_test_df, test_size=0.5, shuffle=False, random_state=42)

    # Preprocessamento
    scaler = StandardScaler()
    X_train = train_df[[
        "velocidade_media", "gps_invalid_pct", "qtd_eventos_gps", "qtd_eventos_stop", "max_satelites",
        "hour", "day_of_week"
    ]]
    y_train = train_df["y_true"]
    X_val = val_df[[
        "velocidade_media", "gps_invalid_pct", "qtd_eventos_gps", "qtd_eventos_stop", "max_satelites",
        "hour", "day_of_week"
    ]]
    y_val = val_df["y_true"]
    X_test = test_df[[
        "velocidade_media", "gps_invalid_pct", "qtd_eventos_gps", "qtd_eventos_stop", "max_satelites",
        "hour", "day_of_week"
    ]]
    y_test = test_df["y_true"]

    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    # Treinar baseline e modelo principal
    baseline_model = np.median(y_train)
    baseline_pred = np.full_like(y_test, baseline_model)

    model = HistGradientBoostingRegressor(random_state=42)
    model.fit(X_train_scaled, y_train)
    y_pred = model.predict(X_test_scaled)

    # Calcular metricas
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    wape = np.sum(np.abs(y_test - y_pred)) / np.sum(y_test)
    medae = median_absolute_error(y_test, y_pred)

    baseline_mae = mean_absolute_error(y_test, baseline_pred)
    baseline_rmse = np.sqrt(mean_squared_error(y_test, baseline_pred))
    baseline_wape = np.sum(np.abs(y_test - baseline_pred)) / np.sum(y_test)

    # Gerar saidas gerenciais
    predictions_df = pd.DataFrame({
        "event_dt": test_df["event_dt"],
        "janela_5min": test_df["janela_5min"],
        "cod_linha": test_df["cod_linha"],
        "cod_veiculo": test_df["cod_veiculo"],
        "y_true": y_test,
        "y_pred": y_pred
    })

    line_hour_metrics_df = predictions_df.groupby(["cod_linha", "hour"])["y_pred", "y_true"].mean().reset_index()
    line_hour_metrics_df = line_hour_metrics_df.rename(columns={"y_pred": "avg_pred_atraso_aproximado_min", "y_true": "avg_real_atraso_aproximado_min"})

    vehicle_day_metrics_df = predictions_df.groupby(["event_dt", "cod_veiculo"])["y_pred", "y_true"].mean().reset_index()
    vehicle_day_metrics_df = vehicle_day_metrics_df.rename(columns={"y_pred": "avg_pred_atraso_aproximado_min", "y_true": "avg_real_atraso_aproximado_min"})

    return {
        "metrics": {
            "mae": mae,
            "rmse": rmse,
            "wape": wape,
            "medae": medae
        },
        "baseline_metrics": {
            "mae": baseline_mae,
            "rmse": baseline_rmse,
            "wape": baseline_wape
        },
        "predictions_df": predictions_df,
        "line_hour_metrics_df": line_hour_metrics_df,
        "vehicle_day_metrics_df": vehicle_day_metrics_df
    }
