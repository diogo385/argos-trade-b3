---
name: analise-acao-b3
description: Analisa uma ação ou um FII brasileiro (B3) com o roteiro padrão do Argos Trade B3 e diz se ele passa nos critérios da carteira simulada. Use quando o usuário perguntar "o que acha de PETR4?", "analisa HGLG11", "vale incluir X?", "compara X com Y", ou pedir um substituto para um ativo da carteira. Só B3; não use para cripto.
---

# Análise de ação ou FII · Argos Trade B3

Carteira **simulada e educacional**: o resultado é estudo, não recomendação de investimento. Só B3.

## Roteiro
1. **Identifique** o ticker atual (houve trocas: EMBR3 → EMBJ3, Eletrobras → AXIA3, Copel → CPLE3, TRPL4 → ISAE4, BRF+Marfrig → MBRF3),
   o bloco em que ele caberia (valorização, dividendos ou FII) e se já está na carteira (`simulado/robo_b3.py`).
2. **Números de mercado**: procure em `backtest/TRIAGEM.md` (liquidez, retorno, volatilidade, queda máxima, beta, DY, swing).
   Se o ticker não estiver lá, inclua-o em `ACOES` ou `FIIS` de `backtest/triagem.py`, faça commit e push (o workflow
   "triagem" roda sozinho no GitHub Actions, que acessa o Yahoo) e use o resultado quando o commit automático chegar.
3. **Fundamentos e notícias** com WebSearch, cada número com fonte e data (RI, CVM, relatório gerencial; portais só como apoio):
   - Ação: setor, P/L, P/VP, ROE, margem, dívida líquida/EBITDA, lucro dos últimos 4 trimestres, DY 12m e mix dividendo × JCP, guidance, riscos.
   - FII: segmento, gestora, P/VP, DY 12m, tendência do rendimento, vacância física/financeira ou inadimplência e indexadores, alavancagem, liquidez, emissões.
4. **Impostos 2026 (pessoa física)**: ações isentas no swing com vendas até R$ 20 mil/mês, senão 15%; day trade 20%; JCP 17,5% na fonte;
   dividendos isentos (retenção de 10% só acima de R$ 50 mil/mês por empresa); rendimento de FII isento; venda de cota de FII 20%.
   Confirme se algo mudou antes de afirmar.
5. **Critérios da carteira** (de `ANALISE.md`), com ✅/⚠️/❌ em cada um:
   - Ações: liquidez acima de R$ 120 mi/dia; resultado recente neutro ou positivo; setor que ainda não está na carteira; dívida controlada.
   - Dividendos: DY 12m e média de 5 anos consistentes; volatilidade baixa; lucro estável; preferência por dividendo em vez de JCP.
   - FIIs: P/VP abaixo de 1 (tijolo); vacância abaixo de 10%; rendimento estável em 12 meses; segmento que ainda não está na carteira.

## Formato da resposta
1. Uma frase de veredito: **passa**, **passa com ressalvas** ou **não passa**, e em qual bloco.
2. Tabela de indicadores (indicador · valor · fonte e data).
3. Pontos a favor e riscos (3 a 5 cada, curtos).
4. Checklist dos critérios com ✅/⚠️/❌.
5. Se for comparação, uma tabela lado a lado e qual fica melhor na carteira e por quê.
6. "Não confirmado": o que não deu para verificar.

Não altere a carteira do robô a partir desta skill; trocas passam pela `revisao-trimestral-b3` e pelo OK do usuário.
