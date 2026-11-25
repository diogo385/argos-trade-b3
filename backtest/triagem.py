"""Triagem quantitativa de ações e FIIs para as carteiras simuladas.

Uso: python triagem.py <pasta_saida>
Baixa do Yahoo Finance o histórico diário (desde 2014) e os proventos de cada ativo e mede:
liquidez, retorno, volatilidade, queda máxima, beta, tendência, dividendos e, nas ações,
como cada uma se sairia em duas estratégias de swing trade (IFR2 e seguir tendência).
Gera <saida>/acoes.csv, <saida>/fiis.csv e ../TRIAGEM.md.
"""
import csv, json, math, statistics, sys, time, urllib.request
from datetime import datetime, timezone, date
from pathlib import Path

ACOES = """WEGE3 ITUB4 BPAC11 PRIO3 VALE3 PETR4 EMBJ3 RENT3 RADL3 SUZB3 EQTL3 SBSP3 LREN3 TOTS3
RDOR3 AXIA3 GGBR4 VIVA3 ASAI3 B3SA3 CYRE3 CURY3 DIRR3 VBBR3 ENEV3 MBRF3 SMFT3 MULT3 ALOS3
HYPE3 BBAS3 BBSE3 TAEE11 ISAE4 EGIE3 CMIG4 CPLE3 VIVT3 ITSA4 CXSE3 SAPR11 KLBN11 BBDC4
SANB11 CPFE3 PSSA3 ABEV3 UGPA3 CSMG3 FLRY3 TIMS3 BRAV3 RECV3 CMIN3 NATU3 POMO4 MOVI3 IRBR3""".split()
FIIS = """HGLG11 BTLG11 XPLG11 LVBI11 BRCO11 VILG11 KNRI11 XPML11 VISC11 HSML11 PMLL11 HGRU11
TRXF11 ALZR11 GARE11 PVBI11 HGRE11 KNCR11 KNIP11 KNSC11 CPTS11 IRDM11 RBRR11 MXRF11 RECR11
MCCI11 VGHF11 TGAR11 KNHF11 JSRE11""".split()
REF = "BOVA11"
CUSTO = 0.0013   # por operação (B3 + diferença de preço)

YAHOO = ("https://query{n}.finance.yahoo.com/v8/finance/chart/{t}.SA"
         "?period1=1388534400&period2={p2}&interval=1d&events=div%2Csplit&includeAdjustedClose=true")
CAB = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "application/json"}


def baixar(t):
    for k in range(6):
        try:
            req = urllib.request.Request(YAHOO.format(n=1 + k % 2, t=t, p2=int(time.time())), headers=CAB)
            with urllib.request.urlopen(req, timeout=60) as r:
                res = json.loads(r.read())["chart"]["result"][0]
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 * (k + 1))
        except Exception:
            time.sleep(2 * (k + 1))
    else:
        return None
    try:
        q = res["indicators"]["quote"][0]
        adj = res["indicators"]["adjclose"][0]["adjclose"]
    except (KeyError, IndexError, TypeError):
        return None  # ativo sem histórico ajustado (ex.: incorporado ou deslistado)
    dias = []
    for i, ts in enumerate(res.get("timestamp") or []):
        c, a, v = q["close"][i], adj[i], q["volume"][i]
        if c and a:
            d = datetime.fromtimestamp(ts - 3 * 3600, timezone.utc).date()
            dias.append((d, float(c), float(a), float(v or 0)))
    divs = [(datetime.fromtimestamp(int(x["date"]) - 3 * 3600, timezone.utc).date(), float(x["amount"]))
            for x in (res.get("events", {}).get("dividends") or {}).values()]
    return {"dias": dias, "divs": sorted(divs)} if len(dias) > 260 else None


def retornos(px):
    return [px[i] / px[i - 1] - 1 for i in range(1, len(px))]


def queda_max(px):
    pico, q = px[0], 0.0
    for p in px:
        pico = max(pico, p)
        q = max(q, 1 - p / pico)
    return q


def cagr(v0, v1, anos):
    return (v1 / v0) ** (1 / anos) - 1 if anos > 0 and v0 > 0 else float("nan")


def mm(px, i, n):
    return sum(px[i - n + 1:i + 1]) / n


def ifr(px, n=2):
    """IFR (RSI) de Wilder."""
    out = [50.0] * len(px)
    ganho = perda = 0.0
    for i in range(1, len(px)):
        d = px[i] - px[i - 1]
        g, l = max(d, 0), max(-d, 0)
        if i <= n:
            ganho += g / n
            perda += l / n
        else:
            ganho = (ganho * (n - 1) + g) / n
            perda = (perda * (n - 1) + l) / n
        if i >= n:
            out[i] = 100 if perda == 0 else 100 - 100 / (1 + ganho / perda)
    return out


