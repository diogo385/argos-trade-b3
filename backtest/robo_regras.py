"""Backtest das regras de decisão do robô B3: reserva, reforço nas quedas, realização de lucro,
saída por tese quebrada e stop de preço. R$ 6.000 = R$ 5.000 investidos + R$ 1.000 de reserva.

Uso: python robo_regras.py <pasta_saida>    → escreve ../ROBO_REGRAS.md

Versões:
  V1 base            sem swing, rebalanceia a cada 3 meses; reserva parada no CDI
  V2 + reforço       usa a reserva para comprar mais quando o ativo cai abaixo do preço médio
  V3 + saídas        V2 + realiza lucro quando a posição passa de 2x o alvo + sai quando os proventos despencam
  V4 + stop          V3 + stop automático de 35% do topo nas ações de valorização
"""
import math, sys
from datetime import date, timedelta
from pathlib import Path

import carteira_sugerida as C
from carteira_sugerida import Carteira, limpo, pct, rs, fdata
from triagem import baixar
from dados import cdi
from config import IR_CAIXA

CAPITAL, RESERVA = 6_000.0, 1_000.0
FRACAO_RESERVA = RESERVA / CAPITAL
REFORCO_1, REFORCO_2 = 0.85, 0.75     # preço ≤ 85% e ≤ 75% do preço médio
REFORCOS_MES = 2                       # no máximo 2 reforços por mês (≈ R$ 500)
TETO_PESO = 2.0                        # nenhum ativo passa de 2x o alvo (10% do investido)
CORTE_DIV_ACAO, CORTE_DIV_FII = 0.30, 0.25
STOP = 0.35
VERSOES = [("v1", "V1 · base (sem swing, rebalanceia a cada 3 meses, reserva parada)"),
           ("v2", "V2 · + reforço nas quedas com a reserva"),
           ("v3", "V3 · + realização de lucro e saída por corte de proventos"),
           ("v4", "V4 · + stop automático de 35% nas ações de valorização")]


def carregar():
    series, divs, avisos = {}, {}, []
    for t in C.VALORIZACAO + C.DIVIDENDOS + list(C.FIIS) + ["BOVA11", "XFIX11"]:
        d = baixar(t)
        if d and t in C.RESERVA_FII and not limpo({x[0].isoformat(): x[2] for x in d["dias"]}):
            r = C.RESERVA_FII[t]
            avisos.append(f"{t}: histórico do Yahoo com erro de base; trocado por {r}")
            C.FIIS[C.FIIS.index(t)] = r
            t, d = r, baixar(r)
        if not d:
            avisos.append(f"{t}: sem dados")
            continue
        series[t] = {x[0].isoformat(): x[2] for x in d["dias"]}
        divs[t] = d["divs"]
        print(t, len(series[t]))
    return series, divs, cdi(), avisos


def saude_proventos(divs, d):
    """Variação dos proventos dos últimos 12 meses contra os 12 anteriores (None se não dá para medir)."""
    hoje = date.fromisoformat(d)
    a = sum(v for x, v in divs if hoje - timedelta(365) < x <= hoje)
    b = sum(v for x, v in divs if hoje - timedelta(730) < x <= hoje - timedelta(365))
    return None if b <= 0 else a / b - 1


