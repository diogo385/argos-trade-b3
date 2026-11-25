# Argos Trade B3 · instruções para o Claude

- Este repositório é **só B3** (ações e FIIs brasileiros). Não use skills, dados ou exemplos de cripto aqui; o Argos Trade Cripto fica em outro repositório.
- Tudo é **simulado e educacional** (dinheiro de mentira). Responda em português do Brasil, em linguagem simples.
- Números de mercado sempre com fonte e data; o que não for confirmado, diga que não foi confirmado.
- A rede da sessão costuma bloquear Yahoo, Banco Central e portais: rode coletas de dados pelo GitHub Actions (workflows em `.github/workflows/`).

## Mapa
| Caminho | O que é |
|---|---|
| `simulado/robo_b3.py` | Robô simulado diário (18h30, dias úteis), regras V3; lista dos 20 ativos |
| `simulado/*.csv`, `simulado/estado.json` | Histórico, operações, proventos e estado do robô (escritos pelo Actions) |
| `index.html` | Monitor web em 5 abas (GitHub Pages: https://diogo385.github.io/argos-trade-b3/) |
| `simulado/mercado.py` + ramo `mercado` | Cotações do dia para a aba Mercado (Actions, a cada 15 min no pregão) |
| `ANALISE.md` | Tese e critérios de cada ativo |
| `PLANO.md` | Regras do sistema (seção 9 = regras em vigor) |
| `backtest/` | Backtests e triagem (`TRIAGEM.md`, `ROBO_REGRAS.md`, `CARTEIRA_SUGERIDA.md`) |
| `revisoes/` | Revisões trimestrais |

## Skills do projeto (`.claude/skills/`)
| Skill | Quando usar |
|---|---|
| `revisao-trimestral-b3` | Depois de cada temporada de resultados: veredito por ativo (manter, observação, trocar) |
| `analise-acao-b3` | Analisar ou comparar uma ação ou FII contra os critérios da carteira |
| `leitura-do-robo` | Explicar o que o robô fez no período e como está contra CDI, Ibovespa e IFIX |
| `cenario-macro-br` | Selic, Focus, IPCA, Ibovespa, IFIX e o efeito na carteira |

Trocas de ativos na carteira do robô só com o OK do usuário.
