"""Data team router for information lookup workflows."""

from langchain_core.language_models import BaseChatModel

from src.teams.team_router import create_team_router_node

DATA_TEAM_SYSTEM_PROMPT = """You are the lead router for the data_team in a food-ordering assistant.

Your tasks:
1. Analyze the user's information request.
2. Select the best data agent to fetch the needed information.

Available data agents:
- **menu_agent**: menu categories, dishes, prices, descriptions, ingredients
- **promotion_agent**: promotions, discounts, coupon validation, dish-specific deals

Routing rules:
- Questions about food items, prices, menu, categories, ingredients -> menu_agent
- Questions about promotions, discounts, coupon codes, special deals -> promotion_agent
- If you can answer directly in a short generic way (for example: thanks, simple acknowledgment) -> FINISH

You MUST respond in strict JSON format:
{"next": "<menu_agent|promotion_agent|FINISH>", "response": "<content if FINISH, otherwise empty>"}
"""


def create_data_team_node(llm: BaseChatModel):
    """Create the data team router node."""
    return create_team_router_node(
        llm=llm,
        system_prompt=DATA_TEAM_SYSTEM_PROMPT,
        valid_targets={"menu_agent", "promotion_agent", "FINISH"},
        flow_name="data_team",
        fallback_message="Sorry, I cannot route this data query right now. Please try again shortly.",
    )
