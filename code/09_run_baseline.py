#!/usr/bin/env python3
"""Etapa 11: executa baseline oficial de ML.

Versao atual:
- baseline temporal para a rodada 2 (`t+1`)
- mediana historica de `y_true` futuro por `cod_linha` + `faixa_horaria`
- split temporal 70/15/15
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, median_absolute_error

from importlib.util import module_from_spec, spec_from_file_location


def ensure_distutils_shim() -> None:
    """Compatibiliza PySpark com Python 3.12 para chamadas `toPandas()`."""
    try:
        import distutils.version  # type: ignore  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    import types

    class LooseVersion:
        def __init__(self, version: str) -> None:
            self.version = version
            self._parts = self._normalize(version)

        @staticmethod
        def _normalize(version: str) -> tuple:
            parts = re.split(r"[.\-+_]", str(version))
            normalized = []
            for part in parts:
                if part == "":
                    continue
                normalized.append(int(part) if part.isdigit() else part.lower())
            return tuple(normalized)

        def _cmp_key(self) -> tuple:
            return self._parts

        def __lt__(self, other: object) -> bool:
            return self._cmp_key() < LooseVersion(str(other))._cmp_key()

        def __le__(self, other: object) -> bool:
            return self._cmp_key() <= LooseVersion(str(other))._cmp_key()

        def __eq__(self, other: object) -> bool:
            return self._cmp_key() == LooseVersion(str(other))._cmp_key()

        def __gt__(self, other: object) -> bool:
            return self._cmp_key() > LooseVersion(str(other))._cmp_key()

        def __ge__(self, other: object) -> bool:
            return self._cmp_key() >= LooseVersion(str(other))._cmp_key()

        def __str__(self) -> str:
            return self.version

    distutils_module = types.ModuleType("distutils")
    version_module = types.ModuleType("distutils.version")
    version_module.LooseVersion = LooseVersion
    distutils_module.version = version_module
    sys.modules["distutils"] = distutils_module
    sys.modules["distutils.version"] = version_module


def load_materializer_helpers():
    module_path = Path(__file__).resolve().parent / "06_materialize_final_table.py"
    spec = spec_from_file_location("materialize_helpers", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Nao foi possivel carregar helpers de {module_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Executa baseline oficial sobre a final_table")
    parser.add_argument("--config", default=str(base / "config.yaml"))
    parser.add_argument("--input-path", default=None, help="Sobrescreve o caminho da Gold/final_table")
    return parser.parse_args()


def safe_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = np.where(np.abs(y_true) < 1e-9, 1.0, np.abs(y_true))
    return float(np.mean(np.abs((y_true - y_pred) / denom)) * 100.0)


def weighted_absolute_percentage_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = float(np.sum(np.abs(y_true)))
    if denom < 1e-9:
        return 0.0
    return float(np.sum(np.abs(y_true - y_pred)) / denom)


def main() -> None:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    helpers = load_materializer_helpers()
    ensure_distutils_shim()

    helpers.load_local_env(base_dir)
    cfg = helpers.load_config(Path(args.config).resolve())
    helpers.resolve_s3_credentials(cfg)
    spark = helpers.build_spark(cfg, app_suffix="baseline")

    artifacts_dir = (base_dir.parent / "artifacts").resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")

    input_path = args.input_path or f"{cfg['paths']['gold_base'].rstrip('/')}/final_table"

    try:
        df = spark.read.parquet(input_path).select(
            "event_dt",
            "janela_5min",
            "cod_linha",
            "cod_veiculo",
            "atraso_aproximado_min",
        )
        pdf = df.toPandas()
    finally:
        spark.stop()

    pdf["event_dt"] = pd.to_datetime(pdf["event_dt"])
    pdf["janela_5min"] = pd.to_datetime(pdf["janela_5min"])
    pdf = pdf.dropna(subset=["atraso_aproximado_min", "janela_5min", "cod_linha", "cod_veiculo"]).copy()
    pdf["faixa_horaria"] = pdf["janela_5min"].dt.hour
    pdf = pdf.sort_values(["cod_linha", "cod_veiculo", "janela_5min", "event_dt"]).reset_index(drop=True)
    pdf["y_true"] = (
        pdf.groupby(["cod_linha", "cod_veiculo"])["atraso_aproximado_min"].shift(-1)
    )
    pdf = pdf.dropna(subset=["y_true"]).copy()
    pdf = pdf.sort_values(["janela_5min", "event_dt", "cod_linha", "cod_veiculo"]).reset_index(drop=True)

    n = len(pdf)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)

    train_df = pdf.iloc[:train_end].copy()
    val_df = pdf.iloc[train_end:val_end].copy()
    test_df = pdf.iloc[val_end:].copy()

    line_hour_baseline = (
        train_df.groupby(["cod_linha", "faixa_horaria"], as_index=False)["y_true"]
        .median()
        .rename(columns={"y_true": "baseline_pred"})
    )
    line_baseline = (
        train_df.groupby("cod_linha", as_index=False)["y_true"]
        .median()
        .rename(columns={"y_true": "line_baseline_pred"})
    )
    global_baseline = float(train_df["y_true"].median())

    test_pred = test_df.merge(line_hour_baseline, on=["cod_linha", "faixa_horaria"], how="left")
    test_pred = test_pred.merge(line_baseline, on=["cod_linha"], how="left")
    test_pred["y_pred"] = (
        test_pred["baseline_pred"]
        .fillna(test_pred["line_baseline_pred"])
        .fillna(global_baseline)
    )

    y_true = test_pred["y_true"].to_numpy(dtype=float)
    y_pred = test_pred["y_pred"].to_numpy(dtype=float)

    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(mean_squared_error(y_true, y_pred) ** 0.5)
    wape = weighted_absolute_percentage_error(y_true, y_pred)
    medae = float(median_absolute_error(y_true, y_pred))
    mape_secondary = safe_mape(y_true, y_pred)

    metrics_df = pd.DataFrame(
        [
            {
                "model_name": "baseline_median_future_by_line_timeband",
                "split_strategy": "temporal_70_15_15",
                "prediction_horizon": "next_window_same_line_vehicle",
                "row_count_total": n,
                "row_count_train": len(train_df),
                "row_count_val": len(val_df),
                "row_count_test": len(test_df),
                "mae": mae,
                "rmse": rmse,
                "wape": wape,
                "medae": medae,
                "mape_secondary": mape_secondary,
                "global_baseline": global_baseline,
            }
        ]
    )

    predictions_df = test_pred[
        ["event_dt", "janela_5min", "cod_linha", "cod_veiculo", "faixa_horaria", "y_true", "y_pred"]
    ].copy()

    metrics_path = artifacts_dir / f"metrics_ml_baseline_{ts}.csv"
    preds_path = artifacts_dir / f"predictions_baseline_{ts}.csv"
    report_path = artifacts_dir / f"baseline_report_{ts}.md"

    metrics_df.to_csv(metrics_path, index=False)
    predictions_df.to_csv(preds_path, index=False)
    report_path.write_text(
        "\n".join(
            [
                "# Baseline Report",
                f"- timestamp: {datetime.now().isoformat()}",
                f"- input_path: `{input_path}`",
                f"- row_count_total: `{n}`",
                f"- row_count_train: `{len(train_df)}`",
                f"- row_count_val: `{len(val_df)}`",
                f"- row_count_test: `{len(test_df)}`",
                "- prediction_horizon: `next_window_same_line_vehicle`",
                f"- mae: `{mae:.6f}`",
                f"- rmse: `{rmse:.6f}`",
                f"- wape: `{wape:.6f}`",
                f"- medae: `{medae:.6f}`",
                f"- mape_secondary: `{mape_secondary:.6f}`",
                f"- metrics_csv: `{metrics_path}`",
                f"- predictions_csv: `{preds_path}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print("=== Baseline Executado ===")
    print(f"input_path: {input_path}")
    print(f"metrics_csv: {metrics_path}")
    print(f"predictions_csv: {preds_path}")
    print(f"report_md: {report_path}")
    print(f"mae: {mae:.6f}")
    print(f"rmse: {rmse:.6f}")
    print(f"wape: {wape:.6f}")
    print(f"medae: {medae:.6f}")
    print(f"mape_secondary: {mape_secondary:.6f}")


if __name__ == "__main__":
    main()
