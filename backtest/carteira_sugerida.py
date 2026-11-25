"""Backtest da carteira sugerida em ANALISE.md, com R$ 5.000.

Uso: python carteira_sugerida.py <pasta_saida>
Baixa os dados (Yahoo e Banco Central), simula e escreve ../CARTEIRA_SUGERIDA.md.

Blocos (5% por ativo):
  valorização 50%  10 ações, com swing: fica comprado só acima da média de 200 dias; fora, o dinheiro rende CDI
  dividendos  25%  5 ações, comprar e segurar, rebalanceadas a cada 3 meses
  FIIs        25%  5 fundos, comprar e segurar, sem vender (venda paga 20% de IR); rendimentos reinvestidos
"""
import copy, csv, math, sys
from datetime import date
from pathlib import Path

from dados import cdi, cotacoes
from config import CUSTO, IR_ALIQUOTA, IR_CAIXA, ISENCAO_ACOES_MES

CAPITAL = 5_000.0
VALORIZACAO = ["BPAC11", "ITUB4", "EMBJ3", "PRIO3", "SBSP3", "WEGE3", "CURY3", "GGBR4", "AXIA3", "FLRY3"]
DIVIDENDOS = ["PETR4", "TAEE11", "CPLE3", "CXSE3", "VIVT3"]
FIIS = ["KNCR11", "BTLG11", "KNRI11", "XPML11", "MCCI11"]
RESERVA_FII = {"XPML11": "VISC11"}   # usado se o histórico do Yahoo vier com erro
PESO = 0.05
REFS = {"BOVA11": "Ibovespa (BOVA11)", "XFIX11": "IFIX (XFIX11)"}
IR_FII = 0.20
ORDEM_MIN = 30.0
MM = 200
FOLGA = 0.03   # sai 3% abaixo da média e volta 3% acima, para não ficar entrando e saindo


# ------------------------------------------------------------------ dados
def limpo(serie):
    """Detecta erro grosseiro de base (salto de mais de 3x ou queda de 70% num dia)."""
    d = sorted(serie)
    for a, b in zip(d, d[1:]):
        r = serie[b] / serie[a]
        if r > 3 or r < 0.3:
            return False
    return True


def baixar_tudo():
    precos, avisos = {}, []
    fiis = list(FIIS)
    for t in VALORIZACAO + DIVIDENDOS + fiis + list(REFS):
        try:
            s = cotacoes(t)
        except Exception as e:
            avisos.append(f"{t}: sem dados ({e.__class__.__name__})")
            continue
        if not limpo(s) and t in RESERVA_FII:
            r = RESERVA_FII[t]
            avisos.append(f"{t}: histórico do Yahoo com erro de base; trocado por {r} na simulação")
            FIIS[FIIS.index(t)] = r
            t, s = r, cotacoes(r)
        precos[t] = s
        print(t, len(s), min(s), max(s))
    return precos, cdi(), avisos


# ------------------------------------------------------------------ carteira
class Carteira:
    def __init__(self, caixa):
        self.caixa, self.qtd, self.pm = caixa, {}, {}
        self.ops = 0
        self.custos = self.ir_pago = self.ir_pendente = 0.0
        self.prej_comum = self.prej_fii = 0.0
        self.vendas_acoes_max = 0.0
        self._mes()

    def _mes(self):
        self.vendas_acoes = self.ganho_acoes = self.ganho_fii = 0.0

    def valor(self, px):
        return self.caixa + sum(q * px[a] for a, q in self.qtd.items())

    def comprar(self, a, reais, p):
        n = math.floor(min(reais, self.caixa) / (p * (1 + CUSTO)))
        if n <= 0 or n * p < ORDEM_MIN:
            return
        custo = n * p * CUSTO
        q = self.qtd.get(a, 0)
        self.pm[a] = (self.pm.get(a, 0) * q + n * p + custo) / (q + n)
        self.qtd[a] = q + n
        self.caixa -= n * p + custo
        self.custos += custo
        self.ops += 1

    def vender(self, a, reais, p, minimo=ORDEM_MIN):
        n = min(self.qtd.get(a, 0), math.floor(reais / p + 1e-9))
        if n <= 0 or n * p < minimo:
            return
        bruto, custo = n * p, n * p * CUSTO
        ganho = bruto - custo - n * self.pm[a]
        if a in FIIS:
            self.ganho_fii += ganho
        else:
            self.ganho_acoes += ganho
            self.vendas_acoes += bruto
        self.qtd[a] -= n
        self.caixa += bruto - custo
        self.custos += custo
        self.ops += 1

    def fechar_mes(self):
        self.vendas_acoes_max = max(self.vendas_acoes_max, self.vendas_acoes)
        acoes = self.ganho_acoes if self.vendas_acoes > ISENCAO_ACOES_MES else min(self.ganho_acoes, 0)
        base = acoes - self.prej_comum
        if base > 0:
            self.ir_pendente += base * IR_ALIQUOTA
            self.prej_comum = 0.0
        else:
            self.prej_comum = -base
        base = self.ganho_fii - self.prej_fii
        if base > 0:
            self.ir_pendente += base * IR_FII
            self.prej_fii = 0.0
        else:
            self.prej_fii = -base
        pago = min(self.ir_pendente, self.caixa)
        self.caixa -= pago
        self.ir_pendente -= pago
        self.ir_pago += pago
        self._mes()

    def liquido(self, px):
        c = copy.deepcopy(self)
        for a, q in c.qtd.items():
            if q:
                c.vender(a, q * px[a] + 1e-6, px[a], minimo=0)
        c.fechar_mes()
        return c.caixa - c.ir_pendente


