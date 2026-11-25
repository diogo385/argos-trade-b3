# Análise e sugestão de carteira · 25/11/2026

Carteira **simulada e educacional**: 10 ações para swing trade (valorização), 5 ações de dividendos e 5 FIIs.
Não é recomendação de investimento. Antes de qualquer uso real, confira os números no RI de cada empresa, no relatório gerencial de cada fundo e na B3.

Base da análise:
- **Triagem com números** (`backtest/TRIAGEM.md`): 58 ações e 29 FIIs, com dados diários desde 2014.
- **Pesquisa web de novembro/2026**: resultados do 3T26, carteiras recomendadas das corretoras e mudanças de imposto.
  A rede bloqueou a abertura dos sites completos; os múltiplos (P/L, P/VP) vêm de resumos de busca e estão marcados como aproximados.

---

## 1. Cenário

| Item | Situação |
|---|---|
| Selic | **13,75%**. O Copom parou os cortes em 04/11/2026; o Focus vê 13,75% no fim de 2026. Próxima reunião: 8 e 9/12. |
| Inflação | Expectativa de 5,2% a 5,6% para 2026, acima do teto da meta (4,5%) |
| Ibovespa | ~164 mil pontos em 24/11. Caiu ~10% em outubro (maior queda mensal desde 2022), −12% no 4º trimestre, +1,8% em 2026 |
| IFIX | ~3.440 pontos, mínima do ano: −4,5% em novembro e −8,5% em 2026 |
| Política | Lula reeleito em 25/10. Mercado preocupado com o lado fiscal. |

**O que isso significa:**
- O **caixa rende ~11,5% ao ano líquido** (CDI menos IR). É a régua que toda a carteira precisa vencer.
- Bolsa e FIIs estão **descontados**: a maioria dos FIIs negocia com P/VP entre 0,75 e 0,90. Isso é oportunidade, mas o motivo é real: juros altos por mais tempo e risco fiscal.
- As casas ficaram mais defensivas. Preferem commodities, bancos, seguros e elétricas, cortaram varejo e, nos FIIs, foram para papel atrelado ao CDI.

## 2. Imposto em 2026 (pessoa física)

| Operação | Regra |
|---|---|
| Ações, swing trade | **Isento** com vendas até R$ 20 mil no mês; acima disso, 15% sobre o lucro |
| Day trade | 20%, sem isenção |
| Dividendos de ações | Isentos. Só há retenção de 10% acima de R$ 50 mil por mês da mesma empresa (Lei 15.270/2025); irrelevante aqui |
| JCP | **17,5%** retidos na fonte desde 01/01/2026 (eram 15%) |
| Rendimentos de FII | **Isentos**. A MP 1303 caducou e a reforma da renda manteve a isenção |
| Venda de cotas de FII | 20% sobre o lucro, sem isenção |

**Consequência:** para renda, empresas que pagam mais em **dividendo** do que em JCP e **FIIs** são mais eficientes. FIIs devem ser segurados, não girados, porque a venda paga 20%.

---

## 3. O que a triagem mostrou sobre swing trade

Testei duas regras clássicas em 58 ações nos últimos 10 anos, com custos:
- **IFR2:** compra na queda forte de curto prazo, desde que a ação esteja acima da média de 200 dias.
- **Tendência:** fica comprado só acima da média de 200 dias.

Resultado, com sinceridade:
- **Nenhuma das duas regras ganhou de comprar e segurar na maioria das ações.**
  - O IFR2 acerta 55% a 75% das operações, mas fica comprado só ~10% do tempo e ganha pouco por operação.
  - A regra de tendência reduz a queda máxima em várias ações, mas costuma render menos.
- O IFR2 funcionou melhor em **CURY3, BPAC11, AXIA3, CXSE3, VIVT3 e TOTS3**. Foi ruim em PETR4, PRIO3, WEGE3 e GGBR4.
- A tendência ganhou de comprar e segurar com queda menor em **EMBJ3** (24,5% contra 23,6% ao ano) e chegou perto em **CXSE3, SBSP3 e PRIO3**.

