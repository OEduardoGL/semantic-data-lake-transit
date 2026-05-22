# Regras Metodologicas da Rodada 2 de ML

## Objetivo
Definir regras formais para a rodada 2 de ML, respondendo aos problemas observados na rodada 1:
- `MAPE` inadequado para o target;
- underfitting da OpenAI;
- suspeita de vazamento/trivializacao na Llama;
- ambiguidade sobre o que exatamente o modelo deve prever.

Estas regras devem orientar:
- o `Prompt 2 v2`;
- a geracao de codigo pelas LLMs;
- a execucao e comparacao da rodada 2;
- a comparacao tecnica da rodada 2.

## Metricas oficiais da rodada 2

### Metricas principais
- `MAE`
  - metrica principal de erro absoluto medio.
  - e a mais interpretavel para o problema, porque o target esta em minutos.

- `RMSE`
  - metrica complementar para penalizar erros grandes.
  - ajuda a mostrar se o modelo erra pouco na media, mas falha muito em alguns casos extremos.

- `WAPE`
  - metrica percentual principal da rodada 2.
  - definicao:
    - `WAPE = sum(|y_true - y_pred|) / sum(|y_true|)`
  - vantagem:
    - e muito mais estavel do que `MAPE` quando existem muitos zeros no target.

### Metrica opcional
- `MedAE` (`Median Absolute Error`)
  - metrica robusta a outliers.
  - pode ser usada como apoio, mas nao precisa ser central na comparacao principal.

### Politica sobre `MAPE`
- `MAPE` deixa de ser metrica principal na rodada 2.
- ele pode aparecer apenas como observacao secundaria ou apendice, com aviso explicito de baixa interpretabilidade.
- a comparacao principal passa a usar:
  - `MAE`
  - `RMSE`
  - `WAPE`

## Tratamento explicito para zeros no target
- diagnostico da rodada 1:
  - cerca de `57.6%` do target no teste e exatamente zero;
  - cerca de `79.2%` a `79.4%` do target no teste esta em ate `0.1` minuto.
- consequencia:
  - metricas baseadas em divisao por `y_true` ficam instaveis.

### Regra oficial
- a rodada 2 deve tratar zeros como parte natural do problema, nao como excecao.
- comparacoes percentuais devem usar `WAPE`, nao `MAPE`.
- se alguma variante de percentual por observacao for reportada, ela deve:
  - excluir explicitamente `y_true = 0`; ou
  - ser apresentada apenas como analise secundaria, nunca como metrica principal.

## Horizonte preditivo oficial
- a tarefa da rodada 2 deixa de ser uma estimacao ambigua da propria linha corrente.
- definicao oficial:
  - prever `atraso_aproximado_min` da **proxima janela disponivel** para o mesmo par:
    - `cod_linha`
    - `cod_veiculo`

### Interpretacao
- cada linha da base de treino representa o estado atual ou historico recente de uma linha/veiculo em uma janela de 5 minutos.
- o target supervisionado deve ser deslocado para frente:
  - `target_t_plus_1 = atraso_aproximado_min` da proxima `janela_5min` disponivel para o mesmo `cod_linha + cod_veiculo`.

### Motivacao
- isso reduz a ambiguidade metodologica da rodada 1.
- isso obriga o modelo a usar informacao disponivel no presente/passado para prever o futuro imediato.
- isso torna a avaliacao mais coerente com um uso operacional real.

## Politica de features: permitidas e proibidas

### Features permitidas (linha atual ou historico passado)
- identificacao e contexto:
  - `cod_linha`
  - `cod_veiculo`
  - `id_empresa`
  - `viagem_sentido`
- tempo:
  - `hour(janela_5min)`
  - `minute(janela_5min)` se mantiver utilidade
  - `day_of_week(event_dt)`
  - indicadores simples como `is_weekend`
- operacionais e espaciais da janela atual:
  - `velocidade_media`
  - `gps_invalid_pct`
  - `qtd_eventos_gps`
  - `qtd_eventos_stop`
  - `max_satelites`
  - `latitude_media`
  - `longitude_media`
  - `headway_referencia_min`
- derivadas historicas criadas por lag/rolling:
  - `lag_1_velocidade_media`
  - `lag_1_gps_invalid_pct`
  - `lag_1_qtd_eventos_gps`
  - `lag_1_qtd_eventos_stop`
  - `lag_1_headway_observado_min`
  - `lag_1_atraso_aproximado_min`
  - medias moveis de janelas anteriores por `cod_linha` ou `cod_linha + cod_veiculo`

### Features proibidas na mesma linha do target
- `atraso_aproximado_min` contemporaneo da propria linha-alvo
- `headway_observado_min` contemporaneo da propria linha-alvo
- qualquer coluna derivada diretamente de `atraso_aproximado_min` ou `headway_observado_min` na mesma linha do target
- qualquer agregado calculado usando informacao do futuro ou do conjunto de teste
- qualquer encoder, imputador ou normalizador ajustado no dataframe completo antes do split temporal

### Regra de interpretabilidade
- se houver necessidade de codificacao de categorias para treino:
  - a codificacao nao deve sobrescrever os IDs originais usados nos artefatos finais;
  - `cod_linha` e `cod_veiculo` originais devem permanecer preservados em `predictions_df` e agregados.

## Politica de split e ajuste de pre-processamento
- split obrigatoriamente temporal.
- nenhuma etapa de preprocessamento pode ser ajustada no dataframe completo antes de separar treino/validacao/teste.
- baseline, encoders, imputadores e quaisquer agregados historicos de apoio devem ser ajustados somente no treino.

## Consequencia pratica para o Prompt 2 v2
O `Prompt 2 v2` deve:
- pedir explicitamente previsao da proxima janela;
- proibir uso contemporaneo de colunas que praticamente definem o target;
- substituir `MAPE` por `WAPE` como metrica percentual principal;
- incentivar modelos mais fortes que regressao linear simples, mas ainda reproduziveis e explicaveis;
- preservar IDs originais nos artefatos de saida.
