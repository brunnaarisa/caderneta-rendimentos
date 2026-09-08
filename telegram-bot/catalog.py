"""
Catálogo de bancos e produtos de investimento.
Taxas verificadas em 01/09/2026.
"""

CATALOG_VERIFIED_DATE = '2026-09-01'

BANK_CATALOG = {
    'Nubank': [
        {'name': 'Caixinha 100% do CDI', 'mode': 'cdi', 'rate': 100, 'exempt': False,
         'cap': None, 'excess_mode': None, 'excess_rate': None, 'note': None},
        {'name': 'Caixinha Turbo 115% do CDI (até R$5 mil)', 'mode': 'cdi', 'rate': 115, 'exempt': False,
         'cap': 5000, 'excess_mode': 'cdi', 'excess_rate': 100,
         'note': 'Precisa movimentar R$900 na conta; validade de 31 dias, renova com novo aporte.'},
        {'name': 'Caixinha Turbo 120% do CDI (Ultravioleta/Nubank+, até R$10 mil)', 'mode': 'cdi', 'rate': 120, 'exempt': False,
         'cap': 10000, 'excess_mode': 'cdi', 'excess_rate': 100,
         'note': 'Só pra clientes Ultravioleta ou Nubank+.'},
        {'name': 'LCI/LCA ~95% do CDI', 'mode': 'cdi', 'rate': 95, 'exempt': True,
         'cap': None, 'excess_mode': None, 'excess_rate': None,
         'note': 'Carência mínima: 180 dias. Valor mínimo entre R$500 e R$1.000.'},
    ],
    'Banco Inter': [
        {'name': 'Caixinha 80% do CDI', 'mode': 'cdi', 'rate': 80, 'exempt': False,
         'cap': None, 'excess_mode': None, 'excess_rate': None, 'note': None},
        {'name': 'CDB 100% do CDI', 'mode': 'cdi', 'rate': 100, 'exempt': False,
         'cap': None, 'excess_mode': None, 'excess_rate': None, 'note': None},
        {'name': 'LCI/LCA 92% do CDI', 'mode': 'cdi', 'rate': 92, 'exempt': True,
         'cap': None, 'excess_mode': None, 'excess_rate': None,
         'note': 'Isenta de IR. Carência: 180 dias.'},
    ],
    'C6 Bank': [
        {'name': 'Cofrinho / CDB 102% do CDI', 'mode': 'cdi', 'rate': 102, 'exempt': False,
         'cap': None, 'excess_mode': None, 'excess_rate': None, 'note': None},
        {'name': 'LCI/LCA ~91% do CDI', 'mode': 'cdi', 'rate': 91, 'exempt': True,
         'cap': None, 'excess_mode': None, 'excess_rate': None,
         'note': 'Carência: 180 dias. Valor mínimo a partir de R$1.000.'},
    ],
    'PicPay': [
        {'name': 'Cofrinho Turbinado 121% do CDI (até R$10 mil)', 'mode': 'cdi', 'rate': 121, 'exempt': False,
         'cap': 10000, 'excess_mode': 'cdi', 'excess_rate': 102,
         'note': 'Precisa receber pelo menos R$999/mês em Pix.'},
        {'name': 'Saldo da conta 102% do CDI', 'mode': 'cdi', 'rate': 102, 'exempt': False,
         'cap': None, 'excess_mode': None, 'excess_rate': None, 'note': None},
    ],
    'Mercado Pago': [
        {'name': 'Saldo 105% do CDI (até R$20 mil)', 'mode': 'cdi', 'rate': 105, 'exempt': False,
         'cap': 20000, 'excess_mode': 'cdi', 'excess_rate': 100,
         'note': 'Acima de R$20 mil, excedente rende 100% do CDI.'},
        {'name': 'Cofrinho 120% do CDI (Meli+, até R$10 mil)', 'mode': 'cdi', 'rate': 120, 'exempt': False,
         'cap': 10000, 'excess_mode': 'cdi', 'excess_rate': 100,
         'note': 'Precisa ser Meli+ ou aportar R$1.000+/mês.'},
    ],
    'Banco do Brasil': [
        {'name': 'Cofrinho BB 91% do CDI', 'mode': 'cdi', 'rate': 91, 'exempt': False,
         'cap': None, 'excess_mode': None, 'excess_rate': None,
         'note': 'É fundo, não CDB — sem FGC.'},
        {'name': 'LCI/LCA ~88% do CDI', 'mode': 'cdi', 'rate': 88, 'exempt': True,
         'cap': None, 'excess_mode': None, 'excess_rate': None,
         'note': 'Valor mínimo geralmente a partir de R$5.000.'},
    ],
    'Itaú': [
        {'name': 'Cofrinhos 100% do CDI', 'mode': 'cdi', 'rate': 100, 'exempt': False,
         'cap': None, 'excess_mode': None, 'excess_rate': None, 'note': None},
        {'name': 'LCI/LCA ~91% do CDI', 'mode': 'cdi', 'rate': 91, 'exempt': True,
         'cap': None, 'excess_mode': None, 'excess_rate': None,
         'note': 'Valor mínimo geralmente a partir de R$5.000.'},
    ],
    'Bradesco': [
        {'name': 'CDB 100% do CDI', 'mode': 'cdi', 'rate': 100, 'exempt': False,
         'cap': None, 'excess_mode': None, 'excess_rate': None, 'note': None},
        {'name': 'LCI/LCA ~88% do CDI', 'mode': 'cdi', 'rate': 88, 'exempt': True,
         'cap': None, 'excess_mode': None, 'excess_rate': None,
         'note': 'Valor mínimo geralmente a partir de R$5.000.'},
    ],
    'Santander': [
        {'name': 'CDB 100% do CDI', 'mode': 'cdi', 'rate': 100, 'exempt': False,
         'cap': None, 'excess_mode': None, 'excess_rate': None,
         'note': 'Produto "Minhas Reservas": mínimo R$1, resgate D+1.'},
        {'name': 'LCI/LCA ~88% do CDI', 'mode': 'cdi', 'rate': 88, 'exempt': True,
         'cap': None, 'excess_mode': None, 'excess_rate': None,
         'note': 'Valor mínimo geralmente a partir de R$5.000.'},
    ],
    'Caixa': [
        {'name': 'CDB 95% do CDI', 'mode': 'cdi', 'rate': 95, 'exempt': False,
         'cap': None, 'excess_mode': None, 'excess_rate': None,
         'note': 'CDB Flex: resgate D+2, mínimo R$1.000.'},
        {'name': 'LCI ~88% do CDI', 'mode': 'cdi', 'rate': 88, 'exempt': True,
         'cap': None, 'excess_mode': None, 'excess_rate': None,
         'note': 'Valor mínimo geralmente a partir de R$5.000.'},
    ],
    'XP Investimentos': [
        {'name': 'CDB ~106% do CDI', 'mode': 'cdi', 'rate': 106, 'exempt': False,
         'cap': None, 'excess_mode': None, 'excess_rate': None,
         'note': 'Taxa varia por prazo e emissor.'},
        {'name': 'LCI/LCA ~88% do CDI', 'mode': 'cdi', 'rate': 88, 'exempt': True,
         'cap': None, 'excess_mode': None, 'excess_rate': None,
         'note': 'Prateleira com títulos de vários emissores.'},
    ],
    'BTG Pactual': [
        {'name': 'CDB ~100% do CDI', 'mode': 'cdi', 'rate': 100, 'exempt': False,
         'cap': None, 'excess_mode': None, 'excess_rate': None,
         'note': 'Taxa varia por prazo e emissor.'},
        {'name': 'LCI/LCA ~88% do CDI', 'mode': 'cdi', 'rate': 88, 'exempt': True,
         'cap': None, 'excess_mode': None, 'excess_rate': None,
         'note': 'Prateleira com títulos de vários emissores.'},
    ],
}


def get_all_banks():
    """Retorna lista de nomes de bancos."""
    return list(BANK_CATALOG.keys())


def get_products(bank_name):
    """Retorna produtos de um banco."""
    return BANK_CATALOG.get(bank_name, [])
