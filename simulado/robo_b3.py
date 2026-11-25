"""Argos Trade B3 · robô SIMULADO (dinheiro de mentira), com as regras da V3 do backtest.

Roda todo dia útil depois do fechamento (GitHub Actions). Autônomo: decide sozinho, registra tudo e avisa no Telegram.

Carteira: R$ 6.000 = R$ 5.000 em 20 ativos (R$ 250 cada) + R$ 1.000 de reserva rendendo CDI.
Regras (backtest/ROBO_REGRAS.md, versão V3):
  - Reforço: ativo 15% abaixo do preço médio → compra mais R$ 250 com a reserva; 2º reforço com mais ~12% de queda.
    Até 2 reforços por mês, nenhum ativo acima de 2x o alvo, e só se os proventos de 12 meses não caíram mais de 10%.
  - Realização de lucro: posição acima de 2x o alvo volta para o alvo.
  - Saída por proventos: ação de dividendos com proventos −30% em 12 meses, ou FII com −25%, é vendida;
    volta quando os proventos se recuperam.
  - Rebalanceamento no primeiro pregão de cada trimestre; FIIs só recebem compras.
  - Queda de 35% do topo numa ação de valorização: só alerta, não vende.
Arquivos: estado.json, historico.csv, operacoes.csv, proventos.csv (nesta pasta).
"""
import csv, json, math, os, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

PASTA = Path(__file__).parent
ESTADO, HISTORICO = PASTA / "estado.json", PASTA / "historico.csv"
OPERACOES, PROVENTOS = PASTA / "operacoes.csv", PASTA / "proventos.csv"
BRASILIA = timezone(timedelta(hours=-3))
ROTULO = "🧪 Argos Trade B3 · SIMULADO"

VALORIZACAO = ["BPAC11", "ITUB4", "EMBJ3", "PRIO3", "SBSP3", "WEGE3", "CURY3", "GGBR4", "AXIA3", "FLRY3"]
DIVIDENDOS = ["PETR4", "TAEE11", "CPLE3", "CXSE3", "VIVT3"]
FIIS = ["KNCR11", "BTLG11", "KNRI11", "XPML11", "MCCI11"]
ATIVOS = VALORIZACAO + DIVIDENDOS + FIIS
REFS = ["BOVA11", "XFIX11"]

CAPITAL, RESERVA = 6_000.0, 1_000.0
FRACAO_RESERVA = RESERVA / CAPITAL
CUSTO = 0.0013
ORDEM_MIN = 30.0
REFORCO_1, REFORCO_2, REFORCOS_MES, TETO = 0.85, 0.75, 2, 2.0
CORTE_DIV_ACAO, CORTE_DIV_FII, SAUDE_MIN_REFORCO = 0.30, 0.25, -0.10
ALERTA_QUEDA = 0.35
IR_ACOES, IR_FII, IR_CAIXA, ISENCAO = 0.15, 0.20, 0.15, 20_000.0

YAHOO = ("https://query{n}.finance.yahoo.com/v8/finance/chart/{t}.SA"
         "?range=2y&interval=1d&events=div%2Csplit")
BCB = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json&dataInicial={i}&dataFinal={f}"
CAB = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "application/json"}


# ---------------------------------------------------------------- utilidades
def brl(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v, casas=1):
    return ("+" if v >= 0 else "−") + f"{abs(v) * 100:.{casas}f}".replace(".", ",") + "%"


