"""LangGraph workflow definition for the multi-agent chatbot."""

import logging

from langgraph.graph import StateGraph, END

from src.agents.state import AgentState
from src.agents.coordinator import create_coordinator_node
from src.teams.data_team import create_data_team_node
from src.teams.action_team import create_action_team_node
from src.agents.menu_agent import create_menu_agent_node
from src.agents.order_agent import create_order_agent_node
from src.agents.promotion_agent import create_promotion_agent_node
from src.config import get_llm

logger = logging.getLogger(__name__)


def _route_after_coordinator(state: AgentState) -> str:
    """Conditional edge: route from top coordinator to team-level node."""
    session_id = state.get("session_id", "")
    next_agent = state.get("next_agent", "FINISH")
    destination = "END" if next_agent == "FINISH" else next_agent
    logger.info(
        "FLOW interaction.handoff session_id=%s from=coordinator to=%s",
        session_id,
        destination,
    )
    if next_agent == "FINISH":
        return END
    return next_agent


def _route_after_data_team(state: AgentState) -> str:
    """Conditional edge: route from data team to information sub-agents."""
    session_id = state.get("session_id", "")
    next_agent = state.get("next_agent", "FINISH")
    destination = "END" if next_agent == "FINISH" else next_agent
    logger.info(
        "FLOW interaction.handoff session_id=%s from=data_team to=%s",
        session_id,
        destination,
    )
    if next_agent == "FINISH":
        return END
    return next_agent


def _route_after_action_team(state: AgentState) -> str:
    """Conditional edge: route from action team to action sub-agents."""
    session_id = state.get("session_id", "")
    next_agent = state.get("next_agent", "FINISH")
    destination = "END" if next_agent == "FINISH" else next_agent
    logger.info(
        "FLOW interaction.handoff session_id=%s from=action_team to=%s",
        session_id,
        destination,
    )
    if next_agent == "FINISH":
        return END
    return next_agent


def build_graph():
    """Build and compile the multi-agent LangGraph workflow.

    Flow:
                START → coordinator → (conditional) → data_team / action_team → (conditional) → leaf agents → END
                    ↓
                  FINISH → END
    """
    llm = get_llm()

    # Create the state graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("coordinator", create_coordinator_node(llm))
    graph.add_node("data_team", create_data_team_node(llm))
    graph.add_node("action_team", create_action_team_node(llm))
    graph.add_node("menu_agent", create_menu_agent_node(llm))
    graph.add_node("order_agent", create_order_agent_node(llm))
    graph.add_node("promotion_agent", create_promotion_agent_node(llm))

    # Set entry point
    graph.set_entry_point("coordinator")

    # Add conditional edges from coordinator
    graph.add_conditional_edges(
        "coordinator",
        _route_after_coordinator,
        {
            "data_team": "data_team",
            "action_team": "action_team",
            END: END,
        },
    )

    # Route from data team to data sub-agents
    graph.add_conditional_edges(
        "data_team",
        _route_after_data_team,
        {
            "menu_agent": "menu_agent",
            "promotion_agent": "promotion_agent",
            END: END,
        },
    )

    # Route from action team to action sub-agents
    graph.add_conditional_edges(
        "action_team",
        _route_after_action_team,
        {
            "order_agent": "order_agent",
            END: END,
        },
    )

    # Route from menu_agent back to END (it handles cart updates internally)
    graph.add_edge("menu_agent", END)
    graph.add_edge("order_agent", END)
    graph.add_edge("promotion_agent", END)

    # Compile the graph
    compiled = graph.compile()
    return compiled


# Singleton graph instance
_graph = None


def get_graph():
    """Get or create the compiled graph singleton."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
