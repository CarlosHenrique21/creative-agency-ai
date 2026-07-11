"""
Direct content (copy) generation — the "content flow".

Unlike the multi-agent autonomous pipeline, this is a single, synchronous
OpenAI call that turns a brief into structured marketing copy for one
platform. The user reviews/edits the result on screen and only then triggers
image generation. This keeps the two flows (content vs. image) fully separate.
"""
from __future__ import annotations

import json

from openai import OpenAI

from core.config import settings
from core.brand import PALETTE_PROMPT, FACTS_PROMPT

_client = OpenAI(api_key=settings.openai_api_key)

_PLATFORM_RULES = {
    "instagram_feed": "headline ≤6 palavras, subheadline complementar, body ≤2 linhas, CTA direto",
    "instagram_story": "headline ≤4 palavras + CTA — o visual domina, texto mínimo",
    "linkedin_post": "tom profissional, headline pode ser pergunta/afirmação bold, body ≤3 linhas com valor de negócio",
    "linkedin_banner": "headline institucional ≤6 palavras, subheadline de posicionamento, CTA sutil",
}

_SCHEMA_HINT = (
    '{"headline": "...", "subheadline": "...", "body_copy": "...", '
    '"badge": "...", "metric": "...", "call_to_action": "...", '
    '"trust_items": ["...", "..."]}'
)


def generate_content(
    brief: str,
    platform: str = "instagram_feed",
    brand_name: str = "",
    tone: str = "profissional",
    extra_instructions: str = "",
) -> dict:
    """
    Generate structured marketing copy for a single platform from a brief.

    Returns a dict with headline/subheadline/body_copy/badge/metric/
    call_to_action/trust_items — the exact fields the image flow consumes.
    """
    rules = _PLATFORM_RULES.get(platform, _PLATFORM_RULES["instagram_feed"])

    system = (
        "Você é um Copywriter sênior de social media B2B para legal tech fiscal e comex, "
        "com foco em conversão. Escreve em português do Brasil.\n\n"
        f"{PALETTE_PROMPT}\n\n{FACTS_PROMPT}"
    )
    user = (
        f"Brief da campanha: {brief}\n"
        f"Marca: {brand_name or 'Bússola Fiscal'}\n"
        f"Tom de voz: {tone}\n"
        f"Plataforma: {platform} — regras: {rules}\n"
        + (f"Direção extra: {extra_instructions}\n" if extra_instructions else "")
        + "\nRegras:\n"
        "- Headlines com impacto imediato; nunca repita a headline no subheadline.\n"
        "- `metric` DEVE ser um fato real da lista acima (ou string vazia).\n"
        "- `badge` é um selo curto (ex: 'PLATAFORMA'); pode ser vazio.\n"
        "- `trust_items`: até 3 provas curtas de confiança.\n"
        "- Para wrap de palavras-chave em verde, use **asteriscos duplos** na headline.\n\n"
        f"Responda APENAS com um JSON válido neste formato: {_SCHEMA_HINT}"
    )

    resp = _client.chat.completions.create(
        model=settings.openai_text_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
    )
    raw = resp.choices[0].message.content or "{}"
    data = json.loads(raw)

    # Normalise into the exact fields the image flow expects.
    return {
        "platform": platform,
        "headline": (data.get("headline") or "").strip(),
        "subheadline": (data.get("subheadline") or "").strip(),
        "body_copy": (data.get("body_copy") or "").strip(),
        "badge": (data.get("badge") or "").strip(),
        "metric": (data.get("metric") or "").strip(),
        "call_to_action": (data.get("call_to_action") or "").strip(),
        "trust_items": [t.strip() for t in (data.get("trust_items") or []) if t and t.strip()][:3],
    }