def telegram(texto):
    token = (os.environ.get("TELEGRAM_TOKEN") or "").strip().removeprefix("bot")   # tolera espaço ou "bot" colado
    chat = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    print("\n--- mensagem ---\n" + texto + "\n----------------")
    if not token or not chat:
        print("(Telegram não configurado: mensagem só no registro)")
        return
    dados = urllib.parse.urlencode({"chat_id": chat, "text": texto}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", dados, timeout=30).read()
    except urllib.error.HTTPError as e:  # mostra o motivo do Telegram (sem expor o token)
        try:
            motivo = json.loads(e.read()).get("description", "")
        except Exception:
            motivo = ""
        print(f"Falha ao enviar para o Telegram: HTTP {e.code} {motivo}")
    except Exception as e:  # falha de aviso não derruba o robô
        print(f"Falha ao enviar para o Telegram: {type(e).__name__}")


def baixar_json(url):
    erro = None
    for k in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=CAB), timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:
            erro = e
            time.sleep(2 * (k + 1))
    raise RuntimeError(f"falha ao baixar dados ({type(erro).__name__})")


def cotacao(t):
    """Último fechamento (sem ajuste), data do pregão, proventos e desdobramentos dos últimos 2 anos."""
    j = None
    for n in (1, 2, 1):
        try:
            j = baixar_json(YAHOO.format(n=n, t=t))
            break
        except RuntimeError:
            continue
    if not j:
        raise RuntimeError(f"sem cotação de {t}")
    r = j["chart"]["result"][0]
    fech = [(ts, c) for ts, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]) if c]
    dia = lambda ts: datetime.fromtimestamp(ts, BRASILIA).date().isoformat()
    ev = r.get("events", {})
    divs = sorted((dia(int(x["date"])), float(x["amount"])) for x in (ev.get("dividends") or {}).values())
    splits = sorted((dia(int(x["date"])), float(x["numerator"]) / float(x["denominator"]))
                    for x in (ev.get("splits") or {}).values())
    return {"preco": float(fech[-1][1]), "data": dia(fech[-1][0]), "divs": divs, "splits": splits}


def cdi_desde(inicio, fim):
    """Taxas diárias do CDI (% ao dia) entre as datas, inclusive."""
    i = date.fromisoformat(inicio).strftime("%d/%m/%Y")
    f = date.fromisoformat(fim).strftime("%d/%m/%Y")
    out = {}
    for x in baixar_json(BCB.format(i=i, f=f)):
        d, m, a = x["data"].split("/")
        out[f"{a}-{m}-{d}"] = float(x["valor"])
    return out


def saude(divs, hoje):
    """Variação dos proventos dos últimos 12 meses contra os 12 anteriores (None se não dá para medir)."""
    h = date.fromisoformat(hoje)
    a = sum(v for d, v in divs if h - timedelta(365) < date.fromisoformat(d) <= h)
    b = sum(v for d, v in divs if h - timedelta(730) < date.fromisoformat(d) <= h - timedelta(365))
    return None if b <= 0 else a / b - 1


# ---------------------------------------------------------------- carteira (dicionário salvo em JSON)
def nova_carteira(caixa):
    return {"caixa": caixa, "qtd": {}, "pm": {}, "custos": 0.0, "ir_pago": 0.0, "ir_pendente": 0.0,
            "prej_comum": 0.0, "prej_fii": 0.0, "vendas_acoes_mes": 0.0, "ganho_acoes_mes": 0.0, "ganho_fii_mes": 0.0}


def valor(c, px):
    return c["caixa"] + sum(q * px[a] for a, q in c["qtd"].items())


def comprar(c, a, reais, p, ops, motivo):
    n = math.floor(min(reais, c["caixa"]) / (p * (1 + CUSTO)))
    if n <= 0 or n * p < ORDEM_MIN:
        return 0
    custo = n * p * CUSTO
    q = c["qtd"].get(a, 0)
    c["pm"][a] = (c["pm"].get(a, 0) * q + n * p + custo) / (q + n)
    c["qtd"][a] = q + n
    c["caixa"] -= n * p + custo
    c["custos"] += custo
    if ops is not None:
        ops.append({"tipo": "COMPRA", "ativo": a, "qtd": n, "preco": p, "valor": n * p, "custo": custo, "motivo": motivo})
    return n


