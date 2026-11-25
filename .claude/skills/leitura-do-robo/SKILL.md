---
name: leitura-do-robo
description: Lê os arquivos do robô simulado do Argos Trade B3 (pasta simulado/) e explica em português simples o que ele fez num período (dia, semana, mês ou desde o início), comparando com a carteira parada, o CDI, o Ibovespa e o IFIX. Use quando o usuário perguntar "como está o robô?", "o que o robô fez essa semana?", "resumo do mês", "por que ele comprou X?" ou "estamos ganhando do CDI?". Só B3.
---

# Leitura do robô · Argos Trade B3

## Fontes
1. `git pull` no repositório `argos-trade-b3` (o robô faz commit todo dia útil depois das 19h15).
2. `simulado/historico.csv` — uma linha por pregão: `data;patrimonio;caixa;carteira_parada;cdi;ibovespa;ifix;operacoes`.
3. `simulado/operacoes.csv` — `data;tipo;ativo;quantidade;preco;valor;custo;motivo` (a primeira leva é a "montagem inicial").
4. `simulado/proventos.csv` — `data_com;ativo;quantidade;valor_por_cota;total`.
5. `simulado/estado.json` — posições (`carteira.qtd`, `carteira.pm`), caixa, `precos` do último fechamento, `fora`, `reforcos`,
   `saude_proventos`, `alertado`, `ir_pago`, `ultimo_pregao`.
6. Regras: `PLANO.md` seção 9 (V3). Se o histórico estiver vazio, diga que o robô ainda não rodou e quando roda (dia útil, 19h15).

## Cálculos (faça com um script Python curto, não de cabeça)
- Período pedido (padrão: últimos 7 dias corridos). Retorno do robô no período e desde o início; o mesmo para carteira parada, CDI, Ibovespa e IFIX.
- Diferença em R$ do robô contra cada referência.
- Operações do período agrupadas por motivo (reforço, realização de lucro, saída por proventos, volta, rebalanceamento trimestral).
- Proventos do período (total e por ativo) e IR pago.
- Os 3 ativos que mais ajudaram e os 3 que mais atrapalharam (variação de preço × quantidade).
- Gatilhos próximos: ativos a menos de 5% do preço de reforço (85% do preço médio), posições acima de 1,8x o alvo,
  proventos de 12 meses perto do corte (−30% ações de dividendos, −25% FIIs), alertas de −35% do topo.

## Resposta (curta, para ler no celular)
1. Uma linha com o resultado: patrimônio, retorno no período e contra o CDI.
2. Tabela pequena: robô · parada · CDI · Ibovespa · IFIX (valor e retorno).
3. "O que o robô fez", em frases simples com o motivo de cada operação.
4. Proventos recebidos.
5. "Fique de olho": gatilhos próximos e alertas.
6. Se o robô está atrás da carteira parada ou do CDI, diga com franqueza e lembre que o período ainda é curto quando for o caso.

Não invente dados que não estão nos arquivos. Não altere nada no repositório com esta skill.
