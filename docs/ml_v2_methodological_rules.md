# Regras Metodológicas da Rodada 2 de ML

## Objetivo
Definir regras formais para a rodada 2 de ML, respondendo aos problemas observados na rodada 1:
- `MAPE` inadequado para o target;
- underfitting da OpenAI;
- suspeita de vazamento/trivialização no pipeline Llama;
- ambiguidade sobre o que exatamente o modelo deve prever.

Estas regras devem orientar:
- o `Prompt 2 v2`;
- a geração de código pelas LLMs;
- a execução e comparação da rodada 2;
- a comparação técnica da rodada 2.

## Métricas adotadas na rodada 2

### Métricas principais
- `MAE`
  - métrica principal de erro absoluto médio.
  - é a mais interpretável para o problema, porque o target está em minutos.

- `RMSE`
  - métrica complementar para penalizar erros grandes.
  - ajuda a mostrar se o modelo erra pouco na média, mas falha muito em alguns casos extremos.

- `WAPE`
  - métrica percentual principal da rodada 2.
  - definição:
    - `WAPE = sum(|y_true - y_pred|) / sum(|y_true|)`
  - vantagem:
    - é muito mais estável do que `MAPE` quando existem muitos zeros no target.

### Métrica opcional
- `MedAE` (`Median Absolute Error`)
  - métrica robusta a outliers.
  - pode ser usada como apoio, mas não precisa ser central na comparação principal.

### Política sobre `MAPE`
- `MAPE` não é adotado como métrica principal na rodada 2.
- ele pode aparecer apenas como observação secundária ou apêndice, com aviso explícito de baixa interpretabilidade.
- a comparação principal passa a usar:
  - `MAE`
  - `RMSE`
  - `WAPE`

## Tratamento explícito para zeros no target
- diagnóstico da rodada 1:
  - cerca de `57.6%` do target no teste é exatamente zero;
  - cerca de `79.2%` a `79.4%` do target no teste está em até `0.1` minuto.
- consequência:
  - métricas baseadas em divisão por `y_true` ficam instáveis.

### Regra adotada
- a rodada 2 deve tratar zeros como parte natural do problema, não como exceção.
- comparações percentuais devem usar `WAPE`, não `MAPE`.
- se alguma variante de percentual por observação for reportada, ela deve:
  - excluir explicitamente `y_true = 0`; ou
  - ser apresentada apenas como análise secundária, nunca como métrica principal.

## Horizonte preditivo adotado
- a tarefa da rodada 2 substitui a estimação ambígua da própria linha corrente por um horizonte preditivo explícito.
- definição adotada:
  - prever `atraso_aproximado_min` da **próxima janela disponível** para o mesmo par:
    - `cod_linha`
    - `cod_veiculo`

### Interpretação
- cada linha da base de treino representa o estado atual ou histórico recente de uma linha/veículo em uma janela de 5 minutos.
- o target supervisionado deve ser deslocado para frente:
  - `target_t_plus_1 = atraso_aproximado_min` da próxima `janela_5min` disponível para o mesmo `cod_linha + cod_veiculo`.

### Motivação
- reduz a ambiguidade metodológica da rodada 1.
- exige que o modelo use informação disponível no presente/passado para prever o futuro imediato.
- torna a avaliação mais coerente com um uso operacional real.

## Política de features: permitidas e proibidas

### Features permitidas (linha atual ou histórico passado)
- identificação e contexto:
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
- derivadas históricas criadas por lag/rolling:
  - `lag_1_velocidade_media`
  - `lag_1_gps_invalid_pct`
  - `lag_1_qtd_eventos_gps`
  - `lag_1_qtd_eventos_stop`
  - `lag_1_headway_observado_min`
  - `lag_1_atraso_aproximado_min`
  - médias móveis de janelas anteriores por `cod_linha` ou `cod_linha + cod_veiculo`

### Features proibidas na mesma linha do target
- `atraso_aproximado_min` contemporâneo da própria linha-alvo
- `headway_observado_min` contemporâneo da própria linha-alvo
- qualquer coluna derivada diretamente de `atraso_aproximado_min` ou `headway_observado_min` na mesma linha do target
- qualquer agregado calculado usando informação do futuro ou do conjunto de teste
- qualquer encoder, imputador ou normalizador ajustado no dataframe completo antes do split temporal

### Regra de interpretabilidade
- se houver necessidade de codificação de categorias para treino:
  - a codificação não deve sobrescrever os IDs originais usados nos artefatos finais;
  - `cod_linha` e `cod_veiculo` originais devem permanecer preservados em `predictions_df` e agregados.

## Política de split e ajuste de pré-processamento
- split obrigatoriamente temporal.
- nenhuma etapa de pré-processamento pode ser ajustada no dataframe completo antes de separar treino/validação/teste.
- baseline, encoders, imputadores e quaisquer agregados históricos de apoio devem ser ajustados somente no treino.

## Consequência prática para o Prompt 2 v2
O `Prompt 2 v2` deve:
- pedir explicitamente previsão da próxima janela;
- proibir uso contemporâneo de colunas que praticamente definem o target;
- substituir `MAPE` por `WAPE` como métrica percentual principal;
- incentivar modelos mais fortes que regressão linear simples, mas ainda reproduzíveis e explicáveis;
- preservar IDs originais nos artefatos de saída.
