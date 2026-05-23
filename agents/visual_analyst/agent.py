from google.adk.agents import LlmAgent
from tools.visual_analysis_tools import analyze_brand_images

visual_analyst_agent = LlmAgent(
    name="visual_analyst",
    model="openai/gpt-4o",
    description="Analisa as imagens de referência da marca com Vision e gera uma especificação visual completa para o designer usar.",
    instruction="""Você é um Art Director especialista em identidade visual de marcas SaaS/Fintech.

1. Chame `analyze_brand_images` com o brand_id de session state.
2. Quando concluir, escreva APENAS: "✅ Visual spec gerada e salva em session state."

Não exiba o conteúdo da spec — ela está em session state para o designer usar diretamente.
Responda em português do Brasil.""",
    tools=[analyze_brand_images],
)
