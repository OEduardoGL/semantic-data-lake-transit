#!/usr/bin/env python3
"""Etapa 12/12.1: gera agregados gerenciais para decisao e Neo4j."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    base = Path(__file__).resolve().parent.parent / "artifacts"
    parser = argparse.ArgumentParser(description="Gera agregados gerenciais a partir de previsoes e baseline")
    parser.add_argument(
        "--baseline-predictions",
        default=str(base / "predictions_baseline_2026-04-18_1904.csv"),
    )
    parser.add_argument(
        "--model-name",
        default="llama_3_3_70b_v2_retry2",
    )
    parser.add_argument(
        "--model-predictions",
        default=str(base / "predictions_llama_3_3_70b_v2_retry2_2026-04-18_1924.csv"),
    )
    parser.add_argument(
        "--model-line-hour",
        default=str(base / "neo4j_metrics_line_hour_llama_3_3_70b_v2_retry2_2026-04-18_1924.csv"),
    )
    parser.add_argument(
        "--model-vehicle-day",
        default=str(base / "neo4j_metrics_vehicle_day_llama_3_3_70b_v2_retry2_2026-04-18_1924.csv"),
    )
    parser.add_argument("--min-line-records", type=int, default=10)
    parser.add_argument("--min-line-hour-records", type=int, default=5)
    parser.add_argument("--min-segment-records", type=int, default=5)
    parser.add_argument("--min-vehicle-records", type=int, default=10)
    return parser.parse_args()


def ensure_hour_column(df: pd.DataFrame) -> pd.DataFrame:
    if "faixa_horaria" in df.columns:
        return df.rename(columns={"faixa_horaria": "hour"})
    if "hour" in df.columns:
        return df
    if "janela_5min" in df.columns:
        out = df.copy()
        out["janela_5min"] = pd.to_datetime(out["janela_5min"])
        out["hour"] = out["janela_5min"].dt.hour
        return out
    raise ValueError("Nao foi possivel inferir coluna de faixa horaria")


def clean_predictions(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    required_cols = ["cod_linha", "cod_veiculo", "y_true", "y_pred"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Predictions sem colunas obrigatorias: {missing}")

    out = df.copy()
    out = ensure_hour_column(out)
    invalid_mask = (
        out["cod_linha"].isna()
        | out["cod_veiculo"].isna()
        | out["y_true"].isna()
        | out["y_pred"].isna()
    )
    invalid_count = int(invalid_mask.sum())
    if invalid_count:
        out = out.loc[~invalid_mask].copy()
    return out, invalid_count


def first_value(df: pd.DataFrame, column: str) -> str:
    if df.empty or column not in df.columns:
        return "n/a"
    value = df.iloc[0][column]
    return str(value)


def main() -> None:
    args = parse_args()
    artifacts_dir = (Path(__file__).resolve().parent.parent / "artifacts").resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")

    baseline_pred = pd.read_csv(args.baseline_predictions)
    model_pred = pd.read_csv(args.model_predictions)
    model_line_hour = pd.read_csv(args.model_line_hour)
    model_vehicle_day = pd.read_csv(args.model_vehicle_day)

    baseline_pred, baseline_invalid = clean_predictions(baseline_pred)
    model_pred, model_invalid = clean_predictions(model_pred)
    model_line_hour = ensure_hour_column(model_line_hour)

    # 1) Agregado principal de atraso previsto por linha/horario
    pred_line_hour = (
        model_pred.groupby(["cod_linha", "hour"], as_index=False)
        .agg(
            pred_atraso_aproximado_min=("y_pred", "mean"),
            real_atraso_aproximado_min=("y_true", "mean"),
            n_registros=("y_true", "size"),
        )
        .query("n_registros >= @args.min_line_hour_records")
        .sort_values(["pred_atraso_aproximado_min", "n_registros"], ascending=[False, False])
        .reset_index(drop=True)
    )
    pred_line_hour.insert(0, "prediction_source", args.model_name)

    # 2) Ranking de linhas criticas
    line_ranking = (
        model_pred.groupby("cod_linha", as_index=False)
        .agg(
            pred_atraso_aproximado_min=("y_pred", "mean"),
            real_atraso_aproximado_min=("y_true", "mean"),
            n_registros=("y_true", "size"),
        )
        .query("n_registros >= @args.min_line_records")
        .sort_values(["pred_atraso_aproximado_min", "n_registros"], ascending=[False, False])
        .reset_index(drop=True)
    )
    line_ranking.insert(0, "rank", range(1, len(line_ranking) + 1))
    line_ranking.insert(1, "prediction_source", args.model_name)

    # 3) Ranking de faixas horarias criticas
    hour_ranking = (
        model_pred.groupby("hour", as_index=False)
        .agg(
            pred_atraso_aproximado_min=("y_pred", "mean"),
            real_atraso_aproximado_min=("y_true", "mean"),
            n_registros=("y_true", "size"),
        )
        .query("n_registros >= @args.min_line_hour_records")
        .sort_values(["pred_atraso_aproximado_min", "n_registros"], ascending=[False, False])
        .reset_index(drop=True)
    )
    hour_ranking.insert(0, "rank", range(1, len(hour_ranking) + 1))
    hour_ranking.insert(1, "prediction_source", args.model_name)

    # 4) Erros por segmento linha/horario/veiculo
    segment_errors = model_pred.copy()
    segment_errors["abs_error"] = (segment_errors["y_true"] - segment_errors["y_pred"]).abs()
    segment_errors = (
        segment_errors.groupby(["cod_linha", "hour", "cod_veiculo"], as_index=False)
        .agg(
            mean_abs_error=("abs_error", "mean"),
            pred_atraso_aproximado_min=("y_pred", "mean"),
            real_atraso_aproximado_min=("y_true", "mean"),
            n_registros=("y_true", "size"),
        )
        .query("n_registros >= @args.min_segment_records")
        .sort_values(["mean_abs_error", "n_registros"], ascending=[False, False])
        .reset_index(drop=True)
    )
    segment_errors.insert(0, "prediction_source", args.model_name)

    # 5) Base comparativa com baseline por linha/horario
    baseline_line_hour = (
        baseline_pred.groupby(["cod_linha", "hour"], as_index=False)
        .agg(
            baseline_pred_atraso_aproximado_min=("y_pred", "mean"),
            baseline_real_atraso_aproximado_min=("y_true", "mean"),
            baseline_n_registros=("y_true", "size"),
        )
    )
    line_hour_compare = pred_line_hour.merge(baseline_line_hour, on=["cod_linha", "hour"], how="left")
    line_hour_compare["pred_minus_baseline"] = (
        line_hour_compare["pred_atraso_aproximado_min"] - line_hour_compare["baseline_pred_atraso_aproximado_min"]
    )

    # 6) Ranking de veiculos mais instaveis
    vehicle_instability = model_vehicle_day.copy()
    vehicle_instability["abs_gap_pred_real"] = (
        vehicle_instability["avg_pred_atraso_aproximado_min"]
        - vehicle_instability["avg_real_atraso_aproximado_min"]
    ).abs()
    vehicle_instability = (
        vehicle_instability.groupby("cod_veiculo", as_index=False)
        .agg(
            pred_atraso_aproximado_min=("avg_pred_atraso_aproximado_min", "mean"),
            real_atraso_aproximado_min=("avg_real_atraso_aproximado_min", "mean"),
            mean_abs_gap_pred_real=("abs_gap_pred_real", "mean"),
            n_registros=("n_registros", "sum"),
            n_dias=("event_dt", "nunique"),
        )
        .query("n_registros >= @args.min_vehicle_records")
        .sort_values(["mean_abs_gap_pred_real", "n_registros"], ascending=[False, False])
        .reset_index(drop=True)
    )
    vehicle_instability.insert(0, "rank", range(1, len(vehicle_instability) + 1))
    vehicle_instability.insert(1, "prediction_source", args.model_name)

    outputs = {
        f"neo4j_metrics_line_hour_final_{ts}.csv": pred_line_hour,
        f"neo4j_metrics_line_ranking_{ts}.csv": line_ranking,
        f"neo4j_metrics_hour_ranking_{ts}.csv": hour_ranking,
        f"neo4j_metrics_segment_error_{ts}.csv": segment_errors,
        f"neo4j_metrics_vehicle_instability_{ts}.csv": vehicle_instability,
        f"neo4j_metrics_line_hour_compare_{ts}.csv": line_hour_compare,
        f"neo4j_metrics_vehicle_day_{args.model_name}_ref_{ts}.csv": model_vehicle_day,
        f"neo4j_metrics_line_hour_{args.model_name}_ref_{ts}.csv": model_line_hour,
    }

    for name, df in outputs.items():
        df.to_csv(artifacts_dir / name, index=False)

    report_path = artifacts_dir / f"decision_aggregates_report_{ts}.md"
    report_lines = [
        "# Decision Aggregates Report",
        f"- timestamp: `{datetime.now().isoformat()}`",
        f"- baseline_predictions: `{Path(args.baseline_predictions).name}`",
        f"- model_name: `{args.model_name}`",
        f"- model_predictions: `{Path(args.model_predictions).name}`",
        f"- model_line_hour: `{Path(args.model_line_hour).name}`",
        f"- model_vehicle_day: `{Path(args.model_vehicle_day).name}`",
        f"- min_line_records: `{args.min_line_records}`",
        f"- min_line_hour_records: `{args.min_line_hour_records}`",
        f"- min_segment_records: `{args.min_segment_records}`",
        f"- min_vehicle_records: `{args.min_vehicle_records}`",
        f"- baseline_invalid_rows_dropped: `{baseline_invalid}`",
        f"- model_invalid_rows_dropped: `{model_invalid}`",
        f"- top_line: `{first_value(line_ranking, 'cod_linha')}`",
        f"- top_line_pred_delay: `{first_value(line_ranking, 'pred_atraso_aproximado_min')}`",
        f"- top_hour: `{first_value(hour_ranking, 'hour')}`",
        f"- top_hour_pred_delay: `{first_value(hour_ranking, 'pred_atraso_aproximado_min')}`",
        f"- top_segment_line: `{first_value(segment_errors, 'cod_linha')}`",
        f"- top_segment_vehicle: `{first_value(segment_errors, 'cod_veiculo')}`",
        f"- top_segment_abs_error: `{first_value(segment_errors, 'mean_abs_error')}`",
        f"- top_vehicle_instability: `{first_value(vehicle_instability, 'cod_veiculo')}`",
        f"- top_vehicle_abs_gap: `{first_value(vehicle_instability, 'mean_abs_gap_pred_real')}`",
        "",
        "## Outputs",
    ]
    for name in outputs:
        report_lines.append(f"- `{artifacts_dir / name}`")
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    manifest_path = artifacts_dir / f"neo4j_package_manifest_{ts}.csv"
    manifest_rows = [
        {"dataset_name": name.replace(f"_{ts}.csv", ""), "file_name": name, "row_count": len(df)}
        for name, df in outputs.items()
    ]
    pd.DataFrame(manifest_rows).to_csv(manifest_path, index=False)

    print("=== Decision Aggregates Generated ===")
    for name in outputs:
        print(artifacts_dir / name)
    print(report_path)
    print(manifest_path)


if __name__ == "__main__":
    main()
