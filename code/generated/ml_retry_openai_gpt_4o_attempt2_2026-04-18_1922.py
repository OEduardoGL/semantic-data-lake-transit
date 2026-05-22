import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, median_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.base import BaseEstimator, TransformerMixin

# Custom transformer to extract temporal features
class TemporalFeatureExtractor(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = X.copy()
        X['hour'] = X['janela_5min'].dt.hour
        X['day_of_week'] = X['event_dt'].dt.dayofweek
        X['is_weekend'] = X['day_of_week'] >= 5
        return X

# Custom transformer to create lag features
class LagFeatureCreator(BaseEstimator, TransformerMixin):
    def __init__(self, lag_columns, lag=1):
        self.lag_columns = lag_columns
        self.lag = lag

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = X.copy()
        for col in self.lag_columns:
            X[f'lag_{self.lag}_{col}'] = X.groupby(['cod_linha', 'cod_veiculo'])[col].shift(self.lag)
        return X

def run_ml_pipeline(df_final):
    # Check for critical columns
    required_columns = [
        'event_dt', 'janela_5min', 'cod_linha', 'cod_veiculo',
        'velocidade_media', 'gps_invalid_pct', 'qtd_eventos_gps',
        'qtd_eventos_stop', 'max_satelites', 'headway_referencia_min',
        'atraso_aproximado_min'
    ]
    for col in required_columns:
        if col not in df_final.columns:
            raise ValueError(f"Missing required column: {col}")

    # Sort by time and create future target (t+1)
    df_final = df_final.sort_values(by=['cod_linha', 'cod_veiculo', 'janela_5min'])
    df_final['y_true'] = df_final.groupby(['cod_linha', 'cod_veiculo'])['atraso_aproximado_min'].shift(-1)
    df_final = df_final.dropna(subset=['y_true'])

    # Feature engineering
    temporal_features = TemporalFeatureExtractor().fit_transform(df_final)
    df_final = pd.concat([df_final, temporal_features], axis=1)
    
    # Create lag features
    lag_feature_creator = LagFeatureCreator(lag_columns=[
        'velocidade_media', 'gps_invalid_pct', 'qtd_eventos_gps', 
        'qtd_eventos_stop', 'headway_referencia_min'
    ])
    df_final = lag_feature_creator.fit_transform(df_final)
    df_final.dropna(inplace=True)

    # Split data
    train_size = int(len(df_final) * 0.7)
    val_size = int(len(df_final) * 0.15)
    train_df = df_final.iloc[:train_size]
    val_df = df_final.iloc[train_size:train_size + val_size]
    test_df = df_final.iloc[train_size + val_size:]

    # Prepare features and target
    feature_cols = [
        'velocidade_media', 'gps_invalid_pct', 'qtd_eventos_gps',
        'qtd_eventos_stop', 'max_satelites', 'headway_referencia_min',
        'hour', 'day_of_week', 'is_weekend',
        'lag_1_velocidade_media', 'lag_1_gps_invalid_pct',
        'lag_1_qtd_eventos_gps', 'lag_1_qtd_eventos_stop',
        'lag_1_headway_referencia_min'
    ]
    X_train, y_train = train_df[feature_cols], train_df['y_true']
    X_val, y_val = val_df[feature_cols], val_df['y_true']
    X_test, y_test = test_df[feature_cols], test_df['y_true']

    # Baseline model: median by line and time band
    train_df['time_band'] = train_df['hour']
    baseline_median = train_df.groupby(['cod_linha', 'time_band'])['y_true'].median().reset_index()
    test_df['time_band'] = test_df['hour']
    test_df = test_df.merge(baseline_median, on=['cod_linha', 'time_band'], how='left', suffixes=('', '_baseline'))
    test_df['y_pred_baseline'] = test_df['y_true_baseline'].fillna(train_df['y_true'].median())

    # Calculate baseline metrics
    baseline_mae = mean_absolute_error(y_test, test_df['y_pred_baseline'])
    baseline_rmse = mean_squared_error(y_test, test_df['y_pred_baseline'], squared=False)
    baseline_wape = baseline_mae / y_test.mean()

    # Model pipeline
    model_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
        ('model', HistGradientBoostingRegressor(random_state=42))
    ])

    # Train model
    model_pipeline.fit(X_train, y_train)

    # Evaluate model
    y_pred = model_pipeline.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = mean_squared_error(y_test, y_pred, squared=False)
    wape = mae / y_test.mean()
    medae = median_absolute_error(y_test, y_pred)

    # Prepare predictions DataFrame
    predictions_df = test_df[['event_dt', 'janela_5min', 'cod_linha', 'cod_veiculo']].copy()
    predictions_df['y_true'] = y_test
    predictions_df['y_pred'] = y_pred

    # Aggregate metrics by line and time band
    line_hour_metrics_df = predictions_df.copy()
    line_hour_metrics_df['faixa_horaria'] = line_hour_metrics_df['janela_5min'].dt.hour
    line_hour_metrics_df = line_hour_metrics_df.groupby(['cod_linha', 'faixa_horaria']).agg(
        avg_pred_atraso_aproximado_min=('y_pred', 'mean'),
        avg_real_atraso_aproximado_min=('y_true', 'mean'),
        n_registros=('y_true', 'size')
    ).reset_index()

    # Aggregate metrics by vehicle and day
    vehicle_day_metrics_df = predictions_df.copy()
    vehicle_day_metrics_df = vehicle_day_metrics_df.groupby(['event_dt', 'cod_veiculo']).agg(
        avg_pred_atraso_aproximado_min=('y_pred', 'mean'),
        avg_real_atraso_aproximado_min=('y_true', 'mean'),
        n_registros=('y_true', 'size')
    ).reset_index()

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
