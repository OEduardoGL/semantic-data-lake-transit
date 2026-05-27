# ML Run Error - Llama v2 Retry 1

- timestamp: `2026-04-18T19:21`
- model_label: `llama_3_3_70b_v2_retry1`
- source_file: `tcc/code/generated/ml_retry_openrouter_meta_llama_llama_3_3_70b_instruct_attempt1_2026-04-18_1913.py`
- stage: `11.2 / Bloco E`
- summary: `O agregado por linha/faixa horaria contou cod_linha dentro do proprio groupby e depois o reset_index tentou reinserir uma coluna com nome duplicado.`

## Traceback real
```text
Traceback (most recent call last):
  File "project/code/10_run_ml_pipeline.py", line 262, in <module>
    main()
  File "project/code/10_run_ml_pipeline.py", line 182, in main
    result = generated_module.run_ml_pipeline(pdf.copy())
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "project/code/generated/ml_retry_openrouter_meta_llama_llama_3_3_70b_instruct_attempt1_2026-04-18_1913.py", line 92, in run_ml_pipeline
    }).reset_index()
       ^^^^^^^^^^^^^
  File "<venv>/site-packages/pandas/core/frame.py", line 6472, in reset_index
    new_obj.insert(
  File "<venv>/site-packages/pandas/core/frame.py", line 5158, in insert
    raise ValueError(f"cannot insert {column}, already exists")
ValueError: cannot insert cod_linha, already exists
```
