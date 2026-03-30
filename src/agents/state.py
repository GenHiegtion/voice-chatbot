"""Shared state definition for the LangGraph multi-agent workflow."""

import operator
from typing import Annotated, Literal

from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """Shared state passed between all agents in the graph.

    Inherits from MessagesState which provides a `messages` field
    that automatically appends new messages.
    """

    # Which agent to route to next
    next_agent: Literal["menu_agent", "order_agent",
                        "promotion_agent", "FINISH"] = "FINISH"

    # Session ID for cart persistence
    session_id: str = ""
