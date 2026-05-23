"""
Tool: analyze_brand_images
Analisa cada imagem de referência da marca com GPT-4o Vision e gera
uma especificação visual completa salva em session state como `visual_spec`.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

from openai import OpenAI
from google.adk.tools import ToolContext

from core.config import settings

_client = OpenAI(api_key=settings.openai_api_key)

_IMAGES_DIR = Path("brand_assets/images")
_SUPPORTED = {".png", ".jpg", ".jpeg", ".webp"}

# Paleta oficial extraída do brand guide
_BRAND_PALETTE = """
PALETA OFICIAL BUSSOLA FISCAL:
Verdes Principais:
  #052A10 — Verde Floresta (cor principal, backgrounds primários)
  #0B4A1E — Verde Profundo (fundos secundários)
  #1A7A3A — Verde Médio (botões, ícones)
  #2DA84F — Verde Brilhante (CTAs, highlights)
  #4DC76A — Verde Claro (bordas suaves, accents)

Acentos Dourados:
  #C8931A — Dourado Principal
  #D4820A — Dourado Escuro
  #E8B040 — Dourado Claro

Neutros:
  #FFFFFF — Branco puro (texto principal)
  #E8EDEA — Cinza claro (texto secundário)
  #5C7063 — Cinza verde (texto terciário)
  #0A1A0D — Quase preto (fundo mais escuro)
"""

_VISION_PROMPT = f"""Você é um Art Director especialista em design de interfaces SaaS/Fintech.
Analise esta imagem de referência da marca BussolaFiscal com máxima precisão e retorne
um JSON com TODOS os elementos visuais identificados.

{_BRAND_PALETTE}

