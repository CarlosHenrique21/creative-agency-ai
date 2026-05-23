from google.adk.agents import LlmAgent

social_media_manager_agent = LlmAgent(
    name="social_media_manager",
    model="openai/gpt-4o",
    description="Revisa os flyers sob a ótica das melhores práticas de cada plataforma e registra o feedback no histórico.",
    instruction="""Você é um Social Media Manager. Avalie os flyers de session state (`flyers`) contra as boas práticas de cada plataforma.

Para cada plataforma, escreva UMA linha apenas:
[PLATAFORMA] ✅ APROVADO | ⚠️ ATENÇÃO: <observação curta>

Seja conciso — máx 1 linha por plataforma. Sem introduções, sem conclusões.
Responda em português do Brasil.""",
    tools=[],
)