def swing_ifr2(px):
    """Connors: compra no fechamento com IFR2 < 10 e preço acima da MM200; sai quando fecha acima da MM5
    ou depois de 10 pregões."""
    r = ifr(px)
    cap, ops, ganhos, dentro, entrada, desde = 1.0, 0, 0, 0, 0.0, 0
    for i in range(200, len(px)):
        if entrada:
            dentro += 1
            if px[i] > mm(px, i, 5) or i - desde >= 10:
                ret = px[i] / entrada * (1 - CUSTO) ** 2 - 1
                cap *= 1 + ret
                ops += 1
                ganhos += ret > 0
                entrada = 0.0
        elif r[i] < 10 and px[i] > mm(px, i, 200):
            entrada, desde = px[i], i
    n = len(px) - 200
    return {"ifr2_ops": ops, "ifr2_acerto": ganhos / ops if ops else float("nan"),
            "ifr2_ret_anual": cagr(1, cap, n / 252), "ifr2_exposicao": dentro / n}


def swing_tendencia(px):
    """Fica comprado enquanto o fechamento está acima da MM200; fora, fica parado (sem CDI aqui)."""
    cap, dentro, ops, pico, q = 1.0, False, 0, 1.0, 0.0
    for i in range(200, len(px)):
        if dentro:
            cap *= px[i] / px[i - 1]
        acima = px[i] > mm(px, i, 200)
        if acima != dentro:
            cap *= 1 - CUSTO
            ops += 1
            dentro = acima
        pico, q = max(pico, cap), max(q, 1 - cap / max(pico, cap))
    n = len(px) - 200
    return {"tend_ret_anual": cagr(1, cap, n / 252), "tend_queda": q, "tend_ops": ops}


def dividendos(divs, dias):
    if not dias:
        return {}
    hoje = dias[-1][0]
    ult = dias[-1][1]
    d12 = [v for d, v in divs if (hoje - d).days <= 365]
    d12a = [v for d, v in divs if 365 < (hoje - d).days <= 730]
    meses = len({(d.year, d.month) for d, v in divs if (hoje - d).days <= 365})
    anos = {}
    for d, v in divs:
        anos.setdefault(d.year, 0.0)
        anos[d.year] += v
    medios = {}
    for d, c, a, v in dias:
        medios.setdefault(d.year, []).append(c)
    dy_anos = [anos.get(y, 0) / statistics.mean(medios[y]) for y in range(hoje.year - 5, hoje.year) if y in medios]
    return {"dy_12m": sum(d12) / ult, "dy_medio_5a": statistics.mean(dy_anos) if dy_anos else float("nan"),
            "dy_min_5a": min(dy_anos) if dy_anos else float("nan"),
            "div_var_12m": (sum(d12) / sum(d12a) - 1) if d12a and sum(d12a) else float("nan"),
            "meses_pagos_12m": meses}


def medir(t, dados, ref):
    dias = dados["dias"]
    px = [a for _, _, a, _ in dias]
    hoje = dias[-1][0]
    m = {"ticker": t, "ultimo": dias[-1][1], "data": hoje.isoformat(), "inicio": dias[0][0].isoformat(),
         "liquidez_mi": statistics.mean(c * v for _, c, _, v in dias[-63:]) / 1e6}
    def ret_desde(dias_atras):
        alvo = [a for d, _, a, _ in dias if (hoje - d).days >= dias_atras]
        return px[-1] / alvo[-1] - 1 if alvo else float("nan")
    m["ret_3m"], m["ret_12m"] = ret_desde(91), ret_desde(365)
    cinco = [a for d, _, a, _ in dias if (hoje - d).days <= 5 * 365]
    m["ret_anual_5a"] = cagr(cinco[0], cinco[-1], 5) if dias[0][0] <= date(hoje.year - 5, hoje.month, 1) else float("nan")
    m["vol_anual"] = statistics.pstdev(retornos(px[-252:])) * math.sqrt(252)
    m["queda_max_5a"] = queda_max(cinco)
    m["vs_mm200"] = px[-1] / mm(px, len(px) - 1, 200) - 1 if len(px) >= 200 else float("nan")
    if ref:
        r_ref = {d: a for d, _, a, _ in ref["dias"]}
        pares = [(a, r_ref[d]) for d, _, a, _ in dias[-504:] if d in r_ref]
        ra, rb = retornos([p[0] for p in pares]), retornos([p[1] for p in pares])
        m["beta_2a"] = statistics.covariance(ra, rb) / statistics.variance(rb) if len(rb) > 50 else float("nan")
    m.update(dividendos(dados["divs"], dias))
    return m


def salvar_csv(caminho, linhas):
    if not linhas:
        return
    campos = list(dict.fromkeys(k for l in linhas for k in l))
    with open(caminho, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for l in linhas:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in l.items()})


def p(x, casas=0):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return f"{x * 100:.{casas}f}%".replace(".", ",").replace("-", "−")


def n(x, casas=1):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return f"{x:.{casas}f}".replace(".", ",").replace("-", "−")


