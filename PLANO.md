# Argos Trade B3 · Plano

Versão 0.1 · 25/11/2026 · fase de simulação

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
| 1 | **Backtest** das duas carteiras (2014–2026), com custos, CDI e IR | Em andamento |
| 2 | **Robô simulado** diário no GitHub Actions, com avisos no Telegram e monitor web | Depois do backtest, se valer a pena |
| 3 | Real, com capital pequeno | Só depois de meses de simulado. Exige corretora com automação (ex.: MetaTrader 5, que só roda no Windows). A decidir. |

---

## 8. Dados (custo zero)

| Dado | Fonte |
|---|---|
| Cotações diárias ajustadas por proventos | Yahoo Finance (tickers com `.SA`) |
| CDI diário | Banco Central, série SGS 12 |
| Execução | GitHub Actions, que tem acesso a esses sites |
