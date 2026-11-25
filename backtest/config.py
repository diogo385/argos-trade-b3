"""Configuração das carteiras simuladas do Argos Trade B3.

As duas carteiras têm a mesma divisão entre risco e caixa (70% em renda variável
e 30% em caixa rendendo CDI), para que a comparação entre elas seja justa.
"""

CARTEIRAS = {
    "etf": {
        "nome": "Carteira de ETFs",
        "alvo": {"BOVA11": 0.35, "IVVB11": 0.25, "GOLD11": 0.10},
    },
    "acoes": {
        "nome": "Carteira de ações",
        "alvo": {
            "ITUB4": 0.10,   # banco
            "VALE3": 0.10,   # mineração
            "PETR4": 0.10,   # petróleo
            "WEGE3": 0.10,   # indústria
            "EGIE3": 0.10,   # energia elétrica
            "ABEV3": 0.10,   # bebidas
            "BBSE3": 0.10,   # seguros
        },
    },
}
# O que sobra do alvo (30%) fica em caixa rendendo CDI.

ETFS = {"BOVA11", "IVVB11", "GOLD11", "SMAL11"}   # IR de 15% sobre o ganho em toda venda
REFERENCIA_BOLSA = "BOVA11"                        # representa o Ibovespa

CAPITAL = 10_000.0      # R$ simulados
INICIO = "2014-01-01"   # baixa dados a partir daqui; o backtest começa quando todos os ativos existem

# Custos por operação: corretagem zero, emolumentos e liquidação da B3 (~0,03%)
# e diferença de preço no mercado fracionário (estimada em 0,10%).
CUSTO = 0.0003 + 0.0010
ORDEM_MIN = 50.0        # ignora ajustes menores que isso (R$)

# Imposto de renda (swing trade, sem day trade)
IR_ALIQUOTA = 0.15
ISENCAO_ACOES_MES = 20_000.0   # vendas de ações até esse valor no mês são isentas
IR_CAIXA = 0.15                # renda fixa longa (Tesouro Selic ou CDB acima de 2 anos)

# Robô: rebalanceia um ativo quando ele se afasta do alvo mais que esta fração do próprio alvo.
# Ex.: com 0,25, um ativo de alvo 10% opera abaixo de 7,5% ou acima de 12,5%.
FAIXAS_ROBO = [0.20, 0.35]

# Períodos de teste: calibração e validação separadas, como no backtest da cripto.
CORTE_VALIDACAO = "2021-01-01"
