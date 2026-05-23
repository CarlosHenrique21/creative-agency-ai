"""
Human-in-the-loop tools usando LongRunningFunctionTool do ADK.
O pipeline pausa e aguarda a próxima mensagem do usuário como resposta.
"""
from __future__ import annotations

from google.adk.tools import ToolContext
from google.adk.tools.long_running_tool import LongRunningFunctionTool


def _request_theme_selection(
    market_summary: str,
    suggested_themes: list[str],
    tool_context: ToolContext,
) -> dict:
    """
    Apresenta o resumo de mercado e os temas sugeridos ao usuário
    e aguarda que ele escolha um tema para a campanha.

    Args:
        market_summary: resumo das tendências e nicho pesquisados
        suggested_themes: lista de 3-5 temas sugeridos para a campanha
        tool_context: ADK tool context

    Returns:
        Pending status — o resultado real vem na próxima mensagem do usuário.
    """
    tool_context.state["pending_theme_selection"] = True
    tool_context.state["suggested_themes"] = suggested_themes
    tool_context.state["market_summary"] = market_summary
    tool_context.actions.skip_summarization = True
    return {
        "status": "awaiting_user_theme_selection",
        "message": "Aguardando o usuário escolher um tema.",
    }


def _request_copy_approval(
    instagram_copy: dict,
    linkedin_copy: dict,
    tool_context: ToolContext,
) -> dict:
    """
    Apresenta os textos dos flyers ao usuário e aguarda aprovação ou alteração.

    Args:
        instagram_copy: dict com headline, subheadline, body_copy, call_to_action do Instagram
        linkedin_copy: dict com headline, subheadline, body_copy, call_to_action do LinkedIn
        tool_context: ADK tool context

    Returns:
        Pending status — o resultado real vem na próxima mensagem do usuário.
    """
    tool_context.state["pending_copy_approval"] = True
    tool_context.state["copy_for_approval"] = {
        "instagram": instagram_copy,
        "linkedin": linkedin_copy,
    }
    tool_context.actions.skip_summarization = True
    return {
        "status": "awaiting_user_copy_approval",
        "message": "Aguardando aprovação ou alteração dos textos pelo usuário.",
    }


# Wrap as LongRunningFunctionTool — pausa o pipeline até o próximo turno do usuário
request_theme_selection = LongRunningFunctionTool(func=_request_theme_selection)
request_copy_approval = LongRunningFunctionTool(func=_request_copy_approval)