def simular(versao, datas, px, fator, divs):
    alvo = C.VALORIZACAO + C.DIVIDENDOS + C.FIIS
    c = Carteira(CAPITAL)
    slot = (CAPITAL - RESERVA) / len(alvo)
    for a in alvo:
        c.comprar(a, slot, px[datas[0]][a])
    ops0 = c.ops
    ev = {"reforço": 0, "realização": 0, "saída por proventos": 0, "stop": 0, "volta": 0}
    fora, topo, reforcos, saude = {}, {}, {a: 0 for a in alvo}, {}
    reforcos_mes, mes = 0, None
    pico, queda, ant, anual = 0.0, 0.0, None, {}
    for d in datas:
        p = px[d]
        if ant:
            c.caixa *= 1 + (fator[d] / fator[ant] - 1) * (1 - IR_CAIXA)
            if d[:7] != ant[:7]:
                c.fechar_mes()
                reforcos_mes = 0
                if versao != "v1":   # proventos medidos uma vez por mês
                    saude = {a: saude_proventos(divs[a], d) for a in C.DIVIDENDOS + C.FIIS}
            v = c.valor(p)
            alvo_ativo = v * (1 - FRACAO_RESERVA) / len(alvo)
            ativos = [a for a in alvo if a not in fora]

            # 1. saídas
            if versao in ("v3", "v4"):
                for a in ativos:
                    if a in fora or not c.qtd.get(a):
                        continue
                    s = saude.get(a)
                    corte = CORTE_DIV_FII if a in C.FIIS else CORTE_DIV_ACAO
                    if s is not None and s < -corte:
                        c.vender(a, c.qtd[a] * p[a] + 1e-6, p[a], minimo=0)
                        fora[a] = "proventos"
                        ev["saída por proventos"] += 1
                    elif c.qtd[a] * p[a] > TETO_PESO * alvo_ativo:
                        c.vender(a, c.qtd[a] * p[a] - alvo_ativo, p[a])
                        ev["realização"] += 1
            if versao == "v4":
                for a in C.VALORIZACAO:
                    if a in fora or not c.qtd.get(a):
                        continue
                    topo[a] = max(topo.get(a, p[a]), p[a])
                    if p[a] < topo[a] * (1 - STOP):
                        c.vender(a, c.qtd[a] * p[a] + 1e-6, p[a], minimo=0)
                        fora[a] = ("stop", d)
                        topo.pop(a, None)
                        ev["stop"] += 1
            # volta: proventos recuperados ou, após stop, 60 pregões e preço acima da mínima + 20%
            for a, motivo in list(fora.items()):
                if motivo == "proventos" and (saude.get(a) or 0) >= 0:
                    del fora[a]; ev["volta"] += 1
                elif isinstance(motivo, tuple) and datas.index(d) - datas.index(motivo[1]) >= 60:
                    del fora[a]; ev["volta"] += 1

            # 2. reforço nas quedas, com a reserva
            if versao != "v1":
                for a in alvo:
                    if a in fora or not c.qtd.get(a) or reforcos_mes >= REFORCOS_MES:
                        continue
                    if p[a] >= c.pm[a]:
                        reforcos[a] = 0
                        continue
                    gatilho = REFORCO_1 if reforcos[a] == 0 else REFORCO_2 if reforcos[a] == 1 else 0
                    s = saude.get(a)
                    saudavel = s is None or s > -0.10
                    if gatilho and p[a] <= c.pm[a] * gatilho / (1 if reforcos[a] == 0 else REFORCO_1) and saudavel \
                            and c.qtd[a] * p[a] + slot <= TETO_PESO * alvo_ativo and c.caixa > slot * 1.05:
                        n0 = c.qtd[a]
                        c.comprar(a, slot, p[a])
                        if c.qtd[a] > n0:
                            reforcos[a] += 1
                            reforcos_mes += 1
                            ev["reforço"] += 1

            # 3. rebalanceamento trimestral (vende o excesso e completa o que falta; FIIs não vendem)
            if (d[:4], (int(d[5:7]) - 1) // 3) != (ant[:4], (int(ant[5:7]) - 1) // 3):
                v = c.valor(p)
                alvo_ativo = v * (1 - FRACAO_RESERVA) / len(alvo)
                ativos = [a for a in alvo if a not in fora]
                for a in ativos:
                    excesso = c.qtd.get(a, 0) * p[a] - alvo_ativo
                    if excesso > 0 and a not in C.FIIS:
                        c.vender(a, excesso, p[a])
                for a in ativos:
                    falta = alvo_ativo - c.qtd.get(a, 0) * p[a]
                    reserva_minima = v * FRACAO_RESERVA * 0.5
                    if falta > 0 and c.caixa - falta > reserva_minima:
                        c.comprar(a, falta, p[a])
                reforcos = {a: 0 for a in alvo}
        v = c.valor(p)
        pico, queda = max(pico, v), max(queda, 1 - v / max(pico, v))
        anual[d[:4]] = v
        ant = d
    liq = c.liquido(px[datas[-1]])
    anos = (date.fromisoformat(datas[-1]) - date.fromisoformat(datas[0])).days / 365.25
    return {"liquido": liq, "retorno": liq / CAPITAL - 1, "anual_pct": (liq / CAPITAL) ** (1 / anos) - 1,
            "queda": queda, "ops": c.ops - ops0, "ir": c.ir_pago, "custos": c.custos,
            "caixa_fim": c.caixa, "eventos": ev, "fim_ano": anual}


def referencia(datas, px, fator, ticker):
    c = Carteira(CAPITAL)
    if ticker:
        c.comprar(ticker, CAPITAL, px[datas[0]][ticker])
    pico, queda, ant, anual = 0.0, 0.0, None, {}
    for d in datas:
        if ant:
            c.caixa *= 1 + (fator[d] / fator[ant] - 1) * (1 - IR_CAIXA)
        v = c.valor(px[d])
        pico, queda = max(pico, v), max(queda, 1 - v / max(pico, v))
        anual[d[:4]] = v
        ant = d
    liq = c.liquido(px[datas[-1]])
    anos = (date.fromisoformat(datas[-1]) - date.fromisoformat(datas[0])).days / 365.25
    return {"liquido": liq, "retorno": liq / CAPITAL - 1, "anual_pct": (liq / CAPITAL) ** (1 / anos) - 1,
            "queda": queda, "ops": 0, "ir": 0.0, "custos": c.custos, "fim_ano": anual}


def main(saida):
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    series, divs, taxas, avisos = carregar()
    alvo = C.VALORIZACAO + C.DIVIDENDOS + C.FIIS
    falta = [a for a in alvo if a not in series]
    if falta:
        raise SystemExit(f"sem dados para {falta}")
    todas = sorted(series["BOVA11"])
    px, ult = {}, {}
    for d in todas:
        for a, s in series.items():
            if d in s:
                ult[a] = s[d]
        px[d] = dict(ult)
    # mesmo início do backtest anterior: todos os ativos com pelo menos 200 pregões
    contagem = {a: 0 for a in alvo}
    datas = []
    for d in todas:
        for a in alvo:
            contagem[a] += d in series[a]
        if all(v >= 200 for v in contagem.values()):
            datas.append(d)
    fator, acum, dias_cdi, j = {}, 1.0, sorted(taxas), 0
    for d in todas:
        while j < len(dias_cdi) and dias_cdi[j] <= d:
            acum *= 1 + taxas[dias_cdi[j]] / 100
            j += 1
        fator[d] = acum

    res = {v: simular(v, datas, px, fator, divs) for v, _ in VERSOES}
    refs = [("cdi", "100% CDI (líquido de IR)", None), ("bova", "100% Ibovespa (BOVA11)", "BOVA11")]
    if "XFIX11" in series and all("XFIX11" in px[d] for d in datas):
        refs.append(("ifix", "100% IFIX (XFIX11)", "XFIX11"))
    for k, _, t in refs:
        res[k] = referencia(datas, px, fator, t)
    linhas = VERSOES + [(k, n) for k, n, _ in refs]

    anos = sorted(res["v1"]["fim_ano"])
    md = [f"# Backtest das regras do robô · {date.today().strftime('%d/%m/%Y')}", "",
          "Gerado pelo GitHub Actions (`backtest/robo_regras.py`).", "",
          f"- **Capital:** {rs(CAPITAL)} = {rs(CAPITAL - RESERVA)} nos 20 ativos de `ANALISE.md` (5% cada) "
          f"+ {rs(RESERVA)} de reserva rendendo CDI.",
          f"- **Período:** {fdata(datas[0])} a {fdata(datas[-1])} ({len(datas)} pregões). Valores líquidos de custos e IR.",
          "- **Reforço:** quando o ativo cai 15% abaixo do preço médio (e de novo com mais 12%), compra mais uma parcela de "
          "~R$ 250 com a reserva. Limites: 2 reforços por mês e nenhum ativo acima de 2x o peso-alvo. Não reforça se os "
          "proventos dos últimos 12 meses caíram mais de 10%.",
          "- **Realização de lucro:** posição acima de 2x o peso-alvo volta para o alvo.",
          "- **Saída por proventos:** ação de dividendos com proventos 30% menores em 12 meses, ou FII com rendimentos 25% "
          "menores, é vendida; volta quando os proventos se recuperam.",
          "- **Stop (só V4):** ação de valorização que cai 35% do topo é vendida; pode voltar depois de 60 pregões.",
          "- **Rebalanceamento a cada 3 meses** em todas as versões; FIIs só recebem compras. A reserva é recomposta para "
          "~1/6 da carteira.", ""]
    if avisos:
        md += ["**Avisos dos dados:** " + "; ".join(avisos) + ".", ""]
    md += ["## Resultado", "",
           "| Versão | Valor final líquido | Retorno | Ao ano | Queda máxima | Operações | IR pago |",
           "|---|---|---|---|---|---|---|"]
    for k, nome in linhas:
        r = res[k]
        md.append(f"| {nome} | {rs(r['liquido'])} | {pct(r['retorno'])} | {pct(r['anual_pct'], 1)} | "
                  f"−{r['queda'] * 100:.0f}% | {r['ops']} | {rs(r['ir'])} |")
    md += ["", "## O que o robô fez", "", "| Versão | Reforços | Realizações | Saídas por proventos | Stops | Voltas |",
           "|---|---|---|---|---|---|"]
    for k, nome in VERSOES:
        e = res[k]["eventos"]
        md.append(f"| {nome.split(' · ')[0]} | {e['reforço']} | {e['realização']} | {e['saída por proventos']} | "
                  f"{e['stop']} | {e['volta']} |")
    md += ["", "## Ano a ano (retorno bruto)", "", "| Versão | " + " | ".join(anos) + " |", "|---|" + "---|" * len(anos)]
    for k, nome in linhas:
        fa, ant, cel = res[k]["fim_ano"], CAPITAL, []
        for y in anos:
            cel.append(pct(fa[y] / ant - 1))
            ant = fa[y]
        md.append(f"| {nome.split(' · ')[0]} | " + " | ".join(cel) + " |")
    md += ["", "## Limitações", "",
           "- O robô só enxerga preço e proventos. Lucro, dívida, vacância e P/VP não entram no backtest (o Yahoo não traz); "
           "essas checagens ficam para a revisão trimestral.",
           "- O histórico de rendimentos de FIIs no Yahoo é incompleto nos primeiros anos; a regra de proventos só age "
           "quando há 24 meses de dados.",
           "- Período curto e ativos escolhidos hoje: viés de sobrevivência e de escolha.", ""]
    (saida.parent / "ROBO_REGRAS.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "resultado")
