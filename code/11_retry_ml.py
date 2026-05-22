#!/usr/bin/env python3
"""Etapa 11.1 (Bloco B): executa retry de ML orientado por erro real."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from openai import OpenAI


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"YAML invalido: {path}")
    return data


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8") as f:
        return f.read()


def load_local_env(base_dir: Path) -> None:
    env_path = (base_dir.parent / ".env.local").resolve()
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def parse_args() -> argparse.Namespace:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Executa retry de ML contra uma LLM")
    parser.add_argument("--config", default=str(base / "config.yaml"))
    parser.add_argument(
        "--prompt-template",
        default=str(base.parent / "prompts" / "prompt_4_retry_ml_2026-04-18_v2.md"),
    )
    parser.add_argument(
        "--provider",
        default="primary",
        choices=["comparison", "openrouter", "openai", "primary"],
        help="comparison/openrouter para Llama 3.3 70B; primary/openai para OpenAI",
    )
    parser.add_argument("--model", default=None, help="Sobrescreve o modelo do config")
    parser.add_argument("--failed-code", required=True, help="Arquivo .py da tentativa que falhou")
    parser.add_argument("--error-file", required=True, help="Arquivo .md/.txt com erro e traceback")
    parser.add_argument("--error-summary", required=True, help="Resumo curto do erro observado")
    parser.add_argument("--attempt", type=int, default=1, help="Numero da tentativa de retry")
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Valida configuracao sem chamar API")
    return parser.parse_args()


def resolve_provider_settings(cfg: dict[str, Any], provider_arg: str) -> tuple[str, str, str, str]:
    llm_cfg = cfg.get("llm", {})

    if provider_arg in {"comparison", "openrouter"}:
        provider = str(llm_cfg.get("comparison_provider", "openrouter"))
        model = str(llm_cfg.get("comparison_model", "meta-llama/llama-3.3-70b-instruct"))
        api_key_env = "OPENROUTER_API_KEY"
        base_url = "https://openrouter.ai/api/v1"
        return provider, model, api_key_env, base_url

    provider = str(llm_cfg.get("primary_provider", "openai"))
    model = str(llm_cfg.get("primary_model", "gpt-4o"))
    api_key_env = "OPENAI_API_KEY"
    base_url = "https://api.openai.com/v1"
    return provider, model, api_key_env, base_url


def extract_python_code(text: str) -> str:
    fenced = re.findall(r"```python\s+(.*?)```", text, flags=re.S)
    if fenced:
        return fenced[0].strip() + "\n"

    generic = re.findall(r"```\s*(.*?)```", text, flags=re.S)
    if generic:
        return generic[0].strip() + "\n"

    return text.strip() + "\n"


def build_output_paths(base_dir: Path, provider: str, model: str, attempt: int) -> tuple[Path, Path, Path]:
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", f"{provider}_{model}").strip("_").lower()

    generated_dir = (base_dir / "generated").resolve()
    generated_dir.mkdir(parents=True, exist_ok=True)

    artifacts_dir = (base_dir.parent / "artifacts").resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    prompt_path = artifacts_dir / f"prompt_4_retry_ml_rendered_{slug}_attempt{attempt}_{ts}.md"
    code_path = generated_dir / f"ml_retry_{slug}_attempt{attempt}_{ts}.py"
    log_path = artifacts_dir / f"ml_retry_call_{slug}_attempt{attempt}_{ts}.json"
    return prompt_path, code_path, log_path


def render_retry_prompt(
    template_text: str,
    model_name: str,
    failed_code: str,
    error_summary: str,
    traceback_text: str,
) -> str:
    sections = [
        template_text.rstrip(),
        "",
        "## Modelo atual",
        model_name,
        "",
        "## Resumo do erro observado",
        error_summary.strip(),
        "",
        "## Traceback real",
        "```text",
        traceback_text.rstrip(),
        "```",
        "",
        "## Codigo anterior que falhou",
        "```python",
        failed_code.rstrip(),
        "```",
        "",
        "## Tarefa",
        (
            "Reescreva o codigo completo corrigindo o erro acima, preservando o split temporal, "
            "o baseline obrigatorio e o contrato de saida do pipeline de ML."
        ),
        "",
    ]
    return "\n".join(sections)


def main() -> None:
    started_at = time.time()
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    load_local_env(base_dir)

    config_path = Path(args.config).resolve()
    cfg = load_yaml(config_path)

    provider, model, api_key_env, base_url = resolve_provider_settings(cfg, args.provider)
    if args.model:
        model = args.model

    temperature = args.temperature
    if temperature is None:
        temperature = float(cfg.get("llm", {}).get("temperature", 0.2))

    prompt_template_path = Path(args.prompt_template).resolve()
    failed_code_path = Path(args.failed_code).resolve()
    error_file_path = Path(args.error_file).resolve()

    template_text = read_text(prompt_template_path)
    failed_code = read_text(failed_code_path)
    traceback_text = read_text(error_file_path)

    prompt_path, code_path, log_path = build_output_paths(base_dir, provider, model, args.attempt)
    rendered_prompt = render_retry_prompt(
        template_text=template_text,
        model_name=model,
        failed_code=failed_code,
        error_summary=args.error_summary,
        traceback_text=traceback_text,
    )
    prompt_path.write_text(rendered_prompt, encoding="utf-8")

    metadata = {
        "timestamp": datetime.now().isoformat(),
        "provider": provider,
        "model": model,
        "attempt": args.attempt,
        "prompt_template": str(prompt_template_path),
        "prompt_rendered": str(prompt_path),
        "failed_code": str(failed_code_path),
        "error_file": str(error_file_path),
        "error_summary": args.error_summary,
        "config_file": str(config_path),
        "temperature": temperature,
        "dry_run": args.dry_run,
        "api_key_env": api_key_env,
        "code_output": str(code_path),
        "log_output": str(log_path),
    }

    if args.dry_run:
        metadata["elapsed_sec"] = round(time.time() - started_at, 3)
        log_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        print("=== Dry Run Retry ML ===")
        print(f"provider: {provider}")
        print(f"model: {model}")
        print(f"attempt: {args.attempt}")
        print(f"prompt_rendered: {prompt_path}")
        print(f"code_output: {code_path}")
        print(f"log_output: {log_path}")
        print("\n[OK] Dry-run concluido: script pronto para retry real de ML.")
        return

    api_key = os.getenv(api_key_env)
    if not api_key:
        raise EnvironmentError(f"Variavel de ambiente obrigatoria ausente: {api_key_env}")

    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {
                "role": "system",
                "content": (
                    "You correct previously generated Python machine learning pipeline code. "
                    "Return only executable Python code, preferably in a single python code block."
                ),
            },
            {"role": "user", "content": rendered_prompt},
        ],
    )

    content = response.choices[0].message.content or ""
    code = extract_python_code(content)
    code_path.write_text(code, encoding="utf-8")

    metadata["response_id"] = response.id
    metadata["raw_response_text"] = content
    metadata["finish_reason"] = response.choices[0].finish_reason
    metadata["elapsed_sec"] = round(time.time() - started_at, 3)
    log_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print("=== Retry ML Code Generated ===")
    print(f"provider: {provider}")
    print(f"model: {model}")
    print(f"attempt: {args.attempt}")
    print(f"prompt_rendered: {prompt_path}")
    print(f"code_output: {code_path}")
    print(f"log_output: {log_path}")
    print("\n[OK] Codigo corrigido de ML gerado e salvo.")


if __name__ == "__main__":
    main()