**Conclusão:**
- O swing trade não deve depender de uma regra mágica.
- A proposta é **swing como gestão de posição**: a ação fica na carteira e o robô aumenta ou reduz a exposição conforme a tendência e o recuo de curto prazo.
- Quando o robô está fora de uma ação, o dinheiro **fica no CDI**, e não parado como no teste acima.
- O próximo backtest vai medir isso nas ações escolhidas.

---

## 4. Ações de valorização (swing trade) · 10

Critérios:
- Liquidez acima de R$ 120 milhões por dia.
- Um setor por ação.
- Resultado do 3T26 neutro ou positivo.
- Recomendações das casas.
- Comportamento nas regras de swing.

| # | Ação | Setor | Por que entra | Risco principal |
|---|---|---|---|---|
| 1 | **BPAC11** | Banco de investimento | Lucro recorde no 3T26 (R$ 5,3 bi, +17%), ROAE 26%, recompra de R$ 2 bi. IFR2 positivo, acerto de 70%. 5 anos: +21% a.a. | Ação mais volátil do setor (beta 1,6) |
| 2 | **ITUB4** | Banco | ROE 23,6%, maior peso da Genial. Queda máxima em 5 anos de só −24% | Tom cauteloso para 2027 |
| 3 | **EMBJ3** | Aeronáutica | Melhor 3º trimestre de entregas da história; elevou o guidance. Melhor ação para seguir tendência (23% acima da MM200). Beta baixo (0,3), descorrelacionada | Ação já subiu muito (+39% a.a. em 5 anos); depende do dólar |
| 4 | **PRIO3** | Petróleo | Produção recorde (~196 mil boe/d), +55% em 12 meses. Tendência funcionou (30% a.a.) | Preço do petróleo; IFR2 ruim, então só seguir tendência |
| 5 | **SBSP3** | Saneamento | Entre as mais recomendadas. EBITDA +14%. Tendência com queda menor que comprar e segurar. 5 anos: +37% a.a. | Lucro do 3T26 caiu por efeito financeiro; risco regulatório |
| 6 | **WEGE3** | Bens de capital | Qualidade histórica (25% a.a. em 10 anos). Volta a ficar acima da MM200 | 3T26 fraco (margem em queda); preço exigente |
| 7 | **CURY3** | Construção (baixa renda) | Lucro recorde (+23%). **Melhor ação no IFR2** (acerto de 78%). Hoje está 18% abaixo da MM200: setup de recuo | Juros altos por mais tempo; queda recente de −23% |
| 8 | **GGBR4** | Siderurgia | Lucro +40% puxado pelos EUA; +41% em 12 meses, acima da MM200. Diversifica em dólar | Ciclo do aço; IFR2 ruim, então só seguir tendência |
| 9 | **AXIA3** | Energia elétrica (ex-Eletrobras) | Até R$ 4 bi aprovados para acionistas; Genial recomenda compra. IFR2 positivo, acerto de 67%. Alta liquidez | Está 17% abaixo da MM200: **entra só quando a tendência virar** |
| 10 | **FLRY3** | Saúde (diagnósticos) | +60% em 12 meses, 25% acima da MM200; uma das small caps mais indicadas | Liquidez menor (R$ 125 mi por dia); setor teve 5 anos ruins |

**Ficaram de fora e por quê:**
- **VALE3:** lucro −54% e tendência de baixa.
- **LREN3:** abandonou o guidance.
- **BBAS3:** ROE de 2,8% e dividendo cortado.
- **RENT3 e MOVI3:** tendência de queda forte.
- **MBRF3:** alavancagem de 3,45 vezes.
- **NATU3 e BRAV3:** quedas de 76% a 88%.
- **ENEV3 e VBBR3:** boas, mas mantive um setor por ação. São as primeiras reservas.

## 5. Ações de dividendos · 5

Critérios:
- DY de 12 meses **e** média de 5 anos.
- Baixa volatilidade.
- Lucro estável.
- Setores diferentes entre si e das ações de valorização.

