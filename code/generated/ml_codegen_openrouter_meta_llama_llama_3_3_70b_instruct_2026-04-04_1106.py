import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from sklearn.preprocessing import LabelEncoder

def run_ml_pipeline(df_final):
    # Tratar nulos remanescentes
    df_final.fillna(df_final.mean(), inplace=True)

    # Gerar features temporais
    df_final['hora'] = df_final['janela_5min'].dt.hour
    df_final['minuto'] = df_final['janela_5min'].dt.minute
    df_final['dia_da_semana'] = df_final['event_dt'].dt.dayofweek

    # Tratar colunas categoricas
    le = LabelEncoder()
    df_final['viagem_sentido'] = le.fit_transform(df_final['viagem_sentido'])

    # Definir features e target
    X = df_final.drop(['atraso_aproximado_min', 'event_dt', 'janela_5min'], axis=1)
    y = df_final['atraso_aproximado_min']

    # Split temporal
    X_train, X_val_test, y_train, y_val_test = train_test_split(X, y, test_size=0.3, shuffle=False)
    X_val, X_test, y_val, y_test = train_test_split(X_val_test, y_val_test, test_size=0.5, shuffle=False)

    # Treinar modelo baseline
    baseline = df_final.groupby('cod_linha')['atraso_aproximado_min'].median()
    y_pred_baseline = baseline[X_test['cod_linha']].values

    # Treinar modelo principal
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    # Avaliar modelos
    metrics = {
        'mae': mean_absolute_error(y_test, y_pred),
        'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
        'mape': mean_absolute_percentage_error(y_test, y_pred)
    }
    baseline_metrics = {
        'mae': mean_absolute_error(y_test, y_pred_baseline),
        'rmse': np.sqrt(mean_squared_error(y_test, y_pred_baseline)),
        'mape': mean_absolute_percentage_error(y_test, y_pred_baseline)
    }

    # Gerar saidas gerenciais
    predictions_df = pd.DataFrame({
        'event_dt': df_final['event_dt'],
        'janela_5min': df_final['janela_5min'],
        'cod_linha': df_final['cod_linha'],
        'cod_veiculo': df_final['cod_veiculo'],
        'y_true': y_test,
        'y_pred': y_pred
    })
    line_hour_metrics_df = df_final.groupby(['cod_linha', 'hora'])['atraso_aproximado_min'].mean().reset_index()
    line_hour_metrics_df.columns = ['cod_linha', 'faixa_horaria', 'avg_atraso_aproximado_min']
    vehicle_day_metrics_df = df_final.groupby(['event_dt', 'cod_veiculo'])['atraso_aproximado_min'].mean().reset_index()
    vehicle_day_metrics_df.columns = ['event_dt', 'cod_veiculo', 'avg_atraso_aproximado_min']

    return {
        'metrics': metrics,
        'baseline_metrics': baseline_metrics,
        'predictions_df': predictions_df,
        'line_hour_metrics_df': line_hour_metrics_df,
        'vehicle_day_metrics_df': vehicle_day_metrics_df
    }
