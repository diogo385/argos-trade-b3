"""Cotações do dia para a aba Mercado do monitor (atraso de cerca de 15 minutos, do Yahoo Finance).

Uso: python mercado.py <arquivo_saida.json>
Roda a cada 15 minutos durante o pregão pelo GitHub Actions, que publica o arquivo no ramo `mercado`.
Não mexe na carteira: o robô continua decidindo só no fechamento.
"""
import json, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from robo_b3 import ATIVOS, BRASILIA, baixar_json

INDICES = {"BOVA11": "BOVA11.SA", "XFIX11": "XFIX11.SA", "IBOV": "%5EBVSP"}
URL = "https://query{n}.finance.yahoo.com/v8/finance/chart/{s}?range=1d&interval=5m"


def cotar(simbolo):
    j = None
    for n in (1, 2):
        try:
            j = baixar_json(URL.format(n=n, s=simbolo))
            break
        except RuntimeError:
            continue
    if not j:
        return None
    r = j["chart"]["result"][0]
    m = r["meta"]
    fech = r.get("indicators", {}).get("quote", [{}])[0].get("close") or []
    serie = [[datetime.fromtimestamp(ts, BRASILIA).strftime("%H:%M"), round(c, 2)]
             for ts, c in zip(r.get("timestamp") or [], fech) if c]
    preco, ant = m.get("regularMarketPrice"), m.get("chartPreviousClose") or m.get("previousClose")
    if not preco or not ant:
        return None
    quando = datetime.fromtimestamp(m.get("regularMarketTime", 0), BRASILIA)
    return {"preco": round(preco, 2), "anterior": round(ant, 2), "var": round(preco / ant - 1, 4),
            "max": m.get("regularMarketDayHigh"), "min": m.get("regularMarketDayLow"),
            "volume": m.get("regularMarketVolume"), "data": quando.date().isoformat(),
            "hora": quando.strftime("%H:%M"), "serie": serie}


def main(saida):
    ativos, falhas = {}, []
    for nome, simbolo in {**{a: a + ".SA" for a in ATIVOS}, **INDICES}.items():
        try:
            c = cotar(simbolo)
        except Exception:
            c = None
        if c:
            ativos[nome] = c
        else:
            falhas.append(nome)
    if len(ativos) < 5:
        raise SystemExit(f"cotações insuficientes ({len(ativos)}); nada publicado")
    agora = datetime.now(BRASILIA)
    Path(saida).write_text(json.dumps({"atualizado": agora.isoformat(timespec="minutes"), "atraso_min": 15,
                                       "falhas": falhas, "ativos": ativos}, separators=(",", ":")))
    print(f"{len(ativos)} cotações às {agora:%H:%M}; falhas: {falhas or 'nenhuma'}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "mercado.json")