| # | Ação | Setor | DY 12m · média 5a | Volatilidade · queda máx. 5a | Por que entra | Risco |
|---|---|---|---|---|---|---|
| 1 | **PETR4** | Petróleo | 9,0% · 25% | 31% · −39% | A mais recomendada do mês (8 de 10 carteiras); 5 anos: +36% a.a. | Interferência política; dividendo do 3T26 veio abaixo do esperado |
| 2 | **TAEE11** | Transmissão de energia | 7,9% · 10,3% | 25% · −20% | Receita regulada e previsível; lucro +12,5% | Pouco crescimento |
| 3 | **CPLE3** | Energia elétrica | 7,1% · 6,7% | 29% · −23% | Copel no Novo Mercado desde dez/2025; 5 anos: +29% a.a. | Pagamento parte em JCP (17,5%) |
| 4 | **CXSE3** | Seguros | 6,9% · 7,2% | 24% · −27% | XP dobrou o peso; P/L ~10; IFR2 e tendência funcionaram | Depende da Caixa |
| 5 | **VIVT3** | Telecom | 7,3% · 6,1% | 27% · −31% | Fluxo de caixa estável, beta 0,6; IFR2 positivo | Setor maduro |

**Reservas:**
- **BBSE3:** maior DY, 12,7%, mas a Brasilseg projeta prêmios −11% a −15% e há fragilidade no BB.
- **ITSA4:** DY de 8,7%; ficou de fora para não concentrar demais no Itaú.
- **ISAE4 e CMIG4.**

## 6. FIIs · 5

Critérios:
- Um segmento por fundo.
- Liquidez.
- P/VP abaixo de 1 no tijolo.
- Rendimento estável nos últimos 12 meses.
- Baixa vacância.
- Recomendação das casas.

| # | FII | Segmento | P/VP | DY 12m | Volatilidade · queda máx. 5a | Por que entra | Risco |
|---|---|---|---|---|---|---|---|
| 1 | **KNCR11** | Papel CDI (high grade) | ~1,00 | 13,4% | **8% · −7%** | O mais recomendado de novembro; com Selic alta é quase "CDI isento"; o mais estável da lista | Rende menos quando a Selic cair |
| 2 | **BTLG11** | Logística | ~0,89 | 10,2% | 9% · −14% | Vacância de 1,1%; comprou galpões AAA alugados a Mercado Livre e Amazon (R$ 965 mi) | Emissões frequentes diluem quem não acompanha |
| 3 | **KNRI11** | Híbrido (galpões e escritórios) | ~0,86 | 9,4% | 18% · −20% | Diversificado, vacância física de 1,9%; rendimentos +11% em 12 meses | Parte em lajes corporativas |
| 4 | **XPML11** | Shoppings | ~0,75 a 0,89 | ~13% | — (dado do Yahoo com erro) | Maior FII de shoppings; escolha do Santander | Consumo desacelerando. **Alternativa: VISC11** (DY 10,6%, rendimentos +12%) |
| 5 | **MCCI11** | Papel (CDI + IPCA) | ~0,93 | 13,6% | 13% · −18% | BTG e XP aumentaram o peso; +16% em 12 meses | Crédito imobiliário; inadimplência não confirmada |

**Evitados:**
- **PVBI11:** vacância de 20% e processo na CVM.
- **TRXF11:** −39% em 12 meses e alavancagem de 27,5%.
- **TGAR11 e VGHF11:** descontos extremos, DY inflado e preço caindo.
- **CPTS11, RBRR11 e RECR11:** preço em queda e DY alto, sinal de risco de crédito.

---

## 7. Divisão sugerida para a simulação

| Bloco | Peso | Como opera |
|---|---|---|
| 10 ações de valorização | 50% (5% cada) | **Swing:** o robô aumenta ou reduz cada posição pela tendência e pelos recuos; o que sair vai para o CDI |
| 5 ações de dividendos | 25% (5% cada) | Comprar e segurar; rebalanceia a cada 3 meses (o vencedor do primeiro backtest) |
| 5 FIIs | 25% (5% cada) | Comprar e segurar; reinveste os rendimentos; não gira, por causa dos 20% de IR na venda |

**Réguas a vencer:**
- 100% CDI líquido (~11,5% ao ano).
- Ibovespa.
- IFIX.
- A mesma carteira sem o swing.

## 8. Limitações

