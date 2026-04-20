"""Shared state definition for the LangGraph multi-agent workflow."""

from typing import Literal

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
