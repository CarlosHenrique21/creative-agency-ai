from __future__ import annotations
from agents.base import BaseAgent
from core.state import CampaignState, FlyerSpec
from prompts.copywriter import SYSTEM_PROMPT, platform_copy_instructions


class CopywriterAgent(BaseAgent):
    """Escreve todos os textos dos flyers adaptados para cada plataforma."""

    name = "copywriter"
    role = "Copywriter"

    async def run(self, state: CampaignState) -> dict:
        self.log.info("writing_copy", platforms=len(state.platforms))

        flyers: dict[str, FlyerSpec] = {}

        for platform in state.platforms:
            spec = state.flyers.get(platform.value, FlyerSpec(platform=platform))
            spec.set_dimensions()

            revision_context = (
                f"\nFeedback da revisão anterior: {spec.revision_notes}"
                if spec.revision_notes
                else ""
            )

            user_prompt = f"""
Brief: {state.brief}
Direção criativa: {state.creative_direction}
Plataforma: {platform.value} ({spec.width}x{spec.height}px)
{platform_copy_instructions(platform)}
{revision_context}

Retorne EXATAMENTE neste formato JSON:
{{
  "headline": "...",
  "subheadline": "...",
  "body_copy": "...",
  "call_to_action": "..."
}}
"""
            raw = await self._chat(SYSTEM_PROMPT, user_prompt)

            import json, re
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                spec.headline = data.get("headline", "")
                spec.subheadline = data.get("subheadline", "")
                spec.body_copy = data.get("body_copy", "")
                spec.call_to_action = data.get("call_to_action", "")

            flyers[platform.value] = spec

        return {
            "flyers": flyers,
            "messages": self._message(f"Copies escritas para {len(flyers)} plataformas."),
        }
