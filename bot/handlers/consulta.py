"""Handler de consultas à IA — o coração do bot.

Inclui detecção de linguagem natural para objetivos de investimento.
Quando o usuário digita algo como "quero investir 500 e ganhar 100 em 1 semana",
detecta a intenção e encaminha para o planejador com análise de mercado ao vivo.
"""

import logging
import re

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from config import FREE_DAILY_LIMIT, PREMIUM_PRICE
from services.ai_advisor import consultar_ia
from services.user_service import (
    check_and_use_consulta,
    get_financial_context,
    get_or_create_user,
    get_remaining_consultas,
    rollback_consulta,
)

logger = logging.getLogger(__name__)


# ── Detecção de intenção de investimento ─────────────────────


def _extrair_objetivo_investimento(texto: str) -> dict | None:
    """
    Detecta se o texto é uma intenção de investimento com valores.
    Retorna {investir, ganhar, dias} se detectou, None caso contrário.

    Exemplos que detecta:
    - "quero investir 500 e ganhar 100 em 1 semana"
    - "investir 1000 e virar 2000 em 1 mês"
    - "500 reais virarem 1000 em uma semana"
    - "quero transformar 500 em 1000 em 7 dias"
    - "tenho 2000 e quero dobrar em 1 mês"
    - "como faço 500 reais virarem 1000?"
    - "quero que 500 vire 1000 em 2 semanas"
    - "colocar 1000 e tirar 1500 em 30 dias"
    """
    texto_lower = texto.lower().strip()

    # Verificar se contém palavras-chave de investimento
    palavras_investir = (
        "investir", "aplicar", "colocar", "botar", "meter",
        "transformar", "virar", "virarem", "vire", "vira",
        "ganhar", "lucrar", "render", "dobrar", "triplicar",
        "tirar", "retirar", "fazer",
    )
    if not any(p in texto_lower for p in palavras_investir):
        return None

    # Verificar se tem contexto de prazo ou retorno (evitar falsos positivos)
    palavras_contexto = (
        "dia", "semana", "mês", "mes", "ano",
        "virar", "vire", "vira", "virarem",
        "ganhar", "lucrar", "render", "dobrar", "triplicar",
        "investir", "investindo", "aplicar", "aplicando",
        "colocar", "transformar", "fazer", "tirar",
        "reais", "r$", "conto",
    )
    # Contar contexto: também contar se há 2+ números no texto
    contexto_score = sum(1 for p in palavras_contexto if p in texto_lower)
    nums_no_texto = len(re.findall(r"\d{2,}", texto_lower))
    if nums_no_texto >= 2:
        contexto_score += 1  # ter 2+ números é forte indicador
    if contexto_score < 2:
        return None

    investir = None
    ganhar = None
    dias = None

    # ── Extrair valores monetários ──

    def parse_valor(s: str) -> float | None:
        """Parse valor numérico do texto."""
        s = s.replace("r$", "").replace("reais", "").replace(" ", "").strip()
        if "mil" in s:
            s = s.replace("mil", "")
            try:
                base = float(s.replace(",", ".")) if s else 1
                return base * 1000
            except ValueError:
                return None
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    # Encontrar todos os valores no texto
    valores_re = re.findall(
        r"r?\$?\s*(\d[\d.,]*(?:\s*(?:mil|reais|conto[s]?))?)",
        texto_lower,
    )
    valores = []
    for v in valores_re:
        parsed = parse_valor(v)
        if parsed and parsed >= 1:
            valores.append(parsed)

    # Números soltos (ex: "500 reais", "1000")
    if len(valores) < 2:
        nums = re.findall(r"\b(\d{2,})\b", texto_lower)
        for n in nums:
            v = float(n)
            if v >= 10 and v not in valores:
                valores.append(v)

    # ── Padrão 1: "investir X e ganhar Y" / "colocar X e tirar Y" ──
    p1 = re.search(
        r"(?:investir|aplicar|colocar|botar|meter)\s+"
        r"(?:r?\$?\s*)?([\d.,]+\s*(?:mil|reais)?)"
        r".*?"
        r"(?:ganhar|lucrar|render)\s+"
        r"(?:r?\$?\s*)?([\d.,]+\s*(?:mil|reais)?)",
        texto_lower,
    )
    if p1:
        investir = parse_valor(p1.group(1))
        ganhar = parse_valor(p1.group(2))

    # ── Padrão 1b: "colocar X e tirar Y" (tirar = valor FINAL) ──
    if not investir:
        p1b = re.search(
            r"(?:investir|aplicar|colocar|botar|meter)\s+"
            r"(?:r?\$?\s*)?([\d.,]+\s*(?:mil|reais)?)"
            r".*?"
            r"(?:tirar|retirar|sacar)\s+"
            r"(?:r?\$?\s*)?([\d.,]+\s*(?:mil|reais)?)",
            texto_lower,
        )
        if p1b:
            investir = parse_valor(p1b.group(1))
            alvo = parse_valor(p1b.group(2))
            if investir and alvo and alvo > investir:
                ganhar = alvo - investir

    # ── Padrão 2: "investir X e virar/vire Y" (virar = valor final) ──
    if not investir:
        p2 = re.search(
            r"(?:investir|aplicar|colocar|botar|meter)\s+"
            r"(?:r?\$?\s*)?([\d.,]+\s*(?:mil|reais)?)"
            r".*?"
            r"(?:vir(?:ar|e|a|em|arem)|transformar\s+em)\s+"
            r"(?:r?\$?\s*)?([\d.,]+\s*(?:mil|reais)?)",
            texto_lower,
        )
        if p2:
            investir = parse_valor(p2.group(1))
            alvo = parse_valor(p2.group(2))
            if investir and alvo and alvo > investir:
                ganhar = alvo - investir

    # ── Padrão 3: "X virar/vire Y" (sem verbo investir) ──
    if not investir:
        p3 = re.search(
            r"(?:r?\$?\s*)?([\d.,]+\s*(?:mil|reais)?)"
            r"\s+(?:vir(?:ar|e|a|em|arem))\s+"
            r"(?:r?\$?\s*)?([\d.,]+\s*(?:mil|reais)?)",
            texto_lower,
        )
        if p3:
            investir = parse_valor(p3.group(1))
            alvo = parse_valor(p3.group(2))
            if investir and alvo and alvo > investir:
                ganhar = alvo - investir

    # ── Padrão 4: "transformar X em Y" ──
    if not investir:
        p4 = re.search(
            r"(?:transformar|fazer)\s+"
            r"(?:r?\$?\s*)?([\d.,]+\s*(?:mil|reais)?)"
            r"\s+(?:em|virar)\s+"
            r"(?:r?\$?\s*)?([\d.,]+\s*(?:mil|reais)?)",
            texto_lower,
        )
        if p4:
            investir = parse_valor(p4.group(1))
            alvo = parse_valor(p4.group(2))
            if investir and alvo and alvo > investir:
                ganhar = alvo - investir

    # ── Padrão 5: "quero dobrar/triplicar X" ──
    if not investir:
        p5 = re.search(
            r"(?:dobrar|duplicar)\s+(?:r?\$?\s*)?([\d.,]+\s*(?:mil|reais)?)",
            texto_lower,
        )
        if p5:
            investir = parse_valor(p5.group(1))
            if investir:
                ganhar = investir  # dobrar = ganhar 100%

        p5b = re.search(
            r"(?:triplicar)\s+(?:r?\$?\s*)?([\d.,]+\s*(?:mil|reais)?)",
            texto_lower,
        )
        if p5b:
            investir = parse_valor(p5b.group(1))
            if investir:
                ganhar = investir * 2  # triplicar = ganhar 200%

    # ── Padrão 6: "tenho X e quero dobrar" ──
    if not investir:
        p6 = re.search(
            r"(?:tenho|possuo)\s+(?:r?\$?\s*)?([\d.,]+\s*(?:mil|reais)?)"
            r".*?(?:dobr|triplic|duplic)",
            texto_lower,
        )
        if p6:
            investir = parse_valor(p6.group(1))
            if investir:
                if "triplic" in texto_lower:
                    ganhar = investir * 2
                else:
                    ganhar = investir

    # ── Padrão 7: fallback com 2 valores (menor=investir, diferença=ganhar) ──
    if not investir and len(valores) >= 2:
        # Verificar se o contexto sugere investimento
        if any(
            p in texto_lower
            for p in ("investir", "investindo", "aplicar", "virar", "ganhar")
        ):
            valores_sorted = sorted(valores)
            investir = valores_sorted[0]
            alvo = valores_sorted[-1]
            if alvo > investir:
                ganhar = alvo - investir

    # ── Extrair prazo ──
    if investir and ganhar:
        # Mapear texto de prazo para dias
        prazo_map = {
            "uma semana": 7, "1 semana": 7, "uma sem": 7, "1 sem": 7,
            "duas semanas": 14, "2 semanas": 14, "2 sem": 14,
            "tres semanas": 21, "3 semanas": 21,
            "um mês": 30, "um mes": 30, "1 mês": 30, "1 mes": 30,
            "dois meses": 60, "dois mes": 60, "2 meses": 60, "2 mes": 60,
            "tres meses": 90, "três meses": 90, "3 meses": 90, "3 mes": 90,
            "seis meses": 180, "6 meses": 180, "6 mes": 180,
            "um ano": 365, "1 ano": 365,
        }

        for label, d in prazo_map.items():
            if label in texto_lower:
                dias = d
                break

        # Tentar extrair "X dias/semanas/meses"
        if not dias:
            pd = re.search(r"(\d+)\s*dias?", texto_lower)
            if pd:
                dias = int(pd.group(1))

            pw = re.search(r"(\d+)\s*sem(?:ana)?s?", texto_lower)
            if pw:
                dias = int(pw.group(1)) * 7

            pm = re.search(r"(\d+)\s*m[eê]s(?:es)?", texto_lower)
            if pm:
                dias = int(pm.group(1)) * 30

            pa = re.search(r"(\d+)\s*anos?", texto_lower)
            if pa:
                dias = int(pa.group(1)) * 365

        # Default: se não informou prazo, assumir 30 dias
        if not dias:
            dias = 30

        # Validar
        if investir >= 10 and ganhar > 0 and dias > 0:
            return {"investir": investir, "ganhar": ganhar, "dias": dias}

    return None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Processa qualquer mensagem de texto que não seja um comando.
    Detecta intenções de investimento em linguagem natural e,
    se encontrar, gera um plano com análise de mercado ao vivo.
    Caso contrário, funciona como a interface principal com a IA.
    """
    if not update.message or not update.message.text:
        return

    telegram_id = update.effective_user.id
    nome = update.effective_user.first_name or "Usuário"
    pergunta = update.message.text.strip()

    # Garantir que o usuário existe no banco (caso o container tenha reiniciado)
    await get_or_create_user(telegram_id, nome)

    if len(pergunta) < 3:
        await update.message.reply_text(
            "Pode elaborar melhor sua pergunta? 😊"
        )
        return

    # ── Detectar objetivo de investimento em linguagem natural ──
    objetivo = _extrair_objetivo_investimento(pergunta)
    if objetivo:
        # Verificar limite de consultas (desafio conta como consulta)
        pode_consultar = await check_and_use_consulta(
            telegram_id, FREE_DAILY_LIMIT
        )
        if not pode_consultar:
            await update.message.reply_text(
                f"😕 Você atingiu o limite de **{FREE_DAILY_LIMIT} consultas grátis** "
                f"por dia.\n\n"
                f"💎 Com o **Premium** (R${PREMIUM_PRICE:.2f}/mês) você tem:\n"
                "• Consultas ilimitadas com a IA\n"
                "• Planos de investimento ilimitados\n"
                "• E muito mais!\n\n"
                "Use /premium para assinar 🚀",
                parse_mode="Markdown",
            )
            return

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )

        await update.message.reply_text(
            f"🎯 Entendi! Você quer investir **R${objetivo['investir']:,.2f}** "
            f"e ganhar **R${objetivo['ganhar']:,.2f}**.\n\n"
            f"🔍 **Analisando o mercado ao vivo...**\n"
            f"_(verificando 8 ativos — pode levar alguns segundos)_",
            parse_mode="Markdown",
        )

        # Usar o planejador do desafio com análise ao vivo
        from handlers.desafio import _montar_plano

        msg = await _montar_plano(
            objetivo["investir"], objetivo["ganhar"], objetivo["dias"]
        )

        # Dar XP pelo desafio + registrar acesso diário
        from services.gamification_service import add_xp, registrar_acesso_diario

        await registrar_acesso_diario(telegram_id)
        resultado_xp = await add_xp(telegram_id, "desafio")

        # Rodapé com XP e consultas restantes
        restantes = await get_remaining_consultas(
            telegram_id, FREE_DAILY_LIMIT
        )
        rodape = ""
        if restantes is not None and restantes <= FREE_DAILY_LIMIT:
            if restantes == 0:
                rodape = "\n\n---\n_Última consulta grátis de hoje. /premium para ilimitado._"
            else:
                rodape = f"\n\n---\n_{restantes}/{FREE_DAILY_LIMIT} consultas grátis restantes hoje._"

        xp_ganho = resultado_xp.get("xp_ganho", 0)
        if xp_ganho:
            rodape += f" | ⭐ +{xp_ganho} XP"
        if resultado_xp.get("subiu_nivel"):
            from handlers.gamificacao import formatar_xp_ganho

            rodape += f"\n🎉 {formatar_xp_ganho(resultado_xp)}"

        # Enviar plano (pode ser longo, dividir se necessário)
        full_msg = msg + rodape
        if len(full_msg) <= 4000:
            await update.message.reply_text(
                full_msg, parse_mode="Markdown"
            )
        else:
            # Dividir em partes
            remaining = full_msg
            while remaining:
                if len(remaining) <= 4000:
                    await update.message.reply_text(
                        remaining, parse_mode="Markdown"
                    )
                    break
                corte = remaining.rfind("\n", 0, 4000)
                if corte == -1:
                    corte = 4000
                await update.message.reply_text(
                    remaining[:corte], parse_mode="Markdown"
                )
                remaining = remaining[corte:].lstrip("\n")

        return

    # ── Fluxo normal: consulta à IA ──

    # Verificar limite de consultas
    pode_consultar = await check_and_use_consulta(telegram_id, FREE_DAILY_LIMIT)

    if not pode_consultar:
        await update.message.reply_text(
            f"😕 Você atingiu o limite de **{FREE_DAILY_LIMIT} consultas grátis** "
            f"por dia.\n\n"
            f"💎 Com o **Premium** (R${PREMIUM_PRICE:.2f}/mês) você tem:\n"
            "• Consultas ilimitadas com a IA\n"
            "• Registro de gastos\n"
            "• Plano financeiro personalizado\n"
            "• Relatórios semanais\n"
            "• E muito mais!\n\n"
            "Use /premium para assinar 🚀",
            parse_mode="Markdown",
        )
        return

    # Indicar que está "digitando"
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    # Buscar contexto financeiro do usuário
    contexto = await get_financial_context(telegram_id)

    # Consultar a IA
    resposta = await consultar_ia(pergunta, contexto)

    # Se a IA retornou erro, devolver a consulta ao usuário
    if resposta.startswith("😕") or resposta.startswith("⚠️") or resposta.startswith("🔄"):
        await rollback_consulta(telegram_id)
        await update.message.reply_text(resposta)
        return

    # Dar XP pela consulta + registrar acesso diário
    from services.gamification_service import add_xp, registrar_acesso_diario

    await registrar_acesso_diario(telegram_id)
    resultado_xp = await add_xp(telegram_id, "consulta_ia")

    # Mostrar quantas consultas restam (só para free)
    restantes = await get_remaining_consultas(telegram_id, FREE_DAILY_LIMIT)
    rodape = ""
    if restantes is not None and restantes <= FREE_DAILY_LIMIT:
        if restantes == 0:
            rodape = f"\n\n---\n_Última consulta grátis de hoje. /premium para ilimitado._"
        else:
            rodape = f"\n\n---\n_{restantes}/{FREE_DAILY_LIMIT} consultas grátis restantes hoje._"

    # Adicionar XP no rodapé
    xp_ganho = resultado_xp.get("xp_ganho", 0)
    if xp_ganho:
        rodape += f" | ⭐ +{xp_ganho} XP"
    if resultado_xp.get("subiu_nivel"):
        from handlers.gamificacao import formatar_xp_ganho

        rodape += f"\n🎉 {formatar_xp_ganho(resultado_xp)}"

    await update.message.reply_text(
        resposta + rodape,
        parse_mode="Markdown",
    )


async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler do /ajuda — lista todos os comandos."""
    await update.message.reply_text(
        "🤖 **FinançasIA — Comandos disponíveis**\n\n"
        "💬 **Consultar a IA:**\n"
        "Envie qualquer dúvida financeira!\n"
        "💡 Ou diga algo como: _\"quero investir 500 e ganhar 100\"_\n"
        "— eu analiso o mercado ao vivo e monto um plano!\n\n"
        "🎓 **Aprender do zero:**\n"
        "/aprender — Aulas passo a passo (do zero mesmo!)\n"
        "/comocomprar — 📖 Como comprar cada tipo de ativo\n\n"
        "📊 **Investimentos:**\n"
        "/oquefazer — 🔥 Estudo de alocação com análise ao vivo\n"
        "/desafio — 🎯 \"Quero ganhar X investindo Y em Z tempo\"\n"
        "/analisar [ativo] — 📈 Análise de mercado em tempo real\n"
        "/simular — 📈 Projeção de patrimônio futuro\n"
        "/investir — Calcular rendimento\n"
        "/comparar — Comparar bancos/corretoras\n"
        "/perfil — Seu perfil de investidor\n"
        "/sugestoes — Investimentos para o seu perfil\n\n"
        "🤖 **Investimento automático:**\n"
        "/aporte — 🚀 Plano mensal (aviso o que comprar no dia do salário!)\n"
        "/meuplano — Ver seu plano mensal\n"
        "/pausaraporte — Pausar lembretes\n\n"
        "📡 **Radar & Alertas:**\n"
        "/radar — 📡 Escaneia 13 ativos e rankeia oportunidades\n"
        "/alvo [ativo] [preço] — 🎯 Alerta quando o preço chegar lá\n"
        "/alvos — 📋 Seus alertas de preço ativos\n"
        "/alertamercado — 🚨 Alertas URGENTES de oportunidades\n"
        "/bomdia — ☀️ Resumo matinal personalizado (todo dia 7h)\n"
        "/seguir [ativo] — 👁️ Adicionar à watchlist\n"
        "/meusativos — 📋 Sua watchlist com preços ao vivo\n\n"
        "💼 **Carteira:**\n"
        "/comprei — Registrar uma compra (com stop-loss automático!)\n"
        "/carteira — Posições com lucro/prejuízo ao vivo\n"
        "/evolucao — 📈 Gráfico de evolução da carteira\n"
        "/alertas — Notificações automáticas de venda/compra\n"
        "/ir — 📊 Calculadora de Imposto de Renda\n"
        "/compartilhar — 🏆 Compartilhar resultados nas redes\n\n"
        "💸 **Controle de gastos:**\n"
        "/gasto — Registrar um gasto\n"
        "/resumo — Resumo dos gastos do mês\n"
        "/orcamento — 💰 Orçamento mensal inteligente\n\n"
        "💳 **Dívidas:**\n"
        "/dividas — Ver/cadastrar dívidas\n"
        "/estrategia — Plano para quitar dívidas\n\n"
        "🎯 **Metas:**\n"
        "/meta — Criar uma meta financeira\n"
        "/metas — Ver suas metas\n\n"
        "🛠️ **Ferramentas:**\n"
        "/painel — 📊 Dashboard financeiro completo\n"
        "/versus — ⚔️ Comparar dois ativos ao vivo\n"
        "/aposentar — 🏖️ Calculadora de independência financeira\n"
        "/dicadodia — 💡 Dica financeira do dia\n\n"
        "🏆 **Gamificação:**\n"
        "/conquistas — ⭐ XP, nível, conquistas e streak\n"
        "/ranking — 🏅 Ranking global\n"
        "/indicar — 🤝 Convide amigos e ganhe bônus\n\n"
        "⚙️ **Outros:**\n"
        "/premium — Plano premium\n"
        "/termos — 📜 Termos de uso e privacidade\n"
        "/start — Recomeçar\n"
        "/ajuda — Esta mensagem\n",
        parse_mode="Markdown",
    )


