# Argos Trade B3

Sistema de rebalanceamento de carteira na B3, **por enquanto 100% simulado**: nenhuma corretora, nenhum dinheiro real.
Só mercado à vista, só saldo próprio, sem day trade e sem nenhuma forma de dívida.

Parte da família **Argos Trade** (na mitologia grega, Argos é o gigante de cem olhos que nunca dormia), ao lado do Argos Trade Cripto.

| Pasta / arquivo | O que é |
|---|---|
| `PLANO.md` | Regras, carteiras, travas, imposto e fases |
| `backtest/` | Teste com dados históricos (Yahoo Finance e CDI do Banco Central) das duas carteiras simuladas |
| `backtest/RESULTADO.md` | Resultado, gerado automaticamente pelo GitHub Actions |
| `ANALISE.md` | Análise e sugestão das 15 ações e 5 FIIs da carteira simulada |
| `backtest/TRIAGEM.md` | Triagem com números de 58 ações e 29 FIIs (gerada pelo Actions) |

## Como rodar o backtest
No GitHub: **Actions → Argos Trade B3 · backtest → Run workflow**. Ele também roda sozinho quando o código do backtest muda,
e salva o resultado em `backtest/RESULTADO.md`.
