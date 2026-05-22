from __future__ import annotations
import json, re
from agents.base import BaseAgent
from core.state import CampaignState, QualityScore, FlyerSpec
from prompts.quality_reviewer import SYSTEM_PROMPT


class QualityReviewerAgent(BaseAgent):
    """Atribui notas objetivas e decide se os flyers estão aprovados ou precisam de revisão."""

    name = "quality_reviewer"
    role = "Quality Reviewer"

    async def run(self, state: CampaignState) -> dict:
        self.log.info("reviewing_quality", cycle=state.revision_cycle)

        quality_scores: dict[str, QualityScore] = {}
        flyers: dict[str, FlyerSpec] = dict(state.flyers)

        smm_feedback = next(
            (m.content for m in reversed(state.messages) if m.agent == "social_media_manager"),
            "",
        )

        for platform_key, spec in flyers.items():
            user_prompt = f"""
Plataforma: {platform_key}
Headline: {spec.headline}
Subheadline: {spec.subheadline}
Body copy: {spec.body_copy}
CTA: {spec.call_to_action}
Feedback do Social Media Manager: {smm_feedback}
Marca: {state.brand.name} | Tom: {state.brand.tone}

Avalie de 0 a 10 cada critério e retorne EXATAMENTE este JSON:
{{
  "brand_consistency": <int>,
  "visual_appeal": <int>,
  "copy_clarity": <int>,
  "platform_fit": <int>,
  "feedback": "<string>",
  "revision_notes": "<notas específicas para revisão se necessário>"
}}
"""
            raw = await self._chat(SYSTEM_PROMPT, user_prompt)
            match = re.search(r"\{.*\}", raw, re.DOTALL)

            if match:
                data = json.loads(match.group())
                score = QualityScore(
                    brand_consistency=data.get("brand_consistency", 5),
                    visual_appeal=data.get("visual_appeal", 5),
                    copy_clarity=data.get("copy_clarity", 5),
                    platform_fit=data.get("platform_fit", 5),
                    feedback=data.get("feedback", ""),
                )
                score.calculate_overall()
                quality_scores[platform_key] = score

                if not score.approved:
                    spec.revision_notes = data.get("revision_notes", score.feedback)
                    flyers[platform_key] = spec

        all_approved = all(s.approved for s in quality_scores.values())
        return {
            "quality_scores": quality_scores,
            "flyers": flyers,
            "revision_cycle": state.revision_cycle + (0 if all_approved else 1),
            "status": "completed" if all_approved else "needs_revision",
            "messages": self._message(
                f"Revisão ciclo {state.revision_cycle}: "
                f"{'todos aprovados' if all_approved else 'revisão necessária'}"
            ),
        }