async def resetlimite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler do /resetlimite — reseta o contador de consultas do usuário."""
    telegram_id = update.effective_user.id
    from database.db import get_db

    db = await get_db()
    try:
        # Mostrar estado atual
        cursor = await db.execute(
            "SELECT consultas_hoje, data_ultima_consulta FROM usuarios "
            "WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        if row:
            info = dict(row)
            await update.message.reply_text(
                f"📊 Estado atual:\n"
                f"• consultas_hoje: {info['consultas_hoje']}\n"
                f"• data_ultima_consulta: {info['data_ultima_consulta']}\n"
                f"• FREE_DAILY_LIMIT: {FREE_DAILY_LIMIT}\n\n"
                f"🔄 Resetando..."
            )
        # Resetar
        await db.execute(
            "UPDATE usuarios SET consultas_hoje = 0 WHERE telegram_id = ?",
            (telegram_id,),
        )
        await db.commit()
        await update.message.reply_text(
            "✅ Limite resetado! Agora mande sua pergunta. 😊"
        )
    finally:
        await db.close()


def get_consulta_handlers() -> list:
    """Retorna os handlers de consulta."""
    from telegram.ext import CommandHandler

    return [
        CommandHandler("ajuda", ajuda),
        CommandHandler("help", ajuda),
        CommandHandler("resetlimite", resetlimite),
        # Este deve ser adicionado por último (pega qualquer texto)
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
    ]