# ------------------------------------------------------------------ simulação
def simular(datas, px, mm, fator_cdi, modo, alvo):
    """modo: 'swing', 'trimestral' (sem swing), 'parada', 'cdi' ou um ticker de referência (100% nele)."""
    c = Carteira(CAPITAL)
    p0 = px[datas[0]]
    if modo in REFS:
        c.comprar(modo, CAPITAL, p0[modo])
    elif modo != "cdi":
        for a in alvo:
            if modo == "swing" and a in VALORIZACAO and p0[a] <= mm[datas[0]][a]:
                continue  # abaixo da média: fica no CDI
            c.comprar(a, CAPITAL * PESO, p0[a])
    ops0 = c.ops
    curva, pico, queda, ant = [], 0.0, 0.0, None
    anual = {}
    for d in datas:
        p = px[d]
        if ant:
            c.caixa *= 1 + (fator_cdi[d] / fator_cdi[ant] - 1) * (1 - IR_CAIXA)
            if d[:7] != ant[:7]:
                c.fechar_mes()
            novo_tri = (d[:4], (int(d[5:7]) - 1) // 3) != (ant[:4], (int(ant[5:7]) - 1) // 3)
            if modo == "swing":
                v = c.valor(p)
                for a in VALORIZACAO:
                    tem = c.qtd.get(a, 0) > 0
                    if tem and p[a] < mm[d][a] * (1 - FOLGA):
                        c.vender(a, c.qtd[a] * p[a] + 1e-6, p[a], minimo=0)
                    elif not tem and p[a] > mm[d][a] * (1 + FOLGA):
                        c.comprar(a, v * PESO, p[a])
            if modo in ("swing", "trimestral") and novo_tri:
                v = c.valor(p)
                ajustar = DIVIDENDOS + (VALORIZACAO if modo == "trimestral" else
                                        [a for a in VALORIZACAO if c.qtd.get(a, 0) > 0])
                dif = {a: v * PESO - c.qtd.get(a, 0) * p[a] for a in ajustar}
                for a in ajustar:
                    if dif[a] < 0:
                        c.vender(a, -dif[a], p[a])
                for a in ajustar + FIIS:   # FIIs só recebem compras, nunca vendem
                    falta = dif.get(a, v * PESO - c.qtd.get(a, 0) * p[a])
                    if falta > 0:
                        c.comprar(a, falta, p[a])
        v = c.valor(p)
        pico, queda = max(pico, v), max(queda, 1 - v / max(pico, v))
        curva.append((d, v))
        anual[d[:4]] = v
        ant = d
    liq = c.liquido(px[datas[-1]])
    anos = (date.fromisoformat(datas[-1]) - date.fromisoformat(datas[0])).days / 365.25
    return {"liquido": liq, "bruto": curva[-1][1], "retorno": liq / CAPITAL - 1,
            "anual_pct": (liq / CAPITAL) ** (1 / anos) - 1, "queda": queda, "ops": c.ops - ops0,
            "ir": c.ir_pago, "custos": c.custos, "vendas_mes_max": c.vendas_acoes_max,
            "fim_ano": anual, "curva": curva}


# ------------------------------------------------------------------ relatório
def pct(x, casas=0):
    return f"{x * 100:+.{casas}f}%".replace(".", ",").replace("+-", "−").replace("-", "−")


def rs(x):
    return "R$ " + f"{x:,.0f}".replace(",", ".")


def fdata(d):
    return f"{d[8:10]}/{d[5:7]}/{d[:4]}"


def main(saida):
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    series, taxas, avisos = baixar_tudo()
    alvo = VALORIZACAO + DIVIDENDOS + FIIS
    faltando = [a for a in alvo if a not in series]
    if faltando:
        raise SystemExit(f"sem dados para {faltando}")
    # calendário = pregões do BOVA11; preços repetem o último quando falta negócio
    todas = sorted(series["BOVA11"])
    px, ult, hist = {}, {}, {a: [] for a in series}
    mm = {}
    for d in todas:
        for a, s in series.items():
            if d in s:
                ult[a] = s[d]
                hist[a].append(s[d])
        px[d] = dict(ult)
        mm[d] = {a: sum(h[-MM:]) / MM for a, h in hist.items() if len(h) >= MM}
    # começa quando todos os ativos da carteira têm 200 pregões (para a média existir)
    datas = [d for d in todas if all(a in mm[d] for a in alvo)]
    refs = [r for r in REFS if r in series and all(r in px[d] for d in datas)]
    for r in REFS:
        if r not in refs:
            avisos.append(f"{REFS[r]}: sem histórico no período inteiro; ficou fora da comparação")
    # índice acumulado do CDI
    fator, acum, dias_cdi, j = {}, 1.0, sorted(taxas), 0
    for d in todas:
        while j < len(dias_cdi) and dias_cdi[j] <= d:
            acum *= 1 + taxas[dias_cdi[j]] / 100
            j += 1
        fator[d] = acum

    modos = [("swing", "**Carteira sugerida, com swing** (proposta)"),
             ("trimestral", "Mesma carteira, sem swing (rebalanceia a cada 3 meses)"),
             ("parada", "Mesma carteira parada (compra e nunca mexe)"),
             ("cdi", "100% CDI (líquido de IR)")] + [(r, f"100% {REFS[r]}") for r in refs]
    res = {m: simular(datas, px, mm, fator, m, alvo) for m, _ in modos}

    with open(saida / "curvas_carteira_sugerida.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["data"] + [m for m, _ in modos])
        for i, d in enumerate(datas):
            w.writerow([d] + [round(res[m]["curva"][i][1], 2) for m, _ in modos])

    anos = sorted(res["swing"]["fim_ano"])
    md = [f"# Backtest da carteira sugerida · {date.today().strftime('%d/%m/%Y')}", "",
          "Gerado pelo GitHub Actions (`backtest/carteira_sugerida.py`). Carteira de `ANALISE.md`.", "",
          f"- **Capital:** {rs(CAPITAL)}, 5% por ativo (cerca de R$ 250), ações inteiras no fracionário.",
          f"- **Período:** {fdata(datas[0])} a {fdata(datas[-1])} ({len(datas)} pregões). Começa quando todos os 20 ativos "
          "já têm 200 pregões de histórico, para o swing ter a média de 200 dias.",
          f"- **Custos:** {str(round(CUSTO * 100, 2)).replace('.', ',')}% por operação. Caixa no CDI com 15% de IR. "
          "IR de 15% nas ações (isento até R$ 20 mil de vendas no mês) e de 20% nos FIIs.",
          "- **Valores líquidos:** no fim, tudo é vendido e o IR devido é descontado.",
          "- **Swing:** cada ação de valorização sai quando fecha 3% abaixo da média de 200 dias e volta quando fecha 3% acima; "
          "fora, os R$ dela rendem CDI. Dividendos e ações em swing são rebalanceados a cada 3 meses; FIIs só recebem compras.", ""]
    if avisos:
        md += ["**Avisos dos dados:** " + "; ".join(avisos) + ".", ""]
    md += ["## Resultado", "",
           "| Estratégia | Valor final líquido | Retorno | Ao ano | Queda máxima | Operações | IR pago | Custos |",
           "|---|---|---|---|---|---|---|---|"]
    for m, nome in modos:
        r = res[m]
        md.append(f"| {nome} | {rs(r['liquido'])} | {pct(r['retorno'])} | {pct(r['anual_pct'], 1)} | "
                  f"−{r['queda'] * 100:.0f}% | {r['ops']} | {rs(r['ir'])} | {rs(r['custos'])} |")
    md += ["", "## Ano a ano (retorno bruto de cada ano)", "",
           "| Estratégia | " + " | ".join(anos) + " |", "|---|" + "---|" * len(anos)]
    for m, nome in modos:
        fa, ant, cel = res[m]["fim_ano"], CAPITAL, []
        for y in anos:
            cel.append(pct(fa[y] / ant - 1))
            ant = fa[y]
        md.append(f"| {nome} | " + " | ".join(cel) + " |")
    md += ["", f"Maior volume de vendas de ações num mês (swing): {rs(res['swing']['vendas_mes_max'])}, "
           "bem abaixo do limite de isenção de R$ 20 mil.", "",
           "## Limitações", "",
           "- Período curto (o histórico de CXSE3 e CURY3 começa em 2020–2021) e marcado por Selic alta.",
           "- Ativos escolhidos em novembro/2026, com o passado já conhecido: há viés de sobrevivência e de escolha.",
           "- Preço ajustado do Yahoo: proventos reinvestidos no próprio ativo; o IR de 17,5% sobre JCP não foi descontado.",
           "- Com R$ 250 por ativo, a compra em ações inteiras deixa sobras em caixa (rendendo CDI).", ""]
    (saida.parent / "CARTEIRA_SUGERIDA.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "resultado")
