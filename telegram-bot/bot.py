"""
🐷 Caderneta Bot — Bot de Telegram para comparar investimentos de renda fixa.

Modelo de monetização:
  • Freemium com limites diários
  • Assinatura Premium via Pix (R$9,90/mês)
  • Programa de indicação (3 indicações = 1 mês grátis)
  • Link de afiliado para o site principal
"""
import os
import logging
import html
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters,
)
from telegram.constants import ParseMode

from catalog import BANK_CATALOG, get_all_banks, CATALOG_VERIFIED_DATE
from calculator import (
    compare_all, simulate_product, suggest_allocation,
    goal_monthly_contribution, ir_rate_for_months,
)
from cdi_fetcher import fetch_cdi, fetch_ipca, get_rates
from subscriptions import (
    init_db, ensure_user, is_premium, check_limit, increment_usage,
    get_daily_usage, activate_premium, get_referral_count,
    apply_referral, get_user, get_stats,
    FREE_DAILY_QUERIES, FREE_COMPARISONS, FREE_SIMULATIONS,
)

# ---------- Config ----------
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))
SITE_URL = os.getenv('SITE_URL', 'https://cadernetaderendimentos.com.br')
PIX_KEY = os.getenv('PIX_KEY', '')  # Sua chave Pix pra receber
PREMIUM_PRICE = os.getenv('PREMIUM_PRICE', 'R$ 9,90/mês')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ---------- Helpers ----------
def fmt(value):
    """Formata valor monetário brasileiro."""
    return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def pct(value):
    """Formata percentual."""
    return f"{value:.2f}%".replace('.', ',')


def limit_message(field):
    """Mensagem de limite atingido."""
    return (
        "⚠️ *Limite diário do plano gratuito atingido\\!*\n\n"
        "Quer consultas ilimitadas? Assine o Premium\\!\n"
        f"💎 Apenas {html.escape(PREMIUM_PRICE)}\n\n"
        "Use /premium pra ver os benefícios\\."
    )


def track_and_check(user_id, field='queries'):
    """Verifica limite e incrementa uso. Retorna (ok, remaining)."""
    ok, remaining = check_limit(user_id, field)
    if ok:
        increment_usage(user_id, field)
    return ok, remaining


# ---------- Commands ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = ensure_user(user.id, user.username, user.first_name)

    # Processa link de indicação: /start ref_CODIGO
    if context.args and context.args[0].startswith('ref_'):
        ref_code = context.args[0][4:]
        referrer_id = apply_referral(user.id, ref_code)
        if referrer_id:
            count = get_referral_count(referrer_id)
            if count > 0 and count % 3 == 0:
                activate_premium(referrer_id, months=1)

    name = html.escape(user.first_name or 'amigo(a)')
    await update.message.reply_text(
        f"🐷 *Olá, {name}\\!*\n\n"
        "Sou o *Caderneta Bot* — te ajudo a descobrir onde seu dinheiro rende mais\\.\n\n"
        "📌 *Comandos principais:*\n"
        "/cdi — Taxa CDI e IPCA atuais\n"
        "/comparar — Comparar rendimento entre bancos\n"
        "/simular — Simular rendimento de uma caixinha\n"
        "/melhor — Onde colocar seu dinheiro \\(sugestão\\)\n"
        "/bancos — Bancos e produtos disponíveis\n"
        "/meta — Calcular quanto poupar pra atingir uma meta\n\n"
        "💎 /premium — Consultas ilimitadas \\+ alertas\n"
        "👥 /indicar — Ganhe Premium grátis indicando amigos\n"
        "❓ /ajuda — Todos os comandos\n\n"
        f"🌐 [Abrir calculadora completa no site]({SITE_URL})",
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐷 *Caderneta Bot — Comandos*\n\n"
        "*Gratuitos \\(com limite diário\\):*\n"
        f"/cdi — Taxa CDI e IPCA atuais\n"
        f"/bancos — Lista de bancos e produtos\n"
        f"/comparar `valor` `meses` — Top 10 rendimentos\n"
        f"/simular `banco` `valor` `meses` — Simular caixinha\n\n"
        "*Premium \\(ilimitado\\):*\n"
        "/melhor `valor` `meses` — Melhor alocação\n"
        "/meta `alvo` `inicial` `meses` — Aporte mensal pra meta\n"
        "/alerta — Receber avisos quando o CDI mudar\n"
        "/relatorio — Resumo completo em texto\n\n"
        "*Conta:*\n"
        "/minhaconta — Ver plano e uso\n"
        "/premium — Assinar Premium\n"
        "/indicar — Indicar amigos \\(3 = 1 mês grátis\\)\n",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def cdi_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user.id)
    rates = get_rates()
    ir_3m = ir_rate_for_months(3)
    ir_12m = ir_rate_for_months(12)

    await update.message.reply_text(
        "📊 *Taxas Atuais*\n\n"
        f"💰 *CDI:* {pct(rates['cdi'])} a\\.a\\.\n"
        f"📈 *IPCA \\(12m\\):* {pct(rates['ipca'])} a\\.a\\.\n"
        f"📉 *Rendimento real:* ~{pct(rates['cdi'] - rates['ipca'])} a\\.a\\.\n\n"
        "🏦 *IR sobre rendimento:*\n"
        f"  • Até 6 meses: 22,5%\n"
        f"  • 6–12 meses: 20%\n"
        f"  • 12–24 meses: 17,5%\n"
        f"  • Acima de 24 meses: 15%\n"
        f"  • LCI/LCA e Poupança: isento\n\n"
        f"_Fonte: Banco Central do Brasil_\n"
        f"🌐 [Calculadora completa]({SITE_URL})",
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )


