from __future__ import annotations
import base64
from agents.base import BaseAgent
from core.config import settings
from core.state import CampaignState, FlyerSpec
from prompts.designer import SYSTEM_PROMPT, build_image_prompt
from rag.logo_compositor import composite_logo, find_logo


class DesignerAgent(BaseAgent):
    """Gera os prompts visuais, chama gpt-image-1 e compõe a logo da marca."""

    name = "designer"
    role = "Designer"

    async def run(self, state: CampaignState) -> dict:
        has_logo = find_logo(state.brand_id) is not None
        self.log.info(
            "designing_flyers",
            count=len(state.flyers),
            has_visual_rag=bool(state.visual_rag_context),
            has_logo=has_logo,
        )

        flyers: dict[str, FlyerSpec] = dict(state.flyers)

        for platform_key, spec in flyers.items():
            image_prompt = await self._build_visual_prompt(spec, state)
            spec.image_prompt = image_prompt

            self.log.info("generating_image", platform=platform_key)
            b64, url = await self._generate_image(spec, image_prompt)

            # Composite logo on top of the generated flyer
            if state.brand_id:
                b64 = composite_logo(b64, state.brand_id, platform_key)

            spec.image_b64 = b64
            spec.image_url = url

        logo_note = " (logo aplicada)" if has_logo else " (sem logo — adicione em brand_assets/logo/)"
        return {
            "flyers": flyers,
            "messages": self._message(
                f"Imagens geradas para {len(flyers)} plataformas{logo_note}."
            ),
        }

    async def _build_visual_prompt(self, spec: FlyerSpec, state: CampaignState) -> str:
        visual_rag_section = ""
        if state.visual_rag_context:
            visual_rag_section = f"""
### Visual Style Guide (from brand reference images)
These visual references define the brand's visual DNA.
You MUST reflect this style in the image prompt:

{state.visual_rag_context}
"""

        logo_note = ""
        if state.brand_id and find_logo(state.brand_id):
            logo_note = (
                "\nIMPORTANT: Leave a clean, uncluttered area for the brand logo "
                "to be composited in post-processing. Do NOT generate a logo in the image."
            )

        user_prompt = f"""
Direção criativa: {state.creative_direction}
Plataforma: {spec.platform.value} ({spec.width}x{spec.height}px)
Headline: {spec.headline}
Subheadline: {spec.subheadline}
Call to action: {spec.call_to_action}
Marca: {state.brand.name}
Cores: {state.brand.primary_color} / {state.brand.secondary_color} / {state.brand.accent_color}
Estilo: {state.brand.font_style}, tom {state.brand.tone}
{visual_rag_section}{logo_note}
Crie um prompt detalhado em inglês para gerar esta imagem com gpt-image-1.
O prompt deve capturar fielmente o estilo visual da marca definido acima.
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
