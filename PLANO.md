# Argos Trade B3 · Plano

Versão 0.2 · 25/11/2026 · fase de simulação (robô simulado diário ativo)

---

## 1. Objetivo e expectativa

Um robô que mantém carteiras na B3 nas proporções-alvo: compra o que caiu abaixo do alvo e vende o que subiu acima dele, usando **somente saldo próprio**.

**O que esperar, com sinceridade:**
- O resultado depende principalmente da bolsa. O robô não cria lucro do nada.
- No Brasil o caixa rende CDI. **Ganhar do CDI com risco de bolsa é difícil**, e é a primeira coisa que o backtest precisa mostrar.
- **Se o backtest mostrar que o robô não vence as referências, o projeto para ali**, sem ter custado dinheiro.

---

## 2. Regras que nunca mudam

1. **Só saldo próprio.** Sem margem, aluguel de ações, opções, termo, futuros ou qualquer dívida.
2. **Só mercado à vista** e **só ordens limitadas**.
3. **Sem day trade.** Nunca compra e vende o mesmo ativo no mesmo dia (IR de 20% e risco maior).
4. **O robô nunca saca** nem transfere dinheiro.
5. **Na dúvida, não opera.** Dado velho, pregão fechado ou saldo inconsistente fazem o robô pausar.
6. **Nenhuma trava pode ser afrouxada pelo próprio sistema.**

---

## 3. Carteiras simuladas

As duas rodam lado a lado, com a mesma divisão de 70% em renda variável e 30% em caixa, para a comparação ser justa.

| Carteira de ETFs | Alvo | | Carteira de ações | Alvo |
|---|---|---|---|---|
| BOVA11 (Ibovespa) | 35% | | ITUB4 · VALE3 · PETR4 · WEGE3 | 10% cada |
| IVVB11 (S&P 500 em reais) | 25% | | EGIE3 · ABEV3 · BBSE3 | 10% cada |
| GOLD11 (ouro) | 10% | | | |
| Caixa no CDI | 30% | | Caixa no CDI | 30% |

- **Mercado fracionário** (código com F, ex.: `WEGE3F`): permite comprar a partir de 1 ação, em vez de lotes de 100.
- **Caixa** representa Tesouro Selic ou CDB de liquidez diária, rendendo CDI.
- Configuração em `backtest/config.py`.

**Referências que o robô precisa vencer:** a mesma carteira sem rebalancear, rebalancear por calendário (mensal, trimestral, anual), 100% Ibovespa e 100% CDI.

---

## 4. Estratégia

- **Quando:** uma vez por dia útil, depois do fechamento do pregão (~18h30 de Brasília).
- **Regra:** se um ativo se afastar do alvo mais que uma fração do próprio alvo (testando 20% e 35%), volta ao alvo. Ex.: alvo 10% com faixa de 20% → opera abaixo de 8% ou acima de 12%.
- Ignora ajustes menores que R$ 50. Primeiro vende, depois compra.
- **Calendário da B3:** não opera em fins de semana e feriados.

---

## 5. Imposto de renda (simulado no backtest)

| Situação | Regra |
|---|---|
| Ações, vendas até R$ 20 mil no mês | **Isento** |
| Ações, vendas acima de R$ 20 mil no mês | 15% sobre o lucro |
| ETFs | 15% sobre o lucro, **sem isenção** |
| Prejuízo | Compensado nos meses seguintes |
| Caixa (renda fixa longa) | 15% sobre o rendimento |
| Dividendos | Isentos (já reinvestidos no preço ajustado) |

Com capital pequeno, a carteira de ações tende a ficar sempre na isenção. Essa é a vantagem que o backtest vai medir.

---

## 6. Travas (para o robô simulado diário)

| Trava | Limite | Ação |
|---|---|---|
| Valor por ordem | No máximo 15% do patrimônio | Veta |
| Pregão fechado ou dado velho | Cotação que não é do último pregão | Não opera |
| Volatilidade extrema | Ativo com movimento acima de 10% no dia | Não opera nele naquele dia |
| Vendas de ações no mês | Perto de R$ 20 mil | Adia vendas para não perder a isenção |
| Saldo | Nunca vende o que não tem nem compra sem caixa | Veta |

---

## 7. Fases

| Fase | O que | Situação |
|---|---|---|
| 1 | **Backtest** das carteiras e das regras do robô, com custos, CDI e IR | Concluído (`backtest/`) |
| 2 | **Robô simulado** diário no GitHub Actions (R$ 6.000, regras V3), com avisos no Telegram | **Ativo desde 25/11/2026** (`simulado/`). Monitor web a fazer. |
| 3 | Real, com capital pequeno | Só depois de meses de simulado. Exige corretora com automação (ex.: MetaTrader 5, que só roda no Windows). A decidir. |

---

## 8. Dados (custo zero)

| Dado | Fonte |
|---|---|
| Cotações diárias ajustadas por proventos | Yahoo Finance (tickers com `.SA`) |
| CDI diário | Banco Central, série SGS 12 |
| Execução | GitHub Actions, que tem acesso a esses sites |

---

## 9. Carteira e regras em vigor no robô simulado (desde 25/11/2026)

Carteira de `ANALISE.md` e regras da V3 de `backtest/ROBO_REGRAS.md`, com R$ 6.000 = R$ 5.000 em 20 ativos (R$ 250 cada) + R$ 1.000 de reserva no CDI.
Esta seção substitui as carteiras de ETFs e de ações da seção 3, que ficaram só como estudo.

| Regra | Como funciona |
|---|---|
| Reforço | Ativo 15% abaixo do preço médio → compra mais R$ 250 com a reserva; 2º reforço com mais ~12% de queda. Até 2 por mês; nenhum ativo acima de 2x o alvo; só se os proventos não caíram mais de 10% |
| Realização de lucro | Posição acima de 2x o alvo volta para o alvo |
| Saída por tese | Ação de dividendos com proventos −30% em 12 meses, ou FII com −25%: vende tudo; volta quando os proventos se recuperam |
| Rebalanceamento | Primeiro pregão de cada trimestre; FIIs só recebem compras (venda de FII paga 20%) |
| Queda forte | Ação de valorização 35% abaixo do topo: **só alerta**, não vende (o stop automático piorou o backtest) |
| Revisão trimestral | Depois de cada temporada de resultados, revisão da tese de cada ativo com o Claude (lucro, dívida, vacância, P/VP) |
