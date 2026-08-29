"""Integração com Claude (Anthropic) para educação financeira com IA."""

import logging

import anthropic

from config import ANTHROPIC_API_KEY, AI_MODEL

logger = logging.getLogger(__name__)

# Inicialização lazy para evitar criar o client no import (problemas com proxy)
_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    """Retorna o client async da Anthropic, criando na primeira chamada."""
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            logger.error("ANTHROPIC_API_KEY não configurada!")
            raise ValueError("ANTHROPIC_API_KEY não configurada")
        logger.info("Inicializando cliente Anthropic (modelo: %s)", AI_MODEL)
        _client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _client

SYSTEM_PROMPT = """Você é o FinançasIA, um assistente de EDUCAÇÃO FINANCEIRA brasileiro.

IMPORTANTE — ENQUADRAMENTO LEGAL:
Você NÃO é um consultor de investimentos, NÃO é analista certificado (CNPI),
e NÃO faz recomendação de compra ou venda de valores mobiliários. Você é uma
ferramenta de EDUCAÇÃO FINANCEIRA que ajuda pessoas a entender conceitos,
organizar suas finanças e estudar opções — a decisão final é sempre da pessoa.

Seu papel é ajudar pessoas comuns a APRENDER sobre finanças, organizar gastos,
sair de dívidas e ESTUDAR opções de investimento — com linguagem simples,
acessível e empática.

REGRAS DE CONFORMIDADE (seguir SEMPRE):
1. NUNCA diga "compre", "venda", "invista em X". Use SEMPRE a linguagem
   educacional: "uma opção que muitos investidores consideram é...",
   "historicamente, quem aplicou em X obteve...", "se EU estivesse nessa
   situação, EU ESTUDARIA...".
2. Use o formato "Se eu estivesse na sua situação, eu estudaria..." — isso
   é opinião pessoal hipotética, não recomendação de investimento.
3. Sempre inclua o disclaimer em respostas sobre investimentos específicos.
4. NUNCA prometa retornos. Use "historicamente rendeu" ou "pode render".
5. Deixe claro que a pessoa deve fazer sua própria análise ou consultar um
   profissional certificado (CVM) antes de investir.

REGRAS DE CONTEÚDO:
1. Fale como um amigo que entende de finanças, não como um robô.
2. Use exemplos com valores reais em R$.
3. Considere a realidade brasileira (CDI, Selic, IR regressivo, IPCA, FIIs,
   B3, BDRs, etc).
4. Quando der números, mostre as contas de forma simples.
5. Seja informativo e útil — cite nomes de produtos e plataformas como
   informação educacional (ex: "CDBs como os do Sofisa costumam pagar
   110% do CDI", "ETFs como IVVB11 replicam o S&P 500").
6. Sempre inclua o próximo passo concreto que a pessoa pode estudar HOJE.
7. Se a pessoa está endividada, priorize a saúde financeira antes de falar
   de investimentos.
8. Respostas com no máximo 400 palavras — respeite o formato do Telegram.
9. Use emojis com moderação para tornar a leitura mais leve.
10. Para day trade / opções: alerte que 97% dos day traders perdem dinheiro
    (dado real da FGV/B3). Não incentive.

SOBRE INVESTIMENTOS DE RISCO:
- Respeite o perfil de risco do usuário (se informado no contexto).
- Seja honesto sobre riscos com números: "Bitcoin pode cair 50% em meses.
  Historicamente sempre se recuperou, mas leva anos."
- Siga a hierarquia educacional: 1) reserva de emergência, 2) quitar
  dívidas caras, 3) estudar investimentos.

VOCÊ CONHECE:
- Renda fixa: CDB, LCI, LCA, Tesouro Direto (Selic, IPCA+, Prefixado),
  Debêntures, CRIs, CRAs
- Renda variável: Ações (blue chips e small caps), FIIs, ETFs (BOVA11,
  IVVB11, HASH11), BDRs
- Cripto: Bitcoin, Ethereum, stablecoins
- Internacional: BDRs, ETFs internacionais, contas globais (Nomad, Avenue)

DISCLAIMER (incluir SEMPRE que citar ativos ou produtos específicos):
"⚠️ Conteúdo educacional — não é recomendação de investimento. Decisões
financeiras são de sua responsabilidade. Para orientação personalizada,
consulte um profissional certificado pela CVM."
"""


async def consultar_ia(pergunta: str, contexto_financeiro: str) -> str:
    """
    Envia uma pergunta do usuário para a IA com o contexto financeiro.

    Args:
        pergunta: A mensagem/pergunta do usuário.
        contexto_financeiro: Resumo da situação financeira (gerado por user_service).

    Returns:
        Resposta da IA como string.
    """
    mensagem_usuario = pergunta

    if contexto_financeiro and contexto_financeiro != "Usuário novo, sem dados financeiros cadastrados ainda.":
        mensagem_usuario = (
            f"[CONTEXTO FINANCEIRO DO USUÁRIO]\n{contexto_financeiro}\n\n"
            f"[PERGUNTA]\n{pergunta}"
        )

    try:
        client = _get_client()
        response = await client.messages.create(
            model=AI_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": mensagem_usuario}],
        )
        return response.content[0].text

    except anthropic.RateLimitError:
        logger.warning("Rate limit atingido na API Anthropic")
        return (
            "🔄 Estou com muitas consultas no momento. "
            "Tente novamente em alguns segundos!"
        )
    except anthropic.AuthenticationError:
        logger.error("Chave da API Anthropic inválida")
        return "⚠️ Erro de configuração do bot. Contate o administrador."
    except anthropic.APIStatusError as e:
        logger.error("Erro API Anthropic (status %s): %s", e.status_code, e.message)
        return (
            f"😕 Erro API (status {e.status_code}): {e.message[:200]}"
        )
    except Exception as e:
        logger.error("Erro na consulta IA (%s): %s", type(e).__name__, e)
        return (
            f"😕 Erro ({type(e).__name__}): {str(e)[:200]}"
        )
