# Prompt 3 - Retry de Wrangling Semantico (v1)

## Objetivo
Corrigir codigo PySpark de wrangling previamente gerado por uma LLM que falhou em importacao ou execucao.

Este prompt deve ser usado no fluxo:
`codigo anterior -> erro real/traceback -> correcao pela LLM -> novo sanity check`.

Escopo desta versao:
- suportar retry controlado para:
  - OpenAI `gpt-4o`;
  - `Llama 3.3 70B Instruct`;
- usar como entrada o codigo anterior e o erro real observado;
- produzir uma nova versao executavel do wrangling, sem explicacoes fora do codigo.

## Contexto obrigatorio a ser fornecido ao modelo
Ao montar este prompt para execucao real, incluir sempre:

1. O codigo anterior completo que falhou.
2. O traceback real completo, sem resumir.
3. O resumo objetivo do erro.
4. As regras semanticas obrigatorias.
5. O contrato de saida obrigatorio.

## Resumo dos erros reais ja observados
### Caso OpenAI
- erro principal: `AnalysisException` em `unionByName`
- causa objetiva: tentativa de unir `gps_events`, `stop_events`, `fare_events` e `operational_events` como se tivessem schemas identicos
- restricao implicita para a correcao:
  - nao usar `unionByName` entre tabelas de schemas diferentes sem padronizacao explicita de colunas

### Caso Llama
- erro principal: `NameError: name 'DataFrame' is not defined`
- causa objetiva: uso de anotacao `DataFrame` sem importar o simbolo
- problema adicional:
  - o codigo incluiu um bloco de exemplo executavel fora de `if __name__ == "__main__":`
- restricao implicita para a correcao:
  - o arquivo gerado precisa ser importavel como modulo, sem executar exemplos no import

## Regras semanticas obrigatorias
Aplicar obrigatoriamente estas regras:

1. Fallback de chaves:
- `id_empresa`, `cod_linha`, `cod_veiculo`: usar fallback para `-1` quando ausente.
- `cod_tabela_programacao` e `viagem_sentido`: podem permanecer `null`.

2. Timestamp canonico:
- usar `event_ts` como tempo canonico de analise;
- preservar `created_at_origem` e `created_at_ingestao` para auditoria.

3. GPS invalido:
- nao descartar automaticamente registros com GPS invalido;
- criar/propagar flag `gps_is_invalid` quando `gps_sinal` invalido, coordenadas nulas ou fora de faixa.

## Requisitos da FinalTable
A saida deve conter, no minimo:
- `event_dt`
- `cod_linha`
- `cod_veiculo`
- `janela_5min`
- `headway_observado_min`
- `headway_referencia_min`
- `atraso_aproximado_min`

## Contrato de saida obrigatorio
Responda com **apenas codigo Python** contendo:

1. Imports completos e corretos no topo.
2. Funcao principal com assinatura exata:
```python
def build_final_table(df_dict: dict[str, DataFrame]) -> DataFrame:
    ...
```
3. Funcao de validacao:
```python
def validate_final_table(df_final: DataFrame) -> None:
    ...
```

## Restricoes tecnicas obrigatorias
- usar apenas API PySpark DataFrame;
- nao usar Pandas;
- nao incluir texto explicativo fora do codigo;
- nao incluir exemplo executavel fora de `if __name__ == "__main__":`;
- o arquivo precisa ser importavel como modulo sem side effects;
- validar presenca de colunas minimas antes das transformacoes;
- falhar com erro explicito quando faltar coluna critica;
- evitar `unionByName` entre tabelas com schemas diferentes, salvo se houver alinhamento explicito de schema;
- preferir joins, agregacoes e selecoes semanticamente consistentes com as 4 tabelas Silver;
- manter transformacoes deterministicas.

## Instrucoes de correcao
Corrija o codigo anterior levando em conta o erro observado.

Regras para a resposta:
- preserve o maximo possivel do que estiver correto;
- altere apenas o necessario para tornar o modulo importavel e a logica executavel;
- se o erro vier de schema, corrija a estrategia de combinacao das tabelas;
- se o erro vier de importacao, corrija imports, anotacoes e side effects;
- retorne uma nova versao completa do codigo, nao apenas diff.

## Variaveis de entrada esperadas na montagem do prompt renderizado
Na execucao real, o runner deve preencher algo como:

```text
{{MODEL_NAME}}
{{FAILED_CODE}}
{{ERROR_SUMMARY}}
{{TRACEBACK}}
```

## Formato final da resposta da LLM
- um unico bloco de codigo Python executavel;
- sem markdown adicional fora do bloco;
- com imports necessarios no topo;
- pronto para salvar como nova versao do wrangling.

## Modelo atual
gpt-4o

## Resumo do erro observado
AnalysisException: event_ts esta como BIGINT e precisa ser convertido para TIMESTAMP antes de aplicar window de 5 minutos

