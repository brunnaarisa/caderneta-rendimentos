"""Cálculos financeiros — rendimentos, projeções, comparações."""


def calcular_rendimento(
    valor_inicial: float,
    aporte_mensal: float,
    taxa_anual: float,
    meses: int,
    percentual_cdi: float = 100,
) -> dict:
    """
    Calcula o rendimento de um investimento atrelado ao CDI.

    Retorna:
        - valor_final_bruto: montante total (antes do IR)
        - total_investido: soma dos aportes
        - rendimento_bruto: ganho antes do IR
        - ir: imposto de renda retido
        - rendimento_liquido: ganho após IR
        - valor_liquido: montante líquido final
    """
    # Taxa mensal efetiva
    taxa_mensal = ((1 + taxa_anual / 100) ** (1 / 12) - 1) * (percentual_cdi / 100)

    montante = valor_inicial
    total_investido = valor_inicial

    for _ in range(meses):
        montante *= 1 + taxa_mensal
        montante += aporte_mensal
        total_investido += aporte_mensal

    rendimento_bruto = montante - total_investido

    # Alíquota de IR regressiva
    aliquota = aliquota_ir(meses * 30)
    ir = rendimento_bruto * aliquota
    rendimento_liquido = rendimento_bruto - ir
    valor_liquido = total_investido + rendimento_liquido

    return {
        "valor_final_bruto": round(montante, 2),
        "total_investido": round(total_investido, 2),
        "rendimento_bruto": round(rendimento_bruto, 2),
        "aliquota_ir": aliquota,
        "ir": round(ir, 2),
        "rendimento_liquido": round(rendimento_liquido, 2),
        "valor_liquido": round(valor_liquido, 2),
    }


def aliquota_ir(dias: int) -> float:
    """Retorna a alíquota regressiva de IR para renda fixa."""
    if dias <= 180:
        return 0.225
    elif dias <= 360:
        return 0.20
    elif dias <= 720:
        return 0.175
    else:
        return 0.15


def comparar_investimentos(
    valor: float,
    aporte: float,
    meses: int,
    taxa_cdi_anual: float,
    opcoes: list[dict],
) -> list[dict]:
    """
    Compara múltiplas opções de investimento.

    opcoes: [{"nome": "Nubank", "percentual_cdi": 100}, ...]

    Retorna lista ordenada por rendimento líquido (melhor primeiro).
    """
    resultados = []
    for opcao in opcoes:
        calc = calcular_rendimento(
            valor_inicial=valor,
            aporte_mensal=aporte,
            taxa_anual=taxa_cdi_anual,
            meses=meses,
            percentual_cdi=opcao["percentual_cdi"],
        )
        resultados.append({**opcao, **calc})

    resultados.sort(key=lambda x: x["valor_liquido"], reverse=True)
    return resultados


def estrategia_dividas(dividas: list[dict], valor_extra: float) -> dict:
    """
    Calcula a melhor estratégia para quitar dívidas.

    Retorna plano com método avalanche (maior juros primeiro)
    e bola de neve (menor saldo primeiro).
    """
    if not dividas:
        return {"mensagem": "Nenhuma dívida cadastrada."}

    # Avalanche: maior taxa de juros primeiro
    avalanche = sorted(dividas, key=lambda d: d.get("taxa_juros_mensal", 0), reverse=True)

    # Bola de neve: menor saldo primeiro
    bola_neve = sorted(dividas, key=lambda d: d.get("valor_total", 0))

    total_dividas = sum(d["valor_total"] for d in dividas)
    juros_total_mensal = sum(
        d["valor_total"] * d.get("taxa_juros_mensal", 0) / 100 for d in dividas
    )

    return {
        "total_dividas": round(total_dividas, 2),
        "juros_mensal_estimado": round(juros_total_mensal, 2),
        "avalanche": [d["nome"] for d in avalanche],
        "bola_neve": [d["nome"] for d in bola_neve],
        "recomendacao": "avalanche" if juros_total_mensal > 0 else "bola_neve",
        "valor_extra_disponivel": valor_extra,
    }


# Bancos populares com percentuais CDI típicos (atualizar conforme mercado)
BANCOS_POPULARES = [
    {"nome": "Nubank (Caixinha)", "percentual_cdi": 100},
    {"nome": "PicPay", "percentual_cdi": 102},
    {"nome": "Mercado Pago", "percentual_cdi": 100},
    {"nome": "Inter", "percentual_cdi": 100},
    {"nome": "C6 Bank", "percentual_cdi": 102},
    {"nome": "Sofisa Direto", "percentual_cdi": 110},
    {"nome": "Pagbank (CDB)", "percentual_cdi": 110},
    {"nome": "BTG Pactual (CDB)", "percentual_cdi": 103},
    {"nome": "Daycoval (CDB)", "percentual_cdi": 110},
    {"nome": "Poupança (referência)", "percentual_cdi": 61.8},
]
