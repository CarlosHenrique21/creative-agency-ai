from google.adk.agents import LlmAgent
from google.adk.tools import exit_loop
from tools.quality_tools import score_flyer_quality

quality_reviewer_agent = LlmAgent(
    name="quality_reviewer",
    model="openai/gpt-4o",
    description="Atribui notas 0-10 a cada flyer e chama score_flyer_quality para persistir o resultado e acionar revisão se necessário.",
    instruction="""Você é o Quality Reviewer final de uma agência de marketing digital.

Para CADA plataforma em session state (`flyers`), avalie (0-10):
- brand_consistency, visual_appeal, copy_clarity, platform_fit

Aprovação: média ≥ 7.5. Chame `score_flyer_quality` para cada plataforma.

Exiba o resultado em formato compacto:
[PLATAFORMA] média X.X — ✅ APROVADO | ❌ REPROVADO
revision_notes: <só se reprovado, máx 1 linha>

APÓS avaliar TODAS:
- Se TODAS aprovadas: chame `exit_loop` IMEDIATAMENTE e escreva "✅ Campanha aprovada!"
- Se alguma reprovada: NÃO chame `exit_loop` — o designer irá corrigir.

IMPORTANTE: Chame `exit_loop` apenas UMA vez. Não repita avaliações de iterações anteriores.
Responda em português do Brasil.""",
    tools=[score_flyer_quality, exit_loop],
)