def main(saida):
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    ref = baixar(REF)
    acoes, fiis, falhas = [], [], []
    for t in ACOES:
        d = baixar(t)
        if not d or (date.today() - d["dias"][-1][0]).days > 15:
            falhas.append(t)
            continue
        m = medir(t, d, ref)
        px = [a for _, _, a, _ in d["dias"]]
        px10 = px[-252 * 10:]
        if len(px10) > 400:
            m.update(swing_ifr2(px10))
            m.update(swing_tendencia(px10))
            anos = (len(px10) - 200) / 252
            m["bh_ret_anual"] = cagr(px10[200], px10[-1], anos)
            m["bh_queda"] = queda_max(px10[200:])
        acoes.append(m)
        print("ação", t, "ok")
    for t in FIIS:
        d = baixar(t)
        if not d or (date.today() - d["dias"][-1][0]).days > 15:
            falhas.append(t)
            continue
        fiis.append(medir(t, d, ref))
        print("fii", t, "ok")
    salvar_csv(saida / "acoes.csv", acoes)
    salvar_csv(saida / "fiis.csv", fiis)

    acoes.sort(key=lambda m: -m["liquidez_mi"])
    md = [f"# Triagem quantitativa · {date.today().strftime('%d/%m/%Y')}", "",
          "Gerado pelo GitHub Actions (`backtest/triagem.py`) com dados diários do Yahoo Finance desde 2014.",
          "Retornos usam preço ajustado por proventos. DY = proventos pagos ÷ preço (ações incluem JCP bruto).",
          f"Sem dados ou ticker inexistente: {', '.join(falhas) or 'nenhum'}.", "",
          "## Ações · mercado", "",
          "| Ação | Liquidez (R$ mi/dia) | 3 meses | 12 meses | 5 anos (a.a.) | Volatilidade | Queda máx. 5a | Beta | vs MM200 | DY 12m | DY médio 5a |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in acoes:
        md.append(f"| {m['ticker']} | {n(m['liquidez_mi'], 0)} | {p(m['ret_3m'])} | {p(m['ret_12m'])} | "
                  f"{p(m['ret_anual_5a'], 1)} | {p(m['vol_anual'])} | −{p(m['queda_max_5a'])} | {n(m.get('beta_2a'), 2)} | "
                  f"{p(m['vs_mm200'])} | {p(m.get('dy_12m'), 1)} | {p(m.get('dy_medio_5a'), 1)} |")
    md += ["", "## Ações · swing trade (últimos até 10 anos, com custos)", "",
           "IFR2: compra com IFR de 2 períodos abaixo de 10 e preço acima da média de 200 dias; sai quando fecha acima da média de 5 dias (máx. 10 pregões).",
           "Tendência: comprado só enquanto o preço está acima da média de 200 dias (fora, dinheiro parado, sem CDI).", "",
           "| Ação | Comprar e segurar (a.a. · queda) | IFR2 (a.a. · acerto · operações · tempo comprado) | Tendência (a.a. · queda · operações) |",
           "|---|---|---|---|"]
    for m in sorted(acoes, key=lambda m: -(m.get("ifr2_ret_anual") or -9)):
        if "ifr2_ops" not in m:
            continue
        md.append(f"| {m['ticker']} | {p(m['bh_ret_anual'], 1)} · −{p(m['bh_queda'])} | "
                  f"{p(m['ifr2_ret_anual'], 1)} · {p(m['ifr2_acerto'])} · {m['ifr2_ops']} · {p(m['ifr2_exposicao'])} | "
                  f"{p(m['tend_ret_anual'], 1)} · −{p(m['tend_queda'])} · {m['tend_ops']} |")
    md += ["", "## FIIs", "",
           "| FII | Liquidez (R$ mi/dia) | 12 meses (total) | 5 anos (a.a.) | Volatilidade | Queda máx. 5a | DY 12m | DY médio 5a | DY mínimo 5a | Variação dos rendimentos 12m | Meses pagos 12m |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in sorted(fiis, key=lambda m: -m["liquidez_mi"]):
        md.append(f"| {m['ticker']} | {n(m['liquidez_mi'], 1)} | {p(m['ret_12m'])} | {p(m['ret_anual_5a'], 1)} | "
                  f"{p(m['vol_anual'])} | −{p(m['queda_max_5a'])} | {p(m.get('dy_12m'), 1)} | {p(m.get('dy_medio_5a'), 1)} | "
                  f"{p(m.get('dy_min_5a'), 1)} | {p(m.get('div_var_12m'))} | {m.get('meses_pagos_12m', '—')} |")
    md += ["", "## Limitações", "",
           "- Preços e proventos do Yahoo podem ter falhas pontuais; conferir números-chave na fonte oficial (RI e B3).",
           "- Resultados de swing usam só preço de fechamento e um único caminho histórico; ações escolhidas hoje têm viés de sobrevivência.",
           "- P/VP, vacância e indicadores contábeis não vêm do Yahoo: estão na análise qualitativa (`ANALISE.md`).", ""]
    (saida.parent / "TRIAGEM.md").write_text("\n".join(md))
    print(f"{len(acoes)} ações e {len(fiis)} FIIs; falhas: {falhas}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "triagem")
