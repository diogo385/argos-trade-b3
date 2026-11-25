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
    hoje = datetime.now(BRASILIA).date()
    execucoes = []
    for x in github("/runs?per_page=20")["workflow_runs"]:
        quando = datetime.fromisoformat(x["created_at"].replace("Z", "+00:00")).astimezone(BRASILIA)
        # só contam as execuções de verdade do fim do dia (o teste do Telegram roda em segundos, mais cedo)
        if quando.date() == hoje and quando.hour >= 18:
            execucoes.append(x)
    if any(x["conclusion"] == "success" for x in execucoes):
        print("Robô rodou hoje. Tudo certo.")
        return
    if any(x["status"] != "completed" for x in execucoes):
        print("Robô ainda rodando. Nada a fazer.")
        return
    if execucoes:  # rodou e falhou: o próprio robô já avisou o motivo
        telegram(f"{ROTULO} · 📵 Sinal de vida\nO robô rodou hoje, mas terminou com erro. A carteira simulada não foi "
                 "alterada. Veja o motivo na mensagem anterior ou em Actions no GitHub.")
        return
    github("/dispatches", {"ref": "main", "inputs": {"teste_telegram": "false"}})
    telegram(f"{ROTULO} · 📵 Sinal de vida\nO robô não tinha rodado hoje no horário (falha do agendador do GitHub). "
             "Disparei a execução agora; o fechamento chega em seguida.")


if __name__ == "__main__":
    main()