def vender(c, a, reais, p, ops, motivo, minimo=ORDEM_MIN):
    n = min(c["qtd"].get(a, 0), math.floor(reais / p + 1e-9))
    if n <= 0 or n * p < minimo:
        return 0
    bruto, custo = n * p, n * p * CUSTO
    ganho = bruto - custo - n * c["pm"][a]
    if a in FIIS:
        c["ganho_fii_mes"] += ganho
    else:
        c["ganho_acoes_mes"] += ganho
        c["vendas_acoes_mes"] += bruto
    c["qtd"][a] -= n
    if c["qtd"][a] == 0:
        del c["qtd"][a]
        del c["pm"][a]
    c["caixa"] += bruto - custo
    c["custos"] += custo
    if ops is not None:
        ops.append({"tipo": "VENDA", "ativo": a, "qtd": n, "preco": p, "valor": bruto, "custo": custo,
                    "motivo": motivo, "ganho": ganho})
    return n


def fechar_mes(c):
    """Apura o IR do mês: ações (isentas até R$ 20 mil de vendas) e FIIs (20%), com prejuízo acumulado."""
    acoes = c["ganho_acoes_mes"] if c["vendas_acoes_mes"] > ISENCAO else min(c["ganho_acoes_mes"], 0)
    devido = 0.0
    for chave, ganho, aliq in (("prej_comum", acoes, IR_ACOES), ("prej_fii", c["ganho_fii_mes"], IR_FII)):
        base = ganho - c[chave]
        if base > 0:
            devido += base * aliq
            c[chave] = 0.0
        else:
            c[chave] = -base
    c["ir_pendente"] += devido
    pago = min(c["ir_pendente"], c["caixa"])
    c["caixa"] -= pago
    c["ir_pendente"] -= pago
    c["ir_pago"] += pago
    c["vendas_acoes_mes"] = c["ganho_acoes_mes"] = c["ganho_fii_mes"] = 0.0
    return pago


