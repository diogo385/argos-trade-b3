# Backtest das regras do robô · 25/11/2026

Gerado pelo GitHub Actions (`backtest/robo_regras.py`).

- **Capital:** R$ 6.000 = R$ 5.000 nos 20 ativos de `ANALISE.md` (5% cada) + R$ 1.000 de reserva rendendo CDI.
- **Período:** 15/02/2022 a 25/11/2026 (1191 pregões). Valores líquidos de custos e IR.
- **V3 (original):** reforço a 15% abaixo do preço médio; realização acima de 2x o alvo; saída quando os proventos de 12 meses caem 30% (ações) ou 25% (FIIs) contra os 12 meses anteriores.
- **V3b (auditoria):** proventos comparados com a média dos 3 anos anteriores e venda só com o corte confirmado em 2 meses seguidos; FII com menos de 10 pagamentos em 12 meses não é medido; no máximo R$ 750 de custo por ativo; não reforça ativo que caiu mais de 40% do preço médio.
- **V3c:** V3b + a realização em 2x o alvo só acontece com lucro de 25% sobre o preço médio, e o reforço pode levar a posição até 3x o alvo (antes o reforço era desfeito logo em seguida).
- **V5:** V3c + ação de valorização 35% abaixo do topo e abaixo da média de 200 dias fica em observação (sem reforço e sem recompra); depois de 60 pregões assim, vende metade.
- **Rebalanceamento a cada 3 meses** em todas as versões; FIIs só recebem compras.

**Avisos dos dados:** XPML11: histórico do Yahoo com erro de base; trocado por VISC11.

## Resultado

| Versão | Valor final líquido | Retorno | Ao ano | Queda máxima | Operações | IR pago |
|---|---|---|---|---|---|---|
| V1 · base (sem swing, rebalanceia a cada 3 meses, reserva parada) | R$ 14.283 | +138% | +19,9% | −11% | 123 | R$ 0 |
| V3 · regras originais (reforço, realização em 2x, saída por proventos contra o ano anterior) | R$ 14.449 | +141% | +20,2% | −10% | 160 | R$ 15 |
| V3b · auditoria: proventos contra a média de 3 anos com persistência, teto de aporte e piso de queda | R$ 14.390 | +140% | +20,1% | −10% | 149 | R$ 0 |
| V3c · V3b + realização só com lucro de 25% (evita desfazer o reforço) | R$ 14.163 | +136% | +19,7% | −10% | 140 | R$ 0 |
| V5 · V3c + saída das ações de valorização (observação e venda de metade) | R$ 13.918 | +132% | +19,3% | −10% | 131 | R$ 0 |
| 100% CDI (líquido de IR) | R$ 9.849 | +64% | +10,9% | −0% | 0 | R$ 0 |
| 100% Ibovespa (BOVA11) | R$ 8.887 | +48% | +8,6% | −21% | 0 | R$ 0 |
| 100% IFIX (XFIX11) | R$ 7.754 | +29% | +5,5% | −16% | 0 | R$ 0 |

## O que o robô fez

| Versão | Reforços | Realizações | Saídas por proventos | Vendas de metade | Voltas |
|---|---|---|---|---|---|
| V1 | 0 | 0 | 0 | 0 | 0 |
| V3 | 19 | 5 | 11 | 0 | 10 |
| V3b | 17 | 5 | 6 | 0 | 4 |
| V3c | 15 | 0 | 6 | 0 | 4 |
| V5 | 13 | 0 | 6 | 0 | 4 |

## Ano a ano (retorno bruto)

| Versão | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| V1 | +14% | +30% | +5% | +35% | +15% |
| V3 | +16% | +27% | +7% | +35% | +14% |
| V3b | +16% | +29% | +7% | +32% | +14% |
| V3c | +15% | +29% | +7% | +32% | +14% |
| V5 | +14% | +29% | +7% | +31% | +14% |
| 100% CDI (líquido de IR) | +9% | +11% | +9% | +12% | +11% |
| 100% Ibovespa (BOVA11) | −4% | +23% | −10% | +35% | +4% |
| 100% IFIX (XFIX11) | +5% | +17% | −6% | +20% | −7% |

## Limitações

- O robô só enxerga preço e proventos. Lucro, dívida, vacância e P/VP não entram no backtest (o Yahoo não traz); essas checagens ficam para a revisão trimestral.
- O histórico de rendimentos de FIIs no Yahoo é incompleto nos primeiros anos; a regra de proventos só age quando há 24 meses de dados.
- Período curto e ativos escolhidos hoje: viés de sobrevivência e de escolha.
