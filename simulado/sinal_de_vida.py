"""Sinal de vida do Argos Trade B3: confere se o robô simulado rodou hoje.

Roda pelo GitHub Actions duas horas depois do horário do robô. Se o robô não rodou (o agendador do GitHub
às vezes pula uma execução), dispara o robô e avisa no Telegram. Se rodou e falhou, só avisa.
"""
import json, os, sys, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from robo_b3 import BRASILIA, ROTULO, telegram

REPO, TOKEN = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"]
API = f"https://api.github.com/repos/{REPO}/actions/workflows/robo-simulado.yml"


def github(caminho, dados=None):
    req = urllib.request.Request(API + caminho, data=json.dumps(dados).encode() if dados else None,
                                 headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        corpo = r.read()
        return json.loads(corpo) if corpo else {}


def main():
    agora = datetime.now(BRASILIA)
    # último dia útil cujo pregão já deveria estar fechado e registrado (o robô roda às 19h15)
    alvo = agora.date() if (agora.hour, agora.minute) >= (19, 45) else agora.date() - timedelta(days=1)
    while alvo.weekday() >= 5:
        alvo -= timedelta(days=1)
    estado = Path(__file__).parent / "estado.json"
    ultimo = json.loads(estado.read_text()).get("ultimo_pregao", "") if estado.exists() else ""
    if ultimo >= alvo.isoformat():
        print(f"Fechamento de {alvo:%d/%m} registrado. Tudo certo.")
        return
    # o robô registra o último pregão mesmo rodando atrasado; em feriado ele percebe e não faz nada
    github("/dispatches", {"ref": "main", "inputs": {"teste_telegram": "false"}})
    telegram(f"{ROTULO} · 📵 Sinal de vida\nO fechamento de {alvo:%d/%m} ainda não estava registrado "
             f"(último: {ultimo[8:10]}/{ultimo[5:7] if ultimo else '--'}). Disparei o robô agora. "
             "Se esse dia foi feriado, pode ignorar.")


if __name__ == "__main__":
    main()