async def bancos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user.id)
    keyboard = []
    banks = get_all_banks()
    # 2 botões por linha
    for i in range(0, len(banks), 2):
        row = [InlineKeyboardButton(banks[i], callback_data=f'bank_{banks[i]}')]
        if i + 1 < len(banks):
            row.append(InlineKeyboardButton(banks[i + 1], callback_data=f'bank_{banks[i + 1]}'))
        keyboard.append(row)

    await update.message.reply_text(
        "🏦 *Escolha um banco pra ver os produtos:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def bank_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    bank_name = query.data.replace('bank_', '')
    products = BANK_CATALOG.get(bank_name, [])
    if not products:
        await query.edit_message_text("Banco não encontrado.")
        return

    lines = [f"🏦 *{html.escape(bank_name)}*\n"]
    for p in products:
        exempt_tag = " 🟢 _isento de IR_" if p.get('exempt') else ""
        cap_tag = f" \\(até {fmt(p['cap'])}\\)" if p.get('cap') else ""
        lines.append(f"• *{html.escape(p['name'])}*{exempt_tag}{cap_tag}")
        if p.get('note'):
            note_escaped = html.escape(p['note'])
            # Escape MarkdownV2 special chars
            for ch in '_*[]()~`>#+-=|{}.!':
                note_escaped = note_escaped.replace(ch, f'\\{ch}')
            lines.append(f"  _{note_escaped}_")

    lines.append(f"\n_Taxas verificadas em {CATALOG_VERIFIED_DATE}_")
    await query.edit_message_text('\n'.join(lines), parse_mode=ParseMode.MARKDOWN_V2)


async def comparar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(user_id)

    ok, remaining = track_and_check(user_id, 'comparisons')
    if not ok:
        await update.message.reply_text(limit_message('comparisons'), parse_mode=ParseMode.MARKDOWN_V2)
        return

    # Parse: /comparar 10000 12
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            "📊 *Como usar:*\n`/comparar <valor> <meses>`\n\n"
            "*Exemplo:*\n`/comparar 10000 12`\n"
            "→ Compara R\\$10\\.000 em 12 meses",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    try:
        amount = float(args[0].replace('.', '').replace(',', '.'))
        months = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ Use números: `/comparar 10000 12`", parse_mode=ParseMode.MARKDOWN_V2)
        return

    if amount <= 0 or months <= 0:
        await update.message.reply_text("❌ Valor e meses precisam ser positivos\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    cdi = fetch_cdi()
    results = compare_all(amount, months, cdi)

    premium = is_premium(user_id)
    top_n = 15 if premium else 5

    lines = [
        f"📊 *Comparação: {fmt(amount)} em {months} {'mês' if months == 1 else 'meses'}*",
        f"_CDI atual: {pct(cdi)} a\\.a\\._\n",
    ]

    for i, r in enumerate(results[:top_n]):
        medal = ['🥇', '🥈', '🥉'][i] if i < 3 else f'{i+1}.'
        exempt_tag = " 🟢" if r['exempt'] else ""
        escaped_bank = html.escape(r['bank'])
        escaped_name = html.escape(r['product_name'])
        for ch in '_*[]()~`>#+-=|{}.!':
            escaped_bank = escaped_bank.replace(ch, f'\\{ch}')
            escaped_name = escaped_name.replace(ch, f'\\{ch}')
        lines.append(
            f"{medal} *{escaped_bank}*{exempt_tag}\n"
            f"   {escaped_name}\n"
            f"   💰 Líquido: *\\+{fmt(r['net_gain'])}*"
        )

    if not premium:
        lines.append(f"\n_Mostrando top {top_n}\\. Premium mostra top {15}\\._")
        lines.append("💎 /premium para ver o ranking completo")

    lines.append(f"\n🌐 [Comparar no site \\(com gráficos\\)]({SITE_URL})")

    await update.message.reply_text(
        '\n'.join(lines),
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )


async def simular_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(user_id)

    ok, remaining = track_and_check(user_id, 'simulations')
    if not ok:
        await update.message.reply_text(limit_message('simulations'), parse_mode=ParseMode.MARKDOWN_V2)
        return

    args = context.args or []
    if len(args) < 3:
        banks_list = ', '.join(get_all_banks()[:6])
        await update.message.reply_text(
            "🧮 *Como usar:*\n`/simular <banco> <valor> <meses>`\n\n"
            "*Exemplo:*\n`/simular Nubank 5000 12`\n\n"
            f"*Bancos disponíveis:* {banks_list}\\.\\.\\.\n"
            "Use /bancos pra ver todos\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # O banco pode ter espaços (ex: "Banco Inter"), pega tudo menos os 2 últimos args
    bank_parts = args[:-2]
    bank_name = ' '.join(bank_parts)
    try:
        amount = float(args[-2].replace('.', '').replace(',', '.'))
        months = int(args[-1])
    except ValueError:
        await update.message.reply_text("❌ Use: `/simular Nubank 5000 12`", parse_mode=ParseMode.MARKDOWN_V2)
        return

    # Busca banco (case-insensitive)
    matched_bank = None
    for b in BANK_CATALOG:
        if b.lower() == bank_name.lower():
            matched_bank = b
            break
    if not matched_bank:
        # Tenta match parcial
        for b in BANK_CATALOG:
            if bank_name.lower() in b.lower():
                matched_bank = b
                break

    if not matched_bank:
        await update.message.reply_text(
            f"❌ Banco '{html.escape(bank_name)}' não encontrado\\. Use /bancos pra ver a lista\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    cdi = fetch_cdi()
    products = BANK_CATALOG[matched_bank]

    lines = [
        f"🧮 *Simulação: {fmt(amount)} em {months} meses no {html.escape(matched_bank)}*",
        f"_CDI: {pct(cdi)} a\\.a\\._\n",
    ]

    for p in products:
        sim = simulate_product(p, amount, months, cdi)
        exempt_tag = " 🟢" if sim['exempt'] else f" \\(IR: {html.escape(sim['ir_label'])}\\)"
        escaped_name = html.escape(p['name'])
        for ch in '_*[]()~`>#+-=|{}.!':
            escaped_name = escaped_name.replace(ch, f'\\{ch}')
        lines.append(
            f"📌 *{escaped_name}*{exempt_tag}\n"
            f"   Investido: {fmt(sim['total_invested'])}\n"
            f"   Bruto: {fmt(sim['gross_balance'])} \\(\\+{fmt(sim['gross_gain'])}\\)\n"
            f"   💰 Líquido: *{fmt(sim['net_balance'])}* \\(\\+{fmt(sim['net_gain'])}\\)\n"
        )

    lines.append(f"🌐 [Simular com gráficos no site]({SITE_URL})")
    await update.message.reply_text(
        '\n'.join(lines),
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )


async def melhor_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(user_id)

    if not is_premium(user_id):
        await update.message.reply_text(
            "💎 *Recurso Premium*\n\n"
            "O comando /melhor analisa todos os bancos e monta a *melhor combinação* "
            "pra distribuir seu dinheiro entre os produtos que mais rendem\\.\n\n"
            f"Assine por apenas {html.escape(PREMIUM_PRICE)} → /premium",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    args = context.args or []
    if len(args) < 1:
        await update.message.reply_text(
            "💡 *Como usar:*\n`/melhor <valor> [meses]`\n\n"
            "*Exemplo:*\n`/melhor 50000 12`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    try:
        amount = float(args[0].replace('.', '').replace(',', '.'))
        months = int(args[1]) if len(args) > 1 else 12
    except ValueError:
        await update.message.reply_text("❌ Use: `/melhor 50000 12`", parse_mode=ParseMode.MARKDOWN_V2)
        return

    cdi = fetch_cdi()
    allocation = suggest_allocation(amount, months, cdi)

    lines = [
        f"💡 *Melhor distribuição para {fmt(amount)} em {months} meses:*",
        f"_CDI: {pct(cdi)} a\\.a\\._\n",
    ]

    total_net = 0
    for i, a in enumerate(allocation):
        sim = simulate_product(a, a['amount'], months, cdi)
        total_net += sim['net_gain']
        exempt_tag = " 🟢" if a['exempt'] else ""
        escaped_bank = html.escape(a['bank'])
        escaped_name = html.escape(a['name'])
        for ch in '_*[]()~`>#+-=|{}.!':
            escaped_bank = escaped_bank.replace(ch, f'\\{ch}')
            escaped_name = escaped_name.replace(ch, f'\\{ch}')
        lines.append(
            f"{i+1}\\. *{escaped_bank}*{exempt_tag}\n"
            f"   {escaped_name}\n"
            f"   Alocar: {fmt(a['amount'])} → líquido: \\+{fmt(sim['net_gain'])}"
        )

    lines.append(f"\n🎯 *Total líquido estimado: \\+{fmt(total_net)}*")
    lines.append(f"\n🌐 [Monte sua combinação no site]({SITE_URL})")

    await update.message.reply_text(
        '\n'.join(lines),
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )


async def meta_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(user_id)

    if not is_premium(user_id):
        await update.message.reply_text(
            "💎 *Recurso Premium*\n\n"
            "O /meta calcula *quanto você precisa guardar por mês* pra chegar "
            "na sua meta no prazo\\.\n\n"
            f"Assine por apenas {html.escape(PREMIUM_PRICE)} → /premium",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    args = context.args or []
    if len(args) < 3:
        await update.message.reply_text(
            "🎯 *Como usar:*\n`/meta <alvo> <valor_inicial> <meses>`\n\n"
            "*Exemplo:*\n`/meta 100000 10000 24`\n"
            "→ Quanto guardar/mês pra sair de R\\$10k e chegar em R\\$100k em 2 anos",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    try:
        target = float(args[0].replace('.', '').replace(',', '.'))
        initial = float(args[1].replace('.', '').replace(',', '.'))
        months = int(args[2])
    except ValueError:
        await update.message.reply_text("❌ Use: `/meta 100000 10000 24`", parse_mode=ParseMode.MARKDOWN_V2)
        return

    cdi = fetch_cdi()

    # Calcula pra alguns produtos populares
    top_products = [
        ('Nubank', BANK_CATALOG['Nubank'][0]),      # 100% CDI
        ('PicPay', BANK_CATALOG['PicPay'][0]),       # 121% CDI
        ('Nubank LCI', BANK_CATALOG['Nubank'][3]),   # 95% CDI isento
    ]

    lines = [
        f"🎯 *Meta: {fmt(target)} em {months} meses*",
        f"_Começando com: {fmt(initial)}_\n",
    ]

    for label, product in top_products:
        contribution = goal_monthly_contribution(target, initial, months, product, cdi)
        if contribution is not None:
            escaped_label = html.escape(label)
            escaped_name = html.escape(product['name'])
            for ch in '_*[]()~`>#+-=|{}.!':
                escaped_label = escaped_label.replace(ch, f'\\{ch}')
                escaped_name = escaped_name.replace(ch, f'\\{ch}')
            lines.append(
                f"🏦 *{escaped_label}* \\({escaped_name}\\)\n"
                f"   → Guardar *{fmt(contribution)}/mês*"
            )

    lines.append(f"\n🌐 [Simulador de metas completo]({SITE_URL})")

    await update.message.reply_text(
        '\n'.join(lines),
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )


async def premium_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = ensure_user(user_id)

    if is_premium(user_id):
        db_user = get_user(user_id)
        await update.message.reply_text(
            f"💎 *Você já é Premium\\!*\n"
            f"Válido até: {html.escape(db_user.get('plan_expires_at', 'indefinido')[:10])}\n\n"
            "Aproveite todos os recursos ilimitados\\! 🚀",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    usage = get_daily_usage(user_id)
    text = (
        "💎 *Caderneta Premium*\n\n"
        "*Plano Gratuito \\(atual\\):*\n"
        f"  • {FREE_COMPARISONS} comparações/dia \\(usado: {usage['comparisons']}\\)\n"
        f"  • {FREE_SIMULATIONS} simulações/dia \\(usado: {usage['simulations']}\\)\n"
        f"  • Top 5 no ranking\n\n"
        "*Plano Premium:*\n"
        "  ✅ Comparações ilimitadas\n"
        "  ✅ Simulações ilimitadas\n"
        "  ✅ Top 15 no ranking\n"
        "  ✅ /melhor — alocação inteligente\n"
        "  ✅ /meta — simulador de metas\n"
        "  ✅ Alertas de mudança no CDI\n"
        "  ✅ Prioridade em novos recursos\n\n"
        f"💰 *{html.escape(PREMIUM_PRICE)}*\n\n"
    )

    keyboard = []
    if PIX_KEY:
        keyboard.append([InlineKeyboardButton("💚 Pagar via Pix", callback_data='pay_pix')])
    keyboard.append([InlineKeyboardButton("👥 Ganhar grátis indicando amigos", callback_data='referral_info')])

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def pay_pix_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not PIX_KEY:
        await query.edit_message_text("Pagamento via Pix não configurado. Fale com o admin.")
        return

    user_id = query.from_user.id
    # Escape MarkdownV2 special chars in PIX_KEY
    escaped_pix = html.escape(PIX_KEY)
    for ch in '_*[]()~`>#+-=|{}.!':
        escaped_pix = escaped_pix.replace(ch, f'\\{ch}')

    await query.edit_message_text(
        "💚 *Pagamento via Pix*\n\n"
        f"1️⃣ Envie *{html.escape(PREMIUM_PRICE)}* para:\n\n"
        f"🔑 Chave Pix: `{escaped_pix}`\n\n"
        f"2️⃣ Envie o comprovante aqui no chat\n"
        f"3️⃣ Ativamos seu Premium em até 1 hora\\!\n\n"
        f"_Seu ID: `{user_id}`_\n"
        "_Mencione esse ID no Pix pra agilizar\\._",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    ref_code = user['referral_code'] if user else 'ERRO'
    count = get_referral_count(user_id)
    remaining = max(0, 3 - (count % 3))

    # Monta link de convite
    bot_username = (await context.bot.get_me()).username
    invite_link = f'https://t.me/{bot_username}?start=ref_{ref_code}'

    escaped_link = invite_link
    for ch in '_*[]()~`>#+-=|{}.!':
        escaped_link = escaped_link.replace(ch, f'\\{ch}')

    await query.edit_message_text(
        "👥 *Programa de Indicação*\n\n"
        "Indique 3 amigos e ganhe *1 mês de Premium grátis*\\!\n\n"
        f"📊 Indicações: *{count}* \\(faltam {remaining} pro próximo mês\\)\n\n"
        f"🔗 Seu link de indicação:\n{escaped_link}\n\n"
        "Compartilhe com amigos que investem\\! 🚀",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def indicar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = ensure_user(user_id)
    ref_code = user['referral_code']
    count = get_referral_count(user_id)
    remaining = max(0, 3 - (count % 3))

    bot_username = (await context.bot.get_me()).username
    invite_link = f'https://t.me/{bot_username}?start=ref_{ref_code}'

    escaped_link = invite_link
    for ch in '_*[]()~`>#+-=|{}.!':
        escaped_link = escaped_link.replace(ch, f'\\{ch}')

    await update.message.reply_text(
        "👥 *Programa de Indicação*\n\n"
        "A cada 3 amigos que usarem seu link, você ganha *1 mês de Premium*\\!\n\n"
        f"📊 Indicações: *{count}* \\(faltam {remaining}\\)\n\n"
        f"🔗 Seu link:\n{escaped_link}\n\n"
        "Compartilhe\\! 🚀",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def minhaconta_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = ensure_user(user_id)
    usage = get_daily_usage(user_id)
    premium = is_premium(user_id)
    plan_name = "💎 Premium" if premium else "🆓 Gratuito"

    lines = [
        f"👤 *Minha Conta*\n",
        f"Plano: *{plan_name}*",
    ]
    if premium:
        db_user = get_user(user_id)
        exp = db_user.get('plan_expires_at', '')[:10]
        lines.append(f"Válido até: {html.escape(exp)}")
    lines.extend([
        f"\n*Uso hoje:*",
        f"  Comparações: {usage['comparisons']}/{FREE_COMPARISONS if not premium else '∞'}",
        f"  Simulações: {usage['simulations']}/{FREE_SIMULATIONS if not premium else '∞'}",
        f"\nTotal de consultas: {user.get('total_queries', 0)}",
        f"Código de indicação: `{user['referral_code']}`",
        f"Indicações: {get_referral_count(user_id)}",
    ])

    await update.message.reply_text('\n'.join(lines), parse_mode=ParseMode.MARKDOWN_V2)


# ---------- Admin ----------
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    stats = get_stats()
    await update.message.reply_text(
        f"📊 *Admin Stats*\n\n"
        f"Total de usuários: {stats['total_users']}\n"
        f"Premium: {stats['premium_users']}\n"
        f"Ativos hoje: {stats['active_today']}\n"
        f"Consultas totais: {stats['total_queries']}",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def admin_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin ativa Premium: /ativar <user_id> <meses>"""
    if update.effective_user.id != ADMIN_USER_ID:
        return
    args = context.args or []
    if len(args) < 1:
        await update.message.reply_text("Uso: /ativar <user_id> [meses]")
        return
    target_id = int(args[0])
    months = int(args[1]) if len(args) > 1 else 1
    activate_premium(target_id, months)
    await update.message.reply_text(f"✅ Premium ativado para {target_id} por {months} mês(es).")


# ---------- Mensagens de texto livre (fallback) ----------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde a mensagens que não são comandos."""
    text = (update.message.text or '').lower().strip()

    # Comprovante de pagamento (foto)
    if update.message.photo:
        if ADMIN_USER_ID:
            user = update.effective_user
            caption = (
                f"💰 Possível comprovante de pagamento\n"
                f"De: {user.first_name} (@{user.username})\n"
                f"ID: {user.id}"
            )
            await context.bot.send_photo(
                chat_id=ADMIN_USER_ID,
                photo=update.message.photo[-1].file_id,
                caption=caption,
            )
        await update.message.reply_text(
            "📬 Comprovante recebido\\! Vamos verificar e ativar seu Premium em breve\\. 🚀",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # Respostas a texto comum
    if any(word in text for word in ['oi', 'olá', 'ola', 'bom dia', 'boa tarde', 'boa noite']):
        await update.message.reply_text(
            "🐷 Olá! Use /ajuda pra ver tudo que posso fazer por você!"
        )
    elif any(word in text for word in ['cdi', 'taxa', 'selic', 'juros']):
        await cdi_cmd(update, context)
    elif any(word in text for word in ['comparar', 'qual melhor', 'onde rende mais']):
        await update.message.reply_text(
            "Use: /comparar <valor> <meses>\n"
            "Exemplo: /comparar 10000 12"
        )
    else:
        await update.message.reply_text(
            "🤔 Não entendi. Use /ajuda pra ver os comandos disponíveis!"
        )


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Encaminha fotos (comprovantes) pro admin."""
    if ADMIN_USER_ID and update.message.photo:
        user = update.effective_user
        caption = (
            f"💰 Possível comprovante de pagamento\n"
            f"De: {user.first_name} (@{user.username})\n"
            f"ID: {user.id}"
        )
        await context.bot.send_photo(
            chat_id=ADMIN_USER_ID,
            photo=update.message.photo[-1].file_id,
            caption=caption,
        )
        await update.message.reply_text(
            "📬 Recebido! Vamos verificar e ativar seu Premium em breve. 🚀"
        )


async def post_init(app: Application):
    """Configura comandos do menu do bot."""
    commands = [
        BotCommand('cdi', '📊 Taxa CDI e IPCA atuais'),
        BotCommand('comparar', '📊 Comparar rendimento entre bancos'),
        BotCommand('simular', '🧮 Simular rendimento de uma caixinha'),
        BotCommand('bancos', '🏦 Ver bancos e produtos'),
        BotCommand('melhor', '💡 Melhor alocação (Premium)'),
        BotCommand('meta', '🎯 Simulador de metas (Premium)'),
        BotCommand('premium', '💎 Assinar Premium'),
        BotCommand('indicar', '👥 Indicar amigos'),
        BotCommand('minhaconta', '👤 Ver plano e uso'),
        BotCommand('ajuda', '❓ Todos os comandos'),
    ]
    await app.bot.set_my_commands(commands)


def main():
    if not BOT_TOKEN:
        print("❌ Defina a variável BOT_TOKEN com o token do @BotFather")
        print("   export BOT_TOKEN='123456:ABC-DEF...'")
        return

    init_db()

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Comandos públicos
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('ajuda', help_cmd))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('cdi', cdi_cmd))
    app.add_handler(CommandHandler('bancos', bancos_cmd))
    app.add_handler(CommandHandler('comparar', comparar_cmd))
    app.add_handler(CommandHandler('simular', simular_cmd))
    app.add_handler(CommandHandler('melhor', melhor_cmd))
    app.add_handler(CommandHandler('meta', meta_cmd))
    app.add_handler(CommandHandler('premium', premium_cmd))
    app.add_handler(CommandHandler('indicar', indicar_cmd))
    app.add_handler(CommandHandler('minhaconta', minhaconta_cmd))

    # Admin
    app.add_handler(CommandHandler('stats', admin_stats))
    app.add_handler(CommandHandler('ativar', admin_activate))

    # Callbacks (botões inline)
    app.add_handler(CallbackQueryHandler(bank_detail_callback, pattern=r'^bank_'))
    app.add_handler(CallbackQueryHandler(pay_pix_callback, pattern=r'^pay_pix$'))
    app.add_handler(CallbackQueryHandler(referral_callback, pattern=r'^referral_info$'))

    # Fotos (comprovantes)
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    # Texto livre (fallback)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("🐷 Caderneta Bot rodando!")
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
