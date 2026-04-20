"""Action team router for order execution workflows."""

from langchain_core.language_models import BaseChatModel

from src.teams.team_router import create_team_router_node

ACTION_TEAM_SYSTEM_PROMPT = """You are the lead router for the action_team in a food-ordering assistant.

Your tasks:
1. Analyze the user's action request.
2. Select the best action agent to execute that request.

Available action agents:
- **order_agent**: add/remove/update cart items, view cart, place order

Routing rules:
- If the user asks for cart or ordering actions -> order_agent
- If it is not an action request (for example only asking for information) -> FINISH with a short direct response

You MUST respond in strict JSON format:
{"next": "<order_agent|FINISH>", "response": "<content if FINISH, otherwise empty>"}
"""


def create_action_team_node(llm: BaseChatModel):
    """Create the action team router node."""
    return create_team_router_node(
        llm=llm,
        system_prompt=ACTION_TEAM_SYSTEM_PROMPT,
        valid_targets={"order_agent", "FINISH"},
        flow_name="action_team",
        fallback_message="Sorry, I cannot route this action request right now. Please try again shortly.",
    )
