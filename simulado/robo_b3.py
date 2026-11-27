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
VETOS, IR_MENSAL, PRECOS = PASTA / "vetos.csv", PASTA / "ir_mensal.csv", PASTA / "precos.json"
BRASILIA = timezone(timedelta(hours=-3))
ROTULO = "🧪 Argos Trade B3 · SIMULADO"

VALORIZACAO = ["BPAC11", "ITUB4", "EMBJ3", "PRIO3", "SBSP3", "WEGE3", "CURY3", "GGBR4", "AXIA3", "FLRY3"]
DIVIDENDOS = ["PETR4", "TAEE11", "CPLE3", "CXSE3", "VIVT3"]
FIIS = ["KNCR11", "BTLG11", "KNRI11", "VISC11", "MCCI11"]   # VISC11 entrou no lugar do XPML11 em 25/11/2026 (ANALISE.md, seção 9)
ATIVOS = VALORIZACAO + DIVIDENDOS + FIIS
REFS = ["BOVA11", "XFIX11"]

CAPITAL, RESERVA = 6_000.0, 1_000.0
FRACAO_RESERVA = RESERVA / CAPITAL
CUSTO = 0.0013
ORDEM_MIN = 30.0
REFORCO_1, REFORCO_2, REFORCOS_MES, TETO = 0.85, 0.75, 2, 2.0
CORTE_DIV_ACAO, CORTE_DIV_FII, SAUDE_MIN_REFORCO = 0.30, 0.25, -0.10
CORTE_PERSISTE = 40          # pregões seguidos (cerca de 2 meses) com o corte confirmado antes de vender
PAGAMENTOS_MIN_FII = 10      # FII com menos pagamentos que isso em 12 meses = histórico com buraco: não mede
APORTE_MAX = 750.0           # custo máximo acumulado num ativo (compra inicial + reforços)
QUEDA_MAX_REFORCO = 0.40     # não reforça ativo que já caiu mais que isso do preço médio
OBS_QUEDA, OBS_PREGOES = 0.35, 60   # ação de valorização 35% abaixo do topo e abaixo da média de 200 dias:
                                    # entra em observação (sem reforço); depois de 60 pregões assim, vende metade
FALHAS_MAX = 5               # mais ativos sem cotação que isso = falha geral: o robô não roda
ALERTA_QUEDA = 0.35
IR_ACOES, IR_FII, IR_CAIXA, ISENCAO = 0.15, 0.20, 0.15, 20_000.0

# Travas do porteiro de risco (nenhuma é afrouxada pelo próprio robô)
ORDEM_MAX = 0.15            # valor máximo de uma ordem, como fração do patrimônio
MAX_OPS_DIA = 8             # fora da montagem inicial e do rebalanceamento trimestral
VOL_MAX_DIA = 0.10          # ativo que mexe mais que isso no dia não é operado
SALTO_SUSPEITO = 0.25       # variação maior que isso sem desdobramento = dado suspeito
VENDAS_MES_LIMITE = 19_000.0  # margem para não perder a isenção de R$ 20 mil em ações
PREGOES_GRAFICO, MM_LONGA = 130, 200

