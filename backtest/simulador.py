"""Backtest das carteiras do Argos Trade B3 contra referências simples.

Uso: python simulador.py <pasta_dados> <pasta_saida>
Lê precos.csv e cdi.csv (gerados por dados.py) e escreve, na pasta de saída,
resumo.json, curvas_<carteira>.csv e o texto RESULTADO.md (na pasta acima da saída).

O que entra na conta: ações inteiras (mercado fracionário), custos da B3 e diferença de preço,
proventos (preço ajustado, reinvestidos), caixa rendendo CDI com IR, imposto de 15% sobre o ganho
em ETFs, isenção de ações até R$ 20 mil de vendas no mês e compensação de prejuízos.
"""
import copy, csv, json, math, sys
from datetime import date
from pathlib import Path

from config import (CAPITAL, CARTEIRAS, CORTE_VALIDACAO, CUSTO, ETFS, FAIXAS_ROBO,
                    IR_ALIQUOTA, IR_CAIXA, ISENCAO_ACOES_MES, ORDEM_MIN, REFERENCIA_BOLSA)


# ---------------------------------------------------------------- dados
def carregar(pasta):
    pasta = Path(pasta)
    with open(pasta / "precos.csv") as f:
        linhas = list(csv.DictReader(f))
    ativos = [k for k in linhas[0] if k != "data"]
    precos, ultimo = {}, {}
    for x in linhas:
        if not x[REFERENCIA_BOLSA]:
            continue  # usa os pregões do BOVA11 como calendário da B3
        for a in ativos:
            if x[a]:
                ultimo[a] = float(x[a])
        precos[x["data"]] = dict(ultimo)  # dias sem negócio repetem o último preço
    with open(pasta / "cdi.csv") as f:
        cdi = {x["data"]: float(x["taxa"]) for x in csv.DictReader(f)}
    # índice acumulado do CDI em cada pregão
    idx, acum, dias_cdi = {}, 1.0, sorted(cdi)
    j = 0
    for d in sorted(precos):
        while j < len(dias_cdi) and dias_cdi[j] <= d:
            acum *= 1 + cdi[dias_cdi[j]] / 100
            j += 1
        idx[d] = acum
    return precos, idx, (min(cdi), max(cdi))


# ---------------------------------------------------------------- carteira
class Carteira:
    def __init__(self, capital):
        self.caixa = capital
        self.qtd, self.pm = {}, {}
        self.ops = self.custos = self.ir_pago = self.ir_pendente = 0.0
        self.prejuizo = 0.0
        self._mes()

    def _mes(self):
        self.vendas_acoes = self.ganho_acoes = self.ganho_etf = 0.0

    def valor(self, px):
        return self.caixa + sum(q * px[a] for a, q in self.qtd.items())

    def comprar(self, a, reais, p, minimo=ORDEM_MIN):
        reais = min(reais, self.caixa)
        n = math.floor(reais / (p * (1 + CUSTO)))
        if n <= 0 or n * p < minimo:
            return
        bruto = n * p
        custo = bruto * CUSTO
        q = self.qtd.get(a, 0)
        self.pm[a] = (self.pm.get(a, 0) * q + bruto + custo) / (q + n)
        self.qtd[a] = q + n
        self.caixa -= bruto + custo
        self.custos += custo
        self.ops += 1
        assert self.caixa >= -1e-6, "caixa negativo"

    def vender(self, a, reais, p, minimo=ORDEM_MIN):
        n = min(self.qtd.get(a, 0), math.floor(reais / p))
        if n <= 0 or n * p < minimo:
            return
        bruto = n * p
        custo = bruto * CUSTO
        ganho = bruto - custo - n * self.pm[a]
        if a in ETFS:
            self.ganho_etf += ganho
        else:
            self.ganho_acoes += ganho
            self.vendas_acoes += bruto
        self.qtd[a] -= n
        self.caixa += bruto - custo
        self.custos += custo
        self.ops += 1

    def fechar_mes(self):
        """Apura o IR do mês (DARF), com compensação de prejuízo acumulado."""
        acoes = self.ganho_acoes if self.vendas_acoes > ISENCAO_ACOES_MES else min(self.ganho_acoes, 0)
        base = self.ganho_etf + acoes - self.prejuizo
        if base > 0:
            self.ir_pendente += base * IR_ALIQUOTA
            self.prejuizo = 0.0
        else:
            self.prejuizo = -base
        pago = min(self.ir_pendente, self.caixa)
        self.caixa -= pago
        self.ir_pendente -= pago
        self.ir_pago += pago
        self._mes()

    def render_caixa(self, fator):
        self.caixa *= 1 + (fator - 1) * (1 - IR_CAIXA)

    def liquido(self, px):
        """Quanto sobraria vendendo tudo hoje e pagando o imposto devido."""
        c = copy.deepcopy(self)
        for a, q in c.qtd.items():
            if q:
                c.vender(a, q * px[a] + 1e-6, px[a], minimo=0)
        c.fechar_mes()
        return c.caixa - c.ir_pendente