## Traceback real
```text
=== Sanity Check OpenAI Retry Attempt 1 ===
timestamp=2026-04-03T19:25:22.289945
module_path=/home/eduardo/code/reproducao-artigo/tcc/code/generated/wrangling_retry_openai_gpt_4o_attempt1_2026-04-03_1921.py
import_status=ok
gps_events: base_path=s3a://transport/silver/gps_events
gps_events: cols=33 names=['event_id', 'event_ts', 'created_at_origem', 'created_at_ingestao', 'sequencial', 'cod_linha', 'prefixo_linha', 'cod_veiculo', 'prefixo_veiculo', 'cod_garagem', 'cod_operador', 'cod_tabela_programacao', 'viagem_sentido', 'status_ignicao', 'status_panico', 'gps_idx', 'gps_timestamp_utc_geracao', 'gps_sinal', 'latitude_raw', 'longitude_raw', 'latitude', 'longitude', 'velocidade', 'direcao', 'numero_satelites', 'hdop', 'pdop', 'odometro_calculado', 'lat_erro', 'lon_erro', 'event_dt', 'tipo_mensagem', 'id_empresa']
gps_events: rows=7
stop_events: base_path=s3a://transport/silver/stop_events
stop_events: cols=30 names=['event_id', 'event_ts', 'created_at_origem', 'created_at_ingestao', 'sequencial', 'cod_linha', 'prefixo_linha', 'cod_veiculo', 'prefixo_veiculo', 'cod_garagem', 'cod_operador', 'cod_tabela_programacao', 'viagem_sentido', 'status_ignicao', 'status_panico', 'id_ponto', 'evento_ponto', 'gps_idx', 'gps_sinal', 'latitude_raw', 'longitude_raw', 'latitude', 'longitude', 'velocidade', 'direcao', 'numero_satelites', 'odometro_calculado', 'event_dt', 'tipo_mensagem', 'id_empresa']
stop_events: rows=2
fare_events: base_path=s3a://transport/silver/fare_events
fare_events: cols=28 names=['event_id', 'event_ts', 'created_at_origem', 'created_at_ingestao', 'sequencial', 'cod_linha', 'prefixo_linha', 'cod_veiculo', 'prefixo_veiculo', 'cod_garagem', 'cod_operador', 'cod_tabela_programacao', 'viagem_sentido', 'status_ignicao', 'status_panico', 'gps_idx', 'gps_sinal', 'latitude_raw', 'longitude_raw', 'latitude', 'longitude', 'velocidade', 'direcao', 'numero_satelites', 'odometro_calculado', 'event_dt', 'tipo_mensagem', 'id_empresa']
fare_events: rows=9499
operational_events: base_path=s3a://transport/silver/operational_events
operational_events: cols=28 names=['event_id', 'event_ts', 'created_at_origem', 'created_at_ingestao', 'sequencial', 'cod_linha', 'prefixo_linha', 'cod_veiculo', 'prefixo_veiculo', 'cod_garagem', 'cod_operador', 'cod_tabela_programacao', 'viagem_sentido', 'status_ignicao', 'status_panico', 'gps_idx', 'gps_sinal', 'latitude_raw', 'longitude_raw', 'latitude', 'longitude', 'velocidade', 'direcao', 'numero_satelites', 'odometro_calculado', 'event_dt', 'tipo_mensagem', 'id_empresa']
operational_events: rows=4
build_final_table_status=error
error_type=AnalysisException
error_message=[DATATYPE_MISMATCH.UNEXPECTED_INPUT_TYPE] Cannot resolve "window(event_ts, 300000000, 300000000, 0)" due to data type mismatch: Parameter 1 requires the ("(TIMESTAMP OR TIMESTAMP WITHOUT TIME ZONE)" or "STRUCT<start: TIMESTAMP, end: TIMESTAMP>" or "STRUCT<start: TIMESTAMP_NTZ, end: TIMESTAMP_NTZ>") type, however "event_ts" has the type "BIGINT".; line 1 pos 0;
'Project [event_id#0, event_ts#1L, created_at_origem#2, created_at_ingestao#3, sequencial#4L, cod_linha#415, prefixo_linha#6, cod_veiculo#449, prefixo_veiculo#8, cod_garagem#9, cod_operador#10L, cod_tabela_programacao#11, viagem_sentido#12, status_ignicao#13, status_panico#14, gps_idx#15, gps_sinal#17, latitude_raw#18, longitude_raw#19, latitude#20, longitude#21, velocidade#22, direcao#23, numero_satelites#24, ... 6 more fields]
+- Union false, false
   :- Project [event_id#0, event_ts#1L, created_at_origem#2, created_at_ingestao#3, sequencial#4L, cod_linha#415, prefixo_linha#6, cod_veiculo#449, prefixo_veiculo#8, cod_garagem#9, cod_operador#10L, cod_tabela_programacao#11, viagem_sentido#12, status_ignicao#13, status_panico#14, gps_idx#15, gps_sinal#17, latitude_raw#18, longitude_raw#19, latitude#20, longitude#21, velocidade#22, direcao#23, numero_satelites#24, ... 5 more fields]
   :  +- Project [event_id#0, event_ts#1L, created_at_origem#2, created_at_ingestao#3, sequencial#4L, cod_linha#415, prefixo_linha#6, cod_veiculo#449, prefixo_veiculo#8, cod_garagem#9, cod_operador#10L, cod_tabela_programacao#11, viagem_sentido#12, status_ignicao#13, status_panico#14, gps_idx#15, gps_timestamp_utc_geracao#16L, gps_sinal#17, latitude_raw#18, longitude_raw#19, latitude#20, longitude#21, velocidade#22, direcao#23, ... 10 more fields]
   :     +- Project [event_id#0, event_ts#1L, created_at_origem#2, created_at_ingestao#3, sequencial#4L, cod_linha#415, prefixo_linha#6, CASE WHEN isnull(cod_veiculo#7) THEN -1 ELSE cod_veiculo#7 END AS cod_veiculo#449, prefixo_veiculo#8, cod_garagem#9, cod_operador#10L, cod_tabela_programacao#11, viagem_sentido#12, status_ignicao#13, status_panico#14, gps_idx#15, gps_timestamp_utc_geracao#16L, gps_sinal#17, latitude_raw#18, longitude_raw#19, latitude#20, longitude#21, velocidade#22, direcao#23, ... 9 more fields]
   :        +- Project [event_id#0, event_ts#1L, created_at_origem#2, created_at_ingestao#3, sequencial#4L, CASE WHEN isnull(cod_linha#5) THEN -1 ELSE cod_linha#5 END AS cod_linha#415, prefixo_linha#6, cod_veiculo#7, prefixo_veiculo#8, cod_garagem#9, cod_operador#10L, cod_tabela_programacao#11, viagem_sentido#12, status_ignicao#13, status_panico#14, gps_idx#15, gps_timestamp_utc_geracao#16L, gps_sinal#17, latitude_raw#18, longitude_raw#19, latitude#20, longitude#21, velocidade#22, direcao#23, ... 9 more fields]
   :           +- Project [event_id#0, event_ts#1L, created_at_origem#2, created_at_ingestao#3, sequencial#4L, cod_linha#5, prefixo_linha#6, cod_veiculo#7, prefixo_veiculo#8, cod_garagem#9, cod_operador#10L, cod_tabela_programacao#11, viagem_sentido#12, status_ignicao#13, status_panico#14, gps_idx#15, gps_timestamp_utc_geracao#16L, gps_sinal#17, latitude_raw#18, longitude_raw#19, latitude#20, longitude#21, velocidade#22, direcao#23, ... 9 more fields]
   :              +- Filter (((event_dt#30 = cast(2023-03-02 as date)) AND (tipo_mensagem#31 = AVL_EVT_POSICIONAMENTO)) AND (id_empresa#32 = 35))
   :                 +- Relation [event_id#0,event_ts#1L,created_at_origem#2,created_at_ingestao#3,sequencial#4L,cod_linha#5,prefixo_linha#6,cod_veiculo#7,prefixo_veiculo#8,cod_garagem#9,cod_operador#10L,cod_tabela_programacao#11,viagem_sentido#12,status_ignicao#13,status_panico#14,gps_idx#15,gps_timestamp_utc_geracao#16L,gps_sinal#17,latitude_raw#18,longitude_raw#19,latitude#20,longitude#21,velocidade#22,direcao#23,... 9 more fields] parquet
   :- Project [event_id#105, event_ts#106L, created_at_origem#107, created_at_ingestao#108, sequencial#109L, cod_linha#549, prefixo_linha#111, cod_veiculo#580, prefixo_veiculo#113, cod_garagem#114, cod_operador#115L, cod_tabela_programacao#116, viagem_sentido#117, status_ignicao#118, status_panico#119, gps_idx#122, gps_sinal#123, latitude_raw#124, longitude_raw#125, latitude#126, longitude#127, velocidade#128, direcao#129, numero_satelites#130, ... 5 more fields]
   :  +- Project [event_id#105, event_ts#106L, created_at_origem#107, created_at_ingestao#108, sequencial#109L, cod_linha#549, prefixo_linha#111, cod_veiculo#580, prefixo_veiculo#113, cod_garagem#114, cod_operador#115L, cod_tabela_programacao#116, viagem_sentido#117, status_ignicao#118, status_panico#119, gps_idx#122, gps_sinal#123, latitude_raw#124, longitude_raw#125, latitude#126, longitude#127, velocidade#128, direcao#129, numero_satelites#130, ... 5 more fields]
   :     +- Project [event_id#105, event_ts#106L, created_at_origem#107, created_at_ingestao#108, sequencial#109L, cod_linha#549, prefixo_linha#111, cod_veiculo#580, prefixo_veiculo#113, cod_garagem#114, cod_operador#115L, cod_tabela_programacao#116, viagem_sentido#117, status_ignicao#118, status_panico#119, id_ponto#120, evento_ponto#121, gps_idx#122, gps_sinal#123, latitude_raw#124, longitude_raw#125, latitude#126, longitude#127, velocidade#128, ... 7 more fields]
   :        +- Project [event_id#105, event_ts#106L, created_at_origem#107, created_at_ingestao#108, sequencial#109L, cod_linha#549, prefixo_linha#111, CASE WHEN isnull(cod_veiculo#112) THEN -1 ELSE cod_veiculo#112 END AS cod_veiculo#580, prefixo_veiculo#113, cod_garagem#114, cod_operador#115L, cod_tabela_programacao#116, viagem_sentido#117, status_ignicao#118, status_panico#119, id_ponto#120, evento_ponto#121, gps_idx#122, gps_sinal#123, latitude_raw#124, longitude_raw#125, latitude#126, longitude#127, velocidade#128, ... 6 more fields]
   :           +- Project [event_id#105, event_ts#106L, created_at_origem#107, created_at_ingestao#108, sequencial#109L, CASE WHEN isnull(cod_linha#110) THEN -1 ELSE cod_linha#110 END AS cod_linha#549, prefixo_linha#111, cod_veiculo#112, prefixo_veiculo#113, cod_garagem#114, cod_operador#115L, cod_tabela_programacao#116, viagem_sentido#117, status_ignicao#118, status_panico#119, id_ponto#120, evento_ponto#121, gps_idx#122, gps_sinal#123, latitude_raw#124, longitude_raw#125, latitude#126, longitude#127, velocidade#128, ... 6 more fields]
   :              +- Project [event_id#105, event_ts#106L, created_at_origem#107, created_at_ingestao#108, sequencial#109L, cod_linha#110, prefixo_linha#111, cod_veiculo#112, prefixo_veiculo#113, cod_garagem#114, cod_operador#115L, cod_tabela_programacao#116, viagem_sentido#117, status_ignicao#118, status_panico#119, id_ponto#120, evento_ponto#121, gps_idx#122, gps_sinal#123, latitude_raw#124, longitude_raw#125, latitude#126, longitude#127, velocidade#128, ... 6 more fields]
   :                 +- Filter (((event_dt#132 = cast(2023-03-02 as date)) AND (tipo_mensagem#133 = AVL_EVT_ENTRADA_SAIDA_PONTO)) AND (id_empresa#134 = 35))
   :                    +- Relation [event_id#105,event_ts#106L,created_at_origem#107,created_at_ingestao#108,sequencial#109L,cod_linha#110,prefixo_linha#111,cod_veiculo#112,prefixo_veiculo#113,cod_garagem#114,cod_operador#115L,cod_tabela_programacao#116,viagem_sentido#117,status_ignicao#118,status_panico#119,id_ponto#120,evento_ponto#121,gps_idx#122,gps_sinal#123,latitude_raw#124,longitude_raw#125,latitude#126,longitude#127,velocidade#128,... 6 more fields] parquet
   :- Project [event_id#201, event_ts#202L, created_at_origem#203, created_at_ingestao#204, sequencial#205L, cod_linha#672, prefixo_linha#207, cod_veiculo#701, prefixo_veiculo#209, cod_garagem#210, cod_operador#211L, cod_tabela_programacao#212, viagem_sentido#213, status_ignicao#214, status_panico#215, gps_idx#216, gps_sinal#217, latitude_raw#218, longitude_raw#219, latitude#220, longitude#221, velocidade#222, direcao#223, numero_satelites#224, ... 5 more fields]
   :  +- Project [event_id#201, event_ts#202L, created_at_origem#203, created_at_ingestao#204, sequencial#205L, cod_linha#672, prefixo_linha#207, cod_veiculo#701, prefixo_veiculo#209, cod_garagem#210, cod_operador#211L, cod_tabela_programacao#212, viagem_sentido#213, status_ignicao#214, status_panico#215, gps_idx#216, gps_sinal#217, latitude_raw#218, longitude_raw#219, latitude#220, longitude#221, velocidade#222, direcao#223, numero_satelites#224, ... 5 more fields]
   :     +- Project [event_id#201, event_ts#202L, created_at_origem#203, created_at_ingestao#204, sequencial#205L, cod_linha#672, prefixo_linha#207, cod_veiculo#701, prefixo_veiculo#209, cod_garagem#210, cod_operador#211L, cod_tabela_programacao#212, viagem_sentido#213, status_ignicao#214, status_panico#215, gps_idx#216, gps_sinal#217, latitude_raw#218, longitude_raw#219, latitude#220, longitude#221, velocidade#222, direcao#223, numero_satelites#224, ... 5 more fields]
   :        +- Project [event_id#201, event_ts#202L, created_at_origem#203, created_at_ingestao#204, sequencial#205L, cod_linha#672, prefixo_linha#207, CASE WHEN isnull(cod_veiculo#208) THEN -1 ELSE cod_veiculo#208 END AS cod_veiculo#701, prefixo_veiculo#209, cod_garagem#210, cod_operador#211L, cod_tabela_programacao#212, viagem_sentido#213, status_ignicao#214, status_panico#215, gps_idx#216, gps_sinal#217, latitude_raw#218, longitude_raw#219, latitude#220, longitude#221, velocidade#222, direcao#223, numero_satelites#224, ... 4 more fields]
   :           +- Project [event_id#201, event_ts#202L, created_at_origem#203, created_at_ingestao#204, sequencial#205L, CASE WHEN isnull(cod_linha#206) THEN -1 ELSE cod_linha#206 END AS cod_linha#672, prefixo_linha#207, cod_veiculo#208, prefixo_veiculo#209, cod_garagem#210, cod_operador#211L, cod_tabela_programacao#212, viagem_sentido#213, status_ignicao#214, status_panico#215, gps_idx#216, gps_sinal#217, latitude_raw#218, longitude_raw#219, latitude#220, longitude#221, velocidade#222, direcao#223, numero_satelites#224, ... 4 more fields]
   :              +- Project [event_id#201, event_ts#202L, created_at_origem#203, created_at_ingestao#204, sequencial#205L, cod_linha#206, prefixo_linha#207, cod_veiculo#208, prefixo_veiculo#209, cod_garagem#210, cod_operador#211L, cod_tabela_programacao#212, viagem_sentido#213, status_ignicao#214, status_panico#215, gps_idx#216, gps_sinal#217, latitude_raw#218, longitude_raw#219, latitude#220, longitude#221, velocidade#222, direcao#223, numero_satelites#224, ... 4 more fields]
   :                 +- Filter (((event_dt#226 = cast(2023-02-28 as date)) AND (tipo_mensagem#227 = AVL_EVT_PASSAGEM_CARTAO)) AND (id_empresa#228 = 55))
   :                    +- Relation [event_id#201,event_ts#202L,created_at_origem#203,created_at_ingestao#204,sequencial#205L,cod_linha#206,prefixo_linha#207,cod_veiculo#208,prefixo_veiculo#209,cod_garagem#210,cod_operador#211L,cod_tabela_programacao#212,viagem_sentido#213,status_ignicao#214,status_panico#215,gps_idx#216,gps_sinal#217,latitude_raw#218,longitude_raw#219,latitude#220,longitude#221,velocidade#222,direcao#223,numero_satelites#224,... 4 more fields] parquet
   +- Project [event_id#291, event_ts#292L, created_at_origem#293, created_at_ingestao#294, sequencial#295L, cod_linha#789, prefixo_linha#297, cod_veiculo#818, prefixo_veiculo#299, cod_garagem#300, cod_operador#301L, cod_tabela_programacao#302, viagem_sentido#303, status_ignicao#304, status_panico#305, gps_idx#306, gps_sinal#307, latitude_raw#308, longitude_raw#309, latitude#310, longitude#311, velocidade#312, direcao#313, numero_satelites#314, ... 5 more fields]
      +- Project [event_id#291, event_ts#292L, created_at_origem#293, created_at_ingestao#294, sequencial#295L, cod_linha#789, prefixo_linha#297, cod_veiculo#818, prefixo_veiculo#299, cod_garagem#300, cod_operador#301L, cod_tabela_programacao#302, viagem_sentido#303, status_ignicao#304, status_panico#305, gps_idx#306, gps_sinal#307, latitude_raw#308, longitude_raw#309, latitude#310, longitude#311, velocidade#312, direcao#313, numero_satelites#314, ... 5 more fields]
         +- Project [event_id#291, event_ts#292L, created_at_origem#293, created_at_ingestao#294, sequencial#295L, cod_linha#789, prefixo_linha#297, cod_veiculo#818, prefixo_veiculo#299, cod_garagem#300, cod_operador#301L, cod_tabela_programacao#302, viagem_sentido#303, status_ignicao#304, status_panico#305, gps_idx#306, gps_sinal#307, latitude_raw#308, longitude_raw#309, latitude#310, longitude#311, velocidade#312, direcao#313, numero_satelites#314, ... 5 more fields]
            +- Project [event_id#291, event_ts#292L, created_at_origem#293, created_at_ingestao#294, sequencial#295L, cod_linha#789, prefixo_linha#297, CASE WHEN isnull(cod_veiculo#298) THEN -1 ELSE cod_veiculo#298 END AS cod_veiculo#818, prefixo_veiculo#299, cod_garagem#300, cod_operador#301L, cod_tabela_programacao#302, viagem_sentido#303, status_ignicao#304, status_panico#305, gps_idx#306, gps_sinal#307, latitude_raw#308, longitude_raw#309, latitude#310, longitude#311, velocidade#312, direcao#313, numero_satelites#314, ... 4 more fields]
               +- Project [event_id#291, event_ts#292L, created_at_origem#293, created_at_ingestao#294, sequencial#295L, CASE WHEN isnull(cod_linha#296) THEN -1 ELSE cod_linha#296 END AS cod_linha#789, prefixo_linha#297, cod_veiculo#298, prefixo_veiculo#299, cod_garagem#300, cod_operador#301L, cod_tabela_programacao#302, viagem_sentido#303, status_ignicao#304, status_panico#305, gps_idx#306, gps_sinal#307, latitude_raw#308, longitude_raw#309, latitude#310, longitude#311, velocidade#312, direcao#313, numero_satelites#314, ... 4 more fields]
                  +- Project [event_id#291, event_ts#292L, created_at_origem#293, created_at_ingestao#294, sequencial#295L, cod_linha#296, prefixo_linha#297, cod_veiculo#298, prefixo_veiculo#299, cod_garagem#300, cod_operador#301L, cod_tabela_programacao#302, viagem_sentido#303, status_ignicao#304, status_panico#305, gps_idx#306, gps_sinal#307, latitude_raw#308, longitude_raw#309, latitude#310, longitude#311, velocidade#312, direcao#313, numero_satelites#314, ... 4 more fields]
                     +- Filter (((event_dt#316 = cast(2023-03-02 as date)) AND (tipo_mensagem#317 = AVL_EVT_RECEBIMENTO_TABELA_PARCIAL)) AND (id_empresa#318 = 35))
                        +- Relation [event_id#291,event_ts#292L,created_at_origem#293,created_at_ingestao#294,sequencial#295L,cod_linha#296,prefixo_linha#297,cod_veiculo#298,prefixo_veiculo#299,cod_garagem#300,cod_operador#301L,cod_tabela_programacao#302,viagem_sentido#303,status_ignicao#304,status_panico#305,gps_idx#306,gps_sinal#307,latitude_raw#308,longitude_raw#309,latitude#310,longitude#311,velocidade#312,direcao#313,numero_satelites#314,... 4 more fields] parquet

traceback=
Traceback (most recent call last):
  File "<stdin>", line 79, in <module>
  File "/home/eduardo/code/reproducao-artigo/tcc/code/generated/wrangling_retry_openai_gpt_4o_attempt1_2026-04-03_1921.py", line 51, in build_final_table
    final_table = combined_df.withColumn("janela_5min", expr("window(event_ts, '5 minutes').start")) \
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/eduardo/code/reproducao-artigo/tcc/code/.venv/lib/python3.12/site-packages/pyspark/sql/dataframe.py", line 5176, in withColumn
    return DataFrame(self._jdf.withColumn(colName, col._jc), self.sparkSession)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/eduardo/code/reproducao-artigo/tcc/code/.venv/lib/python3.12/site-packages/py4j/java_gateway.py", line 1322, in __call__
    return_value = get_return_value(
                   ^^^^^^^^^^^^^^^^^
  File "/home/eduardo/code/reproducao-artigo/tcc/code/.venv/lib/python3.12/site-packages/pyspark/errors/exceptions/captured.py", line 185, in deco
    raise converted from None
pyspark.errors.exceptions.captured.AnalysisException: [DATATYPE_MISMATCH.UNEXPECTED_INPUT_TYPE] Cannot resolve "window(event_ts, 300000000, 300000000, 0)" due to data type mismatch: Parameter 1 requires the ("(TIMESTAMP OR TIMESTAMP WITHOUT TIME ZONE)" or "STRUCT<start: TIMESTAMP, end: TIMESTAMP>" or "STRUCT<start: TIMESTAMP_NTZ, end: TIMESTAMP_NTZ>") type, however "event_ts" has the type "BIGINT".; line 1 pos 0;
'Project [event_id#0, event_ts#1L, created_at_origem#2, created_at_ingestao#3, sequencial#4L, cod_linha#415, prefixo_linha#6, cod_veiculo#449, prefixo_veiculo#8, cod_garagem#9, cod_operador#10L, cod_tabela_programacao#11, viagem_sentido#12, status_ignicao#13, status_panico#14, gps_idx#15, gps_sinal#17, latitude_raw#18, longitude_raw#19, latitude#20, longitude#21, velocidade#22, direcao#23, numero_satelites#24, ... 6 more fields]
+- Union false, false
   :- Project [event_id#0, event_ts#1L, created_at_origem#2, created_at_ingestao#3, sequencial#4L, cod_linha#415, prefixo_linha#6, cod_veiculo#449, prefixo_veiculo#8, cod_garagem#9, cod_operador#10L, cod_tabela_programacao#11, viagem_sentido#12, status_ignicao#13, status_panico#14, gps_idx#15, gps_sinal#17, latitude_raw#18, longitude_raw#19, latitude#20, longitude#21, velocidade#22, direcao#23, numero_satelites#24, ... 5 more fields]
   :  +- Project [event_id#0, event_ts#1L, created_at_origem#2, created_at_ingestao#3, sequencial#4L, cod_linha#415, prefixo_linha#6, cod_veiculo#449, prefixo_veiculo#8, cod_garagem#9, cod_operador#10L, cod_tabela_programacao#11, viagem_sentido#12, status_ignicao#13, status_panico#14, gps_idx#15, gps_timestamp_utc_geracao#16L, gps_sinal#17, latitude_raw#18, longitude_raw#19, latitude#20, longitude#21, velocidade#22, direcao#23, ... 10 more fields]
   :     +- Project [event_id#0, event_ts#1L, created_at_origem#2, created_at_ingestao#3, sequencial#4L, cod_linha#415, prefixo_linha#6, CASE WHEN isnull(cod_veiculo#7) THEN -1 ELSE cod_veiculo#7 END AS cod_veiculo#449, prefixo_veiculo#8, cod_garagem#9, cod_operador#10L, cod_tabela_programacao#11, viagem_sentido#12, status_ignicao#13, status_panico#14, gps_idx#15, gps_timestamp_utc_geracao#16L, gps_sinal#17, latitude_raw#18, longitude_raw#19, latitude#20, longitude#21, velocidade#22, direcao#23, ... 9 more fields]
   :        +- Project [event_id#0, event_ts#1L, created_at_origem#2, created_at_ingestao#3, sequencial#4L, CASE WHEN isnull(cod_linha#5) THEN -1 ELSE cod_linha#5 END AS cod_linha#415, prefixo_linha#6, cod_veiculo#7, prefixo_veiculo#8, cod_garagem#9, cod_operador#10L, cod_tabela_programacao#11, viagem_sentido#12, status_ignicao#13, status_panico#14, gps_idx#15, gps_timestamp_utc_geracao#16L, gps_sinal#17, latitude_raw#18, longitude_raw#19, latitude#20, longitude#21, velocidade#22, direcao#23, ... 9 more fields]
   :           +- Project [event_id#0, event_ts#1L, created_at_origem#2, created_at_ingestao#3, sequencial#4L, cod_linha#5, prefixo_linha#6, cod_veiculo#7, prefixo_veiculo#8, cod_garagem#9, cod_operador#10L, cod_tabela_programacao#11, viagem_sentido#12, status_ignicao#13, status_panico#14, gps_idx#15, gps_timestamp_utc_geracao#16L, gps_sinal#17, latitude_raw#18, longitude_raw#19, latitude#20, longitude#21, velocidade#22, direcao#23, ... 9 more fields]
   :              +- Filter (((event_dt#30 = cast(2023-03-02 as date)) AND (tipo_mensagem#31 = AVL_EVT_POSICIONAMENTO)) AND (id_empresa#32 = 35))
   :                 +- Relation [event_id#0,event_ts#1L,created_at_origem#2,created_at_ingestao#3,sequencial#4L,cod_linha#5,prefixo_linha#6,cod_veiculo#7,prefixo_veiculo#8,cod_garagem#9,cod_operador#10L,cod_tabela_programacao#11,viagem_sentido#12,status_ignicao#13,status_panico#14,gps_idx#15,gps_timestamp_utc_geracao#16L,gps_sinal#17,latitude_raw#18,longitude_raw#19,latitude#20,longitude#21,velocidade#22,direcao#23,... 9 more fields] parquet
   :- Project [event_id#105, event_ts#106L, created_at_origem#107, created_at_ingestao#108, sequencial#109L, cod_linha#549, prefixo_linha#111, cod_veiculo#580, prefixo_veiculo#113, cod_garagem#114, cod_operador#115L, cod_tabela_programacao#116, viagem_sentido#117, status_ignicao#118, status_panico#119, gps_idx#122, gps_sinal#123, latitude_raw#124, longitude_raw#125, latitude#126, longitude#127, velocidade#128, direcao#129, numero_satelites#130, ... 5 more fields]
   :  +- Project [event_id#105, event_ts#106L, created_at_origem#107, created_at_ingestao#108, sequencial#109L, cod_linha#549, prefixo_linha#111, cod_veiculo#580, prefixo_veiculo#113, cod_garagem#114, cod_operador#115L, cod_tabela_programacao#116, viagem_sentido#117, status_ignicao#118, status_panico#119, gps_idx#122, gps_sinal#123, latitude_raw#124, longitude_raw#125, latitude#126, longitude#127, velocidade#128, direcao#129, numero_satelites#130, ... 5 more fields]
   :     +- Project [event_id#105, event_ts#106L, created_at_origem#107, created_at_ingestao#108, sequencial#109L, cod_linha#549, prefixo_linha#111, cod_veiculo#580, prefixo_veiculo#113, cod_garagem#114, cod_operador#115L, cod_tabela_programacao#116, viagem_sentido#117, status_ignicao#118, status_panico#119, id_ponto#120, evento_ponto#121, gps_idx#122, gps_sinal#123, latitude_raw#124, longitude_raw#125, latitude#126, longitude#127, velocidade#128, ... 7 more fields]
   :        +- Project [event_id#105, event_ts#106L, created_at_origem#107, created_at_ingestao#108, sequencial#109L, cod_linha#549, prefixo_linha#111, CASE WHEN isnull(cod_veiculo#112) THEN -1 ELSE cod_veiculo#112 END AS cod_veiculo#580, prefixo_veiculo#113, cod_garagem#114, cod_operador#115L, cod_tabela_programacao#116, viagem_sentido#117, status_ignicao#118, status_panico#119, id_ponto#120, evento_ponto#121, gps_idx#122, gps_sinal#123, latitude_raw#124, longitude_raw#125, latitude#126, longitude#127, velocidade#128, ... 6 more fields]
   :           +- Project [event_id#105, event_ts#106L, created_at_origem#107, created_at_ingestao#108, sequencial#109L, CASE WHEN isnull(cod_linha#110) THEN -1 ELSE cod_linha#110 END AS cod_linha#549, prefixo_linha#111, cod_veiculo#112, prefixo_veiculo#113, cod_garagem#114, cod_operador#115L, cod_tabela_programacao#116, viagem_sentido#117, status_ignicao#118, status_panico#119, id_ponto#120, evento_ponto#121, gps_idx#122, gps_sinal#123, latitude_raw#124, longitude_raw#125, latitude#126, longitude#127, velocidade#128, ... 6 more fields]
   :              +- Project [event_id#105, event_ts#106L, created_at_origem#107, created_at_ingestao#108, sequencial#109L, cod_linha#110, prefixo_linha#111, cod_veiculo#112, prefixo_veiculo#113, cod_garagem#114, cod_operador#115L, cod_tabela_programacao#116, viagem_sentido#117, status_ignicao#118, status_panico#119, id_ponto#120, evento_ponto#121, gps_idx#122, gps_sinal#123, latitude_raw#124, longitude_raw#125, latitude#126, longitude#127, velocidade#128, ... 6 more fields]
   :                 +- Filter (((event_dt#132 = cast(2023-03-02 as date)) AND (tipo_mensagem#133 = AVL_EVT_ENTRADA_SAIDA_PONTO)) AND (id_empresa#134 = 35))
   :                    +- Relation [event_id#105,event_ts#106L,created_at_origem#107,created_at_ingestao#108,sequencial#109L,cod_linha#110,prefixo_linha#111,cod_veiculo#112,prefixo_veiculo#113,cod_garagem#114,cod_operador#115L,cod_tabela_programacao#116,viagem_sentido#117,status_ignicao#118,status_panico#119,id_ponto#120,evento_ponto#121,gps_idx#122,gps_sinal#123,latitude_raw#124,longitude_raw#125,latitude#126,longitude#127,velocidade#128,... 6 more fields] parquet
   :- Project [event_id#201, event_ts#202L, created_at_origem#203, created_at_ingestao#204, sequencial#205L, cod_linha#672, prefixo_linha#207, cod_veiculo#701, prefixo_veiculo#209, cod_garagem#210, cod_operador#211L, cod_tabela_programacao#212, viagem_sentido#213, status_ignicao#214, status_panico#215, gps_idx#216, gps_sinal#217, latitude_raw#218, longitude_raw#219, latitude#220, longitude#221, velocidade#222, direcao#223, numero_satelites#224, ... 5 more fields]
   :  +- Project [event_id#201, event_ts#202L, created_at_origem#203, created_at_ingestao#204, sequencial#205L, cod_linha#672, prefixo_linha#207, cod_veiculo#701, prefixo_veiculo#209, cod_garagem#210, cod_operador#211L, cod_tabela_programacao#212, viagem_sentido#213, status_ignicao#214, status_panico#215, gps_idx#216, gps_sinal#217, latitude_raw#218, longitude_raw#219, latitude#220, longitude#221, velocidade#222, direcao#223, numero_satelites#224, ... 5 more fields]
   :     +- Project [event_id#201, event_ts#202L, created_at_origem#203, created_at_ingestao#204, sequencial#205L, cod_linha#672, prefixo_linha#207, cod_veiculo#701, prefixo_veiculo#209, cod_garagem#210, cod_operador#211L, cod_tabela_programacao#212, viagem_sentido#213, status_ignicao#214, status_panico#215, gps_idx#216, gps_sinal#217, latitude_raw#218, longitude_raw#219, latitude#220, longitude#221, velocidade#222, direcao#223, numero_satelites#224, ... 5 more fields]
   :        +- Project [event_id#201, event_ts#202L, created_at_origem#203, created_at_ingestao#204, sequencial#205L, cod_linha#672, prefixo_linha#207, CASE WHEN isnull(cod_veiculo#208) THEN -1 ELSE cod_veiculo#208 END AS cod_veiculo#701, prefixo_veiculo#209, cod_garagem#210, cod_operador#211L, cod_tabela_programacao#212, viagem_sentido#213, status_ignicao#214, status_panico#215, gps_idx#216, gps_sinal#217, latitude_raw#218, longitude_raw#219, latitude#220, longitude#221, velocidade#222, direcao#223, numero_satelites#224, ... 4 more fields]
   :           +- Project [event_id#201, event_ts#202L, created_at_origem#203, created_at_ingestao#204, sequencial#205L, CASE WHEN isnull(cod_linha#206) THEN -1 ELSE cod_linha#206 END AS cod_linha#672, prefixo_linha#207, cod_veiculo#208, prefixo_veiculo#209, cod_garagem#210, cod_operador#211L, cod_tabela_programacao#212, viagem_sentido#213, status_ignicao#214, status_panico#215, gps_idx#216, gps_sinal#217, latitude_raw#218, longitude_raw#219, latitude#220, longitude#221, velocidade#222, direcao#223, numero_satelites#224, ... 4 more fields]
   :              +- Project [event_id#201, event_ts#202L, created_at_origem#203, created_at_ingestao#204, sequencial#205L, cod_linha#206, prefixo_linha#207, cod_veiculo#208, prefixo_veiculo#209, cod_garagem#210, cod_operador#211L, cod_tabela_programacao#212, viagem_sentido#213, status_ignicao#214, status_panico#215, gps_idx#216, gps_sinal#217, latitude_raw#218, longitude_raw#219, latitude#220, longitude#221, velocidade#222, direcao#223, numero_satelites#224, ... 4 more fields]
   :                 +- Filter (((event_dt#226 = cast(2023-02-28 as date)) AND (tipo_mensagem#227 = AVL_EVT_PASSAGEM_CARTAO)) AND (id_empresa#228 = 55))
   :                    +- Relation [event_id#201,event_ts#202L,created_at_origem#203,created_at_ingestao#204,sequencial#205L,cod_linha#206,prefixo_linha#207,cod_veiculo#208,prefixo_veiculo#209,cod_garagem#210,cod_operador#211L,cod_tabela_programacao#212,viagem_sentido#213,status_ignicao#214,status_panico#215,gps_idx#216,gps_sinal#217,latitude_raw#218,longitude_raw#219,latitude#220,longitude#221,velocidade#222,direcao#223,numero_satelites#224,... 4 more fields] parquet
   +- Project [event_id#291, event_ts#292L, created_at_origem#293, created_at_ingestao#294, sequencial#295L, cod_linha#789, prefixo_linha#297, cod_veiculo#818, prefixo_veiculo#299, cod_garagem#300, cod_operador#301L, cod_tabela_programacao#302, viagem_sentido#303, status_ignicao#304, status_panico#305, gps_idx#306, gps_sinal#307, latitude_raw#308, longitude_raw#309, latitude#310, longitude#311, velocidade#312, direcao#313, numero_satelites#314, ... 5 more fields]
      +- Project [event_id#291, event_ts#292L, created_at_origem#293, created_at_ingestao#294, sequencial#295L, cod_linha#789, prefixo_linha#297, cod_veiculo#818, prefixo_veiculo#299, cod_garagem#300, cod_operador#301L, cod_tabela_programacao#302, viagem_sentido#303, status_ignicao#304, status_panico#305, gps_idx#306, gps_sinal#307, latitude_raw#308, longitude_raw#309, latitude#310, longitude#311, velocidade#312, direcao#313, numero_satelites#314, ... 5 more fields]
         +- Project [event_id#291, event_ts#292L, created_at_origem#293, created_at_ingestao#294, sequencial#295L, cod_linha#789, prefixo_linha#297, cod_veiculo#818, prefixo_veiculo#299, cod_garagem#300, cod_operador#301L, cod_tabela_programacao#302, viagem_sentido#303, status_ignicao#304, status_panico#305, gps_idx#306, gps_sinal#307, latitude_raw#308, longitude_raw#309, latitude#310, longitude#311, velocidade#312, direcao#313, numero_satelites#314, ... 5 more fields]
            +- Project [event_id#291, event_ts#292L, created_at_origem#293, created_at_ingestao#294, sequencial#295L, cod_linha#789, prefixo_linha#297, CASE WHEN isnull(cod_veiculo#298) THEN -1 ELSE cod_veiculo#298 END AS cod_veiculo#818, prefixo_veiculo#299, cod_garagem#300, cod_operador#301L, cod_tabela_programacao#302, viagem_sentido#303, status_ignicao#304, status_panico#305, gps_idx#306, gps_sinal#307, latitude_raw#308, longitude_raw#309, latitude#310, longitude#311, velocidade#312, direcao#313, numero_satelites#314, ... 4 more fields]
               +- Project [event_id#291, event_ts#292L, created_at_origem#293, created_at_ingestao#294, sequencial#295L, CASE WHEN isnull(cod_linha#296) THEN -1 ELSE cod_linha#296 END AS cod_linha#789, prefixo_linha#297, cod_veiculo#298, prefixo_veiculo#299, cod_garagem#300, cod_operador#301L, cod_tabela_programacao#302, viagem_sentido#303, status_ignicao#304, status_panico#305, gps_idx#306, gps_sinal#307, latitude_raw#308, longitude_raw#309, latitude#310, longitude#311, velocidade#312, direcao#313, numero_satelites#314, ... 4 more fields]
                  +- Project [event_id#291, event_ts#292L, created_at_origem#293, created_at_ingestao#294, sequencial#295L, cod_linha#296, prefixo_linha#297, cod_veiculo#298, prefixo_veiculo#299, cod_garagem#300, cod_operador#301L, cod_tabela_programacao#302, viagem_sentido#303, status_ignicao#304, status_panico#305, gps_idx#306, gps_sinal#307, latitude_raw#308, longitude_raw#309, latitude#310, longitude#311, velocidade#312, direcao#313, numero_satelites#314, ... 4 more fields]
                     +- Filter (((event_dt#316 = cast(2023-03-02 as date)) AND (tipo_mensagem#317 = AVL_EVT_RECEBIMENTO_TABELA_PARCIAL)) AND (id_empresa#318 = 35))
                        +- Relation [event_id#291,event_ts#292L,created_at_origem#293,created_at_ingestao#294,sequencial#295L,cod_linha#296,prefixo_linha#297,cod_veiculo#298,prefixo_veiculo#299,cod_garagem#300,cod_operador#301L,cod_tabela_programacao#302,viagem_sentido#303,status_ignicao#304,status_panico#305,gps_idx#306,gps_sinal#307,latitude_raw#308,longitude_raw#309,latitude#310,longitude#311,velocidade#312,direcao#313,numero_satelites#314,... 4 more fields] parquet
```

