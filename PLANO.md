# Argos Trade B3 · Plano

Versão 0.4 · 25/11/2026 · fase de simulação (robô simulado diário ativo, com porteiro de risco)

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

- **Quando:** uma vez por dia útil, depois do fechamento do pregão (~19h15 de Brasília).
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

---

## 10. Porteiro de risco (em vigor)

Toda ordem proposta pela estratégia passa pelo porteiro antes de ser executada. Os vetos ficam em `simulado/vetos.csv` e aparecem no Telegram e no monitor. Esta tabela substitui a da seção 6.

| Trava | Limite | Ação |
|---|---|---|
| Valor por ordem | 15% do patrimônio | Veta |
| Operações por dia | 8, fora da montagem e do rebalanceamento trimestral | Veta até o dia seguinte |
| Cotação que não é do dia | Ativo sem negócio no pregão | Não opera no ativo |
| Dado suspeito | Salto acima de 25% sem desdobramento | Mantém o último preço confiável e não opera; aceita o novo patamar depois de 3 pregões |
| Volatilidade extrema | Movimento acima de 10% no dia | Não opera no ativo naquele dia |
| Day trade | Compra e venda do mesmo ativo no dia | Veta |
| Vendas de ações no mês | R$ 19 mil (margem para a isenção de R$ 20 mil) | Veta vendas que não sejam saída por tese |
| Saldo impossível | Caixa ou quantidade negativa | Para tudo, não grava nada e avisa |

## 11. Avisos no Telegram

| Nível | Quando | O robô faz |
|---|---|---|
| 📊 Fechamento | Todo dia útil, ~19h15 | Operações com motivo, vetos, proventos e patrimônio contra as referências |
| 🗓️ Relatório semanal | Fechamento de sexta | Semana contra parada, CDI, Ibovespa e IFIX; operações, vetos e proventos |
| ℹ️ Informativo | Ação 35% abaixo do topo; patrimônio 15% abaixo do pico | Continua operando |
| ⏸️ Pausa no ativo | Cotação velha, dado suspeito, volatilidade extrema, veto do porteiro | Pula o ativo e retoma sozinho |
| 🛑 Parada técnica | O robô não conseguiu rodar (erro de dados ou de código) | Não altera a carteira; tenta no próximo dia útil |
| 🚨 Urgente | Caixa ou quantidade negativa | Para tudo e não grava |
| 📵 Sinal de vida | 21h15: o robô não rodou ou terminou com erro | Dispara o robô se ele não tinha rodado |

Comandos pelo Telegram (`/status`, `/pausar`) ficam para a fase real: exigem um servidor ligado o tempo todo.

## 12. Critérios para avançar e para desistir

**Simulado → real pequeno, só se tudo abaixo valer:**
- pelo menos **90 dias** de simulado (a partir de 25/11/2026) e **uma revisão trimestral** feita;
- nenhuma parada 🛑 ou 🚨 sem causa entendida e corrigida;
- o robô não está mais de **5 pontos** atrás da carteira parada;
- o resultado é coerente com o backtest (reforços e saídas acontecendo como previsto);
- existe um caminho de execução real definido (corretora e forma de enviar ordens).

**Quando desistir ou voltar para a prancheta:**
- depois de 6 meses, o robô perde para a carteira parada **e** para o CDI;
- alguma trava falha na prática;
- o projeto deixa de ser útil ou interessante para você.

## 13. Imposto e registro

- `simulado/ir_mensal.csv`: apuração de cada mês (vendas de ações, lucro, isenção, lucro em FIIs e IR devido).
- `simulado/operacoes.csv` e `simulado/proventos.csv`: base para a declaração anual, se um dia virar real.

---

## 14. Ajustes da auditoria de 25/11/2026 (em vigor; valem sobre as seções 9 e 10 onde houver diferença)

| Regra | Como ficou | Por quê |
|---|---|---|
| Saída por proventos | Compara os últimos 12 meses com a **média dos 3 anos anteriores** e só vende com o corte confirmado por **40 pregões seguidos**. FII com menos de 10 pagamentos em 12 meses não é medido | A regra antiga venderia PETR4 no segundo dia, por causa dos dividendos extraordinários do ano anterior; e o histórico de FIIs no Yahoo tem buracos |
| Reforço | No máximo **R$ 750 de custo por ativo**; não reforça ativo **mais de 40% abaixo** do preço médio nem ativo em observação | Evita colocar dinheiro sem limite numa ação que só cai |
| Saída das ações de valorização | 35% abaixo do topo **e** abaixo da média de 200 dias: **observação** (sem reforço e sem recompra). Depois de **60 pregões** assim, **vende metade**; repete a cada 60 pregões | Antes essas 10 ações não tinham regra de saída |
| Ativo sem cotação | O robô pula só aquele ativo e avisa; acima de 5 ativos sem cotação, não roda | Antes uma falha derrubava o dia inteiro |
| Horário | Robô às **19h15**; sinal de vida às **21h15** | A B3 fecha às 18h de novembro a março e a cotação tem atraso |
| Revisão trimestral | Tarefa agendada em 22/03, 22/05, 22/08 e 22/11: roda a skill `revisao-trimestral-b3` e grava em `revisoes/`. **Trocas de ativo só com o OK do usuário** | O robô não enxerga lucro, dívida nem notícias |

**Teste com dados de 2022 a 2026** (`backtest/ROBO_REGRAS.md`): V3 original R$ 14.449; V3b (proventos, teto e piso) R$ 14.390; V5 (V3b + realização com lucro mínimo + saída de valorização) R$ 13.918. A regra de venda de metade **não disparou nenhuma vez** nesse período, porque os ativos foram escolhidos sabendo que sobreviveram; o custo veio de não reforçar ações em observação. Ela entra como seguro, não como fonte de retorno. A variação "realização só com 25% de lucro" piorou o teste e **não foi adotada**.

**Limites conhecidos:** proventos entram pelo valor bruto (o JCP tem 17,5% de IR na fonte); a "realização em 2x o alvo" quase nunca dispara, porque o rebalanceamento trimestral age antes.

**Carteira em vigor desde a montagem (25/11/2026):** nos FIIs, **VISC11** entrou no lugar do XPML11, que cortou o rendimento de R$ 0,92 para R$ 0,80 em novembro e estava com P/VP perto de 1 (`ANALISE.md`, seção 9). A troca foi feita antes da primeira compra, então não houve venda nem imposto.

## 15. Relógio próprio (desde 27/11/2026)

O agendador do GitHub atrasou de 6 a 8 horas neste repositório: o fechamento de **26/11/2026 não foi registrado** e as cotações do dia não eram coletadas. Desde então:

- **Relógio** (`.github/workflows/mercado.yml` + `simulado/relogio.py`): um job fica rodando e faz uma passada a cada 10 minutos. Publica as cotações das 9h50 às 18h50, dispara o robô às 19h15 e o sinal de vida às 21h15, sempre em dias úteis. Perto do limite de 6 horas ele dispara o próprio sucessor. O agendamento do GitHub ficou só para religar a corrente se ela cair.
- **Robô:** processa o último pregão que o Yahoo mostra, não o dia do relógio. Uma execução atrasada (depois da meia-noite) ainda registra o fechamento certo; com o pregão em andamento ele não faz nada.
- **Sinal de vida:** olha o `estado.json`. Se o último dia útil fechado não estiver registrado, dispara o robô e avisa.