YAHOO = ("https://query{n}.finance.yahoo.com/v8/finance/chart/{t}.SA"
         "?range=5y&interval=1d&events=div%2Csplit")
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
        return False
    dados = urllib.parse.urlencode({"chat_id": chat, "text": texto}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", dados, timeout=30).read()
        return True
    except urllib.error.HTTPError as e:  # mostra o motivo do Telegram (sem expor o token)
        try:
            motivo = json.loads(e.read()).get("description", "")
        except Exception:
            motivo = ""
        print(f"Falha ao enviar para o Telegram: HTTP {e.code} {motivo}")
    except Exception as e:  # falha de aviso não derruba o robô
        print(f"Falha ao enviar para o Telegram: {type(e).__name__}")
    return False


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
    """Último fechamento (sem ajuste), data do pregão, proventos e desdobramentos dos últimos 5 anos."""
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
    serie = [(dia(ts), round(float(c), 4)) for ts, c in fech[-(PREGOES_GRAFICO + MM_LONGA):]]
    return {"preco": float(fech[-1][1]), "data": dia(fech[-1][0]), "divs": divs, "splits": splits,
            "anterior": float(fech[-2][1]) if len(fech) > 1 else float(fech[-1][1]), "serie": serie}


def cdi_desde(inicio, fim):
    """Taxas diárias do CDI (% ao dia) entre as datas, inclusive."""
    i = date.fromisoformat(inicio).strftime("%d/%m/%Y")
    f = date.fromisoformat(fim).strftime("%d/%m/%Y")
    out = {}
    for x in baixar_json(BCB.format(i=i, f=f)):
        d, m, a = x["data"].split("/")
        out[f"{a}-{m}-{d}"] = float(x["valor"])
    return out


def saude(divs, hoje, fii=False):
    """Proventos dos últimos 12 meses contra a média anual dos 3 anos anteriores (None se não dá para medir).

    Comparar com a média de 3 anos evita vender por causa de um ano anterior com dividendo extraordinário.
    Em FII, janela com poucos pagamentos indica buraco no histórico do Yahoo e fica fora da conta.
    """
    h = date.fromisoformat(hoje)
    def janela(k):  # k = 0 são os últimos 12 meses; 1, 2 e 3 são os anos anteriores
        itens = [v for d, v in divs if h - timedelta(365 * (k + 1)) < date.fromisoformat(d) <= h - timedelta(365 * k)]
        return sum(itens), len(itens)
    atual, n = janela(0)
    if fii and n < PAGAMENTOS_MIN_FII:
        return None
    anteriores = [t for t, q in (janela(k) for k in (1, 2, 3)) if t > 0 and (not fii or q >= PAGAMENTOS_MIN_FII)]
    if not anteriores:
        return None
    return atual / (sum(anteriores) / len(anteriores)) - 1


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
    isento = c["vendas_acoes_mes"] <= ISENCAO
    acoes = c["ganho_acoes_mes"] if not isento else min(c["ganho_acoes_mes"], 0)
    resumo = {"vendas_acoes": c["vendas_acoes_mes"], "ganho_acoes": c["ganho_acoes_mes"],
              "ganho_fiis": c["ganho_fii_mes"], "isento_acoes": isento}
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
    resumo.update(ir_devido=devido, ir_pago=pago)
    return resumo


# ---------------------------------------------------------------- porteiro de risco
class Porteiro:
    """Confere cada ordem proposta contra as travas. Só o que ele aprova é executado; os vetos ficam registrados."""

    def __init__(self, c, px, info, registro):
        self.c, self.px, self.info, self.log = c, px, info, registro
        self.patrimonio = valor(c, px)
        self.aprovadas, self.vetos, self.lados, self.n_ops = 0, [], {}, 0

    def trava(self, tipo, a, reais, livre, tese):
        i = self.info.get(a, {})
        if i.get("velho"):
            return f"cotação velha (último negócio em {i['data'][8:10]}/{i['data'][5:7]})" if i.get("data") else "sem cotação hoje"
        if i.get("suspeito"):
            return f"preço suspeito ({pct(i['var'], 0)} no dia sem desdobramento)"
        if abs(i.get("var", 0)) > VOL_MAX_DIA:
            return f"volatilidade extrema ({pct(i['var'], 0)} no dia)"
        if self.lados.get(a) not in (None, tipo):
            return "sem day trade (já houve operação contrária hoje)"
        if reais > ORDEM_MAX * self.patrimonio:
            return f"ordem acima de {ORDEM_MAX:.0%} do patrimônio"
        if not livre and self.n_ops >= MAX_OPS_DIA:
            return f"limite de {MAX_OPS_DIA} operações no dia"
        if tipo == "VENDA" and a not in FIIS and not tese \
                and self.c["vendas_acoes_mes"] + reais > VENDAS_MES_LIMITE:
            return "vendas de ações no mês perto de R$ 20 mil (preserva a isenção de IR)"
        return None

    def comprar(self, a, reais, ops, motivo, livre=False):
        p = self.px[a]
        reais = min(reais, self.c["caixa"])
        if not p:
            return self._passar("COMPRA", a, reais, motivo, livre, False) and 0
        if math.floor(reais / (p * (1 + CUSTO))) * p < max(ORDEM_MIN, p):
            return 0  # não viraria ordem: nada a aprovar
        return self._passar("COMPRA", a, reais, motivo, livre, False) and self._feito(
            "COMPRA", a, comprar(self.c, a, reais, p, ops, motivo))

    def vender(self, a, reais, ops, motivo, livre=False, tese=False, minimo=ORDEM_MIN):
        p = self.px[a]
        if not p:
            return 0
        n = min(self.c["qtd"].get(a, 0), math.floor(reais / p + 1e-9))
        if n <= 0 or n * p < minimo:
            return 0
        return self._passar("VENDA", a, n * p, motivo, livre, tese) and self._feito(
            "VENDA", a, vender(self.c, a, reais, p, ops, motivo, minimo))

    def _passar(self, tipo, a, reais, motivo, livre, tese):
        t = self.trava(tipo, a, reais, livre, tese)
        if t:
            self.vetos.append({"tipo": tipo, "ativo": a, "valor": round(reais, 2), "trava": t, "motivo": motivo})
            self.log.append(f"porteiro: VETO {tipo.lower()} {a} {brl(reais)} · {t}")
            return False
        return True

    def _feito(self, tipo, a, n):
        if n:
            self.aprovadas += 1
            self.n_ops += 1
            self.lados[a] = tipo
            self.log.append(f"executor: {tipo.lower()} {n} {a} a {brl(self.px[a])}")
        return n


# ---------------------------------------------------------------- regras do dia
def decidir(est, P, px, dados, hoje, ops, alertas):
    c = est["carteira"]
    novo_mes = hoje[:7] != est["ultimo_pregao"][:7]
    novo_tri = (hoje[:4], (int(hoje[5:7]) - 1) // 3) != (est["ultimo_pregao"][:4], (int(est["ultimo_pregao"][5:7]) - 1) // 3)
    if novo_mes:
        r = fechar_mes(c)
        if not IR_MENSAL.exists():
            IR_MENSAL.write_text("mes;vendas_acoes;ganho_acoes;isento_acoes;ganho_fiis;ir_devido;ir_pago\n")
        with open(IR_MENSAL, "a") as f:
            f.write(f"{est['ultimo_pregao'][:7]};{r['vendas_acoes']:.2f};{r['ganho_acoes']:.2f};"
                    f"{'sim' if r['isento_acoes'] else 'não'};{r['ganho_fiis']:.2f};{r['ir_devido']:.2f};{r['ir_pago']:.2f}\n")
        if r["ir_pago"]:
            alertas.append(f"🧾 IR do mês pago (DARF simulado): {brl(r['ir_pago'])}")
        est["reforcos_mes"] = 0
    sau = {a: saude(dados[a]["divs"], hoje, a in FIIS) for a in DIVIDENDOS + FIIS}
    corte_dias = est.setdefault("corte_dias", {})
    est["saude_proventos"] = {a: (round(s, 4) if s is not None else None) for a, s in sau.items()}
    v = valor(c, px)
    alvo = v * (1 - FRACAO_RESERVA) / len(ATIVOS)
    slot = (CAPITAL - RESERVA) / len(ATIVOS)

    # 1. saídas
    for a in list(c["qtd"]):
        s = sau.get(a)
        corte = CORTE_DIV_FII if a in FIIS else CORTE_DIV_ACAO
        cortou = a in sau and s is not None and s < -corte
        corte_dias[a] = corte_dias.get(a, 0) + 1 if cortou else 0
        if cortou and corte_dias[a] == 1:
            alertas.append(f"ℹ️ {a}: proventos de 12 meses {abs(s) * 100:.0f}% abaixo da média dos 3 anos anteriores. "
                           f"Em observação: saio se continuar assim por {CORTE_PERSISTE} pregões.")
        if cortou and corte_dias[a] >= CORTE_PERSISTE:
            if P.vender(a, c["qtd"][a] * px[a] + 1e-6, ops,
                        f"proventos de 12 meses {abs(s) * 100:.0f}% abaixo da média de 3 anos (limite {corte * 100:.0f}%) "
                        f"há {CORTE_PERSISTE} pregões: tese de renda quebrada",
                        tese=True, minimo=0):
                est["fora"][a] = "proventos"
        elif c["qtd"][a] * px[a] > TETO * alvo:
            P.vender(a, c["qtd"][a] * px[a] - alvo, ops,
                     f"posição passou de 2x o alvo ({brl(c['qtd'][a] * px[a])}): realização de lucro")
    # volta de quem saiu por proventos; entrada de quem ficou pendente (ex.: cotação velha na montagem)
    for a, motivo in list(est["fora"].items()):
        if motivo == "proventos" and (sau.get(a) or 0) >= 0:
            del est["fora"][a]
    for a in ATIVOS:
        if a not in c["qtd"] and a not in est["fora"]:
            P.comprar(a, alvo, ops, "entrada na carteira (posição pendente ou proventos recuperados)", livre=True)

    # 1b. saída das ações de valorização: observação e venda de metade
    obs = est.setdefault("obs", {})
    for a in VALORIZACAO:
        if a not in c["qtd"]:
            obs.pop(a, None)
            continue
        est["topo"][a] = max(est["topo"].get(a, px[a]), px[a])
        mm = P.info.get(a, {}).get("mm200")
        ruim = bool(mm) and px[a] < est["topo"][a] * (1 - OBS_QUEDA) and px[a] < mm
        obs[a] = obs.get(a, 0) + 1 if ruim else 0
        if obs[a] == 1:
            alertas.append(f"ℹ️ {a}: {pct(px[a] / est['topo'][a] - 1, 0)} do topo e abaixo da média de 200 dias. Em observação: "
                           f"não reforço, e vendo metade se continuar assim por {OBS_PREGOES} pregões.")
        if obs[a] >= OBS_PREGOES:
            if P.vender(a, c["qtd"][a] * px[a] / 2, ops,
                        f"{OBS_PREGOES} pregões em observação ({pct(px[a] / est['topo'][a] - 1, 0)} do topo, abaixo da média "
                        "de 200 dias): vende metade", tese=True, minimo=0):
                obs[a] = 0

    # 1c. sobra de caixa da montagem: como só dá para comprar cotas inteiras, sobrou dinheiro além da reserva.
    # Uma única vez, completa as posições que ficaram mais longe do alvo, sem deixar o caixa abaixo da reserva.
    if not est.get("sobra_aplicada"):
        v = valor(c, px)
        alvo_m, piso = v * (1 - FRACAO_RESERVA) / len(ATIVOS), v * FRACAO_RESERVA
        for cart, porteiro in ((c, P), (est["parada"], None)):   # a carteira parada recebe o mesmo ajuste
            faltas = sorted(((alvo_m - cart["qtd"].get(a, 0) * px[a], a) for a in ATIVOS
                             if a in cart["qtd"] and a not in est["fora"] and px[a]), reverse=True)
            for falta, a in faltas:
                n = round(falta / px[a])
                gasto = n * px[a] * (1 + CUSTO)
                if n < 1 or cart["caixa"] - gasto < piso:
                    continue
                if porteiro:
                    porteiro.comprar(a, gasto + 0.01, ops, "completa a posição com a sobra de caixa da montagem", livre=True)
                else:
                    comprar(cart, a, gasto + 0.01, px[a], None, "")
        est["sobra_aplicada"] = True

    # 2. reforço nas quedas, com a reserva
    for a in ATIVOS:
        if a in est["fora"] or a not in c["qtd"] or est["reforcos_mes"] >= REFORCOS_MES or obs.get(a, 0) > 0:
            continue
        if px[a] >= c["pm"][a]:
            est["reforcos"][a] = 0
            continue
        k = est["reforcos"].get(a, 0)
        gatilho = REFORCO_1 if k == 0 else (REFORCO_2 / REFORCO_1 if k == 1 else 0)
        s = sau.get(a)
        if gatilho and px[a] <= c["pm"][a] * gatilho and (s is None or s > SAUDE_MIN_REFORCO) \
                and px[a] >= c["pm"][a] * (1 - QUEDA_MAX_REFORCO) \
                and c["qtd"][a] * c["pm"][a] + slot <= APORTE_MAX \
                and c["qtd"][a] * px[a] + slot <= TETO * alvo and c["caixa"] > slot * 1.05:
            queda = px[a] / c["pm"][a] - 1
            if P.comprar(a, slot, ops, f"{k + 1}º reforço: preço {abs(queda) * 100:.0f}% abaixo do preço médio, proventos em dia"):
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
                P.vender(a, excesso, ops, "rebalanceamento trimestral: acima do alvo", livre=True)
        for a in dentro:
            falta = alvo - c["qtd"].get(a, 0) * px[a]
            if falta > 0 and obs.get(a, 0) == 0 and c["caixa"] - falta > v * FRACAO_RESERVA * 0.5:
                P.comprar(a, falta, ops, "rebalanceamento trimestral: abaixo do alvo", livre=True)
        est["reforcos"] = {}

    est["alertado"] = {a: obs.get(a, 0) > 0 for a in VALORIZACAO if a in c["qtd"]}   # usado pelo monitor


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
    return dias is not None


def coletar(hoje, ref, registro, alertas, ultimos, susp_dias):
    """Baixa as cotações e marca o que não é confiável: cotação velha, salto suspeito, volatilidade extrema."""
    dados, falhou = {"BOVA11": ref}, []
    for a in ATIVOS:
        try:
            dados[a] = cotacao(a)
        except Exception:  # um ativo sem cotação não derruba o dia: fica de fora das operações
            ult = ultimos.get(a) or 0.0
            dados[a] = {"preco": ult, "data": "", "divs": [], "splits": [], "anterior": ult, "serie": [], "falhou": True}
            falhou.append(a)
    if len(falhou) > FALHAS_MAX:
        raise RuntimeError(f"sem cotação de {len(falhou)} ativos ({', '.join(falhou)}): falha geral dos dados")
    try:
        dados["XFIX11"] = cotacao("XFIX11")
    except RuntimeError:  # referência do IFIX indisponível: repete o último preço conhecido
        antigo = json.loads(ESTADO.read_text()).get("px_refs", {}) if ESTADO.exists() else {}
        dados["XFIX11"] = {"preco": antigo.get("XFIX11", 1.0), "data": hoje, "divs": [], "splits": [],
                           "anterior": antigo.get("XFIX11", 1.0), "serie": []}
        registro.append("coletor: XFIX11 indisponível, repetido o último preço")
    px, info = {}, {}
    for a, d in dados.items():
        var = d["preco"] / d["anterior"] - 1 if d.get("anterior") else 0.0
        if d.get("falhou"):
            d["data"] = ""
        split_hoje = any(x[0] == d["data"] for x in d["splits"])
        bom = ultimos.get(a) or d.get("anterior") or d["preco"]      # último preço em que o robô confiou
        salto = d["preco"] / bom - 1 if bom else 0.0
        suspeito = abs(salto) > SALTO_SUSPEITO and not split_hoje
        if suspeito and susp_dias.get(a, 0) >= 2:   # 3 pregões seguidos no novo patamar: o preço é real
            suspeito = False
            registro.append(f"coletor: {a} aceito no novo patamar depois de 3 pregões")
        susp_dias[a] = susp_dias.get(a, 0) + 1 if suspeito else 0
        fech = [x for _, x in d.get("serie") or []]
        i = {"data": d["data"], "var": round(salto if suspeito else var, 4), "velho": d["data"] != hoje, "suspeito": suspeito,
             "mm200": sum(fech[-MM_LONGA:]) / MM_LONGA if len(fech) >= MM_LONGA else None}
        px[a] = bom if suspeito else d["preco"]   # dado suspeito não entra na conta do patrimônio
        info[a] = i
        if a in ATIVOS and suspeito:
            alertas.append(f"⏸️ {a}: preço suspeito ({pct(salto, 0)} sem desdobramento). Mantenho o último preço confiável e "
                           "não opero nele hoje.")
        elif a in falhou:
            alertas.append(f"⏸️ {a}: sem cotação no Yahoo hoje (código mudou ou falha de dados). Mantenho o último preço e "
                           "não opero nele; se repetir, vale conferir o código do ativo.")
        elif a in ATIVOS and i["velho"]:
            alertas.append(f"⏸️ {a}: sem negócio hoje (última cotação de {d['data'][8:10]}/{d['data'][5:7]}). Não opero nele hoje.")
    velhos = [a for a in ATIVOS if info[a]["velho"]]
    susp = [a for a in ATIVOS if info[a]["suspeito"]]
    vol = [a for a in ATIVOS if abs(info[a]["var"]) > VOL_MAX_DIA and not info[a]["suspeito"]]
    registro.append(f"coletor: {len(ATIVOS) - len(velhos) - len(susp)} de {len(ATIVOS)} ativos com cotação de hoje"
                    + (f" · velhos: {', '.join(velhos)}" if velhos else "")
                    + (f" · suspeitos: {', '.join(susp)}" if susp else "")
                    + (f" · mais de 10% no dia: {', '.join(vol)}" if vol else ""))
    return dados, px, info, {"ok": len(ATIVOS) - len(velhos) - len(susp), "total": len(ATIVOS),
                             "velhos": velhos, "suspeitos": susp, "volateis": vol}


def salvar_precos(dados):
    """Últimos 130 fechamentos e a média de 200 dias de cada ativo, para o gráfico do monitor."""
    datas = [d for d, _ in dados["BOVA11"]["serie"]][-PREGOES_GRAFICO:]
    saida = {"datas": datas, "fech": {}, "mm200": {}}
    for a in ATIVOS:
        serie = dados[a]["serie"]
        por_dia, mm, ult = dict(serie), {}, None
        valores = [c for _, c in serie]
        for k, (d, _) in enumerate(serie):
            if k + 1 >= MM_LONGA:
                mm[d] = round(sum(valores[k + 1 - MM_LONGA:k + 1]) / MM_LONGA, 4)
        saida["fech"][a] = [por_dia.get(d) for d in datas]
        saida["mm200"][a] = [mm.get(d) for d in datas]
    PRECOS.write_text(json.dumps(saida, separators=(",", ":")))


def relatorio_semanal(est, hoje):
    """Resumo da semana (segunda a sexta) a partir do histórico. Devolve o texto ou None."""
    with open(HISTORICO) as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    seg = date.fromisoformat(hoje) - timedelta(days=date.fromisoformat(hoje).weekday())
    dom = (seg + timedelta(days=6)).isoformat()
    semana = [x for x in linhas if seg.isoformat() <= x["data"] <= dom]
    antes = [x for x in linhas if x["data"] < seg.isoformat()]
    if not semana:
        return None
    base = antes[-1] if antes else {k: CAPITAL for k in ("patrimonio", "carteira_parada", "cdi", "ibovespa", "ifix")}
    fim = semana[-1]
    var = lambda k: float(fim[k]) / float(base[k]) - 1
    with open(OPERACOES) as f:
        ops = [o for o in csv.DictReader(f, delimiter=";") if seg.isoformat() <= o["data"] <= dom and o["motivo"] != "montagem inicial"]
    prov = 0.0
    if PROVENTOS.exists():
        with open(PROVENTOS) as f:
            prov = sum(float(p["total"]) for p in csv.DictReader(f, delimiter=";") if seg.isoformat() <= p["data_com"] <= dom)
    vetos = 0
    if VETOS.exists():
        with open(VETOS) as f:
            vetos = sum(1 for x in csv.DictReader(f, delimiter=";") if seg.isoformat() <= x["data"] <= dom)
    v = float(fim["patrimonio"])
    return (f"{ROTULO} · 🗓️ Relatório da semana ({seg:%d/%m} a {date.fromisoformat(semana[-1]['data']):%d/%m})\n"
            f"Patrimônio: {brl(v)} · semana {pct(var('patrimonio'))} · desde o início {pct(v / CAPITAL - 1)}\n"
            f"Na semana: parada {pct(var('carteira_parada'))} · CDI {pct(var('cdi'), 2)} · "
            f"Ibovespa {pct(var('ibovespa'))} · IFIX {pct(var('ifix'))}\n"
            f"Operações: {len(ops)} ({sum(o['tipo'] == 'COMPRA' for o in ops)} compras, "
            f"{sum(o['tipo'] == 'VENDA' for o in ops)} vendas) · vetos do porteiro: {vetos}\n"
            f"Proventos na semana: {brl(prov)} · caixa: {brl(float(fim['caixa']))}\n"
            f"Fora da carteira: {', '.join(est['fora']) or 'nenhum'}")


def main(agora=None):
    agora = agora or datetime.now(BRASILIA)
    if os.environ.get("TESTE_TELEGRAM") == "true":   # só confere se o bot está ligado; não mexe na carteira
        telegram(f"{ROTULO} · ✅ Teste do Telegram\nO bot do B3 está conectado. A carteira simulada começa no "
                 "fechamento de dia útil, às 19h15, e você recebe o resumo aqui todo dia útil.")
        return
    ref = cotacao("BOVA11")
    # O dia processado é o do último pregão que o Yahoo mostra, não o do relógio: assim uma execução atrasada
    # (depois da meia-noite) ainda registra o fechamento certo. Pregão em andamento não é fechamento.
    hoje = ref["data"]
    if hoje == agora.date().isoformat() and (agora.hour, agora.minute) < (18, 30) and not os.environ.get("FORCAR"):
        print(f"Pregão de {hoje} ainda em andamento. Nada a fazer.")
        return
    dia = date.fromisoformat(hoje)
    ops, alertas, prov, registro = [], [], [], []
    anterior = json.loads(ESTADO.read_text()) if ESTADO.exists() else {}
    if anterior.get("ultimo_pregao", "") >= hoje and not os.environ.get("FORCAR"):
        print(f"O pregão de {hoje} já foi processado. Nada a fazer.")
        return
    susp_dias = anterior.get("suspeito_dias", {})
    dados, px, info, coleta = coletar(hoje, ref, registro, alertas, anterior.get("precos", {}), susp_dias)

    if not anterior:
        est = {"versao": 2, "inicio": hoje, "ultimo_pregao": hoje, "regras": "V3 (backtest/ROBO_REGRAS.md)",
               "carteira": nova_carteira(CAPITAL), "parada": nova_carteira(CAPITAL),
               "refs": {r: CAPITAL / px[r] for r in REFS}, "px_inicio": {r: px[r] for r in REFS},
               "indice_cdi": 1.0, "ultima_taxa_cdi": 0.05, "reforcos": {}, "reforcos_mes": 0,
               "fora": {}, "topo": {}, "alertado": {}, "operacoes": 0}
        P = Porteiro(est["carteira"], px, info, registro)
        slot = (CAPITAL - RESERVA) / len(ATIVOS)
        for a in ATIVOS:
            P.comprar(a, slot, ops, "montagem inicial", livre=True)
            if px[a] and not info[a]["velho"]:
                comprar(est["parada"], a, slot, px[a], None, "")
            else:
                est.setdefault("parada_pendente", []).append(a)
        registro.append(f"estratégia: montagem inicial, {len(ATIVOS)} compras de {brl(slot)} propostas")
        novo, cdi_ok = True, True
    else:
        est = anterior
        cdi_ok = render_cdi(est, hoje)
        if not cdi_ok:
            registro.append("coletor: Banco Central fora do ar, CDI do dia estimado pela última taxa")
        proventos_do_dia({"robo": est["carteira"], "parada": est["parada"]}, dados, est["ultimo_pregao"], hoje, prov)
        for a in list(est.get("parada_pendente", [])):   # a carteira parada também entra no ativo que faltou
            if px[a] and not info[a]["velho"] and not info[a]["suspeito"]:
                comprar(est["parada"], a, (CAPITAL - RESERVA) / len(ATIVOS), px[a], None, "")
                est["parada_pendente"].remove(a)
        P = Porteiro(est["carteira"], px, info, registro)
        decidir(est, P, px, dados, hoje, ops, alertas)
        registro.append(f"estratégia: {len(ATIVOS)} ativos checados, {P.aprovadas + len(P.vetos)} ordens propostas")
        novo = False
    c = est["carteira"]
    # sinal de dívida ou saldo impossível: para tudo antes de gravar
    if c["caixa"] < -0.01 or any(q < 0 for q in c["qtd"].values()):
        raise RuntimeError("🚨 saldo inconsistente (caixa ou quantidade negativa). Nada foi gravado; revisar o robô.")
    registro.append(f"porteiro: {P.aprovadas} aprovadas, {len(P.vetos)} vetadas")
    est["ultimo_pregao"] = hoje
    est["operacoes"] += len(ops) if not novo else 0
    v, vp = valor(c, px), valor(est["parada"], px)
    v_cdi = CAPITAL * est["indice_cdi"]
    v_refs = {r: est["refs"][r] * px[r] for r in REFS}
    est["pico"] = max(est.get("pico", v), v)
    est["px_refs"] = {r: px[r] for r in REFS}
    est["precos"] = {a: round(px[a], 4) for a in ATIVOS + REFS}   # usados pelo monitor web
    est["suspeito_dias"] = susp_dias
    est["variacao_dia"] = {a: info[a]["var"] for a in ATIVOS}
    est["grupos"] = {"valorizacao": VALORIZACAO, "dividendos": DIVIDENDOS, "fiis": FIIS}
    est["capital"], est["reserva"] = CAPITAL, RESERVA
    est["ultima_execucao"] = agora.isoformat(timespec="minutes")
    est["mm200"] = {a: round(info[a]["mm200"], 4) for a in VALORIZACAO if info[a].get("mm200")}
    est["limites"] = {"obs_queda": OBS_QUEDA, "obs_pregoes": OBS_PREGOES, "aporte_max": APORTE_MAX, "queda_max_reforco": QUEDA_MAX_REFORCO, "corte_persiste": CORTE_PERSISTE}
    est["travas"] = {"ordem_max": ORDEM_MAX, "max_ops_dia": MAX_OPS_DIA, "vol_max_dia": VOL_MAX_DIA,
                     "salto_suspeito": SALTO_SUSPEITO, "vendas_mes_limite": VENDAS_MES_LIMITE}
    registro.append(f"diário: patrimônio {brl(v)} · caixa {brl(c['caixa'])} · {len(ops)} operações · {len(prov)} proventos")
    est["fechamento"] = {"data": hoje, "coletor": coleta, "cdi_ok": cdi_ok,
                         "propostas": P.aprovadas + len(P.vetos), "aprovadas": P.aprovadas,
                         "vetos": P.vetos, "operacoes": len(ops), "proventos": len(prov),
                         "alertas": alertas, "telegram": None, "registro": registro}

    # registros
    if not OPERACOES.exists():
        OPERACOES.write_text("data;tipo;ativo;quantidade;preco;valor;custo;motivo\n")
    with open(OPERACOES, "a", newline="") as f:
        w = csv.writer(f, delimiter=";")
        for o in ops:
            w.writerow([hoje, o["tipo"], o["ativo"], o["qtd"], f"{o['preco']:.2f}", f"{o['valor']:.2f}",
                        f"{o['custo']:.2f}", o["motivo"]])
    if P.vetos:
        if not VETOS.exists():
            VETOS.write_text("data;tipo;ativo;valor;trava;motivo\n")
        with open(VETOS, "a", newline="") as f:
            w = csv.writer(f, delimiter=";")
            for x in P.vetos:
                w.writerow([hoje, x["tipo"], x["ativo"], f"{x['valor']:.2f}", x["trava"], x["motivo"]])
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
    try:
        salvar_precos(dados)
    except Exception as e:  # o gráfico do monitor não pode derrubar o robô
        registro.append(f"diário: histórico de preços não salvo ({type(e).__name__})")
    ESTADO.write_text(json.dumps(est, indent=1, ensure_ascii=False))

    # mensagem do dia
    if novo:
        lista = lambda g: ", ".join(g)
        texto = (f"{ROTULO} · Carteira nova iniciada em {dia:%d/%m/%Y}\n"
                 f"Dinheiro de mentira: {brl(CAPITAL)} = {brl(CAPITAL - RESERVA)} em 20 ativos (R$ 250 cada) "
                 f"+ {brl(RESERVA)} de reserva no CDI.\n"
                 f"Valorização: {lista(VALORIZACAO)}\nDividendos: {lista(DIVIDENDOS)}\nFIIs: {lista(FIIS)}\n"
                 f"Compras feitas: {len(ops)} de {len(ATIVOS)} · caixa após as compras: {brl(c['caixa'])}\n"
                 + "".join(a + "\n" for a in alertas) +
                 "".join(f"⏸️ Porteiro vetou {x['ativo']}: {x['trava']}. Entra quando o dado normalizar.\n" for x in P.vetos) +
                 "Rodo todo dia útil às 19h15 e decido sozinho: reforço nas quedas com a reserva, rebalanceio a cada trimestre, "
                 "saio se os proventos despencarem por 2 meses e vendo metade da ação de valorização que ficar 60 pregões em queda forte. "
                 "Toda ordem passa pelo porteiro de risco.")
    else:
        linhas = [f"{ROTULO} · 📊 Fechamento {dia:%d/%m}"]
        for o in ops:
            emoji = "🟢" if o["tipo"] == "COMPRA" else "🔴"
            linhas.append(f"{emoji} {o['tipo']} {o['qtd']} {o['ativo']} a {brl(o['preco'])} = {brl(o['valor'])}\n   Motivo: {o['motivo']}")
        for x in P.vetos:
            linhas.append(f"⏸️ Porteiro vetou {x['tipo'].lower()} de {x['ativo']} ({brl(x['valor'])}): {x['trava']}")
        if prov:
            total = sum(float(x[4]) for x in prov)
            linhas.append(f"💰 Proventos: {brl(total)} (" + ", ".join(f"{x[1]} {brl(float(x[4]))}" for x in prov) + ")")
        linhas += alertas
        if not ops and not P.vetos:
            linhas.append("Nenhuma operação hoje: nenhum gatilho atingido.")
        dias = (date.fromisoformat(hoje) - date.fromisoformat(est["inicio"])).days
        linhas += ["",
                   f"Patrimônio: {brl(v)} ({pct(v / CAPITAL - 1)} em {dias} dias) · caixa {brl(c['caixa'])}",
                   f"Comparação: parada {brl(vp)} · CDI {brl(v_cdi)} · Ibovespa {brl(v_refs['BOVA11'])} · IFIX {brl(v_refs['XFIX11'])}"]
        if v < est["pico"] * 0.85:
            linhas.append(f"ℹ️ Patrimônio {pct(v / est['pico'] - 1, 0)} abaixo do pico. Sigo as regras normalmente.")
        texto = "\n".join(linhas)
    enviado = telegram(texto)
    # relatório semanal: no fechamento de sexta; se a sexta não teve pregão, sai no primeiro pregão seguinte
    semana = "{}-S{:02d}".format(*dia.isocalendar()[:2])
    if not novo:
        ref_dia = None
        if dia.weekday() == 4 and est.get("relatorio_semana") != semana:
            ref_dia, marca = hoje, semana
        elif est.get("semana_atual") not in (None, semana) and est.get("relatorio_semana") != est["semana_atual"]:
            ref_dia, marca = (dia - timedelta(days=dia.weekday() + 3)).isoformat(), est["semana_atual"]
        if ref_dia:
            txt = relatorio_semanal(est, ref_dia)
            if txt:
                telegram(txt)
            est["relatorio_semana"] = marca
    est["semana_atual"] = semana
    est["fechamento"]["telegram"] = "enviado" if enviado else "falhou ou não configurado"
    ESTADO.write_text(json.dumps(est, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        nivel = "" if str(e).startswith("🚨") else "🛑 "
        telegram(f"{ROTULO} · {nivel}O robô não conseguiu rodar hoje.\nMotivo: {e}\n"
                 "Nada foi alterado na carteira simulada. Tento de novo no próximo dia útil.")
        raise
