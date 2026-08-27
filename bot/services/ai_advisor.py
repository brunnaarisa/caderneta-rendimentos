"""Integração com Claude (Anthropic) para consultoria financeira com IA."""

import logging

import anthropic

from config import ANTHROPIC_API_KEY, AI_MODEL

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Você é o FinançasIA, um consultor financeiro pessoal brasileiro.

Seu papel é ajudar pessoas comuns a organizar suas finanças, sair de dívidas e
começar a investir — com linguagem simples, acessível e empática.

REGRAS IMPORTANTES:
1. Fale como um amigo que entende de finanças, não como um robô ou professor.
2. Use exemplos com valores reais em R$.
3. Sempre considere a realidade brasileira (CDI, Selic, IR regressivo, IPCA, etc).
4. Quando der números, mostre as contas de forma simples.
5. Seja direto — dê recomendações claras, não fique em cima do muro.
6. Sempre inclua o próximo passo concreto que a pessoa deve fazer.
7. Se a pessoa está endividada, priorize a saúde financeira antes de investimentos.
8. Nunca recomende investimentos de alto risco sem avisar dos riscos.
9. Respostas com no máximo 400 palavras — respeite o formato do Telegram.
10. Use emojis com moderação para tornar a leitura mais leve.
11. Você NÃO é um consultor certificado — lembre disso quando apropriado.

AVISO LEGAL que você deve incluir APENAS quando der recomendações específicas
de produtos/investimentos:
"⚠️ Isso não é uma recomendação oficial de investimento. Consulte um profissional
certificado para decisões importantes."
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
        response = client.messages.create(
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
    except Exception as e:
        logger.error("Erro na consulta IA: %s", e)
        return (
            "😕 Tive um problema ao processar sua pergunta. "
            "Tente novamente em instantes!"
        )
