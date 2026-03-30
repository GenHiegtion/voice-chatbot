"""LangGraph workflow definition for the multi-agent chatbot."""

from langgraph.graph import StateGraph, END

from src.agents.state import AgentState
from src.agents.coordinator import create_coordinator_node
from src.agents.menu_agent import create_menu_agent_node
from src.agents.order_agent import create_order_agent_node
from src.agents.promotion_agent import create_promotion_agent_node
from src.config import get_llm


def _route_after_coordinator(state: AgentState) -> str:
    """Conditional edge: route based on coordinator's decision."""
    next_agent = state.get("next_agent", "FINISH")
    if next_agent == "FINISH":
        return END
    return next_agent


def build_graph():
    """Build and compile the multi-agent LangGraph workflow.

    Flow:
        START → coordinator → (conditional) → menu_agent / order_agent / promotion_agent → END
                    ↓
                  FINISH → END
    """
    llm = get_llm()

    # Create the state graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("coordinator", create_coordinator_node(llm))
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
            "menu_agent": "menu_agent",
            "order_agent": "order_agent",
            "promotion_agent": "promotion_agent",
            END: END,
        },
    )

    # All sub-agents return to END after processing
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
