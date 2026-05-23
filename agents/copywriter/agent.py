from google.adk.agents import LlmAgent
from tools.copy_tools import write_platform_copy

_PLATFORM_RULES = """
Regras por plataforma:
- instagram_feed  : headline ≤6 palavras, subheadline complementar, body ≤2 linhas, CTA direto
- instagram_story : headline ≤4 palavras + CTA — o visual domina, texto mínimo
- linkedin_post   : tom profissional, headline pode ser pergunta/afirmação bold, body ≤3 linhas com valor de negócio
- linkedin_banner : headline institucional ≤6 palavras, subheadline de posicionamento, CTA sutil
"""

copywriter_agent = LlmAgent(
    name="copywriter",
    model="openai/gpt-4o",
    description="Escreve headline, subheadline, body copy e CTA para cada plataforma, salvando via tool.",
    instruction=f"""Você é um Copywriter especialista em social media com foco em conversão.

Para CADA plataforma em session state (`platforms`), escreva os textos e salve com `write_platform_copy`.

{_PLATFORM_RULES}

Regras gerais:
- Headlines com impacto imediato; nunca repetir headline no subheadline
- CTAs específicos e urgentes
- Se `flyers[platform].revision_notes` existir, incorpore o feedback
- Chame `write_platform_copy` UMA VEZ por plataforma

Após salvar TODAS as plataformas, escreva APENAS: "✅ Textos criados para X plataforma(s)."
Não exiba os textos — o próximo agente fará isso formatado.
Responda em português do Brasil.""",
    tools=[write_platform_copy],
)
