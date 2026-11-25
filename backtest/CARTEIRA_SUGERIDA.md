# Backtest da carteira sugerida · 25/11/2026

Gerado pelo GitHub Actions (`backtest/carteira_sugerida.py`). Carteira de `ANALISE.md`.

- **Capital:** R$ 5.000, 5% por ativo (cerca de R$ 250), ações inteiras no fracionário.
- **Período:** 15/02/2022 a 24/11/2026 (1190 pregões). Começa quando todos os 20 ativos já têm 200 pregões de histórico, para o swing ter a média de 200 dias.
- **Custos:** 0,13% por operação. Caixa no CDI com 15% de IR. IR de 15% nas ações (isento até R$ 20 mil de vendas no mês) e de 20% nos FIIs.
- **Valores líquidos:** no fim, tudo é vendido e o IR devido é descontado.
- **Swing:** cada ação de valorização sai quando fecha 3% abaixo da média de 200 dias e volta quando fecha 3% acima; fora, os R$ dela rendem CDI. Dividendos e ações em swing são rebalanceados a cada 3 meses; FIIs só recebem compras.

**Avisos dos dados:** XPML11: histórico do Yahoo com erro de base; trocado por VISC11 na simulação.

## Resultado

| Estratégia | Valor final líquido | Retorno | Ao ano | Queda máxima | Operações | IR pago | Custos |
|---|---|---|---|---|---|---|---|
| **Carteira sugerida, com swing** (proposta) | R$ 10.859 | +117% | +17,6% | −12% | 202 | R$ 0 | R$ 72 |
| Mesma carteira, sem swing (rebalanceia a cada 3 meses) | R$ 12.511 | +150% | +21,2% | −13% | 126 | R$ 0 | R$ 17 |
| Mesma carteira parada (compra e nunca mexe) | R$ 12.356 | +147% | +20,9% | −14% | 0 | R$ 0 | R$ 6 |
| 100% CDI (líquido de IR) | R$ 8.204 | +64% | +10,9% | −0% | 0 | R$ 0 | R$ 0 |
| 100% Ibovespa (BOVA11) | R$ 7.285 | +46% | +8,2% | −21% | 0 | R$ 0 | R$ 6 |
| 100% IFIX (XFIX11) | R$ 6.356 | +27% | +5,2% | −16% | 0 | R$ 0 | R$ 6 |

## Ano a ano (retorno bruto de cada ano)

| Estratégia | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| **Carteira sugerida, com swing** (proposta) | +11% | +31% | +6% | +34% | +7% |
| Mesma carteira, sem swing (rebalanceia a cada 3 meses) | +14% | +34% | +5% | +39% | +14% |
| Mesma carteira parada (compra e nunca mexe) | +13% | +33% | +6% | +42% | +11% |
| 100% CDI (líquido de IR) | +9% | +11% | +9% | +12% | +11% |
| 100% Ibovespa (BOVA11) | −4% | +23% | −10% | +35% | +2% |
| 100% IFIX (XFIX11) | +5% | +17% | −6% | +20% | −8% |

Maior volume de vendas de ações num mês (swing): R$ 3.401, bem abaixo do limite de isenção de R$ 20 mil.

## Limitações

- Período curto (o histórico de CXSE3 e CURY3 começa em 2020–2021) e marcado por Selic alta.
- Ativos escolhidos em novembro/2026, com o passado já conhecido: há viés de sobrevivência e de escolha.
- Preço ajustado do Yahoo: proventos reinvestidos no próprio ativo; o IR de 17,5% sobre JCP não foi descontado.
- Com R$ 250 por ativo, a compra em ações inteiras deixa sobras em caixa (rendendo CDI).
