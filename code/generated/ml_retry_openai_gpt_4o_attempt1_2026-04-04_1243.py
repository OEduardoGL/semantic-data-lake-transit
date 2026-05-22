import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

def run_ml_pipeline(df_final):
    # Check for critical columns
    required_columns = [
        "event_dt", "janela_5min", "cod_linha", "cod_veiculo", 
        "headway_observado_min", "headway_referencia_min", "atraso_aproximado_min"
    ]
    for col in required_columns:
        if col not in df_final.columns:
            raise ValueError(f"Missing required column: {col}")

    # Handle missing values
    df_final = df_final.dropna(subset=["atraso_aproximado_min"])

    # Feature engineering: extract temporal features
    df_final['janela_5min'] = pd.to_datetime(df_final['janela_5min'])
    df_final['hour'] = df_final['janela_5min'].dt.hour
    df_final['minute'] = df_final['janela_5min'].dt.minute
    df_final['day_of_week'] = df_final['janela_5min'].dt.dayofweek

    # Baseline: median delay by line and time band
    baseline = df_final.groupby(['cod_linha', 'hour'])['atraso_aproximado_min'].median().reset_index()
    baseline.columns = ['cod_linha', 'hour', 'baseline_median_delay']

    # Merge baseline with original data
    df_final = df_final.merge(baseline, on=['cod_linha', 'hour'], how='left')

    # Prepare features and target
    features = ['cod_linha', 'cod_veiculo', 'hour', 'minute', 'day_of_week']
    X = df_final[features]
    y = df_final['atraso_aproximado_min']

    # Split data: temporal split
    df_final = df_final.sort_values(by='janela_5min')
    train_size = int(0.7 * len(df_final))
    val_size = int(0.15 * len(df_final))
    
    X_train, X_val, X_test = X.iloc[:train_size], X.iloc[train_size:train_size+val_size], X.iloc[train_size+val_size:]
    y_train, y_val, y_test = y.iloc[:train_size], y.iloc[train_size:train_size+val_size], y.iloc[train_size+val_size:]

    # Train a simple linear regression model
    model = LinearRegression()
    model.fit(X_train, y_train)

    # Predictions
    y_pred_train = model.predict(X_train)
    y_pred_val = model.predict(X_val)
    y_pred_test = model.predict(X_test)

    # Calculate metrics
    metrics = {
        "mae": mean_absolute_error(y_test, y_pred_test),
        "rmse": mean_squared_error(y_test, y_pred_test, squared=False),
        "mape": np.mean(np.abs((y_test - y_pred_test) / y_test)) * 100
    }

    # Baseline metrics
    y_baseline = df_final['baseline_median_delay'].iloc[train_size+val_size:]
    baseline_metrics = {
        "mae": mean_absolute_error(y_test, y_baseline),
        "rmse": mean_squared_error(y_test, y_baseline, squared=False),
        "mape": np.mean(np.abs((y_test - y_baseline) / y_test)) * 100
    }

    # Predictions DataFrame
    test_indices = df_final.index[train_size+val_size:]
    predictions_df = pd.DataFrame({
        "event_dt": df_final.loc[test_indices, 'event_dt'],
        "janela_5min": df_final.loc[test_indices, 'janela_5min'],
        "cod_linha": df_final.loc[test_indices, 'cod_linha'],
        "cod_veiculo": df_final.loc[test_indices, 'cod_veiculo'],
        "y_true": y_test,
        "y_pred": y_pred_test
    })

    # Aggregated metrics by line and hour
    line_hour_metrics_df = predictions_df.copy()
    line_hour_metrics_df['hour'] = line_hour_metrics_df['janela_5min'].dt.hour
    line_hour_metrics_df = line_hour_metrics_df.groupby(['cod_linha', 'hour']).agg(
        avg_pred_atraso_aproximado_min=('y_pred', 'mean'),
        avg_real_atraso_aproximado_min=('y_true', 'mean'),
        n_registros=('y_true', 'size')
    ).reset_index()

    # Aggregated metrics by vehicle and day
    vehicle_day_metrics_df = predictions_df.copy()
    vehicle_day_metrics_df = vehicle_day_metrics_df.groupby(['event_dt', 'cod_veiculo']).agg(
        avg_pred_atraso_aproximado_min=('y_pred', 'mean'),
        avg_real_atraso_aproximado_min=('y_true', 'mean'),
        n_registros=('y_true', 'size')
    ).reset_index()

    return {
        "metrics": metrics,
        "baseline_metrics": baseline_metrics,
        "predictions_df": predictions_df,
        "line_hour_metrics_df": line_hour_metrics_df,
        "vehicle_day_metrics_df": vehicle_day_metrics_df
    }
