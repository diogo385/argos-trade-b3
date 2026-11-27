"""Relógio do Argos Trade B3: uma passada a cada 10 minutos, chamada pelo workflow `mercado.yml`.

O agendador do GitHub atrasa horas neste repositório. Por isso um único job fica rodando e cuida da hora certa:
  - 9h50 às 18h50, dias úteis: grava as cotações do dia em <arquivo> (o workflow publica no ramo `mercado`);
  - a partir das 19h15, dias úteis: dispara o robô, se ele ainda não rodou hoje;
  - a partir das 21h15, dias úteis: dispara o sinal de vida, uma vez.
Uso: python relogio.py <arquivo_mercado.json>
"""
import json, os, sys, urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from robo_b3 import BRASILIA
import mercado

REPO, TOKEN = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"]
API = f"https://api.github.com/repos/{REPO}/actions/workflows/"


def github(caminho, dados=None):
    req = urllib.request.Request(API + caminho, data=json.dumps(dados).encode() if dados else None,
                                 headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        corpo = r.read()
        return json.loads(corpo) if corpo else {}


def rodou_hoje(workflow, agora, depois_de):
    """Já existe execução deste workflow criada hoje depois do horário dado (HHMM)?"""
    for x in github(f"{workflow}/runs?per_page=15")["workflow_runs"]:
        q = datetime.fromisoformat(x["created_at"].replace("Z", "+00:00")).astimezone(BRASILIA)
        if q.date() == agora.date() and q.hour * 100 + q.minute >= depois_de:
            return True
    return False


def main(saida):
    agora = datetime.now(BRASILIA)
    hhmm, util = agora.hour * 100 + agora.minute, agora.weekday() < 5
    if util and 950 <= hhmm <= 1850:
        try:
            mercado.main(saida)
        except SystemExit as e:
            print("cotações não publicadas:", e)
    if util and hhmm >= 1915 and not rodou_hoje("robo-simulado.yml", agora, 1900):
        github("robo-simulado.yml/dispatches", {"ref": "main", "inputs": {"teste_telegram": "false"}})
        print("robô disparado")
    if util and hhmm >= 2115 and not rodou_hoje("sinal-de-vida.yml", agora, 2100):
        github("sinal-de-vida.yml/dispatches", {"ref": "main"})
        print("sinal de vida disparado")
    print(f"passada das {agora:%H:%M}")


if __name__ == "__main__":
    main(sys.argv[1])
