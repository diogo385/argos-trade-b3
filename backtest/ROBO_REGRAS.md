# Backtest das regras do robô · 25/11/2026

Gerado pelo GitHub Actions (`backtest/robo_regras.py`).

- **Capital:** R$ 6.000 = R$ 5.000 nos 20 ativos de `ANALISE.md` (5% cada) + R$ 1.000 de reserva rendendo CDI.
- **Período:** 15/02/2022 a 24/11/2026 (1190 pregões). Valores líquidos de custos e IR.
- **Reforço:** quando o ativo cai 15% abaixo do preço médio (e de novo com mais 12%), compra mais uma parcela de ~R$ 250 com a reserva. Limites: 2 reforços por mês e nenhum ativo acima de 2x o peso-alvo. Não reforça se os proventos dos últimos 12 meses caíram mais de 10%.
- **Realização de lucro:** posição acima de 2x o peso-alvo volta para o alvo.
- **Saída por proventos:** ação de dividendos com proventos 30% menores em 12 meses, ou FII com rendimentos 25% menores, é vendida; volta quando os proventos se recuperam.
- **Stop (só V4):** ação de valorização que cai 35% do topo é vendida; pode voltar depois de 60 pregões.
- **Rebalanceamento a cada 3 meses** em todas as versões; FIIs só recebem compras. A reserva é recomposta para ~1/6 da carteira.

**Avisos dos dados:** XPML11: histórico do Yahoo com erro de base; trocado por VISC11.

## Resultado

| Versão | Valor final líquido | Retorno | Ao ano | Queda máxima | Operações | IR pago |
|---|---|---|---|---|---|---|
| V1 · base (sem swing, rebalanceia a cada 3 meses, reserva parada) | R$ 14.177 | +136% | +19,7% | −11% | 123 | R$ 0 |
| V2 · + reforço nas quedas com a reserva | R$ 14.544 | +142% | +20,4% | −11% | 153 | R$ 0 |
| V3 · + realização de lucro e saída por corte de proventos | R$ 14.352 | +139% | +20,1% | −10% | 160 | R$ 15 |
| V4 · + stop automático de 35% nas ações de valorização | R$ 13.129 | +119% | +17,8% | −10% | 156 | R$ 15 |
| 100% CDI (líquido de IR) | R$ 9.845 | +64% | +10,9% | −0% | 0 | R$ 0 |
| 100% Ibovespa (BOVA11) | R$ 8.742 | +46% | +8,2% | −21% | 0 | R$ 0 |
| 100% IFIX (XFIX11) | R$ 7.630 | +27% | +5,2% | −16% | 0 | R$ 0 |

## O que o robô fez

| Versão | Reforços | Realizações | Saídas por proventos | Stops | Voltas |
|---|---|---|---|---|---|
| V1 | 0 | 0 | 0 | 0 | 0 |
| V2 | 17 | 0 | 0 | 0 | 0 |
| V3 | 19 | 5 | 11 | 0 | 10 |
| V4 | 15 | 3 | 11 | 10 | 18 |

## Ano a ano (retorno bruto)

| Versão | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| V1 | +14% | +30% | +5% | +35% | +14% |
| V2 | +16% | +30% | +5% | +36% | +14% |
| V3 | +16% | +27% | +7% | +35% | +13% |
| V4 | +13% | +23% | +7% | +31% | +13% |
| 100% CDI (líquido de IR) | +9% | +11% | +9% | +12% | +11% |
| 100% Ibovespa (BOVA11) | −4% | +23% | −10% | +35% | +2% |
| 100% IFIX (XFIX11) | +5% | +17% | −6% | +20% | −8% |

## Limitações

- O robô só enxerga preço e proventos. Lucro, dívida, vacância e P/VP não entram no backtest (o Yahoo não traz); essas checagens ficam para a revisão trimestral.
- O histórico de rendimentos de FIIs no Yahoo é incompleto nos primeiros anos; a regra de proventos só age quando há 24 meses de dados.
- Período curto e ativos escolhidos hoje: viés de sobrevivência e de escolha.
