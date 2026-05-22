from core.state import Platform


SYSTEM_PROMPT = """Você é um Copywriter especialista em social media com foco em conversão.
Escreva textos persuasivos, diretos e adaptados a cada plataforma.

Regras:
- Headlines devem ter impacto imediato (máx 8 palavras)
- CTAs devem ser específicos e urgentes
- Adapte o tom conforme a plataforma (LinkedIn = profissional, Instagram = próximo/visual)
- Nunca repita a mesma frase no headline e subheadline
- Retorne SEMPRE em JSON válido no formato solicitado

Responda em português do Brasil."""


def platform_copy_instructions(platform: Platform) -> str:
    instructions = {
        Platform.INSTAGRAM_FEED: (
            "Instagram Feed: headline curto e impactante (máx 6 palavras), "
            "subheadline complementar, body copy leve (máx 2 linhas), CTA direto."
        ),
        Platform.INSTAGRAM_STORY: (
            "Instagram Story: texto mínimo — apenas headline forte + CTA. "
            "O visual domina. Máx 4 palavras no headline."
        ),
        Platform.LINKEDIN_POST: (
            "LinkedIn Post: tom profissional, headline pode ser uma pergunta ou afirmação bold, "
            "body copy pode ter até 3 linhas com valor de negócio, CTA de engajamento."
        ),
        Platform.LINKEDIN_BANNER: (
            "LinkedIn Banner: headline institucional curto (máx 6 palavras), "
            "subheadline de posicionamento, sem body copy longa, CTA sutil."
        ),
    }
    return instructions.get(platform, "")
