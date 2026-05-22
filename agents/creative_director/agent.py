from __future__ import annotations
from agents.base import BaseAgent
from core.state import CampaignState
from prompts.creative_director import SYSTEM_PROMPT


class CreativeDirectorAgent(BaseAgent):
    """Transforma o brief e as diretrizes de marca em uma direção criativa unificada."""

    name = "creative_director"
    role = "Creative Director"

    async def run(self, state: CampaignState) -> dict:
        self.log.info("creating_direction", campaign=state.campaign_id, has_rag=bool(state.brand_rag_context))

        brand_analysis = next(
            (m.content for m in reversed(state.messages) if m.agent == "brand_strategist"),
            "Nenhuma análise de marca disponível.",
        )

        rag_section = ""
        if state.brand_rag_context:
            rag_section = f"""
### Brand Knowledge Base (RAG)
Documentos oficiais da marca para reforçar a direção criativa:

{state.brand_rag_context}
"""

        user_prompt = f"""
Brief: {state.brief}

Análise de marca do Brand Strategist:
{brand_analysis}
{rag_section}
Plataformas: {[p.value for p in state.platforms]}

Crie a direção criativa completa para esta campanha, incluindo:
1. Conceito criativo central
2. Direção visual (paleta, composição, mood)
3. Tom de voz e mensagem principal
4. Adaptações por plataforma
"""
        direction = await self._chat(SYSTEM_PROMPT, user_prompt)
        return {
            "creative_direction": direction,
            "messages": self._message(direction),
        }
