"""
ADK tools: query the Brand RAG and Visual RAG stores.
Both stores are synchronous (ChromaDB queries are blocking).
"""
from __future__ import annotations

from google.adk.tools import ToolContext

from rag.dependencies import brand_store, visual_store


def query_brand_knowledge(query: str, tool_context: ToolContext) -> str:
    """
    Retrieve relevant chunks from the brand's document knowledge base (ChromaDB).
    Returns concatenated text passages from brand guides, briefs, and style docs.

    Args:
        query: natural-language question or topic to search for
        tool_context: ADK tool context (provides session state)

    Returns:
        Relevant brand document passages as a single string, or empty string
        if no brand_id is set or no documents have been ingested.
    """
    brand_id: str = tool_context.state.get("brand_id", "")
    if not brand_id:
        return ""

    context = brand_store.query(brand_id, query, k=6)

    # Cache in session so other agents don't need to re-query
    tool_context.state["brand_rag_context"] = context
    return context


def query_visual_references(query: str, tool_context: ToolContext) -> str:
    """
    Retrieve a visual style guide derived from the brand's reference images.
    Each image was previously analysed by GPT-4o Vision; the style descriptions
    are stored as embeddings and retrieved by semantic similarity.

    Args:
        query: description of the desired visual mood or content
        tool_context: ADK tool context (provides session state)

    Returns:
        Visual style guide string with keywords ready to inject into an
        image-generation prompt, or empty string if no images are ingested.
    """
    brand_id: str = tool_context.state.get("brand_id", "")
    if not brand_id:
        return ""

    context = visual_store.query(brand_id, query, k=3)

    tool_context.state["visual_rag_context"] = context
    return context
