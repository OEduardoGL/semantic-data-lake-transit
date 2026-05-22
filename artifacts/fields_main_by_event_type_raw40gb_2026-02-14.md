# Campos principais por tipo de evento (raw 40GB)

Campos-base comuns (na maioria dos tipos):
- `timestamp`
- `avlHeader.tipoMensagem`
- `avlHeader.validador.idEmpresa`
- `avlHeader.validador.codLinha`
- `avlHeader.validador.codVeiculo`
- `avlHeader.gps[]`
- `avlHeader.jornada.codOperador`
- `avlHeader.viagem.sentido`

Tipos prioritarios para Silverizacao:
- `AVL_EVT_POSICIONAMENTO`: foco em `avlHeader.gps[]` (lat/lon/velocidade/direcao/satelites/odometro)
- `AVL_EVT_ENTRADA_SAIDA_PONTO`: foco em `avlEventoEntradaSaidaPonto` (`idPonto`, `eventoPonto`) + GPS
- `AVL_EVT_RECEBIMENTO_TABELA_PARCIAL`: foco em `avlEventoTabelaParcial` (`tabelaParcial`, sequenciais)
- `AVL_EVT_PASSAGEM_CARTAO`: foco em `avlEventoPassagemCartao` (campos de validacao/tarifa)
- `AVL_EVT_ABERTURA_FECHAMENTO_VIAGEM`: foco em `avlEventoAberturaFechamentoViagem` (estado da viagem)

Arquivo complementar com percentuais por tipo: `profile_by_event_type_raw40gb_2026-02-14.csv`
