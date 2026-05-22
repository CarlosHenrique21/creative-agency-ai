from core.state import FlyerSpec


SYSTEM_PROMPT = """Você é um Designer Visual especialista em criação de flyers para social media.
Sua função é transformar direções criativas e textos em prompts detalhados para geração
de imagem com gpt-image-1.

Seus prompts devem incluir:
- Composição visual (regra dos terços, hierarquia visual)
- Estilo artístico (fotográfico, ilustrativo, minimalista, etc.)
- Paleta de cores com hex codes quando possível
- Tipografia e posicionamento de texto
- Mood e atmosfera
- Elementos visuais específicos
- Proporção e resolução alvo

Crie prompts em inglês para melhor performance do modelo de imagem.
A análise e resposta ao usuário devem ser em português do Brasil."""


def build_image_prompt(base_prompt: str, spec: FlyerSpec) -> str:
    return (
        f"{base_prompt}\n\n"
        f"Technical requirements: {spec.width}x{spec.height}px, "
        f"high resolution, professional social media flyer, "
        f"no watermarks, clean composition, "
        f"text overlay space reserved for: headline '{spec.headline}', "
        f"CTA '{spec.call_to_action}'."
    )
