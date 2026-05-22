#!/usr/bin/env python3
"""Etapa 11 (Blocos D/E): executa pipeline de ML gerado por LLM sobre a Gold."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd


def ensure_distutils_shim() -> None:
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


def ensure_sklearn_metrics_compat() -> None:
    """Compatibiliza mudancas de assinatura de metricas entre versoes do sklearn."""
    import inspect
    import math
    import sklearn.metrics as sk_metrics

    sig = inspect.signature(sk_metrics.mean_squared_error)
    if "squared" in sig.parameters:
        return

    original = sk_metrics.mean_squared_error

    def mean_squared_error_compat(
        y_true,
        y_pred,
        *,
        sample_weight=None,
        multioutput="uniform_average",
        squared=True,
    ):
        value = original(
            y_true,
            y_pred,
            sample_weight=sample_weight,
            multioutput=multioutput,
        )
        if squared:
            return value
        return math.sqrt(value)

    sk_metrics.mean_squared_error = mean_squared_error_compat


def load_materializer_helpers(base_dir: Path):
    module_path = base_dir / "06_materialize_final_table.py"
    spec = spec_from_file_location("materialize_helpers", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Nao foi possivel carregar helpers de {module_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_generated_module(module_path: Path):
    spec = spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Nao foi possivel carregar modulo gerado: {module_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Executa pipeline de ML gerado por LLM")
    parser.add_argument("--config", default=str(base / "config.yaml"))
    parser.add_argument("--model-file", required=True, help="Arquivo .py gerado pela LLM")
    parser.add_argument("--model-label", required=True, help="Rotulo curto para artefatos")
    parser.add_argument("--input-path", default=None, help="Sobrescreve o caminho da Gold/final_table")
    return parser.parse_args()


def validate_output(result: dict[str, Any]) -> None:
    required_keys = [
        "metrics",
        "baseline_metrics",
        "predictions_df",
        "line_hour_metrics_df",
        "vehicle_day_metrics_df",
    ]
    missing = [key for key in required_keys if key not in result]
    if missing:
        raise ValueError(f"Saida do pipeline sem chaves obrigatorias: {missing}")

    for key in ["predictions_df", "line_hour_metrics_df", "vehicle_day_metrics_df"]:
        if not isinstance(result[key], pd.DataFrame):
            raise TypeError(f"{key} deve ser DataFrame pandas")


def main() -> None:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    artifacts_dir = (base_dir.parent / "artifacts").resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")

    ensure_distutils_shim()
    ensure_sklearn_metrics_compat()
    helpers = load_materializer_helpers(base_dir)
    helpers.load_local_env(base_dir)
    cfg = helpers.load_config(Path(args.config).resolve())
    helpers.resolve_s3_credentials(cfg)
    input_path = args.input_path or f"{cfg['paths']['gold_base'].rstrip('/')}/final_table"

    spark = helpers.build_spark(cfg, app_suffix=f"ml-{args.model_label}")
    try:
        df = spark.read.parquet(input_path)
        pdf = df.toPandas()
    finally:
        spark.stop()

    pdf["event_dt"] = pd.to_datetime(pdf["event_dt"])
    pdf["janela_5min"] = pd.to_datetime(pdf["janela_5min"])
    pdf = pdf.sort_values(["janela_5min", "event_dt", "cod_linha", "cod_veiculo"]).reset_index(drop=True)

    model_path = Path(args.model_file).resolve()
    generated_module = load_generated_module(model_path)
    if not hasattr(generated_module, "run_ml_pipeline"):
        raise AttributeError(f"Modulo sem run_ml_pipeline: {model_path}")

    start = perf_counter()
    result = generated_module.run_ml_pipeline(pdf.copy())
    elapsed_sec = perf_counter() - start
    validate_output(result)

    metrics = dict(result["metrics"])
    baseline_metrics = dict(result["baseline_metrics"])
    metrics_row = {
        "model_name": args.model_label,
        "source_file": str(model_path),
        "input_path": input_path,
        "elapsed_sec": round(elapsed_sec, 6),
        "mae": metrics.get("mae"),
        "rmse": metrics.get("rmse"),
        "wape": metrics.get("wape"),
        "medae": metrics.get("medae"),
        "mape_secondary": metrics.get("mape") if metrics.get("mape") is not None else metrics.get("mape_secondary"),
        "baseline_mae": baseline_metrics.get("mae"),
        "baseline_rmse": baseline_metrics.get("rmse"),
        "baseline_wape": baseline_metrics.get("wape"),
        "baseline_medae": baseline_metrics.get("medae"),
        "baseline_mape_secondary": baseline_metrics.get("mape") if baseline_metrics.get("mape") is not None else baseline_metrics.get("mape_secondary"),
        "row_count_predictions": len(result["predictions_df"]),
    }
    metrics_df = pd.DataFrame([metrics_row])

    metrics_path = artifacts_dir / f"metrics_ml_{args.model_label}_{ts}.csv"
    preds_path = artifacts_dir / f"predictions_{args.model_label}_{ts}.csv"
    line_path = artifacts_dir / f"neo4j_metrics_line_hour_{args.model_label}_{ts}.csv"
    vehicle_path = artifacts_dir / f"neo4j_metrics_vehicle_day_{args.model_label}_{ts}.csv"
    report_path = artifacts_dir / f"ml_run_report_{args.model_label}_{ts}.md"

    metrics_df.to_csv(metrics_path, index=False)
    result["predictions_df"].to_csv(preds_path, index=False)
    result["line_hour_metrics_df"].to_csv(line_path, index=False)
    result["vehicle_day_metrics_df"].to_csv(vehicle_path, index=False)

    report_path.write_text(
        "\n".join(
            [
                "# ML Run Report",
                f"- timestamp: `{datetime.now().isoformat()}`",
                f"- model_label: `{args.model_label}`",
                f"- source_file: `{model_path}`",
                f"- input_path: `{input_path}`",
                f"- elapsed_sec: `{elapsed_sec:.6f}`",
                f"- mae: `{metrics.get('mae')}`",
                f"- rmse: `{metrics.get('rmse')}`",
                f"- wape: `{metrics.get('wape')}`",
                f"- medae: `{metrics.get('medae')}`",
                f"- mape_secondary: `{metrics.get('mape') if metrics.get('mape') is not None else metrics.get('mape_secondary')}`",
                f"- baseline_mae: `{baseline_metrics.get('mae')}`",
                f"- baseline_rmse: `{baseline_metrics.get('rmse')}`",
                f"- baseline_wape: `{baseline_metrics.get('wape')}`",
                f"- baseline_medae: `{baseline_metrics.get('medae')}`",
                f"- baseline_mape_secondary: `{baseline_metrics.get('mape') if baseline_metrics.get('mape') is not None else baseline_metrics.get('mape_secondary')}`",
                f"- metrics_csv: `{metrics_path}`",
                f"- predictions_csv: `{preds_path}`",
                f"- neo4j_line_hour_csv: `{line_path}`",
                f"- neo4j_vehicle_day_csv: `{vehicle_path}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print("=== ML Pipeline Executado ===")
    print(f"model_label: {args.model_label}")
    print(f"metrics_csv: {metrics_path}")
    print(f"predictions_csv: {preds_path}")
    print(f"neo4j_line_hour_csv: {line_path}")
    print(f"neo4j_vehicle_day_csv: {vehicle_path}")
    print(f"report_md: {report_path}")
    print(f"elapsed_sec: {elapsed_sec:.6f}")
    print(f"mae: {metrics.get('mae')}")
    print(f"rmse: {metrics.get('rmse')}")
    print(f"wape: {metrics.get('wape')}")
    print(f"medae: {metrics.get('medae')}")


if __name__ == "__main__":
    main()
