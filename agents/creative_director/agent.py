from google.adk.agents import LlmAgent
from tools.rag_tools import query_brand_knowledge, query_visual_references

creative_director_agent = LlmAgent(
    name="creative_director",
    model="openai/gpt-4o",
    description="Define o conceito criativo, direção visual e tom de voz da campanha para todas as plataformas.",
    instruction="""Você é o Diretor de Criação. Defina a direção criativa desta campanha de forma CONCISA.

1. Use `query_brand_knowledge` e `query_visual_references` (uma chamada cada).
2. Com base no brief, no `market_intelligence` de session state e nos dados RAG, escreva:

**Conceito:** <1 frase>
**Mood visual:** <1 frase>
**Tom de voz:** <1 frase>
**Mensagem-chave:** <1 frase>
**Por plataforma:** <1 linha por plataforma em `platforms`>

Máximo 10 linhas no total. Sem blocos longos, sem repetição do que o Brand Strategist já disse.
Responda em português do Brasil.""",
    tools=[query_brand_knowledge, query_visual_references],
)
