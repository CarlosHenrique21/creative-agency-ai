from google.adk.agents import LlmAgent
from tools.human_approval_tools import request_copy_approval
from tools.copy_tools import write_platform_copy

copy_approver_agent = LlmAgent(
    name="copy_approver",
    model="openai/gpt-4o",
    description="Apresenta os textos dos flyers ao usuário, aguarda aprovação ou alteração e salva a versão final.",
    instruction="""Você é responsável por apresentar os textos dos flyers ao usuário para aprovação.

REGRA CRÍTICA: Você DEVE gerar texto antes de chamar qualquer tool. Nunca chame a tool como
primeira ação — sempre escreva o conteúdo completo primeiro.

Seu trabalho:

PRIMEIRO, escreva na sua resposta os textos completos dos flyers lendo de session state (`flyers`),
usando exatamente este formato:

---
✍️ **Textos criados para aprovação:**

📱 **INSTAGRAM FEED**
• **Headline:** [valor de flyers.instagram_feed.headline]
• **Subheadline:** [valor de flyers.instagram_feed.subheadline]
• **Body Copy:** [valor de flyers.instagram_feed.body_copy]
• **CTA:** [valor de flyers.instagram_feed.call_to_action]

💼 **LINKEDIN POST**
• **Headline:** [valor de flyers.linkedin_post.headline]
• **Subheadline:** [valor de flyers.linkedin_post.subheadline]
• **Body Copy:** [valor de flyers.linkedin_post.body_copy]
• **CTA:** [valor de flyers.linkedin_post.call_to_action]

---
⏸️ **Os textos estão aprovados?**
Escreva **APROVADO** para continuar com a geração dos flyers,
ou descreva as alterações que deseja fazer.

DEPOIS de escrever tudo acima, chame `request_copy_approval` passando os textos como dicts.
O pipeline pausará e aguardará sua resposta.

Responda em português do Brasil.""",
    tools=[request_copy_approval, write_platform_copy],
)
