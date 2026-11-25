---
name: revisao-trimestral-b3
description: Revisão trimestral da tese de cada um dos 20 ativos da carteira simulada do Argos Trade B3 (10 ações de valorização, 5 de dividendos, 5 FIIs) depois da temporada de resultados. Use quando o usuário pedir "revisão trimestral", "revisar a carteira", "revisar a tese", "resultados do 4T/1T/2T/3T", ou quando terminar uma temporada de balanços (fev–mar, abr–mai, jul–ago, out–nov). Dá um veredito por ativo (manter, observação ou trocar) com fontes e datas e registra a revisão no repositório.
---

# Revisão trimestral · Argos Trade B3

Só B3 (ações e FIIs brasileiros). Nunca misture cripto. Carteira **simulada e educacional**: não é recomendação de investimento.

## Antes de começar
1. `git pull` no repositório `argos-trade-b3`.
2. Leia: `ANALISE.md` (tese original de cada ativo e critérios), `PLANO.md` seção 9 (regras em vigor),
   `simulado/estado.json` (posições, preço médio, `fora`, `saude_proventos`, `alertado`), `simulado/operacoes.csv`
   e `simulado/proventos.csv`. A lista de ativos em vigor está em `simulado/robo_b3.py` (`VALORIZACAO`, `DIVIDENDOS`, `FIIS`).
3. Identifique o trimestre revisado (ex.: 4T26) e a última revisão em `revisoes/` (se existir), para comparar.

## Coleta (por ativo)
Use WebSearch (a rede desta sessão costuma bloquear WebFetch em portais; registre quando isso acontecer).
Prefira, nesta ordem: release/ITR da empresa (RI), relatório gerencial do FII (Fundos.NET/B3), CVM, e só depois portais.
Toda cifra leva **fonte e data**. O que não for confirmado vira "não confirmado"; nunca estime número.

**Ações de valorização**: lucro líquido e EBITDA do trimestre vs mesmo trimestre do ano anterior (2 trimestres seguidos de queda?),
margem, dívida líquida/EBITDA, guidance, eventos relevantes (M&A, mudança de gestão, regulação), consenso das casas.
**Ações de dividendos**: proventos declarados nos últimos 12 meses vs 12 anteriores, payout, lucro, mix dividendo × JCP (JCP tem 17,5% de IR), política de dividendos.
**FIIs**: rendimento mensal (tendência de 6 meses), P/VP, vacância física e financeira (tijolo), inadimplência e indexadores (papel),
alavancagem, emissões (diluição), vendas de imóveis, mudanças de gestora.

## Critérios do veredito
| Veredito | Quando |
|---|---|
| **Manter** | Tese intacta: resultado estável ou melhor, proventos em dia, sem evento grave |
| **Observação** | Um sinal amarelo: 1 trimestre fraco, guidance cortado, vacância subindo, dívida/EBITDA acima de 3x, queda de 35% do topo (alerta do robô) |
| **Trocar** | Tese quebrada: lucro caindo 2 trimestres seguidos sem explicação pontual, corte de proventos acima de 30% (ações) ou 25% (FIIs), vacância acima de 15%, alavancagem perigosa, evento de governança, ou o próprio robô já saiu por proventos e não há recuperação à vista |

Um ativo em **observação** por 2 revisões seguidas sem melhora vira **trocar**.
Para cada **trocar**, proponha um substituto do **mesmo bloco e, de preferência, do mesmo setor**, que passe nos critérios do `ANALISE.md`
(liquidez acima de R$ 120 mi/dia para ações, um setor por ação, P/VP abaixo de 1 no FII de tijolo). Reservas já mapeadas:
ENEV3, VBBR3 (valorização); BBSE3, ITSA4, ISAE4, CMIG4 (dividendos); VISC11 (shoppings). Use a skill `analise-acao-b3` no substituto.

## Entrega
1. Crie `revisoes/AAAA-Tn.md` (ex.: `revisoes/2027-T1.md`, revisão dos resultados do 4T26) com:
   - data da revisão, trimestre revisado e resumo em 3 a 5 linhas;
   - tabela única: ativo · bloco · veredito · motivo em uma linha · fonte (link) e data;
   - seção "Trocas propostas" com substituto e justificativa;
   - seção "Não confirmado" listando o que faltou verificar.
2. Mostre no chat a tabela resumida e as trocas propostas.
3. **Trocas na carteira só com o OK do usuário.** Com o OK: edite `VALORIZACAO`/`DIVIDENDOS`/`FIIS` em `simulado/robo_b3.py`
   e implemente a troca no robô (vender o ativo que sai e comprar o novo no próximo fechamento, registrando o motivo
   "revisão trimestral" em `operacoes.csv`), atualize `ANALISE.md` e o `PLANO.md`, faça commit e push. Sem OK, só registre a proposta.
4. Commit da revisão: `Revisão trimestral AAAA-Tn: N manter, N observação, N trocar`.