# ---------------------------------------------------------------- regras do dia
def decidir(est, px, dados, hoje, ops, alertas):
    c = est["carteira"]
    novo_mes = hoje[:7] != est["ultimo_pregao"][:7]
    novo_tri = (hoje[:4], (int(hoje[5:7]) - 1) // 3) != (est["ultimo_pregao"][:4], (int(est["ultimo_pregao"][5:7]) - 1) // 3)
    if novo_mes:
        pago = fechar_mes(c)
        if pago:
            alertas.append(f"🧾 IR do mês pago (DARF simulado): {brl(pago)}")
        est["reforcos_mes"] = 0
    sau = {a: saude(dados[a]["divs"], hoje) for a in DIVIDENDOS + FIIS}
    est["saude_proventos"] = {a: (round(s, 4) if s is not None else None) for a, s in sau.items()}
    v = valor(c, px)
    alvo = v * (1 - FRACAO_RESERVA) / len(ATIVOS)
    slot = (CAPITAL - RESERVA) / len(ATIVOS)

    # 1. saídas
    for a in list(c["qtd"]):
        s = sau.get(a)
        corte = CORTE_DIV_FII if a in FIIS else CORTE_DIV_ACAO
        if a in sau and s is not None and s < -corte:
            vender(c, a, c["qtd"][a] * px[a] + 1e-6, px[a], ops,
                   f"proventos de 12 meses caíram {abs(s) * 100:.0f}% (limite {corte * 100:.0f}%): tese de renda quebrada", minimo=0)
            est["fora"][a] = "proventos"
        elif c["qtd"][a] * px[a] > TETO * alvo:
            vender(c, a, c["qtd"][a] * px[a] - alvo, px[a], ops,
                   f"posição passou de 2x o alvo ({brl(c['qtd'][a] * px[a])}): realização de lucro")
    # volta de quem saiu por proventos
    for a, motivo in list(est["fora"].items()):
        if motivo == "proventos" and (sau.get(a) or 0) >= 0:
            del est["fora"][a]
            comprar(c, a, alvo, px[a], ops, "proventos se recuperaram: volta para a carteira")

    # 2. reforço nas quedas, com a reserva
    for a in ATIVOS:
        if a in est["fora"] or a not in c["qtd"] or est["reforcos_mes"] >= REFORCOS_MES:
            continue
        if px[a] >= c["pm"][a]:
            est["reforcos"][a] = 0
            continue
        k = est["reforcos"].get(a, 0)
        gatilho = REFORCO_1 if k == 0 else (REFORCO_2 / REFORCO_1 if k == 1 else 0)
        s = sau.get(a)
        if gatilho and px[a] <= c["pm"][a] * gatilho and (s is None or s > SAUDE_MIN_REFORCO) \
                and c["qtd"][a] * px[a] + slot <= TETO * alvo and c["caixa"] > slot * 1.05:
            queda = px[a] / c["pm"][a] - 1
            if comprar(c, a, slot, px[a], ops, f"{k + 1}º reforço: preço {abs(queda) * 100:.0f}% abaixo do preço médio, proventos em dia"):
                est["reforcos"][a] = k + 1
                est["reforcos_mes"] += 1

    # 3. rebalanceamento trimestral
    if novo_tri:
        v = valor(c, px)
        alvo = v * (1 - FRACAO_RESERVA) / len(ATIVOS)
        dentro = [a for a in ATIVOS if a not in est["fora"]]
        for a in dentro:
            excesso = c["qtd"].get(a, 0) * px[a] - alvo
            if excesso > 0 and a not in FIIS:
                vender(c, a, excesso, px[a], ops, "rebalanceamento trimestral: acima do alvo")
        for a in dentro:
            falta = alvo - c["qtd"].get(a, 0) * px[a]
            if falta > 0 and c["caixa"] - falta > v * FRACAO_RESERVA * 0.5:
                comprar(c, a, falta, px[a], ops, "rebalanceamento trimestral: abaixo do alvo")
        est["reforcos"] = {}

    # 4. alerta de queda forte (não vende)
    for a in VALORIZACAO:
        if a not in c["qtd"]:
            continue
        est["topo"][a] = max(est["topo"].get(a, px[a]), px[a])
        caiu = px[a] < est["topo"][a] * (1 - ALERTA_QUEDA)
        if caiu and not est["alertado"].get(a):
            alertas.append(f"⚠️ {a} caiu {pct(px[a] / est['topo'][a] - 1, 0)} do topo. Não vendo (o stop automático piorou o "
                           "backtest), mas vale revisar a tese na próxima revisão trimestral.")
        est["alertado"][a] = caiu


# ---------------------------------------------------------------- execução
def proventos_do_dia(carteiras, dados, desde, hoje, linhas):
    """Credita proventos e aplica desdobramentos com data entre o último pregão e hoje."""
    for nome, c in carteiras.items():
        for a, q in list(c["qtd"].items()):
            for d, fator in dados[a]["splits"]:
                if desde < d <= hoje:
                    c["qtd"][a] = round(q * fator)
                    c["pm"][a] /= fator
            for d, v in dados[a]["divs"]:
                if desde < d <= hoje:
                    c["caixa"] += v * c["qtd"][a]
                    if nome == "robo":
                        linhas.append([d, a, c["qtd"][a], f"{v:.6f}", f"{v * c['qtd'][a]:.2f}"])


def render_cdi(est, hoje):
    """Rende o caixa das carteiras pelo CDI desde o último pregão (líquido de 15% de IR)."""
    try:
        taxas = cdi_desde(est["ultimo_pregao"], hoje)
        dias = [d for d in sorted(taxas) if est["ultimo_pregao"] <= d < hoje]
        if taxas:
            est["ultima_taxa_cdi"] = taxas[max(taxas)]
    except RuntimeError:
        dias = None
    if dias is None:  # Banco Central fora do ar: usa a última taxa conhecida para 1 dia
        fatores = [1 + est["ultima_taxa_cdi"] / 100]
    else:
        fatores = [1 + taxas[d] / 100 for d in dias]
    f = math.prod(fatores)
    for c in (est["carteira"], est["parada"]):
        c["caixa"] *= 1 + (f - 1) * (1 - IR_CAIXA)
    est["indice_cdi"] *= 1 + (f - 1) * (1 - IR_CAIXA)


def main(agora=None):
    agora = agora or datetime.now(BRASILIA)
    if os.environ.get("TESTE_TELEGRAM") == "true":   # só confere se o bot está ligado; não mexe na carteira
        telegram(f"{ROTULO} · ✅ Teste do Telegram\nO bot do B3 está conectado. A carteira simulada começa no "
                 "fechamento de dia útil, às 18h30, e você recebe o resumo aqui todo dia útil.")
        return
    hoje = agora.date().isoformat()
    ref = cotacao("BOVA11")
    if ref["data"] != hoje and not os.environ.get("FORCAR"):
        print(f"Sem pregão hoje ({hoje}); último pregão: {ref['data']}. Nada a fazer.")
        return
    dados = {a: cotacao(a) for a in ATIVOS}
    dados["BOVA11"] = ref
    try:
        dados["XFIX11"] = cotacao("XFIX11")
    except RuntimeError:  # referência do IFIX indisponível: repete o último preço conhecido
        antigo = json.loads(ESTADO.read_text()).get("px_refs", {}) if ESTADO.exists() else {}
        dados["XFIX11"] = {"preco": antigo.get("XFIX11", 1.0), "divs": [], "splits": []}
    px = {a: d["preco"] for a, d in dados.items()}
    ops, alertas, prov = [], [], []

    if not ESTADO.exists():
        est = {"versao": 1, "inicio": hoje, "ultimo_pregao": hoje, "regras": "V3 (backtest/ROBO_REGRAS.md)",
               "carteira": nova_carteira(CAPITAL), "parada": nova_carteira(CAPITAL),
               "refs": {r: CAPITAL / px[r] for r in REFS}, "px_inicio": {r: px[r] for r in REFS},
               "indice_cdi": 1.0, "ultima_taxa_cdi": 0.05, "reforcos": {}, "reforcos_mes": 0,
               "fora": {}, "topo": {}, "alertado": {}, "operacoes": 0}
        slot = (CAPITAL - RESERVA) / len(ATIVOS)
        for a in ATIVOS:
            comprar(est["carteira"], a, slot, px[a], ops, "montagem inicial")
            comprar(est["parada"], a, slot, px[a], None, "")
        novo = True
    else:
        est = json.loads(ESTADO.read_text())
        if est["ultimo_pregao"] == hoje and not os.environ.get("FORCAR"):
            print("Já rodou hoje.")
            return
        render_cdi(est, hoje)
        proventos_do_dia({"robo": est["carteira"], "parada": est["parada"]}, dados, est["ultimo_pregao"], hoje, prov)
        decidir(est, px, dados, hoje, ops, alertas)
        novo = False
    est["ultimo_pregao"] = hoje
    est["operacoes"] += len(ops) if not novo else 0
    c = est["carteira"]
    v, vp = valor(c, px), valor(est["parada"], px)
    v_cdi = CAPITAL * est["indice_cdi"]
    v_refs = {r: est["refs"][r] * px[r] for r in REFS}
    est["pico"] = max(est.get("pico", v), v)
    est["px_refs"] = {r: px[r] for r in REFS}
    est["precos"] = {a: round(px[a], 4) for a in ATIVOS + REFS}   # usados pelo monitor web
    est["grupos"] = {"valorizacao": VALORIZACAO, "dividendos": DIVIDENDOS, "fiis": FIIS}
    est["capital"], est["reserva"] = CAPITAL, RESERVA
    est["ultima_execucao"] = agora.isoformat(timespec="minutes")

    # registros
    if not OPERACOES.exists():
        OPERACOES.write_text("data;tipo;ativo;quantidade;preco;valor;custo;motivo\n")
    with open(OPERACOES, "a", newline="") as f:
        w = csv.writer(f, delimiter=";")
        for o in ops:
            w.writerow([hoje, o["tipo"], o["ativo"], o["qtd"], f"{o['preco']:.2f}", f"{o['valor']:.2f}",
                        f"{o['custo']:.2f}", o["motivo"]])
    if prov:
        if not PROVENTOS.exists():
            PROVENTOS.write_text("data_com;ativo;quantidade;valor_por_cota;total\n")
        with open(PROVENTOS, "a", newline="") as f:
            csv.writer(f, delimiter=";").writerows(prov)
    if not HISTORICO.exists():
        HISTORICO.write_text("data;patrimonio;caixa;carteira_parada;cdi;ibovespa;ifix;operacoes\n")
    with open(HISTORICO, "a") as f:
        f.write(f"{hoje};{v:.2f};{c['caixa']:.2f};{vp:.2f};{v_cdi:.2f};{v_refs['BOVA11']:.2f};"
                f"{v_refs['XFIX11']:.2f};{len(ops)}\n")
    ESTADO.write_text(json.dumps(est, indent=1, ensure_ascii=False))

    # mensagem do dia
    if novo:
        lista = lambda g: ", ".join(g)
        telegram(f"{ROTULO} · Carteira nova iniciada em {agora:%d/%m/%Y}\n"
                 f"Dinheiro de mentira: {brl(CAPITAL)} = {brl(CAPITAL - RESERVA)} em 20 ativos (R$ 250 cada) "
                 f"+ {brl(RESERVA)} de reserva no CDI.\n"
                 f"Valorização: {lista(VALORIZACAO)}\nDividendos: {lista(DIVIDENDOS)}\nFIIs: {lista(FIIS)}\n"
                 f"Caixa após as compras: {brl(c['caixa'])}\n"
                 "Rodo todo dia útil depois do fechamento e decido sozinho: reforço nas quedas com a reserva, realizo lucro "
                 "quando uma posição passa de 2x o alvo, saio se os proventos despencarem e rebalanceio a cada trimestre.")
        return
    linhas = [f"{ROTULO} · 📊 Fechamento {agora:%d/%m}"]
    for o in ops:
        emoji = "🟢" if o["tipo"] == "COMPRA" else "🔴"
        linhas.append(f"{emoji} {o['tipo']} {o['qtd']} {o['ativo']} a {brl(o['preco'])} = {brl(o['valor'])}\n   Motivo: {o['motivo']}")
    if prov:
        total = sum(float(x[4]) for x in prov)
        linhas.append(f"💰 Proventos: {brl(total)} (" + ", ".join(f"{x[1]} {brl(float(x[4]))}" for x in prov) + ")")
    linhas += alertas
    if not ops:
        linhas.append("Nenhuma operação hoje: nenhum gatilho atingido.")
    dias = (date.fromisoformat(hoje) - date.fromisoformat(est["inicio"])).days
    linhas += ["",
               f"Patrimônio: {brl(v)} ({pct(v / CAPITAL - 1)} em {dias} dias) · caixa {brl(c['caixa'])}",
               f"Comparação: parada {brl(vp)} · CDI {brl(v_cdi)} · Ibovespa {brl(v_refs['BOVA11'])} · IFIX {brl(v_refs['XFIX11'])}"]
    if v < est["pico"] * 0.85:
        linhas.append(f"ℹ️ Patrimônio {pct(v / est['pico'] - 1, 0)} abaixo do pico. Sigo as regras normalmente.")
    telegram("\n".join(linhas))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        telegram(f"{ROTULO} · ⚠️ O robô não conseguiu rodar hoje.\nMotivo: {e}\n"
                 "Nada foi alterado na carteira simulada. Tento de novo no próximo dia útil.")
        raise
