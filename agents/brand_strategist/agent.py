from __future__ import annotations
from agents.base import BaseAgent
from core.state import CampaignState
from prompts.brand_strategist import SYSTEM_PROMPT


class BrandStrategistAgent(BaseAgent):
    """Analisa o brief e consolida o perfil de marca antes de qualquer criação."""

    name = "brand_strategist"
    role = "Brand Strategist"

    async def run(self, state: CampaignState) -> dict:
        self.log.info("analyzing_brand", brand=state.brand.name)

        user_prompt = f"""
Brief da campanha: {state.brief}

Perfil de marca:
- Nome: {state.brand.name}
- Tom: {state.brand.tone}
- Estilo tipográfico: {state.brand.font_style}
- Cor primária: {state.brand.primary_color}
- Cor secundária: {state.brand.secondary_color}
- Cor de destaque: {state.brand.accent_color}

Plataformas alvo: {[p.value for p in state.platforms]}

Gere as diretrizes de posicionamento e linguagem visual para esta campanha.
"""
        analysis = await self._chat(SYSTEM_PROMPT, user_prompt)
        return {"messages": self._message(analysis)}
