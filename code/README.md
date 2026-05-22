# Code

Scripts numerados representam a ordem logica do pipeline:

1. `01_bronze_to_silver.py`
2. `02_build_semantic_model.py`
3. `03_prompt_wrangling.py`
4. `04_run_wrangling.py`
5. `05_retry_wrangling.py`
6. `06_materialize_final_table.py`
7. `07_prompt_ml.py`
8. `08_run_ml_codegen.py`
9. `09_run_baseline.py`
10. `10_run_ml_pipeline.py`
11. `11_retry_ml.py`
12. `12_generate_decision_aggregates.py`
13. `13_publish_neo4j.py`

Arquivos auxiliares:
- `config.yaml`: configuracao local efetiva, nao versionada
- `config.example.yaml`: configuracao compartilhavel sem credenciais
- `semantic_mapping.yaml`: mapeamento Silver -> ontologia
- `requirements.txt`: dependencias Python
- `run_full_raw_official.sh`: execucao oficial do bruto completo para a etapa 3

Resultados gerados por LLM ficam em:
- `generated/`

Nao editar manualmente um artefato gerado por LLM sem registrar a decisao em documento tecnico apropriado.
