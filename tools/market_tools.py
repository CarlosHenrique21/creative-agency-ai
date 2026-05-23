"""
Tool: analyze_market_trends
Pesquisa tendências do mercado de legal tech fiscal / comex brasileiro
usando o modelo com conhecimento atualizado e salva market_intelligence
no session state.
"""
from __future__ import annotations

from openai import OpenAI
from google.adk.tools import ToolContext

from core.config import settings

_client = OpenAI(api_key=settings.openai_api_key)

_PRODUCT_CONTEXT = """
Produto: BussolaFiscal — SaaS de classificação NCM com IA para comércio exterior brasileiro.
Público-alvo: equipes fiscais de empresas importadoras/exportadoras, despachantes aduaneiros,
assessorias de comex, analistas tributários.
Dores: erros de NCM geram multas de até 150%; processo manual leva +10h/semana; sem rastreabilidade.
Diferencial: 131 regras tributárias especializadas, resultado em segundos, 100% auditável, modelo de créditos sem expiração.
Nicho: legal tech fiscal, B2B, comex brasileiro, automação tributária.
"""

_RESEARCH_PROMPT = """Você é um especialista em marketing B2B para legal tech fiscal e comércio exterior brasileiro.

Contexto do produto:
{product_context}

Campanha atual: {brief}
Plataformas: {platforms}

Pesquise e analise as seguintes dimensões para orientar a campanha:

1. TENDÊNCIAS DO NICHO (2025-2026):
   - O que está em alta em automação fiscal e legal tech no Brasil?
   - Mudanças regulatórias recentes que afetam empresas de comex (NCM, SEFAZ, Receita Federal)?
   - Adoção de IA em processos fiscais e tributários: onde está o mercado?

2. LINGUAGEM QUE RESSOA COM O PÚBLICO:
   - Quais termos técnicos e dores específicas os profissionais de comex usam?
   - O que gera medo/urgência neste público (autuações, multas, prazos)?
   - O que gera aspiração (velocidade, precisão, tranquilidade, compliance)?

3. ÂNGULOS DE COPY MAIS EFICAZES AGORA:
   - Melhor abordagem: dor (medo de multa) vs. ganho (eficiência) vs. novidade (IA)?
   - Qual hook funciona melhor no Instagram para público B2B técnico?
   - Qual abordagem funciona no LinkedIn para decisores (gerentes fiscais, CFOs)?

4. OPORTUNIDADES DE DIFERENCIAÇÃO:
   - Como a BussolaFiscal pode se destacar da concorrência (planilhas, consultorias manuais)?
   - Qual mensagem única captura a proposta de valor de forma irresistível?

5. SUGESTÕES CONCRETAS PARA A CAMPANHA ATUAL:
   - 3 opções de headline para Instagram (curto, impactante, orientado à dor ou ganho)
   - 3 opções de headline para LinkedIn (profissional, orientado a ROI/compliance)
   - 1 hook de abertura para cada plataforma
   - Palavras-chave e termos a usar (e a evitar)

Retorne uma análise estruturada e acionável em português do Brasil.
Seja específico e prático — o copywriter vai usar isso diretamente para criar os textos dos flyers."""


def analyze_market_trends(tool_context: ToolContext) -> dict:
    """
    Pesquisa tendências do mercado de legal tech fiscal e comex brasileiro
    e gera market_intelligence estruturada para orientar a campanha.

    Returns:
        dict com market_intelligence salvo em session state
    """
    brief: str = tool_context.state.get("brief", "")
    platforms: list = tool_context.state.get("platforms", [])

    prompt = _RESEARCH_PROMPT.format(
        product_context=_PRODUCT_CONTEXT,
        brief=brief,
        platforms=", ".join(platforms) if platforms else "instagram_feed, linkedin_post",
    )

    response = _client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é um estrategista de marketing B2B especializado em legal tech, "
                    "automação fiscal e comércio exterior brasileiro. "
                    "Tem conhecimento profundo do mercado de 2025-2026, "
                    "das regulamentações da Receita Federal, SEFAZ e NCM, "
                    "e das melhores práticas de marketing para público técnico B2B."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=2500,
    )

    market_intelligence = response.choices[0].message.content or ""

    # Save to session state
    tool_context.state["market_intelligence"] = market_intelligence

    # Extract a short summary for the return value
    lines = [l.strip() for l in market_intelligence.split("\n") if l.strip()]
    summary_lines = lines[:8]

    return {
        "status": "success",
        "market_intelligence_saved": True,
        "preview": "\n".join(summary_lines),
        "total_insights": len(lines),
    }