## Codigo anterior que falhou
```python
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, when, expr, window, lit
from pyspark.sql.types import DoubleType

def build_final_table(df_dict: dict[str, DataFrame]) -> DataFrame:
    # Validate input DataFrames
    required_columns = {
        "gps_events": ["event_id", "gps_idx", "event_ts", "event_dt", "id_empresa", "cod_linha", "cod_veiculo", "gps_sinal", "latitude", "longitude"],
        "stop_events": ["event_id", "gps_idx", "event_ts", "event_dt", "id_empresa", "cod_linha", "cod_veiculo"],
        "fare_events": ["event_id", "gps_idx", "event_ts", "event_dt", "id_empresa", "cod_linha", "cod_veiculo"],
        "operational_events": ["event_id", "gps_idx", "event_ts", "event_dt", "id_empresa", "cod_linha", "cod_veiculo"]
    }
    
    for key, columns in required_columns.items():
        if key not in df_dict:
            raise ValueError(f"Missing DataFrame for key: {key}")
        for column in columns:
            if column not in df_dict[key].columns:
                raise ValueError(f"Missing column '{column}' in DataFrame '{key}'")

    # Apply semantic rules
    def apply_semantic_rules(df: DataFrame) -> DataFrame:
        return df.withColumn("id_empresa", when(col("id_empresa").isNull(), lit(-1)).otherwise(col("id_empresa"))) \
                 .withColumn("cod_linha", when(col("cod_linha").isNull(), lit(-1)).otherwise(col("cod_linha"))) \
                 .withColumn("cod_veiculo", when(col("cod_veiculo").isNull(), lit(-1)).otherwise(col("cod_veiculo"))) \
                 .withColumn("gps_is_invalid", when((col("gps_sinal") == 0) | col("latitude").isNull() | col("longitude").isNull(), lit(True)).otherwise(lit(False)))

    gps_events = apply_semantic_rules(df_dict["gps_events"])
    stop_events = apply_semantic_rules(df_dict["stop_events"])
    fare_events = apply_semantic_rules(df_dict["fare_events"])
    operational_events = apply_semantic_rules(df_dict["operational_events"])

    # Align schemas by selecting common columns
    common_columns = ["event_id", "event_ts", "created_at_origem", "created_at_ingestao", "sequencial", "cod_linha", "prefixo_linha", 
                      "cod_veiculo", "prefixo_veiculo", "cod_garagem", "cod_operador", "cod_tabela_programacao", "viagem_sentido", 
                      "status_ignicao", "status_panico", "gps_idx", "gps_sinal", "latitude_raw", "longitude_raw", "latitude", 
                      "longitude", "velocidade", "direcao", "numero_satelites", "odometro_calculado", "event_dt", "tipo_mensagem", 
                      "id_empresa", "gps_is_invalid"]

    gps_events = gps_events.select(*[col for col in common_columns if col in gps_events.columns])
    stop_events = stop_events.select(*[col for col in common_columns if col in stop_events.columns])
    fare_events = fare_events.select(*[col for col in common_columns if col in fare_events.columns])
    operational_events = operational_events.select(*[col for col in common_columns if col in operational_events.columns])

    # Combine DataFrames
    combined_df = gps_events.unionByName(stop_events, allowMissingColumns=True) \
                            .unionByName(fare_events, allowMissingColumns=True) \
                            .unionByName(operational_events, allowMissingColumns=True)

    # Create final table
    final_table = combined_df.withColumn("janela_5min", expr("window(event_ts, '5 minutes').start")) \
                             .withColumn("headway_observado_min", lit(None).cast(DoubleType())) \
                             .withColumn("headway_referencia_min", lit(None).cast(DoubleType())) \
                             .withColumn("atraso_aproximado_min", lit(None).cast(DoubleType())) \
                             .select("event_dt", "cod_linha", "cod_veiculo", "janela_5min", "headway_observado_min", "headway_referencia_min", "atraso_aproximado_min")

    validate_final_table(final_table)
    return final_table

def validate_final_table(df_final: DataFrame) -> None:
    # Check for required columns
    required_columns = ["event_dt", "cod_linha", "cod_veiculo", "janela_5min", "headway_observado_min", "headway_referencia_min", "atraso_aproximado_min"]
    for column in required_columns:
        if column not in df_final.columns:
            raise ValueError(f"Missing required column: {column}")

    # Check for numeric types
    numeric_columns = ["headway_observado_min", "headway_referencia_min", "atraso_aproximado_min"]
    for column in numeric_columns:
        if not isinstance(df_final.schema[column].dataType, DoubleType):
            raise TypeError(f"Column {column} must be of type DoubleType")

    # Check for nulls in key columns
    key_columns = ["event_dt", "cod_linha", "cod_veiculo"]
    for column in key_columns:
        if df_final.filter(col(column).isNull()).count() > 0:
            raise ValueError(f"Null values found in key column: {column}")

    # Check coordinate ranges if used
    if "latitude" in df_final.columns and "longitude" in df_final.columns:
        if df_final.filter((col("latitude") < -90) | (col("latitude") > 90) | (col("longitude") < -180) | (col("longitude") > 180)).count() > 0:
            raise ValueError("Latitude or longitude values out of range")
```

## Tarefa
Corrija o codigo acima para que ele seja importavel como modulo e executavel em PySpark no contexto descrito, respeitando todas as restricoes semanticas e tecnicas.
