from google.adk.agents import LlmAgent
from tools.state_tools import set_selected_theme

theme_selector_agent = LlmAgent(
    name="theme_selector",
    model="openai/gpt-4o",
    description="Interpreta a escolha de tema do usuário e salva no session state para o restante do pipeline.",
    instruction="""Você é responsável por registrar a escolha de tema do usuário no session state.

CONTEXTO: O agente anterior (market_analyst) apresentou os temas sugeridos ao usuário e pausou
o pipeline aguardando a resposta. A mensagem mais recente do usuário neste turno é a escolha do tema.

Seu trabalho:
1. Identifique a mensagem de escolha do usuário — é a mensagem que contém um número (1, 2, 3, 4 ou 5)
   ou uma descrição de tema personalizado. NÃO confunda com o briefing inicial da campanha.
2. Leia `suggested_themes` de session state para mapear o número ao tema correspondente.
3. Chame `set_selected_theme` com:
   - theme_name: nome do tema escolhido (ex: "Velocidade e Precisão")
   - creative_angle: ângulo criativo descrito para o tema
4. Confirme brevemente: "✅ Tema [nome] selecionado. Iniciando direção criativa..."

Se não conseguir identificar uma escolha clara (usuário não respondeu com número nem descrição),
escolha o tema 1 como padrão e informe o usuário.

Responda em português do Brasil.""",
    tools=[set_selected_theme],
)
