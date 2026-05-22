from __future__ import annotations
import base64
from agents.base import BaseAgent
from core.config import settings
from core.state import CampaignState, FlyerSpec
from prompts.designer import SYSTEM_PROMPT, build_image_prompt


class DesignerAgent(BaseAgent):
    """Gera os prompts visuais e chama gpt-image-1 para criar cada flyer."""

    name = "designer"
    role = "Designer"

    async def run(self, state: CampaignState) -> dict:
        self.log.info("designing_flyers", count=len(state.flyers))

        flyers: dict[str, FlyerSpec] = dict(state.flyers)

        for platform_key, spec in flyers.items():
            image_prompt = await self._build_visual_prompt(spec, state)
            spec.image_prompt = image_prompt

            self.log.info("generating_image", platform=platform_key)
            b64, url = await self._generate_image(spec, image_prompt)
            spec.image_b64 = b64
            spec.image_url = url

        return {
            "flyers": flyers,
            "messages": self._message(f"Imagens geradas para {len(flyers)} plataformas."),
        }

    async def _build_visual_prompt(self, spec: FlyerSpec, state: CampaignState) -> str:
        user_prompt = f"""
Direção criativa: {state.creative_direction}
Plataforma: {spec.platform.value} ({spec.width}x{spec.height}px)
Headline: {spec.headline}
Subheadline: {spec.subheadline}
Call to action: {spec.call_to_action}
Marca: {state.brand.name}
Cores: {state.brand.primary_color} / {state.brand.secondary_color} / {state.brand.accent_color}
Estilo: {state.brand.font_style}, tom {state.brand.tone}

Crie um prompt detalhado para gerar esta imagem com gpt-image-1.
"""
        return await self._chat(SYSTEM_PROMPT, user_prompt)

    async def _generate_image(self, spec: FlyerSpec, prompt: str) -> tuple[str, str]:
        size = self._map_size(spec.width, spec.height)
        response = await self.client.images.generate(
            model=settings.image_model,
            prompt=build_image_prompt(prompt, spec),
            n=1,
            size=size,
            quality=settings.image_quality,  # type: ignore[arg-type]
            response_format="b64_json",
        )
        item = response.data[0]
        b64 = item.b64_json or ""
        url = item.url or ""
        return b64, url

    @staticmethod
    def _map_size(width: int, height: int) -> str:
        ratio = width / height
        if 0.9 <= ratio <= 1.1:
            return "1024x1024"
        if ratio > 1.5:
            return "1792x1024"
        return "1024x1792"
