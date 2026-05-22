#!/usr/bin/env python3
"""Etapa 7 (Bloco C): montagem programatica do Prompt 1 (wrangling).

Este script NAO chama API de LLM.
Ele apenas consolida o prompt base com contexto semantico e de schema,
gerando um artefato versionado para auditoria/reproducao.
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


def build_schema_context(mapping: dict[str, Any]) -> str:
    tables = mapping.get("silver_tables", {})
    lines: list[str] = []
    lines.append("## Contexto adicional (gerado automaticamente): schema Silver e mapeamento semantico")

    if not isinstance(tables, dict) or not tables:
        lines.append("- Nenhuma tabela mapeada encontrada em semantic_mapping.yaml")
        return "\n".join(lines)

    for table_name, table_cfg_any in sorted(tables.items()):
        if not isinstance(table_cfg_any, dict):
            continue

        semantic_class = str(table_cfg_any.get("semantic_class", ""))
        natural_key = table_cfg_any.get("natural_key", {})
        strategy = ""
        nk_cols: list[str] = []
        if isinstance(natural_key, dict):
            strategy = str(natural_key.get("strategy", ""))
            cols_any = natural_key.get("columns", [])
            if isinstance(cols_any, list):
                nk_cols = [str(x) for x in cols_any]

        object_links_any = table_cfg_any.get("object_links", [])
        data_props_any = table_cfg_any.get("data_properties", [])

        lines.append("")
        lines.append(f"### Tabela `{table_name}`")
        lines.append(f"- Classe semantica: `{semantic_class}`")
        lines.append(f"- Chave natural: `{strategy}` ({', '.join(nk_cols) if nk_cols else 'n/a'})")

        if isinstance(object_links_any, list) and object_links_any:
            links_fmt: list[str] = []
            for link in object_links_any:
                if isinstance(link, dict):
                    src = str(link.get("source_column", ""))
                    pred = str(link.get("predicate", ""))
                    tgt = str(link.get("target_class", ""))
                    links_fmt.append(f"`{src}` -> `{pred}` -> `{tgt}`")
            lines.append("- Links semanticos: " + ("; ".join(links_fmt) if links_fmt else "n/a"))
        else:
            lines.append("- Links semanticos: n/a")

        if isinstance(data_props_any, list) and data_props_any:
            cols_fmt: list[str] = []
            for dp in data_props_any:
                if isinstance(dp, dict):
                    cols_fmt.append(str(dp.get("source", "")))
            unique_cols = sorted({c for c in cols_fmt if c})
            lines.append("- Colunas mapeadas (data properties): " + (", ".join(f"`{c}`" for c in unique_cols) if unique_cols else "n/a"))
        else:
            lines.append("- Colunas mapeadas (data properties): n/a")

    return "\n".join(lines)


def build_required_columns_context(cfg: dict[str, Any]) -> str:
    req = cfg.get("pipeline", {}).get("required_columns_final_table", [])
    lines = ["## Colunas obrigatorias da FinalTable (config.yaml)"]
    if isinstance(req, list) and req:
        for col in req:
            lines.append(f"- `{col}`")
    else:
        lines.append("- Lista nao definida em config.yaml")
    return "\n".join(lines)


def render_prompt(base_prompt: str, mapping: dict[str, Any], rules_md: str, cfg: dict[str, Any]) -> str:
    sections = [
        base_prompt.strip(),
        "\n---\n",
        build_schema_context(mapping),
        "\n\n---\n",
        build_required_columns_context(cfg),
        "\n\n---\n",
        "## Regras semanticas (texto de referencia)\n" + rules_md.strip(),
    ]
    return "\n".join(sections).strip() + "\n"


def parse_args() -> argparse.Namespace:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Monta prompt de wrangling (sem chamada de LLM)")
    parser.add_argument("--config", default=str(base / "config.yaml"))
    parser.add_argument("--prompt-base", default=str(base.parent / "prompts" / "prompt_1_wrangling_2026-02-17_v1.md"))
    parser.add_argument("--mapping", default=str(base / "semantic_mapping.yaml"))
    parser.add_argument("--rules-md", default=str(base.parent / "docs" / "regras_semanticas.md"))
    parser.add_argument("--output", default=None, help="caminho de saida do prompt renderizado")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    config_path = Path(args.config).resolve()
    prompt_base_path = Path(args.prompt_base).resolve()
    mapping_path = Path(args.mapping).resolve()
    rules_path = Path(args.rules_md).resolve()

    for p in (config_path, prompt_base_path, mapping_path, rules_path):
        if not p.exists():
            raise FileNotFoundError(f"Arquivo nao encontrado: {p}")

    cfg = load_yaml(config_path)
    mapping = load_yaml(mapping_path)
    prompt_base = read_text(prompt_base_path)
    rules_md = read_text(rules_path)

    rendered = render_prompt(prompt_base, mapping, rules_md, cfg)

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        ts = datetime.now().strftime("%Y-%m-%d_%H%M")
        output_path = (Path(__file__).resolve().parent.parent / "artifacts" / f"prompt_1_wrangling_rendered_{ts}.md").resolve()

    output_path.write_text(rendered, encoding="utf-8")

    silver_tables = mapping.get("silver_tables", {})
    table_count = len(silver_tables) if isinstance(silver_tables, dict) else 0
    required_cols = cfg.get("pipeline", {}).get("required_columns_final_table", [])
    req_count = len(required_cols) if isinstance(required_cols, list) else 0

    print("=== Prompt Wrangling Renderizado ===")
    print(f"prompt_base: {prompt_base_path}")
    print(f"mapping: {mapping_path}")
    print(f"rules_md: {rules_path}")
    print(f"tables_mapped: {table_count}")
    print(f"required_final_table_cols: {req_count}")
    print(f"output: {output_path}")
    print("\n[OK] Bloco C concluido: prompt final montado sem uso de API.")


if __name__ == "__main__":
    main()
