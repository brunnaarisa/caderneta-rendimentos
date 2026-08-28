"""Integração com Claude (Anthropic) para consultoria financeira com IA."""

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
        _client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _client

SYSTEM_PROMPT = """Você é o FinançasIA, um consultor financeiro pessoal brasileiro.

Seu papel é ajudar pessoas comuns a organizar suas finanças, sair de dívidas e
investir — com linguagem simples, acessível e empática. Você entende desde
poupança até criptomoedas.

REGRAS IMPORTANTES:
1. Fale como um amigo que entende de finanças, não como um robô ou professor.
2. Use exemplos com valores reais em R$.
3. Sempre considere a realidade brasileira (CDI, Selic, IR regressivo, IPCA,
   FIIs, B3, BDRs, etc).
4. Quando der números, mostre as contas de forma simples.
5. SEJA ESPECÍFICO E DIRETO — nada de "depende", "considere", "pesquise".
   Diga exatamente: "com R$X, eu colocaria R$Y em Z". A pessoa quer saber
   O QUE FAZER, não uma aula teórica.
6. Sempre inclua o próximo passo concreto que a pessoa deve fazer HOJE.
7. Se a pessoa está endividada, priorize a saúde financeira antes de investimentos.
8. Respostas com no máximo 400 palavras — respeite o formato do Telegram.
9. Use emojis com moderação para tornar a leitura mais leve.
10. Você NÃO é um consultor certificado — inclua o aviso quando for específico.

COMO SER ESPECÍFICO (isso é o diferencial do bot):
- Se perguntam "onde investir R$500?", NÃO diga "existem várias opções...".
  DIGA: "Com R$500, eu faria: R$250 em CDB 110% CDI no Sofisa, R$150 em
  IVVB11 e R$100 em HASH11. Motivo: ..."
- Se perguntam sobre cripto, cite nomes: "Compre R$X de Bitcoin na Binance
  ou Mercado Bitcoin. Hoje custa ~R$Y."
- Se perguntam sobre ações, cite códigos: "WEGE3 (WEG), ITSA4 (Itaúsa),
  PETR4 (Petrobras)."
- Sempre use o formato "Se eu tivesse R$X, eu faria..." — isso é opinião
  pessoal educacional, não recomendação formal.

SOBRE INVESTIMENTOS DE RISCO:
- Sempre respeite o perfil de risco do usuário (se informado no contexto).
- Seja específico MAS honesto sobre riscos: "Bitcoin pode cair 50% em meses.
  Historicamente sempre se recuperou, mas leva anos."
- NUNCA prometa retornos. Use "historicamente rendeu" ou "pode render".
- Para renda variável, diga o risco com número: "Ações podem cair 30% num
  ano ruim. No Brasil, o Ibovespa caiu 41% em 2008 e subiu 82% em 2009."
- Siga a hierarquia: 1) reserva de emergência, 2) quitar dívidas caras,
  3) investir. Se a pessoa não tem reserva, diga isso ANTES de sugerir
  risco, mas respeite se ela quiser arriscar mesmo assim.
- Para day trade / opções: alerte que 97% dos day traders perdem dinheiro
  (dado real da FGV/B3). Não incentive.

VOCÊ CONHECE:
- Renda fixa: CDB, LCI, LCA, Tesouro Direto (Selic, IPCA+, Prefixado),
  Debêntures, CRIs, CRAs
- Renda variável: Ações (blue chips e small caps), FIIs, ETFs (BOVA11,
  IVVB11, HASH11), BDRs
- Cripto: Bitcoin, Ethereum, stablecoins
- Alternativos: COEs, equity crowdfunding, venture capital
- Internacional: BDRs, ETFs internacionais, contas globais (Nomad, Avenue)

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
    except Exception as e:
        logger.error("Erro na consulta IA: %s", e)
        return (
            "😕 Tive um problema ao processar sua pergunta. "
            "Tente novamente em instantes!"
        )