- Os múltiplos (P/L, P/VP, ROE) e a vacância vêm de resumos de busca; **não foram conferidos nos documentos oficiais**.
- O histórico de dividendos de FIIs no Yahoo é incompleto (a coluna "DY médio 5a" está subestimada), e o preço do XPML11 tem erro na base.
- As ações foram escolhidas hoje, o que gera viés de sobrevivência nos testes históricos.
- Cenário de 25/11/2026: muda com Copom, quadro fiscal e resultados do 4T26.

---

## 9. Revisão pelas skills do projeto · 25/11/2026 (fim do dia)

Feita com `analise-acao-b3` nos 20 ativos e `cenario-macro-br`. Todos os números vêm de resumos de busca (a rede bloqueou os sites oficiais): **não conferidos na fonte**. Onde esta seção contradiz as seções 1 a 6, vale esta.

### Vereditos

| Bloco | Passa | Passa com ressalvas | Não passa |
|---|---|---|---|
| Valorização | BPAC11, ITUB4, PRIO3, GGBR4, FLRY3 | EMBJ3 (lucro −15,6%, metade do esperado), SBSP3 (dívida em 2,7x o EBITDA e lucro em queda), WEGE3 (lucro estável, margem em queda, preço alto), CURY3 (18% abaixo da média de 200 dias, juros altos), AXIA3 (lucro ajustado −19%; a mais fraca do bloco) | — |
| Dividendos | CXSE3 | PETR4 (lucro oscila, parte em JCP), TAEE11 (dívida em 4,7x o EBITDA; liquidez de R$ 98 mi/dia), CPLE3 (JCP maior que dividendos em 2026; dívida +27%), VIVT3 (remuneração quase toda em JCP e redução de capital) | — |
| FIIs | KNCR11, BTLG11, MCCI11 | KNRI11 (distribui R$ 1,10 com resultado de R$ 0,94 por cota) | **XPML11**, se o corte do rendimento se confirmar (R$ 0,92 → R$ 0,80 em novembro, o menor em 43 meses; P/VP perto de 1) |

**Trocas em aberto (dependem do OK do usuário):** XPML11 → VISC11 (rendimento de R$ 0,82 a R$ 0,84, resultado acima do distribuído; falta confirmar P/VP e vacância). AXIA3 é a primeira candidata na revisão de março; reserva natural: ENEV3, ainda sem pesquisa de fundamentos.

### Correções ao texto original

- **Inflação:** o Focus de 23/11 projeta IPCA de 5,15% em 2026; os 5,6% são a projeção do Banco Central. IPCA em 12 meses: 4,63% (outubro).
- **IFIX:** −4,9% em novembro e −8,2% em 2026 (fonte de 24/11). Dólar: R$ 5,91 em 24/11, com pico de R$ 6,00 em 23/11.
- **Ibovespa** no mês, no trimestre e no ano: não confirmados nesta rodada.
- **EMBJ3, AXIA3, SBSP3:** a tese original citava só o lado positivo; o lucro caiu nas três.
- **PRIO3:** produção do 3T26 de 191,6 mil barris por dia (não ~196 mil).
- **AXIA3:** os "até R$ 4 bi" a acionistas são de setembro/2026, não do resultado do 3T26.
- **BPAC11:** a recompra de R$ 2 bi não foi confirmada.
- **BTLG11:** a compra de galpões é uma negociação de R$ 920 mi ainda não concluída.
- **P/VP dos FIIs mais altos que o escrito:** KNCR11 ~1,03, BTLG11 ~0,93, KNRI11 0,92, XPML11 0,95 a 0,99, MCCI11 ~1,01.
- **MCCI11:** inadimplência zero em outubro/2026 (antes "não confirmada").
- **PETR4:** a queda de ~30% nos proventos de 12 meses é coerente com o dividendo extraordinário de R$ 1,55 da janela anterior (provável, não confirmado). No 3T26, o que veio abaixo do esperado foi o lucro.
- **Justificativas de swing** (IFR2, "só seguir tendência", "setup de recuo"): não valem mais; o swing foi abandonado. Em GGBR4 e FLRY3 nenhuma das duas regras deu lucro no histórico. A justificativa de cada ativo hoje é o fundamento.
- **Horário da B3 desde 03/11/2026:** pregão das 10h às 17h55, leilão de fechamento até 18h, sem after-market de ações.
