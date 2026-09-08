"""
Motor de cálculos financeiros — mesmo que o index.html, mas em Python.
"""
import math
from catalog import BANK_CATALOG


def cdi_monthly_rate(cdi_annual):
    """Taxa CDI mensal a partir da anual."""
    return math.pow(1 + cdi_annual / 100, 1 / 12) - 1


def monthly_rate_for(mode, rate, cdi_annual):
    """Taxa mensal efetiva para um produto."""
    if mode == 'cdi':
        return cdi_monthly_rate(cdi_annual) * (rate / 100)
    return rate / 100  # fixed (poupança)


def ir_rate_for_months(months):
    """Alíquota do IR pela tabela regressiva."""
    days = months * 30
    if days <= 180:
        return 0.225, '22,5% (até 180 dias)'
    if days <= 360:
        return 0.20, '20% (181–360 dias)'
    if days <= 720:
        return 0.175, '17,5% (361–720 dias)'
    return 0.15, '15% (acima de 720 dias)'


def simulate_product(product, amount, months, cdi_annual, monthly_contribution=0):
    """
    Simula rendimento de um produto mês a mês, respeitando cap.
    Retorna dict com saldo bruto, líquido, rendimento, IR.
    """
    cap = product.get('cap')
    cap_rate = monthly_rate_for(product['mode'], product['rate'], cdi_annual)

    excess_mode = product.get('excess_mode', product['mode'])
    excess_rate_val = product.get('excess_rate')
    if excess_rate_val is None:
        excess_rate_val = product['rate']
    exc_rate = monthly_rate_for(excess_mode, excess_rate_val, cdi_annual)

    # Separa em parte dentro do cap e excedente
    if cap and cap > 0 and amount > cap:
        cap_part = cap
        excess_part = amount - cap
    else:
        cap_part = amount
        excess_part = 0

    initial = amount
    for _ in range(months):
        # Aporte mensal
        if monthly_contribution > 0:
            if cap and cap > 0:
                room = max(0, cap - cap_part)
                into_cap = min(monthly_contribution, room)
                cap_part += into_cap
                excess_part += monthly_contribution - into_cap
            else:
                cap_part += monthly_contribution

        # Rendimento
        cap_gain = cap_part * cap_rate
        exc_gain = excess_part * exc_rate if excess_part > 0 else 0
        cap_part += cap_gain
        excess_part += exc_gain

    gross_balance = cap_part + excess_part
    total_invested = initial + monthly_contribution * months
    gross_gain = gross_balance - total_invested

    ir_aliquot, ir_label = ir_rate_for_months(months)
    if product.get('exempt', False):
        ir_amount = 0
        net_gain = gross_gain
    else:
        ir_amount = gross_gain * ir_aliquot
        net_gain = gross_gain - ir_amount

    net_balance = total_invested + net_gain

    return {
        'gross_balance': gross_balance,
        'net_balance': net_balance,
        'total_invested': total_invested,
        'gross_gain': gross_gain,
        'net_gain': net_gain,
        'ir_amount': ir_amount,
        'ir_label': ir_label,
        'exempt': product.get('exempt', False),
    }


def compare_all(amount, months, cdi_annual):
    """
    Compara todos os produtos do catálogo para um valor e prazo.
    Retorna lista ordenada por rendimento líquido (maior primeiro).
    """
    results = []
    for bank, products in BANK_CATALOG.items():
        for product in products:
            sim = simulate_product(product, amount, months, cdi_annual)
            results.append({
                'bank': bank,
                'product_name': product['name'],
                'note': product.get('note'),
                **sim,
            })
    results.sort(key=lambda r: r['net_gain'], reverse=True)
    return results


def suggest_allocation(total_amount, months, cdi_annual):
    """
    Alocação gulosa: distribui entre os melhores produtos respeitando caps.
    """
    if total_amount <= 0:
        return []

    ir_rate, _ = ir_rate_for_months(months)
    tranches = []
    for bank, products in BANK_CATALOG.items():
        for p in products:
            net_rate = monthly_rate_for(p['mode'], p['rate'], cdi_annual)
            if not p.get('exempt', False):
                net_rate *= (1 - ir_rate)
            capacity = p.get('cap') or float('inf')
            tranches.append({
                'bank': bank,
                'product': p,
                'capacity': capacity,
                'net_rate': net_rate,
            })
    tranches.sort(key=lambda t: t['net_rate'], reverse=True)

    remaining = total_amount
    allocation = []
    for t in tranches:
        if remaining <= 0.01:
            break
        alloc = min(remaining, t['capacity'])
        allocation.append({
            'bank': t['bank'],
            'name': t['product']['name'],
            'amount': alloc,
            'rate': t['product']['rate'],
            'mode': t['product']['mode'],
            'exempt': t['product'].get('exempt', False),
            'note': t['product'].get('note'),
        })
        remaining -= alloc

    return allocation


def goal_monthly_contribution(target, initial, months, product, cdi_annual):
    """
    Busca binária: quanto preciso aportar por mês pra chegar no alvo.
    """
    if months <= 0:
        return None

    test = simulate_product(product, initial, months, cdi_annual, 0)
    if test['net_balance'] >= target:
        return 0

    lo, hi = 0, max(1, (target - initial) / months)
    for _ in range(100):
        test_hi = simulate_product(product, initial, months, cdi_annual, hi)
        if test_hi['net_balance'] >= target:
            break
        hi *= 2
    else:
        return None

    for _ in range(60):
        mid = (lo + hi) / 2
        test_mid = simulate_product(product, initial, months, cdi_annual, mid)
        if test_mid['net_balance'] < target:
            lo = mid
        else:
            hi = mid

    return hi