Retorne APENAS JSON válido com esta estrutura exata:
{{
  "background": {{
    "color": "<hex exato ou gradiente>",
    "texture": "<flat, subtle noise, radial gradient, etc.>",
    "notes": "<descrição detalhada>"
  }},
  "ui_chrome_elements": [
    "<liste TODOS os elementos de UI visíveis, ex: 'macOS window with red/yellow/green traffic light buttons', 'browser address bar', 'mobile status bar', etc.>"
  ],
  "cards_panels": [
    {{
      "type": "<card, panel, modal, tooltip, etc.>",
      "background_color": "<hex>",
      "border_color": "<hex ou 'none'>",
      "border_radius": "<sharp, medium, large, pill>",
      "shadow": "<none, soft, glow, etc.>",
      "content": "<o que está dentro do card>"
    }}
  ],
  "typography": {{
    "headline": {{
      "size": "<xs/sm/md/lg/xl/2xl — relativo ao layout>",
      "weight": "<regular/medium/semibold/bold/extrabold/black>",
      "color": "<hex>",
      "style": "<normal/italic>",
      "highlight_color": "<hex de palavras destacadas, se houver>"
    }},
    "body": {{
      "size": "<xs/sm/md>",
      "weight": "<regular/medium>",
      "color": "<hex>"
    }},
    "labels_badges": {{
      "case": "<uppercase/capitalize/normal>",
      "size": "<xs/sm>",
      "color": "<hex>",
      "letter_spacing": "<normal/wide/wider>"
    }}
  }},
  "buttons": [
    {{
      "type": "<primary/secondary/ghost/link>",
      "shape": "<rectangle/rounded/pill>",
      "background": "<hex ou 'transparent'>",
      "text_color": "<hex>",
      "border": "<hex ou 'none'>",
      "has_arrow": "<true/false>",
      "has_icon": "<true/false>",
      "label_example": "<texto do botão se visível>"
    }}
  ],
  "badges_pills": [
    {{
      "shape": "<pill/rounded/square>",
      "background": "<hex ou 'transparent'>",
      "border_color": "<hex ou 'none'>",
      "text_color": "<hex>",
      "content_example": "<texto do badge>"
    }}
  ],
  "icons": {{
    "style": "<outline, filled, duotone, emoji, etc.>",
    "color": "<hex>",
    "size": "<sm/md/lg>",
    "examples": ["<descrição de ícone visível>"]
  }},
  "data_elements": [
    "<elementos numéricos ou de dados visíveis, ex: '8501.52.10 em monospace verde', '131 regras NCM em branco bold', etc.>"
  ],
  "trust_social_proof": [
    "<elementos de prova social: checkmarks, badges, selos, depoimentos, etc.>"
  ],
  "layout_structure": {{
    "alignment": "<left/center/right/mixed>",
    "sections": ["<descreva as seções do layout de cima para baixo>"],
    "whitespace": "<tight/balanced/generous>",
    "grid": "<single column/two column/asymmetric/etc.>"
  }},
  "overall_style_keywords": ["<5-10 keywords em inglês para prompt de geração de imagem>"]
}}"""


def analyze_brand_images(tool_context: ToolContext) -> dict:
    """
    Analisa todas as imagens de referência da marca com GPT-4o Vision
    e gera uma especificação visual completa salva em session state.

    Returns:
        dict com o visual_spec consolidado e lista de imagens analisadas
    """
    brand_id: str = tool_context.state.get("brand_id", "")
    images_dir = _IMAGES_DIR

    image_files = sorted([
        f for f in images_dir.iterdir()
        if f.is_file() and f.suffix.lower() in _SUPPORTED
    ])

    if not image_files:
        return {"error": f"Nenhuma imagem encontrada em {images_dir}", "analyzed": 0}

    analyses: list[dict] = []

    for img_path in image_files:
        b64 = base64.b64encode(img_path.read_bytes()).decode()
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(
            img_path.suffix.lstrip(".").lower(), "image/png"
        )

        response = _client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"},
                        },
                        {"type": "text", "text": _VISION_PROMPT},
                    ],
                }
            ],
            temperature=0.1,
            max_tokens=2000,
        )

        raw = response.choices[0].message.content or "{}"
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        try:
            analysis = json.loads(raw)
            analysis["_source_image"] = img_path.name
            analyses.append(analysis)
        except json.JSONDecodeError:
            analyses.append({"_source_image": img_path.name, "_raw": raw})

    # Consolidate into a single visual spec
    visual_spec = _consolidate(analyses)

    # Save to session state
    tool_context.state["visual_spec"] = visual_spec
    tool_context.state["visual_spec_raw"] = analyses

    return {
        "analyzed": len(analyses),
        "images": [a.get("_source_image", "?") for a in analyses],
        "visual_spec_summary": {
            "background": visual_spec.get("background", {}),
            "ui_chrome": visual_spec.get("ui_chrome_elements", []),
            "button_styles": len(visual_spec.get("buttons", [])),
            "style_keywords": visual_spec.get("overall_style_keywords", []),
        },
        "status": "success",
    }


def _consolidate(analyses: list[dict]) -> dict:
    """Merge multiple image analyses into a single authoritative visual spec."""

    # Collect all elements across images
    all_ui_chrome: list[str] = []
    all_cards: list[dict] = []
    all_buttons: list[dict] = []
    all_badges: list[dict] = []
    all_data_elements: list[str] = []
    all_trust: list[str] = []
    all_keywords: list[str] = []
    all_icons: list[str] = []

    bg_color = "#052A10"  # default from brand guide
    headline_color = "#FFFFFF"
    headline_highlight = "#2DA84F"
    headline_weight = "extrabold"
    body_color = "#E8EDEA"

    for a in analyses:
        if not isinstance(a, dict):
            continue

        # Background — prefer darkest
        bg = a.get("background", {})
        if isinstance(bg, dict) and bg.get("color"):
            bg_color = bg["color"]

        # UI chrome (macOS window, etc.)
        chrome = a.get("ui_chrome_elements", [])
        if isinstance(chrome, list):
            all_ui_chrome.extend(chrome)

        # Cards
        cards = a.get("cards_panels", [])
        if isinstance(cards, list):
            all_cards.extend(cards)

        # Typography
        typo = a.get("typography", {})
        if isinstance(typo, dict):
            h = typo.get("headline", {})
            if isinstance(h, dict):
                if h.get("color"):
                    headline_color = h["color"]
                if h.get("highlight_color"):
                    headline_highlight = h["highlight_color"]
                if h.get("weight"):
                    headline_weight = h["weight"]
            b = typo.get("body", {})
            if isinstance(b, dict) and b.get("color"):
                body_color = b["color"]

        # Buttons
        btns = a.get("buttons", [])
        if isinstance(btns, list):
            all_buttons.extend(btns)

        # Badges
        badges = a.get("badges_pills", [])
        if isinstance(badges, list):
            all_badges.extend(badges)

        # Icons
        icons = a.get("icons", {})
        if isinstance(icons, dict):
            all_icons.extend(icons.get("examples", []))

        # Data elements
        data = a.get("data_elements", [])
        if isinstance(data, list):
            all_data_elements.extend(data)

        # Trust
        trust = a.get("trust_social_proof", [])
        if isinstance(trust, list):
            all_trust.extend(trust)

        # Keywords
        kws = a.get("overall_style_keywords", [])
        if isinstance(kws, list):
            all_keywords.extend(kws)

    # Deduplicate preserving order
    def dedup(lst: list) -> list:
        seen: set = set()
        out = []
        for x in lst:
            k = json.dumps(x, sort_keys=True) if isinstance(x, dict) else str(x)
            if k not in seen:
                seen.add(k)
                out.append(x)
        return out

    return {
        "brand_palette": {
            "primary_bg": "#052A10",
            "secondary_bg": "#0B4A1E",
            "mid_green": "#1A7A3A",
            "cta_green": "#2DA84F",
            "light_green": "#4DC76A",
            "white": "#FFFFFF",
            "light_gray": "#E8EDEA",
            "muted": "#5C7063",
        },
        "background": {
            "color": bg_color,
            "texture": "deep dark green, subtle radial gradient lighter at center",
        },
        "ui_chrome_elements": dedup(all_ui_chrome),
        "cards_panels": dedup(all_cards),
        "typography": {
            "headline": {
                "color": headline_color,
                "weight": headline_weight,
                "highlight_color": headline_highlight,
                "style": "extra-bold sans-serif, very large, high contrast",
            },
            "body": {
                "color": body_color,
                "style": "regular sans-serif, smaller",
            },
        },
        "buttons": dedup(all_buttons),
        "badges_pills": dedup(all_badges),
        "icons": dedup(all_icons),
        "data_elements": dedup(all_data_elements),
        "trust_social_proof": dedup(all_trust),
        "overall_style_keywords": dedup(all_keywords),
    }
