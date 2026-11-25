"""Baixa os dados do backtest: cotações diárias ajustadas (Yahoo Finance) e o CDI (Banco Central).

Uso: python dados.py <pasta_destino>
Gera:
  <pasta>/precos.csv  data + uma coluna por ativo (fechamento ajustado por proventos, em R$)
  <pasta>/cdi.csv     data, taxa (CDI do dia, em % ao dia)

Roda no GitHub Actions, que tem acesso a esses sites.
"""
import csv, json, sys, time, urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

from config import CARTEIRAS, INICIO, REFERENCIA_BOLSA

YAHOO = ("https://query{n}.finance.yahoo.com/v8/finance/chart/{t}.SA"
         "?period1={p1}&period2={p2}&interval=1d&events=div%2Csplit&includeAdjustedClose=true")
BCB = ("https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados"
       "?formato=json&dataInicial={i}&dataFinal={f}")
CABECALHO = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "application/json"}


def baixar(url, tentativas=4):
    erro = None
    for k in range(tentativas):
        try:
            req = urllib.request.Request(url, headers=CABECALHO)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:  # rede instável: espera e tenta de novo
            erro = e
            time.sleep(2 * (k + 1))
    raise RuntimeError(f"falha ao baixar {url}: {erro}")


def cotacoes(ticker):
    p1 = int(datetime.fromisoformat(INICIO).replace(tzinfo=timezone.utc).timestamp())
    p2 = int(time.time())
    erro = None
    for n in (1, 2):
        try:
            j = baixar(YAHOO.format(n=n, t=ticker, p1=p1, p2=p2))
            break
        except RuntimeError as e:
            erro = e
    else:
        raise erro
    r = j["chart"]["result"][0]
    ajustado = r["indicators"]["adjclose"][0]["adjclose"]
    serie = {}
    for ts, px in zip(r["timestamp"], ajustado):
        if px:  # dias sem negócio vêm vazios
            # pregão da B3 fecha às 17h/18h de Brasília: a data em UTC-3 é a do pregão
            d = datetime.fromtimestamp(ts - 3 * 3600, timezone.utc).date().isoformat()
            serie[d] = round(float(px), 6)
    return serie


def cdi():
    serie = {}
    ano = int(INICIO[:4])
    hoje = date.today()
    while ano <= hoje.year:  # o BC limita cada consulta a 10 anos; pedimos de 5 em 5
        fim = min(ano + 4, hoje.year)
        url = BCB.format(i=f"01/01/{ano}", f=f"31/12/{fim}")
        for x in baixar(url):
            d, m, a = x["data"].split("/")
            serie[f"{a}-{m}-{d}"] = float(x["valor"])
        ano = fim + 1
    return serie


def main(destino):
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    ativos = sorted({REFERENCIA_BOLSA} | {a for c in CARTEIRAS.values() for a in c["alvo"]})
    precos = {}
    for a in ativos:
        precos[a] = cotacoes(a)
        datas = sorted(precos[a])
        print(f"{a}: {len(datas)} pregões, de {datas[0]} a {datas[-1]}")
    todas = sorted(set().union(*precos.values()))
    with open(destino / "precos.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["data"] + ativos)
        for d in todas:
            w.writerow([d] + [precos[a].get(d, "") for a in ativos])
    taxas = cdi()
    with open(destino / "cdi.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["data", "taxa"])
        for d in sorted(taxas):
            w.writerow([d, taxas[d]])
    print(f"CDI: {len(taxas)} dias, de {min(taxas)} a {max(taxas)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dados")
