from google.adk.agents import LlmAgent
from tools.state_tools import apply_copy_changes

copy_reviewer_agent = LlmAgent(
    name="copy_reviewer",
    model="openai/gpt-4o",
    description="Processa a resposta do usuário sobre os textos: aprova direto ou aplica as alterações solicitadas e exibe os textos finais.",
    instruction="""Você processa a resposta do usuário sobre os textos dos flyers.

Seu trabalho:
1. Leia a última mensagem do usuário.

CASO A — Usuário aprovou (escreveu "APROVADO", "aprovado", "ok", "sim" ou similar):
   - Marque `copy_approved = True` em session state via `apply_copy_changes`
     passando os textos existentes sem alteração (leia de `flyers` em session state)
   - Confirme: "✅ Textos aprovados! Iniciando a geração dos flyers..."

CASO B — Usuário solicitou alterações:
   - Interprete cada alteração pedida
   - Chame `apply_copy_changes` para cada plataforma com os textos atualizados
   - Exiba os textos revisados no mesmo formato:

     📱 INSTAGRAM FEED (revisado)
     • Headline: [novo texto]
     • Subheadline: [novo texto]
     • Body Copy: [novo texto]
     • CTA: [novo texto]

     💼 LINKEDIN POST (revisado)
     • Headline: [novo texto]
     • (etc.)

   - Confirme: "✅ Alterações aplicadas! Iniciando a geração dos flyers..."

Em ambos os casos, após confirmar, o pipeline continuará automaticamente com a geração das imagens.

Dados em session state: flyers, platforms.
Responda em português do Brasil.""",
    tools=[apply_copy_changes],
)
