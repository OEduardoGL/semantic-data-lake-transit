#!/usr/bin/env python3
"""Etapa 10 (Bloco C): montagem programatica do Prompt 2 (ML).

Este script NAO chama API de LLM.
Ele consolida o prompt base de ML com contexto da Gold enriquecida,
configuracao de ML e evidencias tecnicas da `final_table`.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"YAML invalido: {path}")
    return data


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8") as f:
        return f.read()


def build_gold_context(validation_md: str, enrichment_md: str) -> str:
    return "\n".join(
        [
            "## Contexto adicional (gerado automaticamente): validacao da Gold enriquecida",
            validation_md.strip(),
            "\n---\n",
            "## Contexto adicional (gerado automaticamente): documentacao do enriquecimento da FinalTable",
            enrichment_md.strip(),
        ]
    )


def build_ml_config_context(cfg: dict[str, Any]) -> str:
    ml_cfg = cfg.get("ml", {})
    llm_cfg = cfg.get("llm", {})
    lines = ["## Contexto adicional (gerado automaticamente): configuracao de ML e benchmark"]

    target = ml_cfg.get("target", "n/a")
    split_strategy = ml_cfg.get("split_strategy", "n/a")
    test_ratio = ml_cfg.get("test_ratio", "n/a")
    random_seed = ml_cfg.get("random_seed", "n/a")
    baseline = ml_cfg.get("baseline", "n/a")
    metrics = ml_cfg.get("metrics", [])

    lines.append(f"- target oficial: `{target}`")
    lines.append(f"- split_strategy: `{split_strategy}`")
    lines.append(f"- test_ratio: `{test_ratio}`")
    lines.append(f"- random_seed: `{random_seed}`")
    lines.append(f"- baseline oficial: `{baseline}`")
    if isinstance(metrics, list) and metrics:
        lines.append("- metricas oficiais: " + ", ".join(f"`{m}`" for m in metrics))
    else:
        lines.append("- metricas oficiais: n/a")

    lines.append("")
    lines.append("### Modelos do benchmark")
    lines.append(f"- primary: `{llm_cfg.get('primary_provider', 'n/a')}` / `{llm_cfg.get('primary_model', 'n/a')}`")
    lines.append(f"- comparison: `{llm_cfg.get('comparison_provider', 'n/a')}` / `{llm_cfg.get('comparison_model', 'n/a')}`")
    lines.append(f"- max_retries_ml: `{llm_cfg.get('max_retries_ml', 'n/a')}`")
    return "\n".join(lines)


def render_prompt(base_prompt: str, cfg: dict[str, Any], validation_md: str, enrichment_md: str) -> str:
    sections = [
        base_prompt.strip(),
        "\n---\n",
        build_ml_config_context(cfg),
        "\n\n---\n",
        build_gold_context(validation_md, enrichment_md),
    ]
    return "\n".join(sections).strip() + "\n"


def parse_args() -> argparse.Namespace:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Monta prompt de ML (sem chamada de LLM)")
    parser.add_argument("--config", default=str(base / "config.yaml"))
    parser.add_argument("--prompt-base", default=str(base.parent / "prompts" / "prompt_2_ml_2026-04-18_v2.md"))
    parser.add_argument("--gold-validation", default=str(base.parent / "artifacts" / "final_table_validation_2026-04-03_2243.md"))
    parser.add_argument("--gold-enrichment-doc", default=str(base.parent / "docs" / "final_table_enrichment.md"))
    parser.add_argument("--output", default=None, help="caminho de saida do prompt renderizado")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    config_path = Path(args.config).resolve()
    prompt_base_path = Path(args.prompt_base).resolve()
    gold_validation_path = Path(args.gold_validation).resolve()
    gold_enrichment_path = Path(args.gold_enrichment_doc).resolve()

    for p in (config_path, prompt_base_path, gold_validation_path, gold_enrichment_path):
        if not p.exists():
            raise FileNotFoundError(f"Arquivo nao encontrado: {p}")

    cfg = load_yaml(config_path)
    prompt_base = read_text(prompt_base_path)
    validation_md = read_text(gold_validation_path)
    enrichment_md = read_text(gold_enrichment_path)

    rendered = render_prompt(prompt_base, cfg, validation_md, enrichment_md)

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        ts = datetime.now().strftime("%Y-%m-%d_%H%M")
        output_path = (Path(__file__).resolve().parent.parent / "artifacts" / f"prompt_2_ml_rendered_{ts}.md").resolve()

    output_path.write_text(rendered, encoding="utf-8")

    ml_cfg = cfg.get("ml", {})
    metrics = ml_cfg.get("metrics", [])
    metric_count = len(metrics) if isinstance(metrics, list) else 0

    print("=== Prompt ML Renderizado ===")
    print(f"prompt_base: {prompt_base_path}")
    print(f"gold_validation: {gold_validation_path}")
    print(f"gold_enrichment_doc: {gold_enrichment_path}")
    print(f"target: {ml_cfg.get('target', 'n/a')}")
    print(f"metric_count: {metric_count}")
    print(f"output: {output_path}")
    print("\n[OK] Bloco C concluido: prompt final de ML montado sem uso de API.")


if __name__ == "__main__":
    main()