def rebalancear(c, alvo, px, ativos=None):
    v = c.valor(px)
    ativos = ativos or list(alvo)
    dif = {a: v * alvo[a] - c.qtd.get(a, 0) * px[a] for a in ativos}
    for a in ativos:          # primeiro vende, para ter caixa
        if dif[a] < 0:
            c.vender(a, -dif[a], px[a])
    for a in ativos:
        if dif[a] > 0:
            c.comprar(a, dif[a], px[a])


def fora_da_faixa(c, alvo, px, faixa):
    v = c.valor(px)
    return [a for a, w in alvo.items() if abs(c.qtd.get(a, 0) * px[a] / v - w) > w * faixa]


def periodo_chave(d, regra):
    a, m = int(d[:4]), int(d[5:7])
    return {"mensal": (a, m), "trimestral": (a, (m - 1) // 3), "anual": a}[regra]


def simular(alvo, datas, precos, idx, estrategia):
    c = Carteira(CAPITAL)
    if estrategia != "cdi":
        for a, w in alvo.items():
            c.comprar(a, CAPITAL * w, precos[datas[0]][a])
    ops_iniciais = c.ops
    curva, pico, queda, ant = [], 0.0, 0.0, None
    for d in datas:
        px = precos[d]
        if ant:
            c.render_caixa(idx[d] / idx[ant])
            if d[:7] != ant[:7]:
                c.fechar_mes()
            if estrategia in ("mensal", "trimestral", "anual") and \
                    periodo_chave(d, estrategia) != periodo_chave(ant, estrategia):
                rebalancear(c, alvo, px)
            elif estrategia.startswith("robo"):
                sair = fora_da_faixa(c, alvo, px, float(estrategia.split("_")[1]))
                if sair:
                    rebalancear(c, alvo, px, sair)
        v = c.valor(px)
        pico, queda = max(pico, v), max(queda, 1 - v / max(pico, v))
        curva.append((d, v))
        ant = d
    final = precos[datas[-1]]
    liq = c.liquido(final)
    anos = (date.fromisoformat(datas[-1]) - date.fromisoformat(datas[0])).days / 365.25
    return {
        "bruto": curva[-1][1], "liquido": liq,
        "retorno": liq / CAPITAL - 1, "anual": (liq / CAPITAL) ** (1 / anos) - 1 if anos > 0 else 0,
        "queda": queda, "ops": int(c.ops - ops_iniciais),
        "ir": c.ir_pago, "custos": c.custos, "curva": curva,
    }


# ---------------------------------------------------------------- relatório
ESTRATEGIAS = (
    [("parada", "Carteira parada (sem rebalancear)"),
     ("mensal", "Rebalancear todo mês"),
     ("trimestral", "Rebalancear a cada 3 meses"),
     ("anual", "Rebalancear uma vez por ano")]
    + [(f"robo_{f}", f"Robô, faixa de {int(f * 100)}% do alvo") for f in FAIXAS_ROBO]
)
REFERENCIAS = [("bolsa", "100% Ibovespa (BOVA11), comprar e segurar"),
               ("cdi", "100% CDI (líquido de IR)")]


def pct(x):
    return f"{x * 100:+.0f}%".replace("+-", "−").replace("-", "−")


def br(x):
    return f"{x:,.0f}".replace(",", ".")


def fmt_data(d):
    return f"{d[8:10]}/{d[5:7]}/{d[:4]}"


def rodar(pasta_dados, saida):
    precos, idx, faixa_cdi = carregar(pasta_dados)
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    todas = sorted(precos)
    resumo, md = {}, []
    for chave, cart in CARTEIRAS.items():
        alvo = cart["alvo"]
        datas = [d for d in todas if all(a in precos[d] for a in alvo)]
        periodos = [("Completo", datas),
                    ("Calibração", [d for d in datas if d < CORTE_VALIDACAO]),
                    ("Validação", [d for d in datas if d >= CORTE_VALIDACAO])]
        nomes = {p: f"{p} {ds[0][:4]}–{ds[-1][:4]}" for p, ds in periodos}
        res = {}
        for cod, _ in ESTRATEGIAS + REFERENCIAS:
            a = {REFERENCIA_BOLSA: 1.0} if cod == "bolsa" else alvo
            est = "parada" if cod == "bolsa" else cod
            res[cod] = {p: simular(a, ds, precos, idx, est) for p, ds in periodos if len(ds) > 20}
        resumo[chave] = {cod: {p: {k: v for k, v in r.items() if k != "curva"} for p, r in rp.items()}
                         for cod, rp in res.items()}
        with open(saida / f"curvas_{chave}.csv", "w", newline="") as f:
            w = csv.writer(f)
            cods = [c for c, _ in ESTRATEGIAS + REFERENCIAS]
            w.writerow(["data"] + cods)
            for i, d in enumerate(datas):
                w.writerow([d] + [round(res[c]["Completo"]["curva"][i][1], 2) for c in cods])

        md += [f"## {cart['nome']}", "",
               "Alvo: " + ", ".join(f"{a} {int(w * 100)}%" for a, w in alvo.items())
               + f" e caixa {int(round((1 - sum(alvo.values())) * 100))}% no CDI.",
               f"Dados de {fmt_data(datas[0])} a {fmt_data(datas[-1])} ({len(datas)} pregões).", "",
               "Retorno total líquido de custos e IR (anual · queda máxima · operações)", "",
               "| Estratégia | " + " | ".join(nomes[p] for p, ds in periodos if len(ds) > 20) + " |",
               "|---|" + "---|" * sum(len(ds) > 20 for _, ds in periodos)]
        for cod, nome in ESTRATEGIAS + REFERENCIAS:
            cel = [f"{pct(r['retorno'])} ({pct(r['anual'])} a.a. · −{r['queda'] * 100:.0f}% · {r['ops']})"
                   for r in res[cod].values()]
            md.append(f"| {nome} | " + " | ".join(cel) + " |")
        c = res
        md += ["", f"IR pago no período completo: robô {FAIXAS_ROBO[0]:.0%} R$ "
               f"{br(c[f'robo_{FAIXAS_ROBO[0]}']['Completo']['ir'])}, anual R$ {br(c['anual']['Completo']['ir'])}, "
               f"mensal R$ {br(c['mensal']['Completo']['ir'])}. "
               f"Custos de negociação: robô R$ {br(c[f'robo_{FAIXAS_ROBO[0]}']['Completo']['custos'])}, "
               f"mensal R$ {br(c['mensal']['Completo']['custos'])}.", ""]

    (saida / "resumo.json").write_text(json.dumps(resumo, indent=1, ensure_ascii=False))
    grafico = desenhar(saida)
    hoje = date.today().strftime("%d/%m/%Y")
    topo = [f"# Resultado do backtest · {hoje}", "",
            "Gerado automaticamente pelo GitHub Actions (`backtest/simulador.py`).", "",
            f"Capital: R$ {br(CAPITAL)}. Custos: {str(round(CUSTO * 100, 2)).replace(".", ",")}% por operação (B3 + diferença de preço). "
            f"CDI de {fmt_data(faixa_cdi[0])} a {fmt_data(faixa_cdi[1])}, com {IR_CAIXA:.0%} de IR sobre o rendimento do caixa.",
            "Valores **líquidos**: no fim de cada período a carteira é vendida e o IR devido é descontado, "
            "para que a carteira parada não leve vantagem por adiar o imposto.", ""]
    if grafico:
        topo += ["![gráfico](resultado/grafico.png)", ""]
    fim = ["## Limitações", "",
           "- **Viés de sobrevivência na carteira de ações:** as ações foram escolhidas hoje, sabendo que "
           "sobreviveram e continuam grandes. O resultado passado delas tende a parecer melhor do que seria.",
           "- Preço ajustado do Yahoo: dividendos reinvestidos sem imposto; o IR de 15% sobre JCP não foi descontado.",
           "- Diferença de preço no fracionário estimada; em ações menos líquidas pode ser maior.",
           "- É um único caminho histórico. A ordem entre as estratégias pode mudar em outro período.",
           "", "## Como reproduzir", "```",
           "cd backtest",
           "python dados.py dados                # cotações (Yahoo) e CDI (Banco Central)",
           "python simulador.py dados resultado",
           "```", ""]
    (saida.parent / "RESULTADO.md").write_text("\n".join(topo + md + fim))
    print("\n".join(md))


def desenhar(saida):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    fig, eixos = plt.subplots(len(CARTEIRAS), 1, figsize=(10, 4.5 * len(CARTEIRAS)), sharex=False)
    eixos = eixos if len(CARTEIRAS) > 1 else [eixos]
    mostrar = ["parada", "anual", f"robo_{FAIXAS_ROBO[0]}", "bolsa", "cdi"]
    rotulos = dict(ESTRATEGIAS + REFERENCIAS)
    for ax, (chave, cart) in zip(eixos, CARTEIRAS.items()):
        with open(saida / f"curvas_{chave}.csv") as f:
            linhas = list(csv.DictReader(f))
        datas = [date.fromisoformat(x["data"]) for x in linhas]
        for cod in mostrar:
            ax.plot(datas, [float(x[cod]) for x in linhas], label=rotulos[cod],
                    lw=2 if cod.startswith("robo") else 1.2,
                    ls="--" if cod in ("bolsa", "cdi") else "-")
        ax.set_title(f"{cart['nome']} · patrimônio bruto (R$)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(saida / "grafico.png", dpi=110)
    return True


if __name__ == "__main__":
    rodar(sys.argv[1] if len(sys.argv) > 1 else "dados", sys.argv[2] if len(sys.argv) > 2 else "resultado")
