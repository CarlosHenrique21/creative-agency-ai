from __future__ import annotations
from agents.base import BaseAgent
from core.state import CampaignState
from prompts.social_media_manager import SYSTEM_PROMPT


class SocialMediaManagerAgent(BaseAgent):
    """Revisa os flyers sob a ótica das melhores práticas de cada plataforma."""

    name = "social_media_manager"
    role = "Social Media Manager"

    async def run(self, state: CampaignState) -> dict:
        self.log.info("reviewing_platform_fit", platforms=len(state.flyers))

        feedback_parts: list[str] = []

        for platform_key, spec in state.flyers.items():
            user_prompt = f"""
Plataforma: {platform_key}
Headline: {spec.headline}
Subheadline: {spec.subheadline}
Body copy: {spec.body_copy}
CTA: {spec.call_to_action}
Image prompt usado: {spec.image_prompt}

Avalie se este flyer segue as melhores práticas da plataforma {platform_key}.
Forneça feedback específico e acionável. Se está aprovado, diga "APROVADO".
"""
            feedback = await self._chat(SYSTEM_PROMPT, user_prompt)
            feedback_parts.append(f"[{platform_key}] {feedback}")

        full_feedback = "\n\n".join(feedback_parts)
        return {"messages": self._message(full_feedback)}
