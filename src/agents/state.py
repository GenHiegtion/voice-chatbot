"""Shared state definition for the LangGraph multi-agent workflow."""

from typing import Any, Literal, Optional

from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """Shared state passed between all agents in the graph.

    Inherits from MessagesState which provides a `messages` field
    that automatically appends new messages.
    """

    # Which node to route to next in the graph.
    next_agent: Literal[
        "data_team",
        "action_team",
        "menu_agent",
        "promotion_agent",
        "order_agent",
        "FINISH",
    ] = "FINISH"

    # Session ID for cart persistence
    session_id: str = ""

    # Lightweight data-team context for follow-up questions.
    last_topic: Literal["menu", "promotion", "action", ""] = ""
    last_product_id: int | None = None

    # Cart from the App (sent with each request)
    current_cart: list[dict[str, Any]] = []

    # Output cart action fields
    action: str = "None"
    action_data: Optional[list[dict[str, Any]]] = None
