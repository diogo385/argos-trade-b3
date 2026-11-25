---
name: cenario-macro-br
description: Resume o cenário macroeconômico e de mercado do Brasil com fontes e datas (Selic e Copom, Boletim Focus, IPCA, juros futuros, dólar, Ibovespa, IFIX, quadro fiscal) e o que isso significa para a carteira simulada do Argos Trade B3. Use quando o usuário perguntar "como está o mercado?", "o que o Copom fez?", "cenário para a bolsa", "vale a pena FII agora?" ou antes de uma revisão trimestral. Só Brasil/B3; não use para cripto.
---

# Cenário macro Brasil · Argos Trade B3

## Coleta (WebSearch; cada dado com fonte e data)
Prefira fontes primárias: Banco Central (comunicado e ata do Copom, Boletim Focus da segunda-feira mais recente),
IBGE (IPCA), B3 (Ibovespa e IFIX), Tesouro Nacional. Portais só como apoio. Se WebFetch for bloqueado, use os resumos
do WebSearch e marque "não conferido na fonte".

| Item | O que levantar |
|---|---|
| Selic | Taxa atual, decisão e placar da última reunião, sinalização do comunicado/ata, data da próxima reunião |
| Focus | Mediana de Selic, IPCA, PIB e câmbio para o ano corrente e o seguinte, e a variação contra a semana anterior |
| Inflação | IPCA do último mês e em 12 meses, contra a meta (3% com teto de 4,5%) |
| Juros futuros | Direção dos DIs longos na semana/mês e o motivo |
| Câmbio | Dólar no último fechamento e no mês |
| Bolsa | Ibovespa: pontos, mês e ano; setores que mais subiram e caíram |
| FIIs | IFIX: pontos, mês e ano; segmentos fortes e fracos (papel CDI, papel IPCA, logística, shoppings, lajes) |
| Fiscal e político | Fatos da semana que mexeram com o mercado |

## O que isso significa para a carteira
Traduza para a carteira do robô (`simulado/robo_b3.py`, `ANALISE.md`):
- **Régua do CDI**: CDI anual aproximado e líquido de IR (15%); é o mínimo que a carteira precisa vencer.
- **Valorização**: setores da carteira mais expostos ao cenário (juros altos pesam em construção e varejo; dólar forte ajuda exportadoras como EMBJ3, SUZB3, GGBR4).
- **Dividendos**: atratividade do DY contra o CDI líquido; riscos de corte.
- **FIIs**: papel CDI (KNCR11) ganha com Selic alta; tijolo (BTLG11, KNRI11, VISC11) tende a reagir quando os juros caem; P/VP médio do IFIX.
- Fatos que podem acionar regras do robô (corte de proventos, quedas fortes).

## Resposta
1. Resumo em 3 linhas.
2. Tabela de indicadores (item · valor · variação · fonte e data).
3. "Para a carteira" em 3 a 5 pontos.
4. Próximos eventos com data (Copom, IPCA, Focus, temporada de resultados).
5. "Não confirmado".

Não faça previsão de preço; descreva cenários condicionais ("se a Selic cair em dezembro, então...").
